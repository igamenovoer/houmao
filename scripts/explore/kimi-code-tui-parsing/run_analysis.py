#!/usr/bin/env python3
"""Run Arm A replay (baseline + candidate) and the Arm B escape audit.

Usage:
    pixi run python scripts/explore/kimi-code-tui-parsing/run_analysis.py \
        --run-root tmp/houmao-dev-tui-testing/<run-id>

Requires frozen evidence and frozen labels (blind-label boundary: run this
only after ``labels/labels-manifest.json`` exists).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from campaign_lib.esc_audit import run_arm_b
from campaign_lib.replay import run_arm_a


def main() -> int:
    """Run both analysis arms for one frozen, labeled run root."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    labels_manifest = run_root / "labels" / "labels-manifest.json"
    if not labels_manifest.is_file():
        print(
            "ERROR: labels/labels-manifest.json missing; the blind-label boundary "
            "forbids replay before labels are frozen.",
            file=sys.stderr,
        )
        return 2

    recording_root = run_root / "capture" / "recording"
    arm_a = run_arm_a(recording_root=recording_root, replay_root=run_root / "replay")
    arm_b = run_arm_b(recording_root=recording_root, output_root=run_root / "comparison")
    summary = {
        "run_root": str(run_root),
        "arm_a_variants": [
            {k: v for k, v in row.items() if k != "command"} for row in arm_a["variants"]
        ],
        "arm_b_totals": arm_b["totals"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if all(row.get("status") == "ok" for row in arm_a["variants"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
