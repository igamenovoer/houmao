# Evidence: S1 normal multi-turn, heartbeat, tool pairing, H1 load-once (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: S1. Key questions: [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/kimi-hook-capture/s1/run-20261020T133343Z/` (tmux `kimihook-s1-3891294`, pane `%222`) |
| Tool | kimi 2.2.0, `--auto`, 20 observer `[[hooks]]` entries |
| Collector | gen 1, port 42103, 14 accepted events, all `via: http` |
| Recording | 330 samples at 5 fps; labels: `s1-turn-1`, `s1-turn-2`, `s1-heartbeat-hold`, `s1-hot-reload-probe`, `s1-exit` |
| Session | `session_41eb0578-0c5b-4297-958c-6915498b11ba`; created by the first prompt; `SessionStart` 0.247 s after it |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Key fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:33:47.053 | `source=startup`, `model=kimi-code/k3-256k`, `profile=agent` |
| 2 | `UserPromptSubmit` | 13:33:47.177 | `prompt=[{type:text,text:"Reply with exactly: OK"}]`, `is_steer=false` |
| 3 | `TurnStarted` | 13:33:47.234 | `turn_id=0`, `origin_kind=user` |
| 4 | `Stop` | 13:33:52.546 | `stop_hook_active=false` |
| 5 | `UserPromptSubmit` | 13:33:53.182 | echo-hi prompt |
| 6 | `TurnStarted` | 13:33:53.230 | `turn_id=1` |
| 7 | `PreToolUse` | 13:33:57.934 | `tool_name=Bash`, `tool_call_id=tool_2F6UGGAOL8Csw5gQg7H23Tig`, `tool_input={command:"echo hi"}` |
| 8 | `PostToolUse` | 13:33:57.996 | same `tool_call_id`, `tool_output="hi\n"` |
| 9 | `Stop` | 13:34:03.277 | turn 2 end |
| 10 | `SessionHeartbeat` | 13:34:47.042 | `uptime_ms=60001` |
| 11 | `UserPromptSubmit` | 13:34:54.156 | third OK prompt (after H1 append) |
| 12 | `TurnStarted` | 13:34:54.226 | `turn_id=2` |
| 13 | `Stop` | 13:34:56.920 | turn 3 end |
| 14 | `SessionEnd` | 13:34:57.613 | `reason=exit` |

## Measurements

| Fact | Value |
| --- | --- |
| Ready composer | 2.868 s after launch, zero keypresses |
| `SessionStart` | 0.247 s after the first prompt; preceded `UserPromptSubmit` |
| Turn 1 wall | prompt 13:33:46.806 → `Stop` 13:33:52.546 (5.74 s) |
| Turn 2 wall | prompt 13:33:53.182 → `Stop` 13:34:03.277 (10.10 s); tool call at 13:33:57.9 |
| Heartbeat | one at 60.0 s after `SessionStart` (13:34:47.042), `uptime_ms=60001`; no jitter observed in the single interval |
| Exit | `/exit`, tmux gone after 1.469 s; `SessionEnd(reason=exit)` 13:34:57.613 |
| Tool pairing | `PreToolUse`/`PostToolUse` share `tool_call_id`; no `turn_id` on either tool event |
| H1 mid-session marker | config appended at 13:34:53.936 (sha256 `2cd6cb85…`); third prompt produced `UserPromptSubmit` but the marker file stayed **absent** — load-once holds |

## Payload Observations

- `session_title` is fixed at the first prompt ("Reply with exactly: OK") and repeats on every later event, including the echo-hi turn and tool events.
- `turn_id` is a 0-based integer on `TurnStarted` only (0, 1, 2); absent from `UserPromptSubmit`, `Stop`, and tool events.
- `UserPromptSubmit.prompt` is a raw `ContentPart[]` (`[{type:"text", text:"..."}]`); `TurnStarted.prompt` is a plain string.
- `PostToolUse.tool_output` is a string (`"hi\n"`), not a structured object; no `duration_ms` field.
- No `PermissionRequest`/`PermissionResult` under `--auto`, as expected.
- One `SessionHeartbeat` is exactly the 60 s timer; `uptime_ms` is measured from session service creation, not process start.

## Verdict

**PASS.** Three turn cycles, one Bash tool pair, heartbeat + `uptime_ms`, clean `SessionEnd`, and load-once confirmed mid-session. The H1 marker fires only in the S7 restart.

## Harness Corrections (2026-10-20)

1. Scenario opening now submits the frozen first prompt before requiring `SessionStart` (lazy session creation). Recorded in the iteration plan's amended G1.
2. No other S1-specific correction. The `SessionHeartbeat` hold (70 s from launch) was sufficient.

## Cleanup

`kimihook-s1-3891294` killed by runner teardown; collector stopped. Run root retained under `tmp/kimi-hook-capture/s1/`.
