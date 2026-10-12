#!/usr/bin/env python3
"""Author blind ground-truth labels for codex iteration-1 sessions.

Encodes the span tables derived from raw pane snapshots only (plus drive-event
timing). Verifies complete, non-overlapping sample coverage, writes
``labels/labels.json``, then freezes ``labels/labels-manifest.json`` via
``campaign_lib.label_manifest``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from campaign_lib.label_manifest import write_labels_manifest

F = {
    "unknown_blocked": dict(
        diagnostics_availability="available",
        turn_phase="unknown",
        surface_accepting_input="no",
        surface_editing_input="no",
        surface_ready_posture="no",
        surface_pending_input="no",
        last_turn_result="none",
        last_turn_source="none",
    ),
    "ready_fresh": dict(
        diagnostics_availability="available",
        turn_phase="ready",
        surface_accepting_input="yes",
        surface_editing_input="no",
        surface_ready_posture="yes",
        surface_pending_input="no",
        last_turn_result="none",
        last_turn_source="none",
    ),
    "ready_success": dict(
        diagnostics_availability="available",
        turn_phase="ready",
        surface_accepting_input="yes",
        surface_editing_input="no",
        surface_ready_posture="yes",
        surface_pending_input="no",
        last_turn_result="success",
        last_turn_source="explicit_input",
    ),
    "ready_interrupted": dict(
        diagnostics_availability="available",
        turn_phase="ready",
        surface_accepting_input="yes",
        surface_editing_input="no",
        surface_ready_posture="yes",
        surface_pending_input="no",
        last_turn_result="interrupted",
        last_turn_source="explicit_input",
    ),
    "editing": dict(
        diagnostics_availability="available",
        turn_phase="ready",
        surface_accepting_input="yes",
        surface_editing_input="yes",
        surface_ready_posture="yes",
        surface_pending_input="no",
        last_turn_result="none",
        last_turn_source="none",
    ),
    "active": dict(
        diagnostics_availability="available",
        turn_phase="active",
        surface_accepting_input="yes",
        surface_editing_input="no",
        surface_ready_posture="no",
        surface_pending_input="no",
        last_turn_result="none",
        last_turn_source="none",
    ),
    "queue_pending": dict(
        diagnostics_availability="available",
        turn_phase="active",
        surface_accepting_input="yes",
        surface_editing_input="no",
        surface_ready_posture="no",
        surface_pending_input="yes",
        last_turn_result="none",
        last_turn_source="none",
    ),
    "active_interrupted_last": dict(
        diagnostics_availability="available",
        turn_phase="active",
        surface_accepting_input="yes",
        surface_editing_input="no",
        surface_ready_posture="no",
        surface_pending_input="no",
        last_turn_result="interrupted",
        last_turn_source="explicit_input",
    ),
}

# (family, scenario_id, start, end, expectation_key, note)
SESSION1 = [
    (
        "startup",
        "s1-cold-start-trust-modal",
        1,
        4,
        "unknown_blocked",
        "cold-start splash with provisional composer placeholder; app still initializing, trust screen imminent",
    ),
    (
        "startup_modal",
        "s1-cold-start-trust-modal",
        5,
        50,
        "unknown_blocked",
        "'Trust this folder?' screen: '› 1. Trust and continue / 2. Quit / enter continue · esc quit' (untrusted git-repo workdir, bypass launch)",
    ),
    (
        "ready",
        "s1-cold-start-trust-modal",
        51,
        66,
        "ready_fresh",
        "post-trust idle composer 'Ask Codex to do anything', footer with model and warning badge",
    ),
    (
        "editing",
        "s1-draft-editing",
        67,
        92,
        "editing",
        "draft 'Read boltons/iterutils.py...' typed, suffix appended, backspace-erased to empty; composer shows partial draft throughout",
    ),
    (
        "ready",
        "s1-draft-editing",
        93,
        98,
        "ready_fresh",
        "empty composer after erase; no turn started",
    ),
    (
        "active",
        "s1-busy-success",
        99,
        166,
        "active",
        "'• Working (Ns • esc to interrupt)' row with footer braille spinner; prompt echo '› {{SAFE}}...' above; row flickers off for 1-2 samples mid-turn (redraw)",
    ),
    (
        "ready",
        "s1-busy-success",
        167,
        171,
        "ready_fresh",
        "turn 1 docks 'Worked for 15s'; immediate settle window",
    ),
    (
        "ready",
        "s1-busy-success",
        172,
        310,
        "ready_success",
        "settled ready after turn 1 completion",
    ),
    (
        "active",
        "s1-tool-edit-workflow",
        311,
        376,
        "active",
        "turn 2 (read op): Working row then streaming response",
    ),
    (
        "ready",
        "s1-tool-edit-workflow",
        377,
        381,
        "ready_fresh",
        "turn 2 docks 'Worked for 14s'; immediate settle window",
    ),
    ("ready", "s1-tool-edit-workflow", 382, 510, "ready_success", "settled ready after turn 2"),
    (
        "active",
        "s1-tool-edit-workflow",
        511,
        576,
        "active",
        "turn 3 (write op): Working row, '• Created tests/test_houmao_long_horizon.py' cell",
    ),
    (
        "ready",
        "s1-tool-edit-workflow",
        577,
        581,
        "ready_fresh",
        "turn 3 docks 'Worked for 14s'; immediate settle window",
    ),
    ("ready", "s1-tool-edit-workflow", 582, 911, "ready_success", "settled ready after turn 3"),
    ("active", "s1-tool-edit-workflow", 912, 964, "active", "turn 4 (pytest run): Working row"),
    (
        "ready",
        "s1-tool-edit-workflow",
        965,
        969,
        "ready_fresh",
        "turn 4 docks 'Worked for 11s'; immediate settle window",
    ),
    ("ready", "s1-tool-edit-workflow", 970, 1189, "ready_success", "settled ready after turn 4"),
    (
        "active",
        "s1-queue-pending-input",
        1190,
        1225,
        "active",
        "turn 5 (long scan): Working row; no queued input yet",
    ),
    (
        "queue_pending",
        "s1-queue-pending-input",
        1226,
        1371,
        "queue_pending",
        "follow-up submitted mid-busy renders as '› <follow-up text>' above the Working row (later '+ 29 lines (^t to expand)'); codex merges it into the running turn (steer); single 'Worked for 41s' ends with Q1-DRAIN",
    ),
    (
        "ready",
        "s1-queue-pending-input",
        1372,
        1376,
        "ready_fresh",
        "merged turn docks 'Worked for 41s' ending Q1-DRAIN; immediate settle",
    ),
    (
        "ready",
        "s1-queue-pending-input",
        1377,
        1765,
        "ready_success",
        "settled ready after the merged turn drains",
    ),
    (
        "active",
        "s1-interrupt-escape",
        1766,
        1791,
        "active",
        "interrupt-leg turn: Working row until Esc lands",
    ),
    (
        "interrupted",
        "s1-interrupt-escape",
        1792,
        1814,
        "ready_interrupted",
        "'■ Conversation interrupted - use /feedback if something went wrong'; Working row gone; composer placeholder back — a new prompt would start immediately",
    ),
    (
        "compaction",
        "s1-compaction",
        1815,
        1902,
        "active_interrupted_last",
        "'└ Making room to continue.' compaction row WITH the Working row (esc to interrupt) present; composer placeholder visible",
    ),
    (
        "interrupted",
        "s1-exit",
        1903,
        1906,
        "ready_interrupted",
        "exit leg's first C-c interrupts the compaction; interrupt notice; idle composer",
    ),
    (
        "tui_down",
        "s1-exit",
        1907,
        1907,
        "unknown_blocked",
        "second C-c at idle quits codex: 'To continue this session, run: codex resume 01a12eba-...' — single-sample span (below min_span; partial coverage)",
    ),
]

SESSION2 = [
    (
        "startup_modal",
        "s2-startup-warnings",
        1,
        50,
        "unknown_blocked",
        "as_is launch (-a on-request -s read-only) in untrusted git-repo copy: 'Trust this folder?' screen from first sample",
    ),
    (
        "ready",
        "s2-startup-warnings",
        51,
        65,
        "ready_fresh",
        "idle composer after trust; footer '⚠ 2 warnings · f2 to view'",
    ),
    (
        "warnings_screen",
        "s2-startup-warnings",
        66,
        78,
        "unknown_blocked",
        "F2 warnings screen: full-surface overlay, composer not visible",
    ),
    (
        "ready",
        "s2-startup-warnings",
        79,
        87,
        "ready_fresh",
        "warnings screen closed; idle composer",
    ),
    (
        "active",
        "s2-command-approval-deny",
        88,
        187,
        "active",
        "command-approval turn thinking: Working row (1-sample redraw flickers stay active)",
    ),
    (
        "approval_modal",
        "s2-command-approval-deny",
        188,
        201,
        "unknown_blocked",
        "'Would you like to run the following command?' — options '1. Yes, proceed (y) / 2. Yes, and don't ask again... (p) / 3. No, and tell Codex what to do differently (esc)', 'Press enter to confirm or esc to cancel'",
    ),
    (
        "ready",
        "s2-command-approval-deny",
        202,
        268,
        "ready_interrupted",
        "Esc denial: '✗ You canceled the request to run touch ...', '• Failed (exit 1)', then '■ Conversation interrupted'; idle composer",
    ),
    (
        "active",
        "s2-edit-approval-deny",
        269,
        325,
        "active",
        "edit-approval turn: Working row (flicker at s000313-s000316 stays active)",
    ),
    (
        "approval_modal",
        "s2-edit-approval-deny",
        326,
        339,
        "unknown_blocked",
        "edit leg raised the COMMAND form: 'Would you like to run the following command?' for `printf ... > docs/houmao-campaign-note.md` (sandbox write); no 'make the following edits' panel rendered",
    ),
    (
        "ready",
        "s2-edit-approval-deny",
        340,
        406,
        "ready_interrupted",
        "Esc denial: cancel + interrupt notice; idle composer",
    ),
    (
        "model_picker",
        "s2-model-picker",
        407,
        419,
        "unknown_blocked",
        "'/model' popup 'Select Model and Effort' (s000406 @92.74 is a 1-sample redraw gap before the popup, kept in the preceding ready span)",
    ),
    (
        "ready",
        "s2-model-picker",
        420,
        437,
        "ready_interrupted",
        "picker canceled with Esc; idle composer",
    ),
]

SESSIONS = {
    "session1": ("tmp/houmao-dev-tui-testing/2026-10-12-codex-session1-lifecycle-002", SESSION1),
    "session2": (
        "tmp/houmao-dev-tui-testing/2026-10-12-codex-session2-operator-surfaces-002",
        SESSION2,
    ),
}

AMBIGUITIES = [
    "The Working status row flickers off for 1-2 samples mid-turn (redraw frames); affected samples are labeled active throughout.",
    "Session 1 queue leg: codex merges a mid-busy follow-up into the running turn (steer semantics) — one 'Worked for 41s' completes both; queue_pending spans the window where the submitted follow-up renders above the Working row.",
    "Session 2: approval denial ends the turn with the same 'Conversation interrupted' notice as Esc; post-denial windows are labeled last_turn_result=interrupted.",
    "Session 1 tui_down is a single sample (s001907, codex resume hint after the second C-c); below the 2-sample minimum span, recorded as partial coverage.",
    "Session 1 s000001-s000004: cold-start splash shows the provisional composer placeholder before the trust screen; labeled startup (phase unknown) rather than ready.",
]


def main() -> int:
    """Author labels for one session and freeze the manifest."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", choices=sorted(SESSIONS), required=True)
    args = parser.parse_args()

    run_root_str, table = SESSIONS[args.session]
    run_root = Path(run_root_str).resolve()
    snapshots = [
        json.loads(line)
        for line in (run_root / "capture" / "recording" / "pane_snapshots.ndjson")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    total = len(snapshots)

    labels = []
    cursor = 1
    counters: dict[str, int] = {}
    for family, scenario, start, end, expect_key, note in table:
        if start != cursor:
            print(f"ERROR: gap/overlap before {family} {start} (cursor {cursor})", file=sys.stderr)
            return 2
        counters[family] = counters.get(family, 0) + 1
        labels.append(
            {
                "label_id": f"{family}-{counters[family]:03d}",
                "scenario_id": scenario,
                "sample_id": f"s{start:06d}",
                "sample_end_id": f"s{end:06d}",
                "evidence": {"family": family},
                "expectations": F[expect_key],
                "note": note,
            }
        )
        cursor = end + 1
    if cursor != total + 1:
        print(f"ERROR: labels end at {cursor - 1}, recording has {total} samples", file=sys.stderr)
        return 2

    labels_dir = run_root / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)
    (labels_dir / "labels.json").write_text(
        json.dumps({"schema_version": 1, "labels": labels}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = write_labels_manifest(
        run_root=run_root,
        labeler="kimi-code-agent (blind: raw snapshots + drive events only)",
        known_ambiguities=AMBIGUITIES,
    )
    print(
        json.dumps(
            {
                "run_root": str(run_root),
                "labels": len(labels),
                "samples": total,
                "families": counters,
                "labels_sha256": manifest["labels_sha256"][:16],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
