"""Arm C event-store inventory: codex rollout streams vs recording timeline.

Codex writes one rollout JSONL per session under ``<CODEX_HOME>/sessions/``
with top-level record types (``session_meta``, ``event_msg``, ``response_item``,
``turn_context``, …) and lifecycle payload types (``task_started``,
``task_complete``, ``item_completed``, …). This module inventories the rollout
files overlapping one campaign recording's time window and aligns lifecycle
events to the recording's elapsed-second timeline, as KQ-2 feasibility evidence
(event coverage + timestamp alignment, plan Arm C).

Credential hygiene: rollout files contain conversation content, never
credentials; this module reads only ``sessions/**.jsonl`` and never touches
``auth.json`` or token material.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_WINDOW_MARGIN_SECONDS = 120.0
_LIFECYCLE_TYPES = {"task_started", "task_complete"}
_ITEM_TYPES = {"item_completed", "item_started"}


def run_arm_c(*, recording_root: Path, codex_home: Path, output_root: Path) -> dict[str, Any]:
    """Inventory rollout events overlapping one frozen recording's window.

    Returns
    -------
    dict
        Inventory payload written to ``output_root/event-inventory.json``.
    """

    manifest = json.loads((recording_root / "manifest.json").read_text(encoding="utf-8"))
    started = _parse_ts(manifest["started_at_utc"])
    stopped = _parse_ts(manifest["stopped_at_utc"])
    lo = started.timestamp() - _WINDOW_MARGIN_SECONDS
    hi = stopped.timestamp() + _WINDOW_MARGIN_SECONDS

    sessions_root = codex_home / "sessions"
    files = sorted(sessions_root.rglob("*.jsonl")) if sessions_root.is_dir() else []
    overlapping = [p for p in files if lo <= p.stat().st_mtime <= hi]

    inventory_rows: list[dict[str, Any]] = []
    timeline_events: list[dict[str, Any]] = []
    for path in overlapping:
        payload_tally: dict[str, int] = {}
        top_tally: dict[str, int] = {}
        for row in _iter_records(path):
            top_tally[row["type"]] = top_tally.get(row["type"], 0) + 1
            ptype = row.get("payload_type")
            if ptype:
                payload_tally[ptype] = payload_tally.get(ptype, 0) + 1
            if ptype in _LIFECYCLE_TYPES | _ITEM_TYPES:
                elapsed = row["timestamp"].timestamp() - started.timestamp()
                timeline_events.append(
                    {
                        "elapsed_seconds": round(elapsed, 3),
                        "payload_type": ptype,
                        "turn_id": row.get("turn_id"),
                        "rollout_file": path.name,
                    }
                )
        inventory_rows.append(
            {
                "rollout_file": str(path),
                "sha256": _sha256(path),
                "top_level_types": top_tally,
                "payload_types": payload_tally,
            }
        )
    timeline_events.sort(key=lambda item: item["elapsed_seconds"])

    payload = {
        "schema_version": 1,
        "recording_root": str(recording_root),
        "codex_home": str(codex_home),
        "window_utc": {
            "started": manifest["started_at_utc"],
            "stopped": manifest["stopped_at_utc"],
        },
        "audited_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "rollout_files_in_window": len(overlapping),
        "inventories": inventory_rows,
        "lifecycle_timeline": timeline_events,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "event-inventory.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _iter_records(path: Path):
    """Yield normalized rows (timestamp, type, payload_type, turn_id)."""

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = row.get("timestamp")
            rtype = row.get("type")
            if not ts or not rtype:
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            yield {
                "timestamp": _parse_ts(ts),
                "type": rtype,
                "payload_type": payload.get("type"),
                "turn_id": payload.get("turn_id"),
            }


def _parse_ts(value: str) -> datetime:
    """Parse one recorder/rollout timestamp (ISO-8601, Z or offset)."""

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of one file."""

    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
