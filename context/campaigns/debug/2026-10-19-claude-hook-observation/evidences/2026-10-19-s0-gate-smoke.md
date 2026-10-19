# Evidence: S0 gate smoke (claude 2.1.303, DeepSeek relay, deepseek-flash[1m])

Date: 2026-10-19. Iteration: [iteration 1](../iterations/2026-10-19-plan-1-hook-capture-matrix.md). Arm: S0 (gate). Key questions: [KQ-1](../key-questions/KQ-1-settings-injection.md), [KQ-2](../key-questions/KQ-2-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/hook-capture/s0/run-20261019T131518Z/` (tmux session `hookcap-s0-1799716`, pane `%94`, pane pid 1799728) |
| Tool | `claude` 2.1.303 via `~/.local/bin/claude-deepseek` (banner `Claude Code v2.1.303`; harness `launch.json` records launcher path, not binary SHA — named gap) |
| Observer settings | `observer-settings-gen1.json` (session-scoped `--settings`; 9 v1 events; secret-free, `$HOUMAO_HOOK_TOKEN` env reference) |
| Collector | gen 1, port 34267, `channel.json` started 13:15:18 UTC / monotonic 3470469.841493 |
| Model verification | banner `deepseek-flash[1m] with max effort · API Usage Billing` — **raw model id, not the friendly name** (see anomalies); gate needle matched `deepseek-flash[1m]` |
| Recording | 5 fps active mode, 10 samples (13:15:19–13:15:21), `pane_snapshots.ndjson` SHA-256 `ee00929a…`, `run_tainted` not asserted (10-sample run) |
| Labels | 2 ranges filled in `labels/labels-template.json` (s0-composer-ready, s0-turn-ok) with artifact digests |
| Hook stream | `events.ndjson` SHA-256 `16ec8d67…`, 3 events, all `via: http` (SessionStart delivered through emit_hook.py POST, not file fallback) |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Top-level payload field names |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:15:19 | `hook_event_name`, `session_id`, `source` (`startup`), `model` (`deepseek-flash[1m]`), `cwd`, `transcript_path` + emitter-added `received_at_utc`, `emitter_sequence`, `channel_generation` |
| 2 | `UserPromptSubmit` | 13:15:19 | `hook_event_name`, `session_id`, `cwd`, `transcript_path`, `prompt` (`Reply with exactly: OK`), `prompt_id`, `permission_mode` (`bypassPermissions`) — **no `source` field** |
| 3 | `Stop` | 13:15:20 | `hook_event_name`, `session_id`, `cwd`, `transcript_path`, `prompt_id`, `permission_mode`, `stop_hook_active` (false), `last_assistant_message` (`OK`), `background_tasks` ([]), `session_crons` ([]), `effort` (`{level: max}`) |

## Delivery Latency

- `SessionStart`: collector `started_at_utc` 13:15:18, claude `launched_at_utc` 13:15:19 (monotonic 3470469.789), event received 13:15:19 — **under 1 s, far inside the 15 s G1 window**. Provider start to hook delivery effectively immediate.
- `UserPromptSubmit`: Enter pressed 13:15:19 (driver log monotonic 3470470.467); event received 13:15:19 — sub-second.
- `Stop`: prompt submitted 13:15:19; `Stop` received 13:15:20; pane answer settle visible at sample s000008 (13:15:21). Turn wall time ≈ 1.6 s. The hook arrived **before** the 5 fps pane showed the settled surface (recorder granularity, not a discrepancy).

## Anomalies vs Predeclared Expectation

Expectation: `SessionStart` + `UserPromptSubmit` + `Stop` arrive; provider behavior unchanged. **All met; provider answered `OK` normally.**

Named observations (not failures):

1. **Banner renders the raw model id.** The launcher's friendly-name pin (`ANTHROPIC_DEFAULT_SONNET_MODEL_NAME='DeepSeek Flash'`) does not reach the 2.1.303 banner; it shows `deepseek-flash[1m] with max effort · API Usage Billing`. First S0 attempt (run-20261019T131232Z) aborted on the original `DeepSeek Flash` needle — harness bug, fixed to accept the launcher-pinned id, one retry per gate policy. Campaign note: the plan's "DeepSeek Flash" bootstrap needle must read as "the launcher-pinned model", which the TUI renders as the raw id.
2. **No trust dialog on 2.1.303** for a fresh git-less workdir under `--dangerously-skip-permissions` (prior campaign's 2.1.296 recon saw `Quick safety check` even under bypass). Bootstrap logged `trust dialog accepted: False` and proceeded on composer markers. Design section 6 trust precondition may be satisfied by default on this build for this posture.
3. **Payload shape deltas vs design section 1 inventory**: `Stop` carries an unlisted `effort` field; `UserPromptSubmit` omits the optional `source`. Both harmless for the channel; KQ-3 catalog must record actual fields, not assumed ones.
4. `SessionStart` `source` is `startup` (design lists `clear`/`fork`/`resume`/`compact` semantics) — s7 will tell whether `--resume` yields a distinct value.

## Gate Verdicts Informed

| Gate | Verdict | Evidence |
| --- | --- | --- |
| G0 (harness) | PASS | self-test 4/4 earlier today |
| G1 (S0 smoke) | **PASS** | SessionStart < 1 s; prompt answered; model gate passed (pinned id); provider normal |
| G2 (injection honored) | partial | 3 families exercised produced events; silent families named: `StopFailure`, `PermissionRequest`, `PreCompact`, `PostCompact`, `PostToolUse`, `PostToolUseFailure` (not exercised by S0 — recorded, not ignored) |
| G3 (pairing) | PASS | pane recording (10 samples) + events.ndjson + labels; `channel.json` carries `started_at_utc` 13:15:18 + `started_monotonic` 3470469.841493 for alignment; recorder `manifest.json` has `started_at_utc` |

## Cleanup

`hookcap-s0-1799716` killed by runner teardown; no collector process left (`pgrep -f collector.py` clean after the run).
