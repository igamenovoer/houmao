# Evidence: S0 gate smoke (codex-cli 0.163.0, codex-gac lane, gpt-6.1-sol)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: S0 (gate) plus the failed-run record for the first gate attempt. Key question: [KQ-1](../key-questions/KQ-1-unattended-trust-injection.md) (P1.1 bypass arm).

**Iteration status at the time: STOPPED at G1.** The hook/trust half of S0 works, but the credential lane returns HTTP 402 (no active subscription), so the "GAC lane responds / `Stop` arrives" condition failed.

**Superseded on 2026-10-20:** the campaign switched lanes to `codex-openlux-auto`; the successful S0 gate is recorded in [2026-10-20-s0-gate-smoke-openlux.md](2026-10-20-s0-gate-smoke-openlux.md). This document remains the dated record of the GAC 402 blocker and the SessionStart gate-misfire fix. T1/T2/S2 were subsequently run on OpenLux.

## Runs

| Component | Run 1 (flawed, gate misfire) | Run 2 (gate retry) |
| --- | --- | --- |
| Run root | `tmp/codex-hook-capture/s0/run-20261020T034822Z/` | `tmp/codex-hook-capture/s0/run-20261020T035053Z/` |
| tmux / pane | `codexhook-s0-2897268` / `%156` | `codexhook-s0-2900954` / `%158` |
| Launched | 2026-10-20T03:48:22.849Z (mono 3522853.692469) | 2026-10-20T03:50:53.382Z (mono 3523004.226455) |
| Codex | `codex-cli 0.163.0`, native binary sha256 `8a96f66d…`, shim sha256 `61b0194f…` | same (`launch.json`) |
| Flags | `--dangerously-bypass-hook-trust` (no pre-trust) | same |
| Scratch home | `codex-home/` with `hooks.json` (14 events, 1 sync command handler each; sha256 `5b0c1325…`) + `config.toml` workspace trust preseed | same hooks sha256 |
| Collector | gen 1, port 45141, started 03:48:23.069Z | gen 1, port 35843, started 03:50:53.607Z |
| Recording | 5 fps active, 92 samples, interval 0.2 s, not tainted | 5 fps active, 558 samples, interval 0.2 s, not tainted |
| Labels | filled (`s0-ready`; `s0-turn-ok` = not reached) | filled (`s0-ready`, `s0-turn-ok` = provider failure, `s0-provider-402`) |
| Hook stream | 1 event (`SessionEnd`) | 3 events (`SessionStart`, `UserPromptSubmit`, `SessionEnd`); no `Stop` |
| Outcome | aborted at the pre-prompt gate | run completed; provider call failed 402 |

Artifact digests are in each `labels/labels-template.json`. Raw run roots stay under `tmp/` and are not committed.

## Run 1: gate misfire (driver bug, not a product finding)

The runner's bootstrap waited up to 20 s for `SessionStart` **before submitting any prompt**. The pane reached the composer at 03:48:23.527 (0.68 s after launch, zero keypresses, no trust modal), but no `SessionStart` arrived, so the run aborted at 03:48:43.537. `SessionEnd` (seq 1, 03:48:43.809) was delivered by teardown, which already proved hooks were installed and executing.

Cause, confirmed in the campaign baseline source: Codex 0.163 queues the startup `SessionStart` source at session creation (`codex-rs/core/src/session/session.rs:1993`) and dispatches it only from `run_pending_session_start_hooks` when the first turn starts (`codex-rs/core/src/session/turn.rs:340`; the `SessionEnd` dispatcher is independent). A TUI sitting at the composer with zero keypresses can therefore never produce `SessionStart` at this version. The predeclared G1 wording ("within 15 s of provider start with ZERO keypresses") is unsatisfiable as written; the hook gate must move to the first frozen prompt.

Driver fix (recorded below) moved the gate to first-turn start. This run is retained as the flawed-run record and is not counted as S0 evidence for hook delivery.

## Run 2: ordered event sequence

