# Claude CAO Esc-Interrupt Demo

This demo validates that a CAO-managed Claude Code session can be interrupted with a real tmux `Esc` keypress and can still answer a follow-up prompt.

## Prerequisites

- `pixi` is installed and working.
- `tmux` is installed and available on `PATH`.
- Local CAO server access is available at `http://localhost:9889` or `http://127.0.0.1:9889`.
  - If not already running, the demo auto-starts local `cao-server` via `gig_agents.cao.tools.cao_server_launcher` and stops it on exit.
  - If launcher start reuses a healthy local server with unknown ownership (`pid` unresolved), the demo retries with launcher `stop`/`start` and skips with explicit ownership diagnostics if still untracked.
- Credential profile exists under `$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/env/vars.env`.

## What It Does

1. Builds a Claude brain manifest with `build-brain`.
2. Starts a `cao_rest` runtime session.
   - The session passes `--cao-profile-store` aligned with launcher home (`$CAO_LAUNCHER_HOME_DIR/.aws/cli-agent-orchestrator/agent-store` by default).
3. Runs `scripts/interrupt_driver.py` to:
   - submit a long-ish first prompt,
   - wait for `processing`,
   - resolve tmux target via `GET /terminals/{id}` (`terminal.name`),
   - send `Esc` using `tmux send-keys -t <session_name>:<window_name> Escape`,
   - wait for `idle`,
   - submit a second prompt and extract a non-empty answer.
4. Writes `report.json` and verifies it against `expected_report/report.json`.

## Run

```bash
scripts/demo/cao-claude-esc-interrupt/run_demo.sh
```

Optional snapshot refresh:

```bash
scripts/demo/cao-claude-esc-interrupt/run_demo.sh --snapshot-report
```

## Local-Only Behavior

- This demo is intentionally local-only because it injects a key into local tmux.
- If `CAO_BASE_URL` is not `http://localhost:9889` or `http://127.0.0.1:9889`, the script exits `0` with a `SKIP:` message.
- If processing is not observed quickly after first prompt, the script exits `0` with `SKIP:` to avoid flaky false failures.
- If CAO cannot load the generated runtime profile, the script exits `0` with `SKIP: CAO profile store mismatch` (not `missing credentials`).

## Debugging

- The report includes `session_name`, `window_name`, `terminal_id`, and `terminal_log_path`.
- Attach to tmux for live inspection:

```bash
tmux attach -t <session_name>
```

- Follow the CAO terminal pipe log from the report:

```bash
tail -f ~/.aws/cli-agent-orchestrator/logs/terminal/<terminal_id>.log
```
