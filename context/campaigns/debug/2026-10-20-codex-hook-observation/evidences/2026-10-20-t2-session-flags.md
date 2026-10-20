# Evidence: T2 session-flags (`-c`) injection arm (codex-cli 0.163.0, openlux-auto lane)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: T2 (P1.4). Key question: [KQ-1](../key-questions/KQ-1-unattended-trust-injection.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/codex-hook-capture/t2/run-20261020T040614Z/` (tmux `codexhook-t2-2930657`, pane `%174`) |
| Launcher | `~/.local/bin/codex-openlux-auto`, lane `openlux-auto`, profile `openlux-auto.config.toml` |
| Injection | 14 × `-c hooks.<Event>=[{hooks=[{type="command",command="<pixi python> <emit_hook.py>",timeout=5,async=false}]}]` (28 argv items) + `--dangerously-bypass-hook-trust` (29 launcher args total) |
| hooks.json | **absent by design**; verified missing after the run (`hooks_json_path: null`) |
| Collector | gen 1, port 38915 |
| Recording | 62 samples at 0.2 s, non-empty, not tainted |
| Labels | `t2-session-start`, `t2-turn` filled with digests |

Command:

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario t2
```

## Ordered Event Sequence

| Seq | Event | received_at_utc | Key fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 04:06:21.203 | `source: startup`, `model: gpt-6.1-sol`, `permission_mode: bypassPermissions`, `session_id` |
| 2 | `UserPromptSubmit` | 04:06:21.247 | `turn_id`, `prompt: "Reply with exactly: OK"` |
| 3 | `Stop` | 04:06:27.261 | `turn_id`, `last_assistant_message: "OK"` |
| 4 | `SessionEnd` | 04:06:28.112 | `reason: "other"` |

Composer ready at 04:06:17.950 (0.68 s after launch), zero keypresses, no trust modal. Prompt Enter at 04:06:21.2; `SessionStart` followed immediately; turn wall time ~6.0 s.

## Injection Shape

The generated argv pairs were of the form:

```text
-c 'hooks.SessionStart=[{hooks=[{type="command",command="/data/.../.pixi/envs/default/bin/python /data/.../emit_hook.py",timeout=5,async=false}]}]'
```

PascalCase event keys are required by `HookEventsToml` (`codex-rs/config/src/hook_config.rs:39-68`), and the harness uses them for all 14 events. The session-flags layer is trusted by the bypass flag; no user hooks file exists, so every delivered event necessarily came from the `-c` layer.

## Managed-Launch Canonicalization (P1.4 second half)

The managed Codex launch policy strips caller overrides only for unattended-owned surfaces. `_codex_override_targets_owned_surface()` (`src/houmao/agents/launch_policy/provider_hooks.py:684-706`) returns true for exactly:

- `approval_policy`
- `sandbox_mode`
- `notice.hide_full_access_warning`
- `tui.show_tooltips`
- `notice.model_migrations.*`
- `projects.*.trust_level`

`hooks.*` is **not** in that set, so `-c hooks.<Event>=[...]` survives the canonicalization and would reach Codex on the managed path. No live managed-path launch was run in this iteration; this half is source-derived and should be rechecked when the production change lands.

## KQ-1 Verdict

**P1.4 CONFIRMED (raw launcher).** Hooks injected only through `-c hooks.<Event>=[...]` execute in unattended TUI mode when combined with `--dangerously-bypass-hook-trust`: `SessionStart`, `UserPromptSubmit`, `Stop`, and `SessionEnd` all arrived, with no hooks.json in the scratch home. The managed canonicalizer's owned-surface list does not include `hooks.*`, so it should not interfere; that interaction remains to be exercised on the managed path.

**Caveat:** `-c` injection bypasses the persisted-trust mechanism (it relies on the bypass flag or on session-flags trust state). It is therefore a composable injection surface, not an auto-trust solution by itself.
