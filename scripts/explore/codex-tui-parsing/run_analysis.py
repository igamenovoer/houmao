#!/usr/bin/env python3
"""Run Arm A replays (fallback + 0.144.x baselines, optional candidate), Arm B escape audit, Arm C event inventory.

Usage:
    pixi run python scripts/explore/codex-tui-parsing/run_analysis.py \
        --run-root tmp/houmao-dev-tui-testing/<run-id> [--with-candidate]

Requires frozen evidence and frozen labels (blind-label boundary: run this
only after ``labels/labels-manifest.json`` exists). ``--with-candidate`` adds
the monkey-patched candidate replay and is valid only once
``campaign_lib/patches.py`` carries the codex candidate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from campaign_lib.esc_audit import run_arm_b
from campaign_lib.event_store import run_arm_c
from campaign_lib.launch import DEFAULT_CODEX_HOME
from campaign_lib.replay import run_arm_a


def main() -> int:
    """Run the analysis arms for one frozen, labeled run root."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument(
        "--with-candidate",
        action="store_true",
        help="Also replay the monkey-patched candidate detector (post-repair phase)",
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=DEFAULT_CODEX_HOME,
        help="CODEX_HOME whose sessions/ rollouts feed the Arm C inventory",
    )
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
    arm_a = run_arm_a(
        recording_root=recording_root,
        replay_root=run_root / "replay",
        include_candidate=args.with_candidate,
    )
    arm_b = run_arm_b(recording_root=recording_root, output_root=run_root / "comparison")
    arm_c = run_arm_c(
        recording_root=recording_root,
        codex_home=args.codex_home.resolve(),
        output_root=run_root / "comparison",
    )
    summary = {
        "run_root": str(run_root),
        "arm_a_variants": [
            {k: v for k, v in row.items() if k != "command"} for row in arm_a["variants"]
        ],
        "arm_b_totals": arm_b["totals"],
        "arm_c_rollout_files": arm_c["rollout_files_in_window"],
        "arm_c_lifecycle_events": len(arm_c["lifecycle_timeline"]),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if all(row.get("status") == "ok" for row in arm_a["variants"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
