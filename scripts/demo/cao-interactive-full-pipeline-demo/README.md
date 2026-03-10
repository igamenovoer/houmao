# How Do I Keep the Interactive Claude CAO Demo Running as `alice`?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path`).

This tutorial pack answers one concrete question:

> "How do I launch a long-running Claude-on-CAO session as `alice`, send manual prompts and control keys, inspect the live session, and stop it cleanly when I'm done?"

Success means you can run the wrapper commands from this repository checkout, let `launch_alice.sh` create an isolated per-run root under `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/`, and use `run_demo.sh inspect` or `run_demo.sh verify` as advanced follow-up tools instead of as the primary walkthrough.

## Prerequisites Checklist

- [ ] `pixi` is installed.
- [ ] The repo environment is installed (`pixi install` once).
- [ ] `tmux` is available on `PATH`.
- [ ] `cao-server` is available on `PATH`, or you are prepared to let the demo replace an already-healthy local `cao-server` at `http://127.0.0.1:9889`.
- [ ] Claude credentials exist under `$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/`.
- [ ] You are running from this repository checkout.

Important notes:

- The workflow is intentionally pinned to `http://127.0.0.1:9889`; `CAO_BASE_URL` overrides are ignored for this demo pack.
- The wrapper scripts delegate to `run_demo.sh`, which keeps the repo-root-derived workspace, launcher home, worktree, and other shell defaults aligned with the underlying Python workflow engine.
- By default, `start` creates a fresh run root at `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/`, uses that directory as the CAO launcher home, and creates a nested git worktree at `<run-root>/wktree` for the interactive session workdir.
- If a verified local `cao-server` is already serving `http://127.0.0.1:9889`, startup prompts before replacing it. Pass `-y` to any wrapper script to skip that confirmation.

## Implementation Idea

1. Launch the tutorial agent with a wrapper that delegates to `run_demo.sh start --agent-name alice`.
2. Persist session state, turn artifacts, and runtime metadata in one per-run workspace so follow-up commands reuse the same interactive session through the recorded current-run marker.
3. Use `send_prompt.sh` for normal prompt turns that should capture a response artifact and update the prompt-turn history.
4. Use `send_keys.sh` for raw control input when you need to drive menus, send `Escape`, or type token-like text without treating it as a prompt turn.
5. Use `run_demo.sh inspect` whenever you want tmux attach and log-tail commands for the live session, plus the live Claude Code state.
6. Stop explicitly when you are done; only maintainers need the optional `verify` step, and it remains a minimum two-turn regression check.

## Critical Example Code (Wrapper Workflow With Inline Comments)

```bash
# 1) Launch or replace the tutorial session as alice.
scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh

# 2) Show tmux, terminal-log, and live-state details for the active session.
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect

# Optional: include the last 400 characters of clean projected Claude dialog text.
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect --with-output-text 400

# 3) Send one inline prompt through the persisted session identity.
scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh \
  --prompt "Summarize the current workspace state."

# 4) Send one raw control-input sequence without creating a prompt turn.
scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh '<[Escape]>'

# 5) Stop the active session explicitly when you are finished.
scripts/demo/cao-interactive-full-pipeline-demo/stop_demo.sh
```

## Step 1: Launch `alice`

Run the launch wrapper:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh
```

The wrapper delegates through `run_demo.sh`, which reuses the pack's default workspace and environment settings. The persisted `state.json` will record the canonicalized runtime identity `AGENTSYS-alice`, even though the wrapper-friendly input name is `alice`.

During startup, the demo now prints short progress breadcrumbs to `stderr` as it prepares the workspace, ensures CAO availability, builds the brain, and waits for the interactive Claude session to become ready. By default the command finishes with a readable session summary on `stdout`; use `run_demo.sh start --agent-name alice --json` if you need the structured payload.

Expected output shape:

```text
Interactive CAO Demo Started

Session Summary
session_status: active
agent_identity: AGENTSYS-alice
terminal_id: <terminal-id>

Commands
tmux_attach: tmux attach -t AGENTSYS-alice
terminal_log_tail: tail -f /abs/path/to/<run-root>/.aws/cli-agent-orchestrator/logs/terminal/<terminal-id>.log
```

If Claude startup takes a while, expect recurring `stderr` wait messages explaining that the demo is still waiting for the interactive session to launch and become ready for input.

By default, the launch flow creates a fresh run root under `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/`, writes state and logs there, and starts the interactive session from the nested git worktree at `<run-root>/wktree`.

If a verified local `cao-server` is already running on the fixed loopback target, the launch flow prompts before replacing it. Use `launch_alice.sh -y` for non-interactive reruns.

Before launch, the demo also resets stale `AGENTSYS-alice` state: it tries to stop the prior session, kills any leftover tmux session with that canonical name, and clears prior-run turn/report artifacts from the previously recorded run root so the replacement behaves like a fresh start.

## Step 2: Inspect the Live Session

Inspect the current session whenever you want to attach to tmux or tail the CAO terminal log:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect
```

