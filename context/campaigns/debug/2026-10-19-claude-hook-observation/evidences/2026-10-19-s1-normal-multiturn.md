# Evidence: S1 normal multi-turn (claude 2.1.303, DeepSeek relay, deepseek-flash[1m])

Date: 2026-10-19. Iteration: [iteration 1](../iterations/2026-10-19-plan-1-hook-capture-matrix.md). Arm: S1 normal. Key questions: [KQ-2](../key-questions/KQ-2-delivery-semantics.md), [KQ-3](../key-questions/KQ-3-payload-catalog.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/hook-capture/s1/run-20261019T131758Z/` (tmux session `hookcap-s1-1804779`, pane `%96`) |
| Tool | `claude` 2.1.303 via `~/.local/bin/claude-deepseek` (banner-verified) |
| Observer settings | `observer-settings-gen1.json` (9 v1 events) |
| Collector | gen 1, `channel.json` started 13:17:58 UTC / monotonic 3470629.65 (pair present) |
| Model verification | banner `deepseek-flash[1m] with max effort · API Usage Billing` (gate passed) |
| Recording | 5 fps active mode, 20 samples (13:17:58–13:18:02), `pane_snapshots.ndjson` SHA-256 `473a6ca7…` |
| Labels | 3 ranges filled (`s1-turn-1`, `s1-turn-2`, `s1-exit`) with digests |
| Hook stream | `events.ndjson` SHA-256 `db204994…`, 5 events, all `via: http` |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Notable payload fields (field names; session-authored prompt/answer text quoted) |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:17:58 | `session_id`, `source` (`startup`), `model`, `cwd`, `transcript_path` + emitter stamps |
| 2 | `UserPromptSubmit` | 13:17:58 | `prompt` (`Reply with exactly: OK`), `prompt_id` (`81a1f41e-…`), `permission_mode` (`bypassPermissions`), `session_id`, `cwd`, `transcript_path` |
| 3 | `Stop` | 13:18:00 | `prompt_id` (`81a1f41e-…`, matches #2), `last_assistant_message` (`OK`), `stop_hook_active` (false), `background_tasks` ([]), `session_crons` ([]), `effort`, `permission_mode` |
| 4 | `UserPromptSubmit` | 13:18:01 | `prompt` (`What is 2+2? Reply with just the number.`), `prompt_id` (`9184e884-…`), same envelope fields as #2 |
| 5 | `Stop` | 13:18:02 | `prompt_id` (`9184e884-…`, matches #4), `last_assistant_message` (`4`), rest as #3 |

Full field sets are identical in shape to the S0 capture (see the S0 evidence doc); no new fields appeared on the second turn.

## Delivery Latency and Ordering

- Turn 1: submit 13:17:58 → `Stop` 13:18:00 (≈ 2.0 s; first turn includes model warm-up).
- Turn 2: submit 13:18:01 → `Stop` 13:18:02 (≈ 1.0 s).
- Strict ordering held: `UserPromptSubmit` immediately precedes its `Stop`; `prompt_id` pairs tie each turn together (turn identity continuity across turns confirmed for the non-compaction case; s4 covers the compaction case).
- Both `Stop` events arrived before the pane showed the settled surface at 5 fps granularity (recorder samples s000010 / s000018).

## SessionEnd

`/exit` at 13:18:02; provider exited cleanly (pane shows `Resume this session with claude --resume …`). **No `SessionEnd` event arrived** — expected: it is not in the v1 subscribed set (design tiers it P2/optional). Absence recorded honestly in `run-summary.json` (`session_end_observed: false`) and the `s1-exit` label. A future arm wanting SessionEnd evidence must subscribe it explicitly.

## G2 Check (Families S1 Exercised)

| Family | Expected | Observed | Verdict |
| --- | --- | --- | --- |
| `SessionStart` | 1 | 1 | pass |
| `UserPromptSubmit` | 2 | 2 | pass |
| `Stop` | 2 | 2 | pass |
| `StopFailure`, `PermissionRequest`, `PreCompact`, `PostCompact`, `PostToolUse`, `PostToolUseFailure` | 0 (not exercised) | 0 | silent-by-design, named not ignored |

No unexpected event types; no `PostToolUse` fired (neither turn used tools — correct).

## Anomalies vs Predeclared Expectation

Expectation: "full turn cycle x2; SessionEnd on exit if supported." Both turn cycles completed with correct answers (`OK`, `4`). SessionEnd: not supported by our subscription — recorded as named absence rather than a failure. No other anomalies; provider behavior normal.

## Gate Verdicts Informed

| Gate | Verdict | Evidence |
| --- | --- | --- |
| G2 (injection honored, S1 scope) | **PASS** | every exercised family produced its events; `prompt_id` correlation intact |
| G3 (pairing) | **PASS** | 20-sample recording + 5-event stream + 3 labels; collector monotonic/UTC pair present |

## Cleanup

Runner teardown killed `hookcap-s1-1804779` and SIGTERMed the collector; no leftovers.
