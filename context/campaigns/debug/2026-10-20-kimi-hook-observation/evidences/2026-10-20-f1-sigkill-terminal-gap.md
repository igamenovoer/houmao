# Evidence: F1 SIGKILL mid-turn — terminal gap (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: F1. Key questions: [KQ-3](../key-questions/KQ-3-delivery-semantics.md), [KQ-5](../key-questions/KQ-5-merge-semantics.md) (replay phase uses this stream).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/kimi-hook-capture/f1/run-20261020T134947Z/` (tmux `kimihook-f1-3948157`, pane `%242`) |
| Tool | kimi 2.2.0, `--auto`, 20 observer entries |
| Collector | gen 1, port 32981, 3 accepted events |
| Recording | 30 samples; recording ends at 7.25 s, when the pane dies (`terminal-gap` signature) |
| Kill target | pane pid `3948177` (kimi), SIGKILL to the process tree |
| Prior run | `run-20261020T134906Z` (same result, 12 s window); canonical run extends the window to 70 s |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Key fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:49:09.763 | `source=startup` |
| 2 | `UserPromptSubmit` | 13:49:09.858 | essay prompt |
| 3 | `TurnStarted` | 13:49:09.913 | `turn_id=0` |
| — | *(kill -9 at ~13:49:53)* | — | — |
| — | *(no further events)* | — | — |

## Measurements

| Fact | Value |
| --- | --- |
| Ready composer | 3.244 s |
| `SessionStart` | 0.253 s after prompt |
| Kill | ~3 s into generation, pane pid 3948177 |
| Post-kill observation | **70 s** (past the 60 s heartbeat due) |
| Events after kill | **none** — no `Stop`, no `Interrupt`, no `SessionEnd`, no `SessionHeartbeat` |
| Heartbeat cessation | the session had not yet reached its first 60 s tick; a 70 s silent window past that due time proves cessation |
| Pane recording | last sample `s000030` at 7.25 s; no terminal frames after the kill |

## Verdict

**PASS as a fault capture.** SIGKILL produces a terminal gap: the stream simply stops after `TurnStarted`; no settle event of any kind arrives, and the heartbeat does not fire. The reducer's terminal-gap fallback must use silence plus pane death, not a hook settle event. A 60 s heartbeat makes heartbeat-loss a slow liveness signal; this run quantifies the gap as at least 70 s with no signal.

## Harness Corrections (2026-10-20)

- Scenario opening now submits the essay prompt before requiring `SessionStart`.
- Post-kill observation extended from 12 s to 70 s (`F1_POST_KILL_OBSERVATION_SECONDS`) so the heartbeat due time is covered. This is a wait-timing correction, not a provider action.

## Cleanup

The tmux session died with the process; runner teardown tolerated the already-gone session and stopped the collector. Both run roots retained under `tmp/kimi-hook-capture/f1/`.