| Seq | Event | received_at_utc | Monotonic | Key payload fields |
| --- | --- | --- | --- | --- |
| 1 | `SessionStart` | 03:50:57.267 | 3523008.110655 | `session_id`, `source: "startup"`, `model: "gpt-6.1-sol"`, `permission_mode: "bypassPermissions"`, `cwd`, `transcript_path` |
| 2 | `UserPromptSubmit` | 03:50:57.311 | 3523008.155402 | `session_id`, `turn_id: 01a1576f-09b3-7d20-b9ee-c150b5153742`, `model`, `permission_mode`, `prompt: "Reply with exactly: OK"`, `cwd`, `transcript_path` |
| 3 | `SessionEnd` | 03:52:58.294 | 3523129.137649 | `session_id`, `reason: "other"`, `cwd`, `transcript_path` (no `turn_id`) |

No `Stop`, `PreModelRequest`, or `PostModelRequest` arrived. The turn ended in a provider error, and the source-derived expectation is that `Stop` fires only on normal completion; this run is consistent with that, but the provider failure means it is not clean evidence for the no-`Stop`-on-error rule.

## Delivery latency

- Composer ready: **0.66 s after launch** (03:50:54.046, monotonic 3523004.889822), zero keypresses, no hooks trust modal. Pane sample s000001 at 03:50:54.010 already shows `› Ask Codex to do anything`.
- First prompt Enter: 03:50:57.202 (monotonic 3523008.045656).
- `SessionStart`: received 03:50:57.267, **65 ms after Enter**; 3.885 s after process launch.
- `UserPromptSubmit`: 44 ms later, before the provider call.
- Provider failure surface: sample s000024 at 03:50:59 (6.18 s after recorder start): `Working (1s • esc to interrupt)` → `Reconnecting... 1/5` → `Unexpected status 402 Payment Required: Access denied: No active subscription, url: https://gaccode.com/codex/v1/responses`.
- Exit: `/quit` Enter 03:52:58.238; `SessionEnd` 56 ms later.

Because the first prompt is only sent after the 3 s pre-prompt observation window, `SessionStart` lands ~3.9 s after launch, inside the 15 s grace even though the zero-keypress wording is not met. Hook execution itself begins at first-turn start.

## Provider failure (the G1 blocker)

The frozen prompt was accepted by the TUI and the two pre-model hooks fired, but the GAC relay returned **HTTP 402 Payment Required: "Access denied: No active subscription"**. The TUI retried (`Reconnecting... 1/5`) and then surfaced the error in the transcript. No `Stop` was emitted. This is an account/lane condition, not a harness or hook-config failure:

- The same scratch home and `hooks.json` produced `SessionStart`, `UserPromptSubmit`, and `SessionEnd`, all `via: http`.
- The provider error body names `https://gaccode.com/codex/v1/responses`, the lane's configured relay.
- No credential material was read, printed, or copied; the runner never touches the API key.

Gate G1 therefore **FAILS** on "the GAC lane responds". The prompt was not answered and `Stop` never arrived, so the S0 turn-cycle expectation is unmet.

## TUI observations worth carrying forward

- Composer placeholder: `› Ask Codex to do anything`.
- Startup banner: `>_ OpenAI Codex (v0.163.0)`, workdir line, then `permissions: YOLO mode` (the approvals bypass from `codex-gac`).
- Model/status line: `GPT-6.1-Sol default · <workdir>`; footer `? for shortcuts`.
- Busy indicator: `• Working (1s • esc to interrupt)`; reconnect state: `• Reconnecting... 1/5 (1s • esc to interrupt)` followed by an indented `└ Unexpected status …` line.
- Footer shows `⚠ 5 warnings · f2 to view` from startup onward. The warnings were not inspected (would require f2 and is outside KQ-1); the count was identical in both runs, so it is not caused by the 402. One known contributor is the expected `Interrupt` 5 s → 3 s timeout clamp warning.
- No hooks trust modal appeared in either run: `--dangerously-bypass-hook-trust` suppresses the TUI review (`startup_hooks_review.rs::review_is_needed`).

