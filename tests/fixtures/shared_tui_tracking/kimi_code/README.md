# Kimi Code TUI tracking fixtures

Raw `output_text` slices captured from kimi-code **2.1.1** (the supported floor), frozen from the 2026-10-10 debug campaign's blind-labeled 5 fps recordings. Each fixture is one verbatim pane sample, ANSI escapes included, exactly as tmux capture delivered it.

Provenance (run roots under `tmp/houmao-dev-tui-testing/`, labels frozen in each run's `labels/labels.json`):

| Fixture | Recording run root | Sample | Frozen label family |
| --- | --- | --- | --- |
| `startup_trust_modal.txt` | `2026-10-10-kimi-2.1.1-session1-lifecycle` | s000005 | startup_modal |
| `idle_ready.txt` | `2026-10-10-kimi-2.1.1-session1-lifecycle` | s000107 | ready |
| `editing_draft.txt` | `2026-10-10-kimi-2.1.1-session1-lifecycle` | s000040 | editing |
| `busy_thinking.txt` | `2026-10-10-kimi-2.1.1-session1-lifecycle` | s000080 | active (braille `Thinking…`) |
| `busy_tool_moon.txt` | `2026-10-10-kimi-2.1.1-session1-lifecycle` | s000088 | active (moon spinner + tool row) |
| `subagent_running.txt` | `2026-10-10-kimi-2.1.1-session1-lifecycle` | s001327 | active (subagent `… Agent Running (…)` row visible) |
| `queue_pending.txt` | `2026-10-10-kimi-2.1.1-session1-lifecycle` | s001300 | queue_pending |
| `interrupt_resume.txt` | `2026-10-10-kimi-2.1.1-session1-lifecycle` | s001883 | interrupted (stale notice + resumed activity) |
| `approval_panel.txt` | `2026-10-10-kimi-2.1.1-session2-attempt-002` | s000040 | approval_modal (`Run this command?`) |
| `plan_review.txt` | `2026-10-10-kimi-2.1.1-session2-attempt-002` | s000560 | approval_modal (`Ready to build with this plan?`) |
| `question_dialog.txt` | `2026-10-10-kimi-2.1.1-session2-attempt-002` | s000740 | question_dialog (AskUserQuestion) |

The 0.11.x/0.23.x-era synthetic fixtures were removed when kimi-code support became floor-gated at 2.1.1 (`openspec/changes/raise-kimi-code-floor-2-1-1/`).

State conventions these fixtures pin (kimi 2.1.x signal contract):

- A visible composer accepts input even while a turn is active (kimi queues the submission); only modal surfaces close acceptance and editing.
- Modal surfaces (trust modal, approvals, plan review, question dialog) report `active_evidence` with a `modal_blocked` reason and not-ready posture.
- Busy evidence is the live-edge spinner union: moon frames directly, braille frames qualified by a 2.1.x label (`Thinking…`/`Working…` U+2026, `Retrying (N/M)`, `Compacting context…`, `Orchestrating…`, `… Agent Running (…)`).
- An `Interrupted by user` notice persists in scrollback; it marks the surface interrupted only when no concurrent spinner-union activity is visible.
