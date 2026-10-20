# Evidence: S0 gate smoke on the OpenLux lane (codex-cli 0.163.0)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: S0 (gate, P1.1). Key question: [KQ-1](../key-questions/KQ-1-unattended-trust-injection.md).

Supersedes the failed GAC attempt in [2026-10-20-s0-gate-smoke.md](2026-10-20-s0-gate-smoke.md) after the lane switch recorded in the campaign intent and iteration plan.

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/codex-hook-capture/s0/run-20261020T035949Z/` (tmux `codexhook-s0-2916034`, pane `%160`) |
| Launcher | `~/.local/bin/codex-openlux-auto` (lane `openlux-auto`, profile `openlux-auto.config.toml`) |
| Tool | `codex-cli 0.163.0` |
| Flags | `--dangerously-bypass-hook-trust` (no pre-trust) |
| Hook config | `codex-home/hooks.json`, 14 events, sha256 `5b0c1325…` |
| Collector | gen 1, port 36371, started 03:59:49.553Z |
| Recording | 137 samples at 0.2 s, non-empty, not tainted |
| Labels | `s0-ready`, `s0-turn-ok` filled with digests |

Command:

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s0
```

## Ordered Event Sequence

| Seq | Event | received_at_utc | Monotonic | Key payload fields |
| --- | --- | --- | --- | --- |
| 1 | `SessionStart` | 03:59:53.225 | 3523544.068849 | `session_id`, `source: "startup"`, `model: "gpt-6.1-sol"`, `permission_mode: "bypassPermissions"`, `cwd`, `transcript_path` |
| 2 | `UserPromptSubmit` | 03:59:53.269 | 3523544.112690 | `turn_id: 01a15777-374a-7062-bbbb-ef07d728cef0`, `prompt: "Reply with exactly: OK"`, `model`, `permission_mode` |
| 3 | `Stop` | 04:00:19.594 | 3523570.438390 | `turn_id` matches, `last_assistant_message: "OK"`, `stop_hook_active: false` |
| 4 | `SessionEnd` | 04:00:20.187 | 3523571.030913 | `reason: "other"`, no `turn_id` |

All four arrived `via: http` through `emit_hook.py`.

## Gate Measurements

- Launch 03:59:49.329Z; composer ready at 03:59:50.004Z (**0.68 s**), **zero keypresses**, no trust modal.
- Prompt Enter at 03:59:53.161 (monotonic 3523544.005299).
- `SessionStart` 64 ms after Enter (3.90 s after launch), `UserPromptSubmit` 44 ms after that, both before the provider call.
- Provider round-trip: busy state from s000016; assistant `OK` visible at recorder sample s000132 (04:00:19, elapsed 30.3 s); `Stop` at 04:00:19.594 with `last_assistant_message: "OK"`. Turn wall time ≈ 26.4 s.
- `/quit` at 04:00:20.142; `SessionEnd` 45 ms later.

**G1 result: PASS.** The composer is reached unattended, there is no trust modal, `SessionStart`/`UserPromptSubmit` arrive, and `Stop` proves the model round-trip works. The predeclared "SessionStart with zero keypresses" wording remains corrected to first-turn scope: Codex 0.163 queues startup `SessionStart` and dispatches it when the first turn starts (`core/src/session/turn.rs:340`), so the event cannot precede any input at an idle composer.

## Model Identity

- Hook payload `model`: **`gpt-6.1-sol`** (all payloads that carry it).
- TUI status line: **`GPT-6.1-Sol default`**, with `permissions: YOLO mode` under the OpenLux launcher.
- The status line text differs from the payload slug only in display casing/label; the provider is OpenLux (`https://api.openlux.ai/v1` profile).

## Pane Observations

- Composer: `› Ask Codex to do anything`.
- Startup banner: `>_ OpenAI Codex (v0.163.0)`, workdir line, `permissions: YOLO mode`.
- Busy: `• Working (Ns • esc to interrupt)`; no reconnect/error text.
- Footer: `? for shortcuts` and `⚠ 5 warnings · f2 to view` (warnings not inspected; includes the expected `Interrupt` timeout clamp).
- Answer surface: `• OK` under the prompt, then the composer returns.

## KQ-1 Verdict

**P1.1 CONFIRMED (trust/injection half).** `hooks.json` plus `--dangerously-bypass-hook-trust` installs and executes the observer hooks in unattended TUI mode with no trust modal and no keypresses before the composer. `SessionStart` is first-turn scoped, arrives 64 ms after the first prompt's Enter, and the full turn cycle completes (`UserPromptSubmit` → `Stop` with `OK`). The lane responds, so G1 passes on OpenLux.
