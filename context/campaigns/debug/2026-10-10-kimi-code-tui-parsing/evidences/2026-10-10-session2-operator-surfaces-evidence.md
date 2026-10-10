# Evidence: Session 2 — Operator-Interaction Surfaces (kimi-code 2.1.1, manual mode)

Date: 2026-10-10. Iteration: [plan 1](../iterations/2026-10-10-plan-1-state-matrix-capture.md). Key question: [KQ-1](../key-questions/KQ-1-signal-survival.md).

## Run Identity

| Field | Value |
| --- | --- |
| Run root | `tmp/houmao-dev-tui-testing/2026-10-10-kimi-2.1.1-session2-attempt-002/` |
| Prior attempt | `2026-10-10-kimi-2.1.1-session2-attempt-001/` (preserved; see deviations) |
| Tool | kimi 2.1.1, bare launch (as_is posture, plan mode toggled mid-session), tmux pane 220x50 |
| Recorder | `tools.terminal_record`, active mode, 0.2 s interval (5 fps), 797 samples over 179.5 s |
| Recording SHA-256 | `292c776bea2f7f2afa700883cd0a16e7cd96513e6356ded381d70936b1d03b28` (`pane_snapshots.ndjson`) |
| Labels | 19 ranges, complete coverage, frozen 2026-10-10T14:08:10Z, `labels_sha256=90745f14...` |
| Fixture | Boltons copy pre-trusted via `ensure_kimi_workspace_trust` (record `wd_boltons_ebb12c5d93b2`), collection preflight 437 passed |
| Spec | `iterations/2026-10-10-plan-1-state-matrix-capture/session-2-operator-surfaces.yaml` (4 cases, 32 ops, 0 drive failures) |

## Gates

G1 recording integrity: pass (after re-freeze, same as session 1). G2 coverage: pass (all four modal families captured). G3 blind-label integrity: pass. G4 replay execution: pass for baseline (`kimi_code` / `>=0.34.0`) and candidate (`kimi_code` / `2.1.x-candidate`). G5 taint: none. G6: not applicable (manual mode by design).

## What the Session Captured

- Bash approval: `Run this command?` with options `1. Approve once / 2. Approve for this session / 3. Reject / 4. Reject with feedback`, bounded by `─` rules; rejection-with-feedback row (`Not needed for this test.`).
- Write approval: `Write this file?`, forced by targeting `/tmp/houmao-campaign-note-s2.md` (in-workspace writes are auto-approved by kimi's `git-cwd-write-approve` policy).
- Plan review: `Ready to build with this plan?` with `Approve once / Reject / Revise`; Revise plus feedback row (`Keep it shorter.`); revised plan re-presented and rejected.
- AskUserQuestion dialog: ` question` title, `[N]` options, `esc cancel` hint; canceled with Escape.

## Arm A: Detector Replay vs Blind Ground Truth

Per-sample agreement over 797 samples:

| Field | Baseline `>=0.34.0` | Candidate v3 |
| --- | --- | --- |
| surface_accepting_input (ready to enter prompt) | 0.629 | 1.000 |
| surface_ready_posture (accept prompt) | 0.681 | 1.000 |
| turn_phase | 0.609 | 0.927 |
| surface_editing_input | 0.980 | 0.980 |
| surface_pending_input | 0.908 | 0.908 |
| last_turn_result | 0.960 | 0.960 |
| last_turn_source | 0.960 | 0.960 |
| diagnostics_availability | 1.000 | 1.000 |
| false_ready samples | 254 | 0 |
| false_busy samples | 0 | 0 |

Baseline failure shape: all 73 modal samples (approval panels, question dialog) read as idle-ready, plus braille-phase busy spans; 254 of 797 samples were false-ready. This is the admission-safety failure the campaign prioritizes.

Candidate v3 residual mismatches (none admission-critical): modal spans show `turn_phase=active` where GT labels `unknown` (58 samples; a vocabulary convention decision, see Findings) and `surface_pending_input=unknown` where GT says `no` (73 samples; conservative direction); question dialog shows stale `editing_input=yes` (15 samples); post-rejection turns read `last_turn_result=none` where GT says `success` (32 samples).

## Signal Survival (Session 2 Families)

| Signal | Fired / expected | False fires | Verdict |
| --- | --- | --- | --- |
| `APPROVAL_HEADERS` (all five) | 58/58 | 0 | surviving |
| `APPROVAL_CHOICE_RE` on 2.1 option labels | 58/58 | 0 | surviving |
| question dialog pattern (` question` + `[N]`/`esc cancel`) | 15/15 | 0 | surviving as a signal; uncovered by the detector |
| `PROMPT_TOKEN_RE` editor detection | 724/724 | 43 | degraded (editor box stays visible below modal spans; detector must gate on modal presence, which the candidate does) |
| moon spinner frames | 281/520 | 0 | phase-scoped |
| braille spinner frames (all carry 2.1 labels here) | 239/520 | 0 | phase-scoped |
| spinner union | 520/520 | 0 | complete busy coverage |
| legacy activity label regex | 0/520 | 0 | broken |

## Arm B: Escape-Sequence Audit

Zero OSC 133 and zero OSC `9;4` in all 797 samples. The only OSC content is 824 OSC 8 hyperlink sequences (`file:///…` paths in approval panels), which carry no state semantics. Same conclusion as session 1: escape-sequence state channels are dead for tmux-capture parsing.

## Deviations

- Attempt 001 (preserved at `…-session2-attempt-001/`) failed two cases: the Write prompt targeted an in-workspace path (auto-approved by `git-cwd-write-approve`, so no panel), and the plan case left the agent executing after revision, whose stray Bash approval blocked the question case. The spec was amended: write target moved to `/tmp`, the plan case now rejects the revised plan and dismisses leftovers before the question case. Attempt 001's recording still holds valid approval-panel raw material (a 160 s unanswered `Run this command?` span).
- `session.cast` re-frozen as in session 1; snapshot digests unchanged.

## Findings Feeding the Repair Proposal

1. Approval detection survives intact for the five known headers with the 2.1 option labels; the parser must additionally treat the question dialog (` question` + `[N]` + `esc cancel`) and the goal-start prompt (`Approve CreateGoal?`) as modal surfaces, and the server parser's startup needles must include `Trust this folder?`.
2. `turn_phase` convention on modal spans needs a product decision: the reducer reports `active` (turn blocked in flight) where this campaign's GT labeled `unknown`. Recommend formalizing modal-blocked as `active` with a `blocked` reason, since a turn is genuinely in flight; then adjust the labeling rubric accordingly.
3. The question dialog leaves a stale composer draft reading `editing=yes`; the detector should clear editing while a modal owns input focus.
