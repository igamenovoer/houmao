#!/usr/bin/env python3
"""Author blind ground-truth labels for claude iteration-1 sessions.

Encodes the span tables derived from raw pane snapshots only (plus drive-event
timing). Verifies complete, non-overlapping sample coverage, writes
``labels/labels.json``, then freezes ``labels/labels-manifest.json`` via
``campaign_lib.label_manifest``.

Sessions: session1 (lifecycle), session2 (operator surfaces, attempt 002 with
ask rules), session2a (attempt 001, auto-mode auto-approval evidence).
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
    "editing_success": dict(
        diagnostics_availability="available",
        turn_phase="ready",
        surface_accepting_input="yes",
        surface_editing_input="yes",
        surface_ready_posture="yes",
        surface_pending_input="no",
        last_turn_result="success",
        last_turn_source="explicit_input",
    ),
    "editing_interrupted": dict(
        diagnostics_availability="available",
        turn_phase="ready",
        surface_accepting_input="yes",
        surface_editing_input="yes",
        surface_ready_posture="yes",
        surface_pending_input="no",
        last_turn_result="interrupted",
        last_turn_source="explicit_input",
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
    "active_editing": dict(
        diagnostics_availability="available",
        turn_phase="active",
        surface_accepting_input="yes",
        surface_editing_input="yes",
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
}

# (family, scenario_id, start, end, expectation_key, note)
SESSION1 = [
    (
        "startup_modal",
        "s1-bootstrap-trust-modal",
        1,
        51,
        "unknown_blocked",
        "trust dialog 'Quick safety check: Is this a project you created or one you trust?' with default 'No, exit' selected (renders even under --dangerously-skip-permissions)",
    ),
    (
        "ready",
        "s1-bootstrap-trust-modal",
        52,
        66,
        "ready_fresh",
        "post-trust idle composer: banner 'Claude Code v2.1.296 / Sonnet 5.5 · API Usage Billing', placeholder 'Try \"create a util logging.py that...\"', footer 'bypass permissions on'",
    ),
    (
        "editing",
        "s1-draft-editing",
        67,
        92,
        "editing",
        "draft typing, suffix append, exact backspace erase; the full draft renders by s000067 and the composer returns to placeholder at s000093 (span boundaries corrected in the post-repair pass from composer surface evidence)",
    ),
    ("ready", "s1-draft-editing", 93, 97, "ready_fresh", "empty composer after erase"),
    ("editing", "s1-busy-success", 98, 98, "editing", "submit-short type-phase frame"),
    (
        "active",
        "s1-busy-success",
        99,
        161,
        "active",
        "busy footer 'esc to interrupt' from s000099; spinner family '<glyph> <gerund>… (Ns · ↓ N tokens)'",
    ),
    (
        "ready",
        "s1-busy-success",
        162,
        312,
        "ready_success",
        "turn docked '✻ Cooked for 14s · done 10:03 PM'; footer flips to '← for agents' at s000162",
    ),
    (
        "active",
        "s1-tool-edit-workflow",
        313,
        387,
        "active",
        "read turn (pairwise/windowed docstrings)",
    ),
    (
        "ready",
        "s1-tool-edit-workflow",
        388,
        513,
        "ready_success",
        "read turn docked; the composer stays empty through s000513 (the write-test prompt renders only at submission — the former s000512-s000513 editing span was a drive-timing guess, corrected in the post-repair pass from composer surface evidence)",
    ),
    (
        "active",
        "s1-tool-edit-workflow",
        514,
        614,
        "active",
        "write+test turn: Write(tests/test_houmao_probe.py) auto-allowed under bypass, pytest run",
    ),
    (
        "ready",
        "s1-tool-edit-workflow",
        615,
        928,
        "ready_success",
        "write turn docked '✻ Sautéed for 22s · done 10:04 PM'",
    ),
    (
        "editing",
        "s1-queue-pending-input",
        929,
        929,
        "editing_success",
        "submit-medium type-phase frame",
    ),
    ("active", "s1-queue-pending-input", 930, 955, "active", "queue turn active before follow-up"),
    (
        "active_editing",
        "s1-queue-pending-input",
        956,
        956,
        "active_editing",
        "follow-up draft typed into the busy composer (typing while busy is allowed)",
    ),
    (
        "queue_pending",
        "s1-queue-pending-input",
        957,
        968,
        "queue_pending",
        "composer placeholder becomes 'Press up to edit queued messages' while the follow-up sits queued",
    ),
    (
        "active",
        "s1-queue-pending-input",
        969,
        1317,
        "active",
        "queued follow-up echoes into the transcript as a '❯' user block and merges into the running turn; single dock '✻ Cogitated for 1m 27s · done 10:07 PM'",
    ),
    ("ready", "s1-queue-pending-input", 1318, 1371, "ready_success", "queue turn drained"),
    ("active", "s1-interrupt-escape", 1372, 1398, "active", "interrupt-leg turn (IT-7 prompt)"),
    (
        "interrupted",
        "s1-interrupt-escape",
        1399,
        1421,
        "editing_interrupted",
        "Esc abort: turn stops with NO '⎿ Interrupted' transcript line; the interrupted prompt is restored into the composer as a draft; at s001421 the driver's '/compact' types onto the restored draft (mangling captured)",
    ),
    (
        "active",
        "s1-compaction",
        1422,
        1509,
        "active",
        "mangled 'IT-7/compact' prompt turn (compaction never ran; driver composition bug, declared coverage gap): spinner '✽ Ebbing…' with streaming answer tail",
    ),
    (
        "active_editing",
        "s1-model-picker",
        1510,
        1510,
        "active_editing",
        "'/model' draft typed into the busy composer at the turn's answer-streaming tail; the slash autocomplete menu hides the busy footer and spinner for one frame",
    ),
    (
        "model_picker",
        "s1-model-picker",
        1511,
        1524,
        "unknown_blocked",
        "'Select model' picker fully rendered from s001511: numbered entries with per-Mtok prices, '❯ 5. Sonnet ✔' selected, '… +8 models'; Esc keeps model ('Kept model as Sonnet 5.5'). Boundary corrected in the post-repair pass: s001511 already shows the complete picker surface, and by s001525 the picker is gone (spinner + busy footer back), not a materializing border",
    ),
    (
        "active",
        "s1-model-picker",
        1525,
        1532,
        "active",
        "the streaming turn RESUMES after the picker closes: spinner plus 'esc to interrupt' footer return until the queued /model interruption lands at s001533. Boundary corrected in the post-repair pass from raw footer/spinner evidence",
    ),
    (
        "ready",
        "s1-exit",
        1533,
        1563,
        "ready_interrupted",
        "idle composer, '⎿ Interrupted · What should Claude do instead?' in transcript from s001533; 'Press Ctrl-C again to exit' hint s001538-s001540; double C-c did not exit (hint timing) — TUI alive at end, tui_down coverage gap",
    ),
]

SESSION2 = [
    (
        "startup_modal",
        "s2-bootstrap-trust-modal",
        1,
        51,
        "unknown_blocked",
        "trust dialog (same shape as session 1); s000051 is the blank dismissal frame",
    ),
    (
        "ready",
        "s2-bootstrap-trust-modal",
        52,
        66,
        "ready_fresh",
        "idle composer, footer 'auto mode on'; the placeholder tip still renders at s000066 (editing boundary corrected in the post-repair pass from composer surface evidence)",
    ),
    ("editing", "s2-command-approval-deny", 67, 67, "editing", "submit-command type-phase frame"),
    (
        "active",
        "s2-command-approval-deny",
        68,
        107,
        "active",
        "command turn thinking; 'esc to interrupt' footer until the dialog replaces it",
    ),
    (
        "approval_modal",
        "s2-command-approval-deny",
        108,
        121,
        "unknown_blocked",
        "boxed 'Bash command' panel: 'Ask rule Bash(touch:*) overrides auto mode for this command.', 'Do you want to proceed?', '❯ 1. Yes / 2. No', 'Esc to cancel · Tab to amend'",
    ),
    (
        "ready",
        "s2-command-approval-deny",
        122,
        188,
        "ready_interrupted",
        "Esc denial: '⎿ Interrupted · What should Claude do instead?' plus dock '✻ Baked for 9s · done 10:19 PM'",
    ),
    (
        "editing",
        "s2-edit-approval-deny",
        189,
        189,
        "editing_interrupted",
        "submit-write type-phase frame",
    ),
    ("active", "s2-edit-approval-deny", 190, 225, "active", "edit turn thinking before the dialog"),
    (
        "approval_modal",
        "s2-edit-approval-deny",
        226,
        990,
        "unknown_blocked",
        "boxed 'Create file' panel with content preview: 'Do you want to create houmao-campaign-note.md?', options '1. Yes / 2. Yes, and always allow access… (shift+tab) / 3. No'; held through the driver's 180 s wrong-needle wait (the wait expected 'Do you want to proceed?'); dismissed by the runner's recovery Esc at 223.02 s",
    ),
    (
        "ready",
        "s2-edit-approval-deny",
        991,
        1070,
        "ready_interrupted",
        "denial: '⎿ User rejected write to ../../../../../docs/houmao-campaign-note.md' plus dock '✻ Cogitated for 8s · done 10:22 PM'",
    ),
    ("model_picker", "s2-model-picker", 1071, 1084, "unknown_blocked", "'Select model' picker"),
    (
        "ready",
        "s2-model-picker",
        1085,
        1104,
        "ready_interrupted",
        "picker canceled with Esc; idle composer",
    ),
]

SESSION2A = [
    ("startup_modal", "s2-bootstrap-trust-modal", 1, 51, "unknown_blocked", "trust dialog"),
    (
        "ready",
        "s2-bootstrap-trust-modal",
        52,
        65,
        "ready_fresh",
        "idle composer with 'Auto mode is now Claude Code's default permission mode' banner block",
    ),
    (
        "editing",
        "s2-command-approval-deny",
        66,
        66,
        "editing",
        "submit-command type-phase frame: the full command draft renders in the composer at s000066 (boundary corrected in the post-repair pass from composer surface evidence)",
    ),
    (
        "active",
        "s2-command-approval-deny",
        67,
        148,
        "active",
        "auto mode auto-approved the touch command (no dialog); 'Ran 1 shell command' visible from s000147",
    ),
    (
        "ready",
        "s2-command-approval-deny",
        149,
        950,
        "ready_success",
        "command turn docked '✻ Churned for 18s · done 10:09 PM'; long dwell through the 180 s wrong-needle wait",
    ),
    (
        "active",
        "s2-edit-approval-deny",
        951,
        1750,
        "active",
        "edit turn: Write auto-approved ('Allowed by auto mode classifier'), spinner '* Blanching… (1m 26s · ↓ 64 tokens)' with /btw tip; stalled ~180 s on the wrong-needle wait",
    ),
    (
        "ready",
        "s2-edit-approval-deny",
        1751,
        1831,
        "ready_interrupted",
        "runner recovery Esc at ~394.15 s interrupted the stalled turn: '⎿ Interrupted · What should Claude do instead?'",
    ),
    ("model_picker", "s2-model-picker", 1832, 1844, "unknown_blocked", "'Select model' picker"),
    ("ready", "s2-model-picker", 1845, 1864, "ready_interrupted", "picker canceled; idle composer"),
]

SESSIONS = {
    "session1": ("tmp/houmao-dev-tui-testing/2026-10-12-claude-session1-lifecycle", SESSION1),
    "session2": (
        "tmp/houmao-dev-tui-testing/2026-10-12-claude-session2-operator-surfaces-002",
        SESSION2,
    ),
    "session2a": (
        "tmp/houmao-dev-tui-testing/2026-10-12-claude-session2-operator-surfaces",
        SESSION2A,
    ),
}

AMBIGUITIES = [
    "Session 1: Esc mid-turn aborts silently (no '⎿ Interrupted' transcript line) and restores the prompt into the composer as a draft; the interrupted result is adjudicated from drive events, not surface text.",
    "Session 1: the '/compact' op typed onto the restored draft and submitted a mangled 'IT-7/compact' prompt; compaction coverage is a declared gap and the mangled turn is labeled as an ordinary active turn.",
    "Session 1: the queued '/model' opens the picker while the mangled turn keeps streaming; the turn RESUMES after the picker closes (s001526-s001532: spinner + busy footer) and ends '⎿ Interrupted' at s001533. Picker frames are labeled modal from full render (s001511); resumed frames are labeled active per surface evidence (post-repair boundary correction).",
    "Session 1 exit leg: two C-c presses 1 s apart did not exit (the hint appears after the second press); TUI stays alive through the final sample — tui_down is a coverage gap.",
    "Session 2 (002): the edit-approval dialog was dismissed by the runner's recovery Escape at 223.02 s after the wrong-needle wait timed out, not by the leg's own deny-esc; the 180 s dwell is labeled approval_modal throughout.",
    "Session 2a (001): auto mode auto-approved both approval-bait legs with no dialog; labeled as ordinary active/ready turns — this run is the auto-mode evidence baseline, not approval coverage.",
    "Completion verb markers ('✻ <Verb> for <dur> · done <time>') use per-turn randomized verbs (Cooked, Sautéed, Cogitated, Baked, Churned observed); the dock line persists in scrollback but only its visibility in the captured tail is labeled.",
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
