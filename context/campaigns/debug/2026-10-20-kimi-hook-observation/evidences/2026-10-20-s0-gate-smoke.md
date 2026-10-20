# Evidence: S0 gate smoke, amended G1 pass (kimi 2.2.0, K3-256k)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: S0 (gate). Key questions: [KQ-1](../key-questions/KQ-1-config-injection-coexistence.md), [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Amended-gate run | `tmp/kimi-hook-capture/s0/run-20261020T133111Z/` (tmux `kimihook-s0-3886839`, pane `%220`) |
| Original-criterion run | `tmp/kimi-hook-capture/s0/run-20261020T132548Z/` (zero events; gate refuted) |
| Earlier harness runs | `run-20261020T131852Z` (676 samples), `run-20261020T132224Z` (675 samples); both readiness false negatives |
| Tool | `kimi` 2.2.0 at `/home/huangzhe/.kimi-code/bin/kimi`, SHA-256 `db89c999…`, launched `--auto` |
| Scratch home | `kimi-home/` seeded by `cp` from `~/.kimi-code` at runtime; contents never read or printed by the harness |
| Hooks config | 21 `[[hooks]]` entries: 20 observer events + 1 deliberate duplicate `UserPromptSubmit` (P3.5 probe); strict read-back validation passed; `kimi doctor config` returned `OK` |
| Workspace trust | pre-seeded; no trust modal painted |
| Collector | gen 1, port 38337, five accepted events, all `via: http` |
| Recording | 5 fps active mode, 35 samples (`s000001`–`s000035`), immutable manifest, `run_tainted: false` |
| Labels | `s0-ready` and `s0-turn-ok` filled with sample ranges |
| Model cost | one short OK turn |

## Ordered Event Sequence (amended-gate run)

| Seq | Event | received_at_utc | Top-level payload field names |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:31:15.110 | `hook_event_name`, `session_id`, `source` (`startup`), `model` (`kimi-code/k3-256k`), `profile` (`agent`), `cwd`, `client_type` (`kimi_code_cli`) |
| 2 | `UserPromptSubmit` | 13:31:15.228 | `hook_event_name`, `session_id`, `cwd`, `client_type`, `prompt` (ContentPart[]: `[{type: "text", text: "Reply with exactly: OK"}]`), `is_steer` (`false`), `session_title` (`Reply with exactly: OK`) |
| 3 | `TurnStarted` | 13:31:15.286 | `hook_event_name`, `session_id`, `cwd`, `client_type`, `turn_id` (`0`, integer), `origin_kind` (`user`), `prompt` (string), `session_title` |
| 4 | `Stop` | 13:31:18.596 | `hook_event_name`, `session_id`, `cwd`, `client_type`, `session_title`, `stop_hook_active` (`false`) |
| 5 | `SessionEnd` | 13:31:19.534 | `hook_event_name`, `session_id`, `cwd`, `client_type`, `session_title`, `reason` (`exit`) |

The sequence is `SessionStart → UserPromptSubmit → TurnStarted → Stop → SessionEnd`. `SessionStart` precedes the prompt's `UserPromptSubmit`, and no permission event fired under `--auto`, as expected.

## Timings

| Milestone | Time | Source |
| --- | --- | --- |
| Process launch | 13:31:11.650 UTC (monotonic 3557822.494329) | `launch.json` `time.launched_*` |
| Ready composer | **3.219 s after launch** (13:31:14.869), zero keypresses | `composer-ready` input event |
| Prompt Enter | 13:31:14.872 (monotonic 3557825.715706) | `driver-input-events.ndjson` |
| `SessionStart` received | **0.238 s after prompt** (13:31:15.110) | collector envelope 1 |
| `UserPromptSubmit` received | 0.356 s after prompt (13:31:15.228) | collector envelope 2 |
| `TurnStarted` received | 0.414 s after prompt (13:31:15.286) | collector envelope 3 |
| `Stop` received | 3.72 s after prompt (13:31:18.596) | collector envelope 4 |
| Exit start | 13:31:19.031 | `exit_attempts[0].started_at_utc` |
| tmux session gone | 13:31:20.001 (exit took 0.968 s via `/exit`) | `exit_attempts[0]` |
| `SessionEnd` received | 13:31:19.534 | collector envelope 5 |

## Dedup Verdict (P3.5)

The scratch config carried 21 entries: the normal 20 plus a byte-identical duplicate `UserPromptSubmit` entry (same event, command, timeout 5, no matcher). One prompt produced **exactly one** `UserPromptSubmit` delivery. **Dedup holds live** (first-wins `(cwd, command)` dedup), confirming the source's `matchHooks.ts` behavior.

## Gate Verdict (amended 2026-10-20)

| Gate | Verdict | Evidence |
| --- | --- | --- |
| G1 (a) ready within 15 s, zero keypresses | PASS | 3.219 s |
| G1 (b) `SessionStart(source=startup)` within 15 s of prompt and before UPS/Stop | PASS | 0.238 s; envelope order 1 < 2 < 4; `source: startup` |
| G1 (c) turn completes with `Stop` | PASS | `Stop` received; pane shows `● OK` |
| G1 overall (amended) | **PASS** | `extra.g1.passed: true`, all five checks true |
| G2 (injection honored) | PASS for exercised families | lifecycle, prompt, turn, stop, session end all delivered |
| G3 (pairing) | PASS | 35 samples + 5-event stream + 2 labels; launch/prompt/ready monotonic stamps recorded |

### Why the original G1 failed (dated correction, 2026-10-20)

The original criterion required `SessionStart` within 15 s of launch with zero keypresses. On kimi 2.2.0 the TUI starts session-less (`SESSIONLESS_STARTUP_NOTICE`, `apps/kimi-code/src/tui/constant/kimi-tui.ts:13-14`) and creates the session lazily on the first message (`ensureSession()`, `apps/kimi-code/src/tui/kimi-tui.ts:2737-2764`). `SessionStart` is registered on `onDidCreateSession` and awaited there (`sessionExternalHooksService.ts:66-74,110-125`), so it cannot fire before a keypress. The original-criterion run produced zero events in 25 s after a 2.865 s ready composer.

Amended G1: ready within 15 s with zero keypresses; after the frozen prompt, `SessionStart(source=startup)` within 15 s and no later than the matching `UserPromptSubmit`/`Stop`; turn completes with `Stop`. This preserves the awaited-at-create proposition while matching the session-less startup.

## Harness Corrections (2026-10-20)

1. **Readiness scan corrected for inline layout.** `composer_ready()` now scans the whole visible pane for the `context:` footer plus one companion marker. The previous last-10-lines rule produced two false negatives: the ready surface occupies the top ~22 rows of a 56-row pane, with blank rows below.
2. **Surface diagnostics added.** `PaneDriver.visible_text()` logs `capture-pane-failed`; `bootstrap_session()` records `startup-surface-poll` every 25 polls and saves a timeout snapshot.
3. **S0 ordering amended.** `run_s0()` now submits the frozen prompt first, then requires `SessionStart` within 15 s of the prompt, checks `source=startup`, checks event ordering, and computes the amended G1 verdict. The pre-prompt `require_session_start()` call was removed.
4. **Dedup probe added.** `prepare_home()` appends the duplicate `UserPromptSubmit` entry for `s0` and records `hooks.dedup_probe`; `run_s0()` records delivery count and `dedup_holds`.

## Cleanup

`kimihook-s0-3886839` exited via `/exit`; runner teardown killed the tmux session and stopped the collector. Run roots remain under `tmp/kimi-hook-capture/s0/` as gitignored campaign evidence.
