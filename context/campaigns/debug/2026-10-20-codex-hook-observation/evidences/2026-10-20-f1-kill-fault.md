# Evidence: F1 kill -9 fault (codex-cli 0.163.0, openlux-auto lane)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: F1. Key questions: [KQ-3](../key-questions/KQ-3-delivery-semantics.md), [KQ-5](../key-questions/KQ-5-merge-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/codex-hook-capture/f1/run-20261020T042538Z/` (tmux `codexhook-f1-2968806`, pane `%188`) |
| Lane | `openlux-auto` |
| Flags | `--dangerously-bypass-hook-trust` |
| Collector | gen 1, port 33601; heartbeat through 04:26:00.897, then stopped by teardown |
| Recording | 45 samples at 0.2 s; recorder ended with a pane-resolution failure when the target vanished |
| Labels | `f1-generation`, `f1-kill` filled with digests |

Command:

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario f1
```

## Ordered Event Sequence

| Seq | Event | received_at_utc | turn_id |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 04:25:45.202 | - |
| 2 | `UserPromptSubmit` | 04:25:45.268 | `01a1578e-…` |

Then **nothing**. Expected and observed absent: `Stop`, `Interrupt`, `SessionEnd`, `PreToolUse`, `PostToolUse`, `PreModelRequest`, `PostModelRequest`.

## Fault Timeline

- Prompt Enter 04:25:45.137; `SessionStart`/`UserPromptSubmit` arrive within 131 ms.
- Pane shows `Working (0s … 3s • esc to interrupt)`; last captured frame `s000045` at 04:25:48.55 still shows the working state.
- `kill -9` on the pane process tree at **04:25:48.545**, signalled pids `[2968844 (pane shell), 2968866 (codex)]`, 3.4 s after Enter.
- The tmux pane disappears immediately. The pane recorder stops with `stop_reason: "failed: Tmux pane %188 could not be resolved: Could not find pane_id=%188 for list-panes"` and `run_tainted=false`.
- No hook event is received in the 12 s post-kill window (`f1_post_kill_events: []`).
- The collector continues to heartbeat after the agent death (`last_heartbeat_at_utc` 04:26:00.897, `last_sequence: 2`) and is stopped only by runner teardown at 04:26:00.897.
- `session_end_observed` is `null` (the runner never waits for `SessionEnd` in this arm).

## Terminal-Gap Evidence (KQ-5)

This is the concrete terminal-gap signature for the reducer:

1. The event stream ends with `UserPromptSubmit` and no terminal event (`Stop`, `Interrupt`, or `SessionEnd`).
2. The pane recorder itself reports the target pane unresolvable, so pane liveness is false.
3. The collector heartbeat continues, so a quiet event stream is not a collector outage.

A reducer must therefore treat an open turn with no terminal event as `unknown/terminal_gap` after a liveness check (pane/process/collector heartbeat), not as a completed turn. `SessionEnd` cannot be relied on for kill -9; the hook is torn down with the process.

## Payload Inventory

`SessionStart` and `UserPromptSubmit` match the schemas exactly (`UserPromptSubmit` has `cwd`, `hook_event_name`, `model`, `permission_mode`, `prompt`, `session_id`, `transcript_path`, `turn_id`; optional `agent_id`/`agent_type` absent). No `Stop` payload exists to inspect in this run.

## KQ Verdicts

- **KQ-3:** on SIGKILL, exactly `Stop`, `Interrupt`, and `SessionEnd` are missing; the last event is `UserPromptSubmit`. The turn remains open in the stream.
- **KQ-5:** the reliable terminal-gap fallback is a liveness check (pane resolution or process table) plus the collector heartbeat, not a timeout on hook silence alone. A collector timeout would produce a false terminal-gap signal; the heartbeat distinguishes them.
