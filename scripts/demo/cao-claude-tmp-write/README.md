# Claude CAO Tmp-Write Demo

This demo validates that a CAO-managed Claude Code session can create a deterministic runnable file under `tmp/` without modifying tracked repository files.

## Prerequisites

- `pixi` is installed and working.
- `tmux` is installed and available on `PATH`.
- Local CAO server access is available at `http://localhost:9889` or `http://127.0.0.1:9889`.
  - If not already running, the demo auto-starts local `cao-server` via `gig_agents.cao.tools.cao_server_launcher` and stops it on exit.
- Credential profile exists under `$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/env/vars.env`.

## What It Does

1. Builds a Claude brain manifest with `build-brain`.
2. Starts a `cao_rest` session in agent-definition root.
3. Sends a templated prompt that asks Claude to write `tmp/<unique_subdir>/hello.py`.
4. Verifies:
   - the file exists,
   - `python tmp/<unique_subdir>/hello.py` prints the sentinel,
   - `git diff --name-only` is empty.
5. Writes `report.json` and verifies it against `expected_report/report.json`.

## Run

```bash
scripts/demo/cao-claude-tmp-write/run_demo.sh
```

Optional snapshot refresh:

```bash
scripts/demo/cao-claude-tmp-write/run_demo.sh --snapshot-report
```

## Local-Only Behavior

- This demo is intentionally local-only.
- If `CAO_BASE_URL` is not `http://localhost:9889` or `http://127.0.0.1:9889`, the script exits `0` with a `SKIP:` message.

## Debugging

- The report includes `session_name` and `terminal_id`.
- Attach to tmux for live inspection:

```bash
tmux attach -t <session_name>
```

- Follow the CAO terminal pipe log from the report:

```bash
tail -f ~/.aws/cli-agent-orchestrator/logs/terminal/<terminal_id>.log
```
