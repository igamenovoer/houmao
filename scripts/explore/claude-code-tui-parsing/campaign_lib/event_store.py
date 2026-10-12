"""Arm C transcript inventory: claude session JSONL store vs recording timeline.

Claude Code writes one transcript JSONL per session under
``~/.claude/projects/<workdir-slug>/`` while the TUI runs. Records carry
top-level ``type`` (``user``, ``assistant``, ``system``, ``progress``,
``summary``, …), ISO ``timestamp``, ``cwd``, ``sessionId``, and uuid links.
This module inventories the transcript files overlapping one campaign
recording's time window and aligns timestamped records to the recording's
elapsed-second timeline, as KQ-2 feasibility evidence (event coverage +
timestamp alignment, plan Arm C).

Credential hygiene: transcripts contain conversation content, never
credentials; this module tallies event structure and timestamps only and
never copies prompt payloads into artifacts. It reads only
``projects/**/*.jsonl`` and never touches ``.credentials.json``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_WINDOW_MARGIN_SECONDS = 120.0


def run_arm_c(
    *,
    recording_root: Path,
    claude_config_dir: Path,
    workdir: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Inventory transcript records overlapping one frozen recording's window.

    Transcript files are selected by mtime overlap with the recording window
    and confirmed by a ``cwd`` match against the session workdir, so other
    claude sessions on this host are excluded.

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

    projects_root = claude_config_dir / "projects"
    files = sorted(projects_root.rglob("*.jsonl")) if projects_root.is_dir() else []
    overlapping = [p for p in files if lo <= p.stat().st_mtime <= hi]

    inventory_rows: list[dict[str, Any]] = []
    timeline_events: list[dict[str, Any]] = []
    matched_files = 0
    for path in overlapping:
        type_tally: dict[str, int] = {}
        subtype_tally: dict[str, int] = {}
        cwd_match = False
        file_events: list[dict[str, Any]] = []
        for row in _iter_records(path):
            if row["cwd"] is not None and row["cwd"] == str(workdir):
                cwd_match = True
            type_tally[row["type"]] = type_tally.get(row["type"], 0) + 1
            if row["subtype"]:
                subtype_tally[row["subtype"]] = subtype_tally.get(row["subtype"], 0) + 1
            if (
                row["timestamp"] is not None
                and started.timestamp() <= (row["timestamp"].timestamp()) <= stopped.timestamp()
            ):
                file_events.append(
                    {
                        "elapsed_seconds": round(
                            row["timestamp"].timestamp() - started.timestamp(), 3
                        ),
                        "type": row["type"],
                        "subtype": row["subtype"],
                        "transcript_file": path.name,
                    }
                )
        if not cwd_match:
            continue
        matched_files += 1
        timeline_events.extend(file_events)
        inventory_rows.append(
            {
                "transcript_file": str(path),
                "sha256": _sha256(path),
                "top_level_types": type_tally,
                "subtypes": subtype_tally,
            }
        )
    timeline_events.sort(key=lambda item: item["elapsed_seconds"])

    payload = {
        "schema_version": 1,
        "recording_root": str(recording_root),
        "claude_config_dir": str(claude_config_dir),
        "workdir": str(workdir),
        "window_utc": {
            "started": manifest["started_at_utc"],
            "stopped": manifest["stopped_at_utc"],
        },
        "audited_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "transcript_files_in_window": len(overlapping),
        "transcript_files_matching_workdir": matched_files,
        "inventories": inventory_rows,
        "event_timeline": timeline_events,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "event-inventory.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _iter_records(path: Path):
    """Yield normalized rows (timestamp, type, subtype, cwd) from one transcript."""

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rtype = row.get("type")
            if not rtype:
                continue
            ts_raw = row.get("timestamp")
            timestamp = _parse_ts(ts_raw) if isinstance(ts_raw, str) else None
            yield {
                "timestamp": timestamp,
                "type": str(rtype),
                "subtype": row.get("subtype") if isinstance(row.get("subtype"), str) else None,
                "cwd": row.get("cwd") if isinstance(row.get("cwd"), str) else None,
            }


def _parse_ts(value: str) -> datetime:
    """Parse one recorder/transcript timestamp (ISO-8601, Z or offset)."""

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of one file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
