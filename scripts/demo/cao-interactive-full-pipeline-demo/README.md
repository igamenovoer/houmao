# How Do I Run the Interactive CAO Demo With Claude or Codex?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path`).

This demo pack answers one concrete question:

> "How do I launch a long-running CAO-backed session, keep using the same workspace across prompts and control input, inspect the live terminal, and stop it cleanly when I'm done?"

The pack now uses one recipe-first startup contract for both Claude and Codex. If you omit `--brain-recipe`, the demo implicitly uses `claude/gpu-kernel-coder-default`. If you run `launch_alice.sh`, the wrapper still injects `--agent-name alice`, so the persisted runtime identity becomes `AGENTSYS-alice` even though the selected recipe has its own default name.

## Prerequisites Checklist

- [ ] `pixi` is installed.
- [ ] The repo environment is installed once with `pixi install`.
- [ ] `tmux` is available on `PATH`.
- [ ] `cao-server` is available on `PATH`, or you are prepared to let the demo replace an already-healthy local `cao-server` at `http://127.0.0.1:9889`.
  Recommended install: `uv tool install --upgrade git+https://github.com/imsight-forks/cli-agent-orchestrator.git@hz-release`
- [ ] Claude credentials exist under `$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/` if you want the default Claude path.
- [ ] Codex credentials exist under `$AGENT_DEF_DIR/brains/api-creds/codex/personal-a-default/` or `$AGENT_DEF_DIR/brains/api-creds/codex/yunwu-openai/` if you want one of the Codex paths.
- [ ] You are running from this repository checkout.

Important notes:

- The workflow is intentionally pinned to `http://127.0.0.1:9889`; `CAO_BASE_URL` overrides are ignored for this demo pack.
- The wrapper scripts delegate to `run_demo.sh`, which keeps the repo-root-derived workspace, launcher home, worktree, and other shell defaults aligned with the underlying Python workflow engine.
- By default, `start` creates a fresh run root at `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/`, uses that directory as the CAO launcher home, and creates a nested git worktree at `<run-root>/wktree` for the interactive session workdir. That nested layout is a demo-owned isolation default, not a repo-owned CAO requirement.
- If startup finds a verified local `cao-server` already healthy at `http://127.0.0.1:9889`, it replaces that server automatically for the new run. There is no replacement prompt anymore.
- Direct `run_demo.sh start` uses the selected recipe's `default_agent_name` unless you supply `--agent-name`.
- `launch_alice.sh` is only a convenience wrapper. Its special behavior is just `--agent-name alice`.
- The demo still passes `AGENT_DEF_DIR` explicitly for brain build and session start, but follow-up prompt/control/stop flows target the persisted runtime name and let `realm_controller` recover the effective agent-definition root from the live tmux session.
- The persisted `agent_identity` stays canonical (`AGENTSYS-<name>`), while `session_name`, `tmux_target`, and surfaced attach commands use the actual live tmux handle (`AGENTSYS-<name>-<agent-id-prefix>`).

## Supported Startup Recipes

The demo resolves selectors relative to `brains/brain-recipes/` under the active agent-definition directory. `.yaml` is optional.

- Default implicit recipe: `claude/gpu-kernel-coder-default`
- Explicit Claude recipe: `claude/gpu-kernel-coder-default`
- Explicit Codex recipe: `codex/gpu-kernel-coder-default`
- Explicit Codex Yunwu recipe: `codex/gpu-kernel-coder-yunwu-openai`

Selectors may be basename-only when they are unique. For example, `gpu-kernel-coder-yunwu-openai` resolves to `codex/gpu-kernel-coder-yunwu-openai`.

The basename `gpu-kernel-coder-default` is intentionally ambiguous because both `claude/gpu-kernel-coder-default` and `codex/gpu-kernel-coder-default` exist. In that case the command fails with an explicit error such as:

```text
error: Multiple brain recipes matched `gpu-kernel-coder-default`: claude/gpu-kernel-coder-default, codex/gpu-kernel-coder-default. Retry with subdirectory context, for example `--brain-recipe claude/gpu-kernel-coder-default`.
```

## Implementation Idea

1. Start the session from one tracked recipe.
2. Persist the resolved `tool`, `variant_id`, and canonical `brain_recipe` in `state.json`.
3. Reuse that persisted state for `inspect`, `send-turn`, `send-keys`, `verify`, and `stop`, including runtime-owned recovery of the active session's agent-definition root for name-addressed control.
4. Use `launch_alice.sh` when you want the tutorial-friendly `alice` identity, or use `run_demo.sh start` directly when you want the recipe-defined default name or a custom `--agent-name`.

