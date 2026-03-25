# Houmao-Server Interactive Full-Pipeline Demo

This demo pack is the pair-managed counterpart to the older CAO interactive full-pipeline demo. Startup goes through a demo-owned `houmao-server`, top-level `houmao-mgr install`, and detached `houmao-mgr cao launch --headless`, while every follow-up action uses direct `houmao-server` HTTP routes against the persisted server authority for that run.

The pack intentionally uses a demo-owned generous compatibility startup profile so detached launch stays reliable under automation and slow provider startup:

- shell-ready timeout: `20s`
- provider-ready timeout: `120s`
- Codex warmup override: `10s`
- detached compatibility create timeout: `180s`

## Prerequisites

- `pixi`
- `git`
- `tmux`
- a working Claude Code or Codex CLI, depending on the selected provider

The demo does not assume an operator-managed `houmao-server` is already running. Each `start` provisions a fresh run root under `tmp/demo/houmao-server-interactive-full-pipeline-demo/`, starts a loopback `houmao-server` owned by that run, installs the tracked compatibility profile, and launches one detached delegated TUI session into a demo-owned git worktree.

## Quick Start

Start the default Claude-backed run:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/run_demo.sh start
```

Launch the fixed `alice` variant:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/launch_alice.sh
```

Start the Codex-backed variant:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/run_demo.sh start --provider codex
```

Tune the demo-owned compatibility startup budget explicitly:

```bash
DEMO_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS=180 \
DEMO_COMPAT_CREATE_TIMEOUT_SECONDS=240 \
scripts/demo/houmao-server-interactive-full-pipeline-demo/run_demo.sh start --provider codex
```

Submit a prompt:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/send_prompt.sh --prompt "Summarize the current open tasks."
```

Interrupt the active turn:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/interrupt_demo.sh
```

Inspect the live run:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/inspect_demo.sh
scripts/demo/houmao-server-interactive-full-pipeline-demo/inspect_demo.sh --with-dialog-tail 400
```

Verify and stop:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/verify_demo.sh
scripts/demo/houmao-server-interactive-full-pipeline-demo/stop_demo.sh
```

## Workflow

`start` performs these steps:

1. Creates a fresh run root and a demo-owned git worktree at `<run-root>/wktree`.
2. Starts `sys.executable -m houmao.server serve` on a selected loopback port with demo-owned runtime, registry, jobs, and HOME roots.
3. Installs the tracked `gpu-kernel-coder` compatibility profile into that server through `houmao-mgr install`.
4. Launches one detached delegated TUI session through `houmao-mgr cao launch --headless --yolo` without attaching the caller terminal.
5. Waits for the delegated runtime manifest under the demo-owned run root, loads the persisted `houmao_server` bridge section, confirms the launch is already addressable through `/houmao/agents/{agent_ref}`, and writes `state.json`.

The demo-owned server start command passes explicit compatibility startup overrides into `houmao-server serve`, and the detached launch command passes an explicit compatibility create timeout into `houmao-mgr cao launch --headless`. If you override one side for a slow environment, keep the detached create timeout larger than the bounded server startup chain.

The persisted v1 route contract is:

- `agent_ref = session_name`
- `session_name` is the CAO-compatible session name created by the pair, typically `cao-<name>`
- `agent_identity` is the canonicalized operator-facing identity derived from the explicit `--session-name` override when present, or from the resolved session name otherwise

## Route Split

After startup, the demo only talks to the recorded `houmao-server` authority:

- `inspect` reads:
  - `GET /houmao/agents/{agent_ref}/state`
  - `GET /houmao/agents/{agent_ref}/state/detail`
  - `GET /houmao/agents/{agent_ref}/history`
  - `GET /houmao/terminals/{terminal_id}/state`
- `send-turn` submits:
  - `POST /houmao/agents/{agent_ref}/requests` with `request_kind = submit_prompt`
- `interrupt` submits:
  - `POST /houmao/agents/{agent_ref}/requests` with `request_kind = interrupt`
- `stop` tears down the TUI session through:
  - `POST /houmao/agents/{agent_ref}/stop`

The demo does not use post-launch `houmao-mgr agents ...`, `houmao-cli`, or any raw control-input `send-keys` equivalent.

## `launch_alice.sh` Behavior

`launch_alice.sh` forwards `--session-name alice` into startup. The pair-managed control core normalizes that to the CAO-compatible session name `cao-alice`, and the demo persists:

- `requested_session_name = "alice"`
- `session_name = "cao-alice"`
- `agent_ref = "cao-alice"`
- `agent_identity = "AGENTSYS-alice"`

This keeps the stable operator-facing override while preserving the current server-addressable session naming contract.

## Manual Inspection Guidance

`inspect_demo.sh` defaults to sanitized state output. It includes managed-agent availability, turn posture, last-turn result, terminal stability, and other non-text observables. Parser-derived dialog text is hidden by default. Use `--with-dialog-tail <chars>` when you explicitly want the last tracked dialog-tail excerpt from the server-owned tracked-terminal route.

Useful files inside one run root:

- `state.json`: persisted startup state and stable identifiers
- `report.json`: sanitized verification report generated by `verify`
- `turns/turn-*.json`: prompt-request acceptance plus bounded post-request state evidence
- `interrupts/interrupt-*.json`: interrupt-request acceptance plus bounded post-request state evidence
- `logs/houmao-server.stdout.log` and `logs/houmao-server.stderr.log`: demo-owned server logs
- `logs/install.stdout.log` and `logs/install.stderr.log`: pair-owned install logs
- `runtime/sessions/houmao_server_rest/<session-name>/manifest.json`: delegated runtime manifest discovered after launch

The shell wrappers resolve the active run from `tmp/demo/houmao-server-interactive-full-pipeline-demo/current_run_root.txt` unless `DEMO_WORKSPACE_ROOT` is set explicitly.

Optional startup override environment variables forwarded by `run_demo.sh`:

- `DEMO_SERVER_START_TIMEOUT_SECONDS`
- `DEMO_REQUEST_SETTLE_TIMEOUT_SECONDS`
- `DEMO_REQUEST_POLL_INTERVAL_SECONDS`
- `DEMO_SERVER_STOP_TIMEOUT_SECONDS`
- `DEMO_COMPAT_SHELL_READY_TIMEOUT_SECONDS`
- `DEMO_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS`
- `DEMO_COMPAT_CODEX_WARMUP_SECONDS`
- `DEMO_COMPAT_CREATE_TIMEOUT_SECONDS`
