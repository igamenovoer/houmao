# Evidence: S7 resume, session-id continuity, H1 hot-reload (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: S7. Key questions: [KQ-1](../key-questions/KQ-1-config-injection-coexistence.md), [KQ-2](../key-questions/KQ-2-event-availability-payloads.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/kimi-hook-capture/s7/run-20261020T134720Z/` (gen 1 tmux `kimihook-s7-3942407`, pane `%236`; gen 2 `kimihook-s7-resume-3942407`) |
| Tool | kimi 2.2.0, `--auto`, 20 observer entries; H1 marker entry appended between generations through `append_raw_toml_block()` |
| Collector | generation 1 port 33419; generation 2 port 33419-bump (see `launch.json`), 10 accepted events total |
| Recording | gen 1 42 samples (`pane-recording`); gen 2 37 samples (`pane-recording-resume`) |
| Labels | `s7-first-turn`, `s7-exit`, `s7-resume` |

## Ordered Event Sequence

| Seq | Gen | Event | received_at_utc | Key fields |
| --- | --- | --- | --- | --- |
| 1 | 1 | `SessionStart` | 13:47:23.269 | `source=startup`, session id `session_a8ef893e-6859-48da-aff2-d220e6133fea` |
| 2 | 1 | `UserPromptSubmit` | 13:47:23.385 | OK prompt |
| 3 | 1 | `TurnStarted` | 13:47:23.444 | `turn_id=0` |
| 4 | 1 | `Stop` | 13:47:28.391 | turn end |
| 5 | 1 | `SessionEnd` | 13:47:29.187 | `reason=exit` |
| 6 | 2 | `SessionStart` | 13:47:31.058 | `source=resume`, **same session id** |
| 7 | 2 | `UserPromptSubmit` | 13:47:33.756 | post-resume OK prompt |
| 8 | 2 | `TurnStarted` | 13:47:33.815 | `turn_id=1` (session-scoped counter continues; **corrected 2026-10-20 by replay**) |
| 9 | 2 | `Stop` | 13:47:37.449 | turn end |
| 10 | 2 | `SessionEnd` | 13:47:38.209 | `reason=exit` |

## Measurements

| Fact | Value |
| --- | --- |
| Gen 1 `SessionStart` | 0.247 s after first prompt, `source=startup` |
| Gen 1 exit | `/exit` 1.467 s, `SessionEnd` 13:47:29.187 |
| Marker append | 13:47:30.153, config sha256 `45bdbd53…`, unvalidated raw block |
| Gen 2 ready | 3.283 s after resume launch |
| Gen 2 `SessionStart` | **0.796 s after resume launch, before the post-resume prompt**, `source=resume` |
| Session id | identical across generations (`session_a8ef893e…`) |
| `SessionStart.session_title` | present in gen 2 (restored title), absent in gen 1 fresh start |
| H1 marker mid-session | absent in S1 after mid-session append |
| H1 marker after restart | **FIRED** on the post-resume `UserPromptSubmit`; recorded `s7_hot_reload_marker_fired_after_restart=true` |
| Gen 2 exit | `/exit` 1.467 s; `SessionEnd(reason=exit)` 13:47:38.209 |

## Payload Observations

- Resume `SessionStart` carries `session_title` (the restored first prompt title); a fresh `SessionStart` does not, because the title does not exist at creation.
- `turn_id` continued at **1** in the resumed generation (`0` in gen 1): the session-scoped turn counter does **not** restart at 0 after resume. The replay phase corrected the earlier capture note, which read the gen 2 row as `turn_id=0`; `raw-provider-payloads.ndjson` row 8 carries `"turn_id": 1` (dated correction 2026-10-20).
- The resumed `SessionStart` fires at launch, not at the first message, because `--continue` creates/restores the session immediately.
- `SessionEnd(reason=exit)` fires in both generations.

## Verdict

**PASS.** `SessionStart(source=resume)` with session-id continuity, clean `SessionEnd` in both generations, load-once confirmed by the mid-session marker absence, and the appended marker hook firing only after restart. This is the E1c hot-reload answer: hooks load once per process; a restart is required.

## Harness Corrections (2026-10-20)

- Gen 1 opening now submits the OK prompt before requiring `SessionStart`.
- Resume path now probes for a pre-prompt `SessionStart` for up to 15 s and falls back to a prompt-created session; on this run it arrived pre-prompt.
- No other S7-specific correction.

## Cleanup

Both tmux sessions ended; collector generations stopped and archived. Run root retained under `tmp/kimi-hook-capture/s7/`.
