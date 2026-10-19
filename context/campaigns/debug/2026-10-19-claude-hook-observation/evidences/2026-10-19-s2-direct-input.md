# Evidence: S2 direct input (claude 2.1.303, DeepSeek relay, deepseek-flash[1m])

Date: 2026-10-19. Iteration: [iteration 1](../iterations/2026-10-19-plan-1-hook-capture-matrix.md). Arm: S2 direct input. Key question: [KQ-2](../key-questions/KQ-2-delivery-semantics.md) (does `UserPromptSubmit` fire without any gateway submission record).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/hook-capture/s2/run-20261019T131948Z/` (tmux session `hookcap-s2-1808235`, pane `%98`) |
| Tool | `claude` 2.1.303 via `~/.local/bin/claude-deepseek` (banner-verified) |
| Observer settings | `observer-settings-gen1.json` (9 v1 events) |
| Collector | gen 1, `channel.json` monotonic/UTC pair present |
| Model verification | banner `deepseek-flash[1m] with max effort · API Usage Billing` (gate passed) |
| Recording | 5 fps active mode, 11 samples (13:19:49–13:19:51), `pane_snapshots.ndjson` SHA-256 `8bd14acc…` |
| Labels | 1 range filled (`s2-direct-input`) with digests |
| Hook stream | `events.ndjson` SHA-256 `c21023b5…`, 3 events, all `via: http` |

## Input Path (the arm variable)

The prompt was typed with raw `tmux send-keys -l` + Enter by the campaign driver. There is no gateway, API, or SDK submission path in this harness at all — the pane tty is the only input channel. The recorder's own `input_events.ndjson` is empty (claude-tool recordings do not capture pane keystrokes); the authoritative input record is `driver-input-events.ndjson` (send_text at 13:19:49 monotonic 3470757.99, Enter 0.15 s later).

## Ordered Event Sequence

| Seq | Event | received_at_utc | Notable payload fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:19:48 | as S0/S1 (`source: startup`, `model`, `cwd`, `transcript_path`, emitter stamps) |
| 2 | `UserPromptSubmit` | 13:19:49 | `prompt` (`Reply with exactly: OK`), `prompt_id` (`c83f5af4-…`), `permission_mode`, `session_id`, `cwd`, `transcript_path` — **fires on direct pane input** |
| 3 | `Stop` | 13:19:50 | `prompt_id` matches #2, `last_assistant_message` (`OK`), `stop_hook_active` (false), `background_tasks` ([]), `session_crons` ([]), `effort` |

## Delivery Latency

Submit 13:19:49 → `UserPromptSubmit` 13:19:49 (sub-second) → `Stop` 13:19:50. Turn ≈ 1.5 s. Pane busy footer s000002–s000008; settled s000009; provider exited by s000010 after `/exit`.

## Arm Verdict

Predeclared expectation: "`UserPromptSubmit` fires without any gateway submission record." **Confirmed.** The event arrived with the full normal payload (including `prompt` text and `prompt_id`) for keystrokes injected straight into the pane. This validates design section 1.1's use of `UserPromptSubmit` as an authoritative turn-start fact independent of any submission gateway.

## Anomalies

None. Event shapes identical to S0/S1. No `PostToolUse` (no tool calls). No trust dialog (consistent with S0/S1 on this build).

## Gate Verdicts Informed

| Gate | Verdict | Evidence |
| --- | --- | --- |
| G2 (S2 scope) | **PASS** | exercised families (`SessionStart`, `UserPromptSubmit`, `Stop`) all produced events; silent families named in S0/S1 docs |
| G3 (pairing) | **PASS** | 11-sample recording + 3-event stream + label; collector monotonic/UTC pair present |

## Cleanup

Runner teardown killed `hookcap-s2-1808235`; collector SIGTERMed; no leftovers.
