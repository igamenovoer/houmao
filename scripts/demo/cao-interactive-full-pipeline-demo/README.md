# Interactive Claude CAO Full-Pipeline Demo

This demo pack provides a repeatable interactive CAO workflow for Claude Code. Instead of auto-tearing down after one prompt, it keeps a tmux-backed `cao_rest` session alive until you explicitly stop it, and it stores the session identity plus inspection metadata in a stable workspace state file.

## Prerequisites

- `pixi` is installed and working.
- `tmux` is installed and available on `PATH`.
- A healthy CAO server is reachable at `http://127.0.0.1:9889`.
  - If the fixed loopback CAO target is not already healthy, the demo uses `gig_agents.cao.tools.cao_server_launcher` and requires `cao-server` on `PATH`.
  - The workflow is intentionally pinned to `http://127.0.0.1:9889`; `CAO_BASE_URL` overrides are ignored.
- Claude credentials exist under `$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/`.

## Workspace Layout

The demo uses a stable workspace rooted at `tmp/cao_interactive_full_pipeline_demo` by default.

- `state.json`: active/inactive session metadata, including `agent_identity`, `session_manifest`, `tmux_target`, `terminal_id`, and `terminal_log_path`
- `turns/`: one JSON artifact plus captured stdout/stderr logs per `send-turn`
- `report.json`: verification report emitted by `verify`
- `runtime/`: generated brain/session runtime artifacts

Override the workspace root with `DEMO_WORKSPACE_ROOT=/abs/path`.

## Operator Workflow

Start or replace the interactive session:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start --agent-name interactive-demo
```

If the previous `state.json` is still marked active, `start` first issues `brain_launch_runtime stop-session --agent-identity <previous-name>` and then replaces the state with the new session metadata.

Inspect the live session:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect
```

The inspect output prints the `tmux attach` command and the `tail -f` command for the CAO terminal log recorded in `state.json`.

Drive prompts through the same session identity:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh send-turn --prompt-file scripts/demo/cao-interactive-full-pipeline-demo/inputs/first_prompt.txt
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh send-turn --prompt-file scripts/demo/cao-interactive-full-pipeline-demo/inputs/second_prompt.txt
```

The demo stores each turn under `turns/turn-*.json`, recording the prompt, timestamps, runtime exit status, and extracted response text. `send-turn` fails if the response text is empty.

Generate and verify a report after at least two turns:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify
```

`verify` writes `report.json` and then runs [`scripts/verify_report.py`](scripts/verify_report.py) against [`expected_report/report.json`](expected_report/report.json). The verifier asserts that one `agent_identity` was reused across at least two turns and that the recorded responses are non-empty.

Refresh the expected snapshot if the sanitized report contract changes intentionally:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify --snapshot-report
```

Stop the session explicitly when you are done:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh stop
```

If the remote tmux/CAO session is already gone, `stop` still marks the local `state.json` inactive as long as the failure looks like stale or missing remote state.
