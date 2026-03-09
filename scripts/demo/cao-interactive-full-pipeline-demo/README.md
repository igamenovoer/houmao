# How Do I Keep the Interactive Claude CAO Demo Running as `alice`?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path`).

This tutorial pack answers one concrete question:

> "How do I launch a long-running Claude-on-CAO session as `alice`, send manual prompts, inspect the live session, and stop it cleanly when I'm done?"

Success means you can run the wrapper commands from this repository checkout, keep one stable workspace under `tmp/cao_interactive_full_pipeline_demo`, and use `run_demo.sh inspect` or `run_demo.sh verify` as advanced follow-up tools instead of as the primary walkthrough.

## Prerequisites Checklist

- [ ] `pixi` is installed.
- [ ] The repo environment is installed (`pixi install` once).
- [ ] `tmux` is available on `PATH`.
- [ ] A healthy CAO server is reachable at `http://127.0.0.1:9889`, or `cao-server` is available on `PATH` so the demo can launch one locally if needed.
- [ ] Claude credentials exist under `$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/`.
- [ ] You are running from this repository checkout.

Important notes:

- The workflow is intentionally pinned to `http://127.0.0.1:9889`; `CAO_BASE_URL` overrides are ignored for this demo pack.
- The wrapper scripts delegate to `run_demo.sh`, which keeps the workspace, launcher home, and other shell defaults aligned with the underlying Python workflow engine.

## Implementation Idea

1. Launch the tutorial agent with a wrapper that delegates to `run_demo.sh start --agent-name alice`.
2. Persist session state, turn artifacts, and runtime metadata in one stable workspace so follow-up commands reuse the same interactive session.
3. Use `run_demo.sh inspect` whenever you want tmux attach and log-tail commands for the live session.
4. Stop explicitly when you are done; only maintainers need the optional `verify` step, and it remains a minimum two-turn regression check.

## Critical Example Code (Wrapper Workflow With Inline Comments)

```bash
# 1) Launch or replace the tutorial session as alice.
scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh

# 2) Show tmux and terminal-log commands for the active session.
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect

# 3) Send one inline prompt through the persisted session identity.
scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh \
  --prompt "Summarize the current workspace state."

# 4) Stop the active session explicitly when you are finished.
scripts/demo/cao-interactive-full-pipeline-demo/stop_demo.sh
```

## Step 1: Launch `alice`

Run the launch wrapper:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh
```

The wrapper delegates through `run_demo.sh`, which reuses the pack's default workspace and environment settings. The persisted `state.json` will record the canonicalized runtime identity `AGENTSYS-alice`, even though the wrapper-friendly input name is `alice`.

Expected JSON excerpt:

```json
{
  "state": {
    "active": true,
    "agent_identity": "AGENTSYS-alice"
  }
}
```

If the previous state is still marked active, the launch flow first stops the earlier session and then replaces it with the new `alice` session metadata.

## Step 2: Inspect the Live Session

Inspect the current session whenever you want to attach to tmux or tail the CAO terminal log:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect
```

Expected output shape:

```text
active: True
agent_identity: AGENTSYS-alice
tmux_attach: tmux attach -t AGENTSYS-alice
terminal_log_tail: tail -f ~/.aws/cli-agent-orchestrator/logs/terminal/<terminal-id>.log
```

This is the advanced interface mentioned throughout the tutorial. The new wrappers and `run_demo.sh inspect` operate on the same persisted workspace state.

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

## Step 4: Stop the Session Explicitly

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

This writes `report.json` in the workspace and compares a sanitized view against [`expected_report/report.json`](expected_report/report.json) through [`scripts/verify_report.py`](scripts/verify_report.py). Even after extra manual prompts, `verify` remains a minimum two-turn maintainer check rather than a full transcript assertion for every recorded turn.

Refresh the tracked snapshot only when that maintainer contract changes intentionally:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify --snapshot-report
```

## Troubleshooting

- `error: No active interactive session exists. Run start before send-turn.`
  - Launch `alice` first with `launch_alice.sh`.
- `error: Prompt text must not be empty.`
  - Re-run `send_prompt.sh --prompt "<text>"` with a non-empty string.
- `agent_identity` shows `AGENTSYS-alice` instead of `alice`
  - This is expected; the runtime canonicalizes the wrapper-friendly name before persisting state.
- CAO connectivity errors against `127.0.0.1:9889`
  - Confirm the fixed local CAO target is healthy, or ensure `cao-server` is available on `PATH` so the demo can launch one locally.
- `stop_demo.sh` reports stale or missing remote state
  - The local state will still be marked inactive when the failure matches the demo's tolerated stale-session markers.

## Appendix: Key Parameters

| Name | Value | Explanation |
|---|---|---|
| CAO base URL | `http://127.0.0.1:9889` | Fixed loopback target used by this demo pack. |
| Tutorial agent input | `alice` | Name passed by `launch_alice.sh`. |
| Persisted runtime identity | `AGENTSYS-alice` | Canonicalized identity recorded in `state.json`, `inspect`, and turn artifacts. |
| Workspace root | `tmp/cao_interactive_full_pipeline_demo` | Stable workspace for state, turns, report, logs, and runtime files. Override with `DEMO_WORKSPACE_ROOT=/abs/path`. |
| Agent definitions | `tests/fixtures/agents` | Default agent-definition root. Override with `AGENT_DEF_DIR=/path`. |
| Launcher home | `tmp/cao_interactive_full_pipeline_demo` | Default launcher home used for CAO profile-store alignment. Override with `CAO_LAUNCHER_HOME_DIR=/path`. |
| Role name | `gpu-kernel-coder` | Default role passed through `run_demo.sh`. Override with `DEMO_ROLE_NAME=<name>`. |
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
- `stop_demo.sh`
- `run_demo.sh`
- `scripts/verify_report.py`

Implementation files:

- `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py`

Generated workspace outputs (untracked):

- `state.json`
- `turns/turn-*.json`
- `turns/turn-*.events.jsonl`
- `turns/turn-*.stderr.log`
- `report.json` after `verify`
- `runtime/`
- `logs/`
- `cao-server-launcher.toml`