## KQ-1 proposition verdicts

| Proposition | Verdict | Evidence |
| --- | --- | --- |
| P1.1 Bypass flag runs hooks unattended | **SUPPORTED for trust/injection, with a timing correction.** `hooks.json` + `--dangerously-bypass-hook-trust` produced installed handlers with no trust modal and no keypresses before the composer (0.66 s). `SessionStart` is first-turn scoped, so it arrives 65 ms after the first prompt's Enter, not before any input; `UserPromptSubmit` follows 44 ms later. The full G1 gate is still **FAIL** because the provider returned 402 and `Stop` never arrived. | Run 2 events 1-2; driver log; pane samples s000001/s000015-s000024 |
| P1.2 Pre-trusted-hash arm | **NOT EXECUTED** (stopped at G1). The T1 perturbation driver support was implemented but no live T1 session was run; hash reimplementation remains live-unvalidated. | n/a |
| P1.3 Control failure mode | **NOT EXECUTED** (stopped at G1). No S2 modal/skip evidence at 0.163.0 yet. | n/a |
| P1.4 Session-flags (`-c`) injection | **NOT EXECUTED** (stopped at G1). | n/a |

## Driver fixes made to `scripts/explore/codex-hook-observation/run_capture.py`

All are runner-level; `src/` and the collector/emitter/hash core were not modified.

1. `bootstrap_session` no longer hard-fails when `SessionStart` is absent before the first prompt. It records `session-start-pre-prompt` after a 3 s observation and defers the gate (`run_capture.py:1258-1275`).
2. New `require_session_start_on_first_turn()` enforces `SessionStart` after each arm's first frozen prompt, where 0.163 dispatches it (`run_capture.py:1316`). Wired into s0/t1/t2 (via `run_s0`), s1, s3 step 1, s4, s5, s6, and both s7 generations.
3. S2 interactive trust is now marker-driven: `interactive_trust_all()` reads the pane after each key and only presses Enter when `›` is on "Trust all and continue" (`run_capture.py:1160`). The previous blind `Down/Enter/Enter` was wrong because the list starts with no selection, so one Down selects "Review hooks". This fix is **not live-exercised** (S2 not run).
4. T1 now has the predeclared perturbation half: `run_t1()` runs the OK turn, appends ` # t1-perturbation` to only the `SessionStart` command in place (same path, same `[hooks.state]` hash), relaunches on the same scratch home with a second collector generation, and records trust-modal vs composer vs silent-skip (`run_capture.py:1382`, `run_capture.py:1422`). **Not live-exercised**.
5. Scenario dispatch passes the relaunch context to T1 (`run_capture.py:2130`).
6. S2 post-trust now records whether `SessionStart` arrives after the interactive trust write and degrades its event waits instead of hanging when hooks stay dead.

Harness self-test still passes after the edits (`SELF-TEST PASSED`; ruff check/format clean).

## Deviations and open items

- **Gate wording amendment required:** G1's "SessionStart within 15 s of provider start with zero keypresses" must read "within 15 s of provider start, first-turn scoped (arrives at the first prompt)". The zero-keypress half is impossible at 0.163.0 by construction.
- **Provider lane blocker:** the GAC relay answers 402 "No active subscription". T1/T2/S2 were stopped per the gate rule. If the parent wants the KQ-1 trust propositions anyway, they are still testable at near-zero token cost: `SessionStart`/`UserPromptSubmit` fire before the failing model call, and S2's hash-write validation needs only the trust modal. That decision is left to the campaign owner.
- The `5 warnings` footer counter is unexplained; not inspected.
- Run 1 is a flawed run (gate misfire) and is kept only as the driver-fix record.

## Cleanup

Both tmux sessions and recorders were torn down by the runner; `pgrep` shows no `collector.py` or `terminal_record` leftovers; no campaign tmux sessions remain. Pane recordings are non-empty (92 and 558 samples) and `run_tainted=false` in both manifests.
