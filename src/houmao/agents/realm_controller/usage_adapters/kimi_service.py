"""Read accounting records inside one certified Kimi ACP journal interval."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.usage_adapters import UsageAdapter
from houmao.agents.realm_controller.usage_adapters.common import (
    text_id,
    verify_service_turn_receipt,
)
from houmao.agents.realm_controller.usage_models import (
    UsageObservation,
    UsageTurnSnapshot,
    opaque_usage_reference,
)

_MAX_INTERVAL = 64 << 20
_MAX_ROW = 4 << 20
_JOURNAL_TERMINALS = {"completed": "completed", "failed": "failed", "interrupted": "cancelled"}


def read_kimi_service_usage(
    *,
    snapshot: UsageTurnSnapshot,
    home: Path,
    receipt: dict[str, Any],
    process: dict[str, Any],
    outcome: str,
) -> tuple[str, list[UsageObservation]]:
    """Validate the owner receipt and read only its bounded main-turn rows."""

    session_id, native_turn_id = verify_service_turn_receipt(snapshot, receipt, process, outcome)
    native_prompt_id = text_id(receipt.get("native_prompt_id"))
    if native_prompt_id is None:
        raise ValueError("Kimi accounting receipt lacks a native prompt identity")

    source = receipt.get("journal_path")
    start = receipt.get("journal_baseline_offset")
    end = receipt.get("journal_settled_offset")
    if (
        not isinstance(source, str)
        or type(start) is not int
        or type(end) is not int
        or start < 0
        or not 0 < end - start <= _MAX_INTERVAL
    ):
        raise ValueError("Invalid Kimi accounting journal interval")
    path = Path(source)
    root = home / "sessions"
    if not path.is_relative_to(root) or path != path.resolve(strict=True):
        raise ValueError("Kimi accounting journal is outside the selected home")
    parts = path.relative_to(root).parts
    if len(parts) != 5 or parts[1:] != (session_id, "agents", "main", "wire.jsonl"):
        raise ValueError("Kimi accounting journal does not belong to the selected main session")

    version = snapshot.metadata.get("service_tool_version")
    adapter = UsageAdapter.from_provider(
        "kimi", session_id, provider_version=version if isinstance(version, str) else None
    )
    source_id = opaque_usage_reference(source)
    expected_reason = _JOURNAL_TERMINALS[outcome]
    launched = ended = settled = False
    observations: list[UsageObservation] = []
    with path.open("rb") as journal:
        stat = os.fstat(journal.fileno())
        if (
            stat.st_dev != receipt.get("journal_device")
            or stat.st_ino != receipt.get("journal_inode")
            or stat.st_size < end
        ):
            raise ValueError("Kimi accounting journal identity changed")
        journal.seek(start)
        while journal.tell() < end:
            offset = journal.tell()
            line = journal.readline(min(end - offset, _MAX_ROW))
            if not line.endswith(b"\n"):
                raise ValueError("Incomplete Kimi accounting journal record")
            row = json.loads(line)
            if not isinstance(row, dict) or row.get("agentId") != "main":
                continue
            kind = row.get("type")
            if not isinstance(kind, str):
                continue
            if kind == "turn.prompt":
                if (
                    launched
                    or text_id(row.get("turnId")) != native_turn_id
                    or row.get("promptId") != native_prompt_id
                ):
                    raise ValueError("Kimi accounting journal contains another turn")
                launched = True
            elif kind == "turn.ended" and launched:
                if (
                    ended
                    or text_id(row.get("turnId")) != native_turn_id
                    or row.get("reason") != expected_reason
                ):
                    raise ValueError("Kimi accounting journal terminal does not match")
                ended = True
            elif kind in {"prompt.completed", "prompt.aborted"}:
                settled |= launched and row.get("promptId") == native_prompt_id
                continue
            elif kind != "usage.record" or not launched or ended or row.get("usageScope") != "turn":
                continue
            if kind == "usage.record" and not (
                text_id(row.get("requestId")) or text_id(row.get("id"))
            ):
                # This native build writes one usage row per request without its provider ID.
                row["requestId"] = f"kimi-{source_id}-{offset}"
            observed = adapter.parse(
                row, source_ref=f"{source_id}:{offset}", binding_id=snapshot.binding_id
            )
            observations.extend(
                item for item in observed if item.provider_turn_id == native_turn_id
            )
    if not (launched and ended and settled):
        raise ValueError("Kimi accounting terminal interval is incomplete")
    return native_turn_id, observations