Expected output shape:

```text
Interactive CAO Demo Inspect

Session Summary
session_status: active
claude_code_state: idle
agent_identity: AGENTSYS-alice
terminal_id: <terminal-id>

Commands
tmux_attach: tmux attach -t AGENTSYS-alice
terminal_log_tail: tail -f /abs/path/to/<run-root>/.aws/cli-agent-orchestrator/logs/terminal/<terminal-id>.log
```

This is the advanced interface mentioned throughout the tutorial. The wrappers and `run_demo.sh inspect` operate on the current run root recorded under `tmp/demo/cao-interactive-full-pipeline-demo/current_run_root.txt`, and the printed `tail -f` command resolves from the active launcher's effective home directory instead of assuming your login-shell `~/.aws/...` tree.

When the live CAO terminal is still reachable, `claude_code_state` reflects the current CAO terminal status such as `idle`, `processing`, `waiting_user_answer`, `completed`, or `error`. If the live lookup is unavailable, `inspect` still prints the persisted metadata and falls back to `claude_code_state: unknown`.

If you want a clean text tail from the current Claude UI without raw ANSI or tmux scrollback noise, request it explicitly:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect --with-output-text 500
```

That option fetches live CAO `mode=full` output, projects it through the runtime-owned Claude dialog parser, and prints only the last requested characters as `output_text_tail`. If live output or projection is unavailable, the command keeps the normal inspect metadata and reports that the clean output-text tail is unavailable instead of falling back to raw scrollback.

## Step 3: Send Prompts Manually

Send an inline prompt through the active session:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh \
  --prompt "Say hello from the interactive CAO demo."
```

Send another prompt whenever you are ready:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh \
  --prompt "Summarize the files you can see in this workspace."
```

Each call writes a turn artifact under `turns/turn-*.json` plus captured stdout and stderr logs for the underlying runtime command. Repeat this step as many times as you want; the main tutorial is intentionally open-ended.

If you prefer tracked prompt ideas while experimenting, the pack includes:

- `inputs/first_prompt.txt`
- `inputs/second_prompt.txt`

Those files are examples to copy from, not commands you must use in the primary walkthrough.

## Step 4: Send Control Input Manually

Send one raw control-input sequence through the active session when you need to shape the live UI without creating a prompt turn:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh '<[Escape]>'
```

Drive a slash-command or menu flow through the lower-level interface when you want to see the exact advanced command:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh send-keys \
  '/model<[Enter]><[Down]><[Enter]>'
```

If you want token-like text to be sent literally instead of interpreting `<[Enter]>` as a keypress, pass `--as-raw-string`:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh \
  '/model<[Enter]>' \
  --as-raw-string
```

Each control-input call writes a record under `controls/control-*.json` plus captured stdout and stderr logs for the underlying runtime command. These artifacts are intentionally separate from `turns/` because control input does not count as a prompt/response turn.

Use `run_demo.sh inspect`, tmux attach, or the terminal log tail to observe the effect after sending keys.

## Step 5: Stop the Session Explicitly

When you are done, stop the active session:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/stop_demo.sh
```

The stop flow marks `state.json` inactive even if the remote tmux or CAO session is already stale, as long as the failure matches the demo's stale-session tolerance rules.

## Maintainer Appendix: Optional Verify

`verify` is not part of the main walkthrough. Use it only when you want to confirm the existing regression contract after at least two successful prompts:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify
```

This writes `report.json` in the workspace and compares a sanitized view against [`expected_report/report.json`](expected_report/report.json) through [`scripts/verify_report.py`](scripts/verify_report.py). Even after extra manual prompts or control-input actions, `verify` remains a minimum two-turn maintainer check rather than a full transcript assertion for every recorded turn.

