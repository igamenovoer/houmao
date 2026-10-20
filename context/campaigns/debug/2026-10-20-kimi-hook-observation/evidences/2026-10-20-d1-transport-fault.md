# Evidence: D1 collector death — command fallback (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: D1. Key questions: [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/kimi-hook-capture/d1/run-20261020T135119Z/` (tmux `kimihook-d1-3951036`, pane `%244`) |
| Tool | kimi 2.2.0, `--auto`, 20 observer entries |
| Collector | gen 1, port 36855; killed immediately after `SessionStart` (1 HTTP row, then dead) |
| Recording | 42 samples; labels `d1-session-start`, `d1-fallback-turn` |
| Session | created by the D1 prompt; `SessionStart` delivered before the kill |

## Ordered Event Sequence and Channels

| Seq | Event | Channel | received_at_utc | Delivery metadata |
| --- | --- | --- | --- | --- |
| 1 | `SessionStart` | HTTP | 13:51:22.271 | collector `sequence=1`, `via: http` |
| 2 | `UserPromptSubmit` | file fallback | 13:51:22.369 | `sequence=null`, `via: command_fallback`, `emitter_seq=2` |
| 3 | `TurnStarted` | file fallback | 13:51:22.423 | `emitter_seq=3` |
| 4 | `Stop` | file fallback | 13:51:27.378 | `emitter_seq=4` |
| 5 | `SessionEnd` | file fallback | 13:51:27.913 | `emitter_seq=5` |

## Measurements

| Fact | Value |
| --- | --- |
| Ready composer | 2.9 s class |
| `SessionStart` | over HTTP before the collector stop |
| Fallback engagement | immediate for the next event (`UserPromptSubmit`) |
| Fallback ordering | `emitter_seq` 2, 3, 4, 5 strictly increasing; `sequence: null` on every fallback row |
| Session impact | none: OK answer, `Stop` 5.1 s after prompt, clean `/exit` in 1.469 s, `SessionEnd` delivered |
| Error surface | none in the pane; emitter stayed silent on stdout and always exited 0 |

## Verdict

**PASS.** The emitter's file fallback engages on collector death, preserves order via `emitter_seq`, and the kimi session is completely unaffected. The fallback path delivered the full turn plus session close. This confirms P3.2 live and the fail-open contract.

## Harness Corrections (2026-10-20)

- Scenario opening now submits the prompt to create the session, waits for `SessionStart` with a 50 ms poll, then kills the collector. Because session creation is lazy, the prompt that creates the session is also the D1 turn; the kill lands between `SessionStart` and `UserPromptSubmit` in this run, so only `SessionStart` is HTTP and the whole turn is fallback.

## Cleanup

`kimihook-d1-3951036` exited via `/exit`; collector already dead; teardown archived its status. Run root retained under `tmp/kimi-hook-capture/d1/`.