## Critical Example Code

```bash
# 1) Easiest tutorial launch: default Claude recipe, but force the name to alice.
scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh

# 2) Same wrapper, but launch Codex with the same alice override.
scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh \
  --brain-recipe codex/gpu-kernel-coder-default

# 3) Direct launch with the recipe-defined default agent name.
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start

# 4) Direct launch with an explicit Codex variant and an explicit custom name.
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start \
  --brain-recipe codex/gpu-kernel-coder-yunwu-openai \
  --agent-name gpu-demo

# 5) Inspect the active session and optionally include clean projected dialog text.
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect --with-output-text 400

# 6) Drive the live session.
scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh \
  --prompt "Summarize the current workspace state."
scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh '<[Escape]>'

# 7) Stop explicitly when you are done.
scripts/demo/cao-interactive-full-pipeline-demo/stop_demo.sh
```

## Step 1: Launch a Session

Wrapper path:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh
```

The wrapper forwards through `run_demo.sh start --agent-name alice`. With no explicit recipe selector, that means the session is backed by `claude/gpu-kernel-coder-default`, but the persisted identity is still `AGENTSYS-alice`.
The live tmux handle is distinct and will typically look like `AGENTSYS-alice-<agent-id-prefix>`.

Direct recipe-backed path:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start
```

That command uses the default Claude recipe and the recipe-defined default agent name `cao-claude-demo`, which becomes `AGENTSYS-cao-claude-demo` after canonicalization.

Explicit Codex example:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start \
  --brain-recipe codex/gpu-kernel-coder-default
```

That command uses the Codex recipe-defined default agent name `cao-codex-demo`, which becomes `AGENTSYS-cao-codex-demo`.

Expected output shape:

```text
Interactive CAO Demo Started

Session Summary
session_status: active
tool: claude
variant_id: claude-gpu-kernel-coder-default
brain_recipe: claude/gpu-kernel-coder-default
agent_identity: AGENTSYS-alice
tmux_attach: tmux attach -t AGENTSYS-alice-<agent-id-prefix>
terminal_id: <terminal-id>
```

Startup progress prints to `stderr` while the demo prepares the workspace, ensures CAO availability, builds the recipe-selected brain, and waits for the interactive session to become ready.

## Step 2: Inspect the Live Session

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect
```

Expected output shape:

```text
Interactive CAO Demo Inspect

Session Summary
session_status: active
tool: claude
variant_id: claude-gpu-kernel-coder-default
brain_recipe: claude/gpu-kernel-coder-default
tool_state: idle
agent_identity: AGENTSYS-alice
session_name: AGENTSYS-alice-<agent-id-prefix>
```

`tool_state` is the live CAO terminal status for the persisted session and may be `idle`, `processing`, `waiting_user_answer`, `completed`, `error`, or `unknown`.

If you want a clean text tail instead of raw scrollback, request it explicitly:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect --with-output-text 500
```

That command fetches CAO `mode=full` output and projects it through the runtime-owned parser stack for the persisted tool. Claude launches use the Claude parser; Codex launches use the Codex parser.

## Step 3: Send Prompts Manually

```bash
scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh \
  --prompt "Say hello from the interactive CAO demo."
```

Each prompt writes a turn artifact under `turns/turn-*.json` plus the captured stdout and stderr logs for the underlying runtime command.

Because the follow-up runtime call targets the persisted `AGENTSYS-...` name, the demo does not pass an explicit `--agent-def-dir` on this path; runtime recovers it from the session's tmux environment.
Use the surfaced `tmux_attach` command or `session_name` from `inspect` when you need to attach manually; do not assume the live tmux handle is exactly the canonical `agent_identity`.

## Step 4: Send Control Input Manually

```bash
scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh '<[Escape]>'
```

If you want token-like text to be sent literally instead of interpreting `<[Enter]>` as a keypress, pass `--as-raw-string`:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh \
  '/model<[Enter]>' \
  --as-raw-string
```

Control-input artifacts live under `controls/` and do not count as prompt turns for `verify`.

Like prompt turns, these name-addressed control-input calls rely on the live session's tmux-published `AGENTSYS_AGENT_DEF_DIR` instead of passing `--agent-def-dir` explicitly.

## Step 5: Stop the Session Explicitly

```bash
scripts/demo/cao-interactive-full-pipeline-demo/stop_demo.sh
```

The stop flow marks `state.json` inactive even if the remote tmux or CAO session is already stale, as long as the failure matches the demo's stale-session tolerance rules.

