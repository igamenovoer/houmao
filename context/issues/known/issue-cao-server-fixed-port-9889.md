# Issue: Orphan Upstream CAO Reference Is Fixed To localhost:9889

## Summary

The orphan upstream CLI Agent Orchestrator (CAO) reference in this repo
(`extern/orphan/cli-agent-orchestrator`, version `1.1.0`) is still fixed to
`localhost:9889`.

That orphan snapshot is now historical context, not the supported launcher
contract for this repo. The tracked CAO fork used by our launcher/runtime path
supports port selection through `CAO_PORT`, and this repo now supports
launcher-managed loopback URLs on `http://localhost:<port>` and
`http://127.0.0.1:<port>`.

If your installed `cao-server` binary comes from an older upstream build that
still ignores `CAO_PORT`, launcher start on a non-default port fails explicitly
instead of silently falling back to `9889`.

## Evidence (Upstream Source)

CAO defines server host/port constants:

- `SERVER_HOST = "localhost"`
- `SERVER_PORT = 9889`

Source: `extern/orphan/cli-agent-orchestrator/src/cli_agent_orchestrator/constants.py`

The `cao-server` console script runs uvicorn using those constants:

- `uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)`

Source: `extern/orphan/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py`

There is no `click`/`argparse` parsing layer for `cao-server` (it maps directly
to `cli_agent_orchestrator.api.main:main` via `pyproject.toml`).

## Current Repo Behavior

- `gig_agents.cao.tools.cao_server_launcher` accepts loopback URLs with explicit
  ports and passes the selected port to `cao-server` through `CAO_PORT`.
- Launcher runtime artifacts remain partitioned under
  `runtime_root/cao-server/<host>-<port>/`.
- Runtime CAO REST calls and tmux env composition apply loopback `NO_PROXY`
  behavior to supported loopback hosts on any explicit port.
- The interactive CAO demo and the CAO launcher tutorial/demo pack remain
  intentionally pinned to `127.0.0.1:9889`.

## Why This Note Still Matters

- The orphan source tree is still useful as a historical reference for why this
  repo originally assumed `9889`.
- If a developer installs an older `cao-server` build from outside the tracked
  fork, non-default launcher ports may still fail because that binary ignores
  `CAO_PORT`.

## Operator Guidance

- Preferred install: `uv tool install --upgrade git+https://github.com/imsight-forks/cli-agent-orchestrator.git@hz-release`
- Verify the active binary with `command -v cao-server`.
- For a one-shot non-default local port, run launcher commands with
  `--base-url http://127.0.0.1:9991` (or another loopback port).
- If launcher `start` says the spawned process appears to ignore `CAO_PORT`,
  upgrade the installed `cao-server` binary and retry.