Refresh the tracked snapshot only when that maintainer contract changes intentionally:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify --snapshot-report
```

## Troubleshooting

- `error: No active interactive session exists. Run start before send-turn.`
  - Launch `alice` first with `launch_alice.sh`.
- `error: No active interactive session exists. Run start before send-keys.`
  - Launch `alice` first with `launch_alice.sh`.
- `error: Prompt text must not be empty.`
  - Re-run `send_prompt.sh --prompt "<text>"` with a non-empty string.
- `error: Key stream must not be empty.`
  - Re-run `send_keys.sh '<[key-stream]>'` with a non-empty positional key stream.
- `agent_identity` shows `AGENTSYS-alice` instead of `alice`
  - This is expected; the runtime canonicalizes the wrapper-friendly name before persisting state.
- CAO connectivity errors against `127.0.0.1:9889`
  - Confirm the fixed local CAO target is healthy, or ensure `cao-server` is available on `PATH` so the demo can launch one locally.
- `error: Startup aborted because the existing verified local \`cao-server\` was not replaced.`
  - Re-run `launch_alice.sh` and answer `y`, or pass `-y` to bypass the prompt.
- `error: The fixed loopback target is occupied by a process that could not be safely verified as \`cao-server\`.`
  - Stop the non-demo process on `127.0.0.1:9889` before retrying.
- `stop_demo.sh` reports stale or missing remote state
  - The local state will still be marked inactive when the failure matches the demo's tolerated stale-session markers.

## Appendix: Key Parameters

| Name | Value | Explanation |
|---|---|---|
| CAO base URL | `http://127.0.0.1:9889` | Fixed loopback target used by this demo pack. |
| Tutorial agent input | `alice` | Name passed by `launch_alice.sh`. |
| Persisted runtime identity | `AGENTSYS-alice` | Canonicalized identity recorded in `state.json`, `inspect`, and turn artifacts. |
| Workspace root | `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/` | Fresh per-run workspace for state, turns, report, logs, runtime files, and launcher config. Override with `DEMO_WORKSPACE_ROOT=/abs/path`. |
| Current-run marker | `tmp/demo/cao-interactive-full-pipeline-demo/current_run_root.txt` | Follow-up wrapper commands resolve the active/latest run root from here when `DEMO_WORKSPACE_ROOT` is omitted. |
| Agent definitions | `tests/fixtures/agents` | Default agent-definition root. Override with `AGENT_DEF_DIR=/path`. |
| Launcher home | `<workspace-root>` | Default launcher home used for CAO profile-store alignment. Override with `CAO_LAUNCHER_HOME_DIR=/path`. |
| Session workdir | `<launcher-home>/wktree` | Default git worktree created for the interactive session. Override with `DEMO_WORKDIR=/abs/path`. |
| Role name | `gpu-kernel-coder` | Default role passed through `run_demo.sh`. Override with `DEMO_ROLE_NAME=<name>`. |
| Control-input raw flag | `--as-raw-string` | Sends the provided key stream literally instead of parsing `<[key-name]>` tokens. |
| Demo-wide yes flag | `-y` | Accepted by `run_demo.sh`, `launch_alice.sh`, `send_prompt.sh`, `send_keys.sh`, and `stop_demo.sh`; bypasses prompts such as fixed-port CAO replacement. |
| Verify contract | minimum two successful turns | Optional maintainer check, not part of the main tutorial flow. |

## Appendix: File Inventory

Input files (tracked):

- `inputs/first_prompt.txt`
- `inputs/second_prompt.txt`

Expected maintainer artifact (tracked):

- `expected_report/report.json`

Scripts:

- `launch_alice.sh`
- `send_prompt.sh`
- `send_keys.sh`
- `stop_demo.sh`
- `run_demo.sh`
- `scripts/verify_report.py`

Implementation files:

- `src/gig_agents/demo/cao_interactive_demo/__init__.py`
- `src/gig_agents/demo/cao_interactive_demo/models.py`
- `src/gig_agents/demo/cao_interactive_demo/rendering.py`
- `src/gig_agents/demo/cao_interactive_demo/runtime.py`
- `src/gig_agents/demo/cao_interactive_demo/cao_server.py`
- `src/gig_agents/demo/cao_interactive_demo/commands.py`
- `src/gig_agents/demo/cao_interactive_demo/cli.py`

Generated workspace outputs (untracked):

- `current_run_root.txt` under `tmp/demo/cao-interactive-full-pipeline-demo/`
- `state.json`
- `turns/turn-*.json`
- `turns/turn-*.events.jsonl`
- `turns/turn-*.stderr.log`
- `controls/control-*.json`
- `controls/control-*.stdout.json`
- `controls/control-*.stderr.log`
- `report.json` after `verify`
- `runtime/`
- `logs/`
- `wktree/`
- `cao-server-launcher.toml`
