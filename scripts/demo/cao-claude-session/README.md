# Claude CAO Runtime Demo

This tutorial pack demonstrates a real CAO-backed Claude Code session: build a brain home, start a CAO runtime session, send one prompt, and verify that a non-empty response is returned.

## Prerequisites

- `pixi` is installed and working.
- `tmux` is installed and available on `PATH`.
- `cao-server` is installed and available on `PATH`.
  Recommended install: `uv tool install --upgrade git+https://github.com/imsight-forks/cli-agent-orchestrator.git@hz-release`
  - By default, the demo auto-starts a local CAO server at `http://localhost:9889` via `gig_agents.cao.tools.cao_server_launcher` and stops it on exit.
  - If `CAO_BASE_URL` is another supported loopback URL such as `http://127.0.0.1:9991`, the demo auto-starts or reuses that selected local port through the launcher.
  - If an untracked local `cao-server` is already healthy on the selected loopback port, the demo restarts it to ensure runtime/profile-store alignment.
  - If you set `CAO_BASE_URL` to a non-loopback URL, the demo expects that server to already be running.
- Credential profile exists under `$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/`.

## What It Does

1. Uses `build-brain` for tool `claude` with local config + creds profile.
2. Starts a `cao_rest` runtime session.
   - The session writes the generated CAO agent profile to the same store used by the launched server (`$CAO_LAUNCHER_HOME_DIR/.aws/cli-agent-orchestrator/agent-store` by default).
3. Sends one prompt from [`inputs/prompt.txt`](inputs/prompt.txt).
4. Verifies the generated report against [`expected_report/report.json`](expected_report/report.json).

## Run

```bash
scripts/demo/cao-claude-session/run_demo.sh
```

Optional snapshot refresh:

```bash
scripts/demo/cao-claude-session/run_demo.sh --snapshot-report
```

## Verify

- The script writes a runtime report under `tmp/demo_cao_claude_*/report.json`.
- Verification is done by [`scripts/verify_report.py`](scripts/verify_report.py).
- The verifier enforces:
  - non-empty `response_text`,
  - `backend == "cao_rest"`,
  - `tool == "claude"`,
  - sanitized shape matches `expected_report/report.json`.

## SKIP Behavior

The demo exits `0` with a `SKIP:` message when:

- credentials are missing,
- credentials are invalid/unauthorized,
- CAO/service connectivity is unavailable.

Unexpected failures (for example invalid script assumptions or missing required binaries) exit non-zero.
