# Issue: Upstream CAO Server Port Is Fixed (localhost:9889)

## Summary

In the upstream CLI Agent Orchestrator (CAO) implementation we reference in this
repo (`extern/orphan/cli-agent-orchestrator`, version `1.1.0`), the `cao-server`
entrypoint binds to `localhost:9889` via hard-coded constants and does not
expose a supported way to change host/port (no CLI flags and no env var
override).

If your `cao-server` binary comes from a different CAO version (for example via
`uv tool install`), verify whether upstream behavior has changed; do not assume
port configurability exists unless you confirm it in that installed version.

This is an upstream limitation that affects our ability to:

- run multiple local CAO servers in parallel on different ports, and
- choose an alternate port to avoid collisions with an existing process.

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

## Impact on This Repo

- Our defaults (for example `--cao-base-url http://localhost:9889`) match
  upstream, but any workflow that wants a different port cannot rely on vanilla
  `cao-server`.
- Any “CAO server launcher” we build must treat port selection as *not
  controllable* when launching upstream `cao-server` (unless upstream changes).

## Workarounds

If you must expose CAO on a different port without modifying upstream code:

- Run a local TCP forwarder (for example `socat`) from an alternate port to
  `localhost:9889` (still only one CAO server process).
- Run CAO in a container and use port mapping (container listens on 9889, host
  maps to another port).

If you require multiple CAO servers on the same host concurrently, upstream CAO
would need to support configurable host/port (or you need isolated network
namespaces/containers).
