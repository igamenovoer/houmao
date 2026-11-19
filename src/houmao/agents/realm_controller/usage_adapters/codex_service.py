"""Read provider response charges for one verified Codex app-server turn."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.usage_adapters import UsageAdapter
from houmao.agents.realm_controller.usage_adapters.common import (
    mapping,
    verify_service_turn_receipt,
)
from houmao.agents.realm_controller.usage_models import (
    UsageObservation,
    UsageTurnSnapshot,
    opaque_usage_reference,
)

_MAX_SCAN = 64 << 20
_MAX_ROW = 8 << 20
_TERMINAL_TYPES = {
    "completed": {"task_complete"},
    "failed": {"task_complete", "turn_failed", "task_failed"},
    "interrupted": {"turn_aborted", "task_aborted", "turn_interrupted"},
}


def read_codex_service_usage(
    *,
    snapshot: UsageTurnSnapshot,
    home: Path,
    receipt: dict[str, Any],
    process: dict[str, Any],
    outcome: str,
) -> tuple[str, list[UsageObservation]]:
    """Read only exact response IDs between the saved turn's start and terminal."""

    thread_id, turn_id = verify_service_turn_receipt(snapshot, receipt, process, outcome)
    rollout = receipt.get("rollout_path")
    workspace = snapshot.metadata.get("service_working_directory")
    start = receipt.get("rollout_baseline_offset", 0)
    if not isinstance(rollout, str) or not workspace or type(start) is not int or start < 0:
        raise ValueError("Codex accounting receipt lacks a qualified rollout")
    path = Path(rollout)
    if (
        not path.is_relative_to(home / "sessions")
        or path != path.resolve(strict=True)
        or not path.name.endswith(f"-{thread_id}.jsonl")
    ):
        raise ValueError("Codex accounting rollout is outside the selected home or thread")

    adapter = UsageAdapter.from_provider("codex", thread_id)
    source = opaque_usage_reference(rollout)
    observations: list[UsageObservation] = []
    launched = False
    with path.open("rb") as journal:
        header = journal.readline(_MAX_ROW)
        if not header.endswith(b"\n"):
            raise ValueError("Incomplete Codex accounting rollout header")
        meta = mapping(json.loads(header))
        native = mapping(meta.get("payload"))
        if (
            meta.get("type") != "session_meta"
            or native.get("id") != thread_id
            or native.get("cwd") != workspace
        ):
            raise ValueError("Codex accounting rollout changed its thread or workspace")
        adapter.parse(meta, source_ref=f"{source}:0")
        journal.seek(max(start, len(header)))
        limit = journal.tell() + _MAX_SCAN
        while (offset := journal.tell()) < limit:
            line = journal.readline(min(_MAX_ROW, limit - offset))
            if not line.endswith(b"\n"):
                break
            message = mapping(json.loads(line))
            row = mapping(message.get("payload"))
            if row.get("turn_id") != turn_id:
                continue
            if message.get("type") == "event_msg":
                event = row.get("type")
                if event == "task_started":
                    launched = True
                elif launched and isinstance(event, str) and event in _TERMINAL_TYPES[outcome]:
                    return turn_id, observations
            elif launched and message.get("type") == "turn_context":
                adapter.parse(message, source_ref=f"{source}:{offset}")
            elif (
                launched
                and message.get("type") == "token_usage_record"
                and row.get("thread_id") == thread_id
                and row.get("root_turn_id") == turn_id
            ):
                measured = adapter.parse(
                    message, source_ref=f"{source}:{offset}", binding_id=snapshot.binding_id
                )
                observations.extend(
                    item for item in measured if item.measurement_scope == "request"
                )
    raise ValueError("Codex accounting rollout lacks the exact terminal interval")
