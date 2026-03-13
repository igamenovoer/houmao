# Claude CAO Tmp-Write Demo

This demo validates that a CAO-managed Claude Code session can create a deterministic runnable file under `tmp/` without modifying tracked repository files.

## Prerequisites

- `pixi` is installed and working.
- `tmux` is installed and available on `PATH`.
- Local CAO server access is available at supported loopback URLs like `http://localhost:9889` or `http://127.0.0.1:9991`.
  Recommended install if you need a local CAO binary: `uv tool install --upgrade git+https://github.com/imsight-forks/cli-agent-orchestrator.git@hz-release`
  - If not already running, the demo auto-starts local `cao-server` via `houmao.cao.tools.cao_server_launcher` and stops it on exit.
  - If launcher start reuses a healthy local server with unknown ownership (`pid` unresolved), the demo retries with launcher `stop`/`start` and skips with explicit ownership diagnostics if still untracked.
- Credential profile exists under `$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/env/vars.env`.

## What It Does

1. Builds a Claude brain manifest with `build-brain`.
2. Starts a `cao_rest` session in agent-definition root.
   - The session passes `--cao-profile-store` aligned with launcher home (`$CAO_LAUNCHER_HOME_DIR/.aws/cli-agent-orchestrator/agent-store` by default).
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
- If `CAO_BASE_URL` is not a supported loopback URL (`http://localhost:<port>` or `http://127.0.0.1:<port>`), the script exits `0` with a `SKIP:` message.
- If CAO cannot load the generated runtime profile, the script exits `0` with `SKIP: CAO profile store mismatch` (not `missing credentials`).

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
