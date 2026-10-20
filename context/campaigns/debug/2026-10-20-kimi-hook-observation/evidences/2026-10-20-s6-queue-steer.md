# Evidence: S6 queued/steered follow-up (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: S6. Key questions: [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Canonical run (Ctrl-S) | `tmp/kimi-hook-capture/s6/run-20261020T134110Z/` (tmux `kimihook-s6-3912706`, pane `%234`) |
| Plain-Enter deviation run | `tmp/kimi-hook-capture/s6/run-20261020T133838Z/` (no `UserPromptQueued`) |
| Tool | kimi 2.2.0, `--auto`, 20 observer entries |
| Collector | gen 1, port 40317, 11 accepted events |
| Recording | 1,534 samples (long essay + waits); labels `s6-first-turn`, `s6-queued-turn` |
| Session | `session_b40a26ef-18e7-4aab-9188-d87ea728ccfb`; `SessionStart` 0.241 s after the essay prompt |

## Key-Sequence Correction (2026-10-20)

The predeclared action ("type `Reply with exactly: OK` while busy") used `Enter`. That path **does not emit** `UserPromptQueued`: the text stayed in the composer and was submitted 65 ms after `Stop`, as a normal second turn (`run-20261020T133838Z`: one `Stop` at 13:40:10.013, `UserPromptSubmit` at 13:40:10.078, `is_steer=false`, no queue event). The documented steer key is `Ctrl-S` (`docs/en/guides/interaction.md:131`, `docs/en/reference/keyboard.md:62`). The canonical run therefore types the prompt and sends `C-s`.

## Ordered Event Sequence (canonical Ctrl-S run)

| Seq | Event | received_at_utc | Key fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:41:14.286 | `source=startup` |
| 2 | `UserPromptSubmit` | 13:41:14.410 | essay prompt, `is_steer=false` |
| 3 | `TurnStarted` | 13:41:14.471 | `turn_id=0`, `origin_kind=user` |
| 4 | `UserPromptQueued` | 13:41:16.960 | `prompt_id=msg_01M5CRPZZM31SG8FVZVJAK8S1K`, `queue_length=1`, `prompt=[{type:text,text:"Reply with exactly: OK"}]` |
| 5 | `SessionHeartbeat` | 13:42:14.274 | `uptime_ms=60001` |
| 6 | `Stop` | 13:42:53.982 | one Stop ends the combined turn |
| 7-10 | `SessionHeartbeat` x4 | 13:43:14.286, 13:44:14.286, 13:45:14.288, 13:46:14.289 | 60 s cadence |
| 11 | `SessionEnd` | 13:46:55.178 | `reason=exit` |

## Measurements and Semantics

| Fact | Value |
| --- | --- |
| `UserPromptQueued` latency | 2.49 s after the essay `UserPromptSubmit`, 0.19 s after Ctrl-S |
| Queued payload | `prompt_id=msg_01M5…`, `queue_length=1`, `prompt` ContentPart[], `session_title` = essay title |
| Steer drain | **no second `UserPromptSubmit` and no second `Stop`**: the message was injected into the running turn; the model answered `OK` at ~102.9 s and one `Stop` ended the combined turn |
| `is_steer` | only the first `UserPromptSubmit` exists and carries `false`; the steered message has no UPS |
| Heartbeats | 5 in the long turn, 60 s cadence (`uptime_ms` 60001, 120001, …) |
| Exit | `/exit` in 1.473 s; `SessionEnd(reason=exit)` |

Plain-Enter run for comparison: no `UserPromptQueued`; the typed text submitted immediately after `Stop` (65 ms), producing a second `UserPromptSubmit`/`TurnStarted`/`Stop` pair. The queue event is specific to the steer path, not to typing while busy.

## Verdict

**PASS with a corrected key.** `UserPromptQueued(prompt_id, queue_length)` is captured on the documented `Ctrl-S` steer path. The eventual `UserPromptSubmit.is_steer` expectation does **not** apply: a steered message is injected into the active turn and has no separate UPS. The reducer must treat `UserPromptQueued` as the queue signal and the absence of a second UPS as steer-into-turn, not as a missing submission.

## Harness Corrections (2026-10-20)

- Scenario opening now submits the essay prompt before requiring `SessionStart`.
- S6 second input changed from `submit_text()` (Enter) to `send_text()` + `C-s`, with the first run recorded as a deviation.
- `second_stop` now uses `wait_for_count` so a single combined `Stop` is recorded as observed rather than forcing a second one.

## Cleanup

`kimihook-s6-3912706` exited via `/exit`; collector stopped. Both run roots retained under `tmp/kimi-hook-capture/s6/`.
