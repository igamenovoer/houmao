"""Arm B escape-sequence audit over frozen pane snapshots.

Counts OSC 133 zone markers and OSC ``9;4`` progress sequences per captured
sample to decide whether terminal escape channels survive
``tmux capture-pane -p -e`` at all (KQ-2 feasibility input). SGR presence is
tallied as a control: if SGR survives but OSC does not, the channel is dead
for tmux-capture-based parsing regardless of what kimi-code emits.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_OSC_133 = "\x1b]133;"
_OSC_9_4 = "\x1b]9;4;"
_OSC_ANY = "\x1b]"
_SGR_ANY = "\x1b["


def run_arm_b(*, recording_root: Path, output_root: Path) -> dict[str, Any]:
    """Audit escape-sequence survival across one frozen recording.

    Returns
    -------
    dict
        Audit payload with per-sample rows and aggregate tallies, written to
        ``output_root/escape-audit.json``.
    """

    snapshots_path = recording_root / "pane_snapshots.ndjson"
    if not snapshots_path.is_file():
        raise FileNotFoundError(f"No pane snapshots at `{snapshots_path}`")

    rows: list[dict[str, Any]] = []
    tally = {"osc_133": 0, "osc_9_4": 0, "osc_any": 0, "sgr_any": 0, "plain_only": 0}
    with snapshots_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            snapshot = json.loads(line)
            text = snapshot.get("output_text") or ""
            row = {
                "sample_id": snapshot["sample_id"],
                "elapsed_seconds": snapshot["elapsed_seconds"],
                "osc_133_count": text.count(_OSC_133),
                "osc_9_4_count": text.count(_OSC_9_4),
                "osc_any_count": text.count(_OSC_ANY),
                "sgr_any_count": text.count(_SGR_ANY),
            }
            rows.append(row)
            tally["osc_133"] += row["osc_133_count"]
            tally["osc_9_4"] += row["osc_9_4_count"]
            tally["osc_any"] += row["osc_any_count"]
            tally["sgr_any"] += row["sgr_any_count"]
            if row["osc_any_count"] == 0 and row["sgr_any_count"] == 0:
                tally["plain_only"] += 1

    payload = {
        "schema_version": 1,
        "recording_root": str(recording_root),
        "audited_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "sample_count": len(rows),
        "totals": tally,
        "samples": rows,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "escape-audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload
