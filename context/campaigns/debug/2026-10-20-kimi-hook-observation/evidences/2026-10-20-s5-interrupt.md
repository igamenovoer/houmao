# Evidence: S5 Esc interrupt mid-turn (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: S5. Key questions: [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-4](../key-questions/KQ-4-blocked-state-permission.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/kimi-hook-capture/s5/run-20261020T133804Z/` (tmux `kimihook-s5-3903427`, pane `%230`) |
| Tool | kimi 2.2.0, `--auto`, 20 observer entries |
| Collector | gen 1, port 33071, 5 accepted events |
| Recording | 70 samples; labels `s5-generation`, `s5-post-escape` |
| Session | `session_…`; `SessionStart` 0.266 s after the essay prompt |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Key fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:38:07.586 | `source=startup` |
| 2 | `UserPromptSubmit` | 13:38:07.685 | `Write a long essay about recursion.` |
| 3 | `TurnStarted` | 13:38:07.743 | `turn_id=0`, `origin_kind=user` |
| 4 | `Interrupt` | 13:38:10.626 | `turn_id=0`, `reason=cancelled` |
| 5 | `SessionEnd` | 13:38:19.500 | `reason=exit` |

## Measurements

| Fact | Value |
| --- | --- |
| Ready composer | 2.91 s |
| `SessionStart` | 0.266 s after prompt |
| Esc sent | 13:38:10.56 (driver log), ~2.8 s after `TurnStarted` |
| `Interrupt` | 13:38:10.626, same `turn_id=0`, `reason=cancelled` |
| `Stop` count | 0 before and 0 after Esc; **no `Stop`** for the aborted turn |
| `Interrupt` field set | `client_type`, `cwd`, `hook_event_name`, `reason`, `session_id`, `session_title`, `turn_id` (7 fields) |
| Exit | `/exit` in 1.47 s; `SessionEnd(reason=exit)` at 13:38:19.500 |

The pane shows the partial essay stopping at Esc, the composer returning, and no answer completion. The hook stream's `Interrupt` is the only settle event for the aborted turn.

## Verdict

**PASS.** `Interrupt(turn_id=0, reason=cancelled)` fires in place of `Stop`; the aborted turn produces no `Stop`. This is the reducer rule for the `interrupted` posture.

## Harness Corrections (2026-10-20)

- Scenario opening now submits the essay prompt before requiring `SessionStart`.
- No S5-specific key correction; `Escape` worked directly.

## Cleanup

`kimihook-s5-3903427` exited via `/exit`; collector stopped. Run root retained under `tmp/kimi-hook-capture/s5/`.