This stop path also targets the persisted agent name and relies on the same tmux-session-derived agent-definition-root default.

## Maintainer Appendix: Optional Verify

`verify` is not part of the main walkthrough. Use it after at least two successful prompts:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify
```

This writes `report.json` in the workspace and compares a sanitized view against the variant-specific snapshot in `expected_report/<variant-id>.json` through [`scripts/verify_report.py`](scripts/verify_report.py). Even after extra manual prompts or control-input actions, `verify` remains a minimum two-turn maintainer check rather than a full transcript assertion for every recorded turn.

Refresh the tracked snapshot only when that maintainer contract changes intentionally:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify --snapshot-report
```

## Troubleshooting

- `error: No active interactive session exists. Run start before send-turn.`
  - Launch a session first with `launch_alice.sh` or `run_demo.sh start`.
- `error: No active interactive session exists. Run start before send-keys.`
  - Launch a session first with `launch_alice.sh` or `run_demo.sh start`.
- `agent_identity` shows `AGENTSYS-alice` instead of `alice`
  - This is expected; the runtime canonicalizes the wrapper-friendly override before persisting state.
- `tool_state: unknown`
  - The session metadata still exists, but live CAO terminal lookup failed.
- CAO connectivity errors against `127.0.0.1:9889`
  - Confirm the fixed local CAO target is healthy, or ensure `cao-server` is available on `PATH` so the demo can launch one locally.
- `error: Multiple brain recipes matched \`gpu-kernel-coder-default\``
  - Retry with subdirectory context such as `--brain-recipe claude/gpu-kernel-coder-default` or `--brain-recipe codex/gpu-kernel-coder-default`.

## Appendix: Key Parameters

| Name | Value | Explanation |
| --- | --- | --- |
| CAO base URL | `http://127.0.0.1:9889` | Fixed loopback target used by this demo pack. |
| Default implicit recipe | `claude/gpu-kernel-coder-default` | Used when `run_demo.sh start` omits `--brain-recipe`. |
| Wrapper override name | `alice` | `launch_alice.sh` injects this through `--agent-name alice`. |
| Direct Claude default name | `cao-claude-demo` | Default name carried by `claude/gpu-kernel-coder-default`. |
| Direct Codex default name | `cao-codex-demo` | Default name carried by the tracked Codex recipes. |
| Workspace root | `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/` | Fresh per-run workspace for state, turns, report, logs, runtime files, and launcher config. Override with `DEMO_WORKSPACE_ROOT=/abs/path`. |
| Current-run marker | `tmp/demo/cao-interactive-full-pipeline-demo/current_run_root.txt` | Follow-up wrapper commands resolve the active/latest run root from here when `DEMO_WORKSPACE_ROOT` is omitted. |
| Agent definitions | `tests/fixtures/agents` | Default agent-definition root. Override with `AGENT_DEF_DIR=/path`. |
| Launcher home | `<workspace-root>` | Default launcher home used for CAO profile-store alignment. Override with `CAO_LAUNCHER_HOME_DIR=/path`. |
| Session workdir | `<launcher-home>/wktree` | Default git worktree created for the interactive session for demo isolation. Override with `DEMO_WORKDIR=/abs/path`. |
| Role name | `gpu-kernel-coder` | Default role passed through `run_demo.sh`. Override with `DEMO_ROLE_NAME=<name>`. |
| Verify snapshots | `expected_report/<variant-id>.json` | Variant-specific maintainer snapshot files. |

## Appendix: File Inventory

Input files:

- `inputs/first_prompt.txt`
- `inputs/second_prompt.txt`

Expected maintainer artifacts:

- `expected_report/claude-gpu-kernel-coder-default.json`
- `expected_report/codex-gpu-kernel-coder-default.json`
- `expected_report/codex-gpu-kernel-coder-yunwu-openai.json`

Scripts:

- `launch_alice.sh`
- `send_prompt.sh`
- `send_keys.sh`
- `stop_demo.sh`
- `run_demo.sh`
- `scripts/verify_report.py`

Implementation files:

- `src/houmao/demo/cao_interactive_demo/brain_recipes.py`
- `src/houmao/demo/cao_interactive_demo/models.py`
- `src/houmao/demo/cao_interactive_demo/cli.py`
- `src/houmao/demo/cao_interactive_demo/commands.py`
- `src/houmao/demo/cao_interactive_demo/runtime.py`
- `src/houmao/demo/cao_interactive_demo/rendering.py`
- `src/houmao/demo/cao_interactive_demo/cao_server.py`
