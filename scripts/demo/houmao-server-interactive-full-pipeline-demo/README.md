# Houmao-Server Interactive Full-Pipeline Demo

This demo pack now exercises the local/serverless managed-agent workflow. Startup does not bring up a demo-owned `houmao-server`; instead it builds one local brain home, launches one detached local interactive managed agent, and then reuses shared-registry plus resumed-controller surfaces for inspect, prompt, interrupt, verify, and stop.

The demo still keeps explicit bounded startup waits so automation can tolerate slower provider startup:

- shell-ready timeout: `20s`
- provider-ready timeout: `120s`
- Codex warmup override: `10s`

## Prerequisites

- `pixi`
- `git`
- `tmux`
- a working Claude Code or Codex CLI, depending on the selected provider

Each `start` creates or reuses a run root under `tmp/demo/houmao-server-interactive-full-pipeline-demo/`, resolves the tracked native selector from the demo pack's `agents/` entry (a repository-tracked symlink to `tests/fixtures/agents/`), provisions a demo-owned git worktree, and launches one detached local interactive session with run-local runtime, registry, and jobs roots.

## Quick Start

Start the default Claude-backed run:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/run_demo.sh start
```

Launch the stable `alice` variant:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/launch_alice.sh
```

Start the Codex-backed variant:

```bash
scripts/demo/houmao-server-interactive-full-pipeline-demo/run_demo.sh start --provider codex
```

Tune the local startup budget explicitly:

```bash
DEMO_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS=180 \
DEMO_COMPAT_CODEX_WARMUP_SECONDS=0 \
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
2. Resolves selector `gpu-kernel-coder` from the tracked native agent-definition root `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents/`.
3. Builds one local brain home into the run-owned runtime root.
4. Launches one detached local interactive managed agent using the same underlying build and runtime surfaces as `houmao-mgr agents launch`.
5. Waits for the tracked local shell to become available and for the provider UI to reach a ready posture.
6. Writes `state.json` with the managed-agent identity tuple and run-owned runtime paths.

The persisted local contract is:

- `agent_name` is the friendly managed-agent name used for local registry lookup
- `agent_id` is the authoritative managed-agent id published by the runtime
- `tmux_session_name` is the concrete tmux session owned by the local interactive backend
- `requested_session_name` is the optional operator override supplied to `start`
- `session_manifest_path` and `session_root` point at the launched local runtime session under the run-owned runtime root

When `--session-name` is omitted, the demo derives a stable default `agent_name` from the selected variant, currently `<tool>-gpu-kernel-coder`.

## `launch_alice.sh` Behavior

`launch_alice.sh` forwards `--session-name alice` into startup. In the revised local flow, that override is used as both the friendly managed-agent name and the tmux session name for the stable wrapper contract, so the demo records:

- `requested_session_name = "alice"`
- `agent_name = "alice"`
- `tmux_session_name = "alice"`
- `agent_id = <runtime-derived id for alice>`

## Local Control Split

After startup, the demo stays local:

- `inspect` resolves the persisted managed agent through the run-local shared registry and collects managed-agent state, detail, history, and tracked-terminal state from local helper surfaces
- `send-turn` submits a prompt through the resumed local runtime controller path
- `interrupt` submits an interrupt through the resumed local runtime controller path
- `stop` resumes the local runtime controller and requests force-cleanup stop, with best-effort tmux and stale session-root cleanup
- `verify` combines prompt/interrupt artifacts with live local tracked state/history when available, and otherwise falls back to the captured local artifacts

The demo does not use a demo-owned `houmao-server`, direct server routes, or raw `send-keys` style control.

## Manual Inspection Guidance

`inspect_demo.sh` defaults to sanitized state output. It includes managed-agent availability, turn posture, last-turn result, terminal stability, and other non-text observables. Parser-derived dialog text is hidden by default. Use `--with-dialog-tail <chars>` when you explicitly want the last tracked dialog-tail excerpt from the local tracked terminal state.

Useful files inside one run root:

- `state.json`: persisted startup state and stable local identifiers
- `report.json`: sanitized verification report generated by `verify`
- `turns/turn-*.json`: prompt acceptance plus bounded post-request local state evidence
- `interrupts/interrupt-*.json`: interrupt acceptance plus bounded post-request local state evidence
- `runtime/`: build homes and local runtime session manifests owned by the run
- `registry/`: shared-registry records owned by the run
- `jobs/`: local per-session job directories owned by the run
- `wktree/`: the demo-owned git worktree used as the managed-agent working directory

The shell wrappers resolve the active run from `tmp/demo/houmao-server-interactive-full-pipeline-demo/current_run_root.txt` unless `DEMO_WORKSPACE_ROOT` is set explicitly.

Optional startup override environment variables forwarded by `run_demo.sh`:

- `DEMO_REQUEST_SETTLE_TIMEOUT_SECONDS`
- `DEMO_REQUEST_POLL_INTERVAL_SECONDS`
- `DEMO_COMPAT_SHELL_READY_TIMEOUT_SECONDS`
- `DEMO_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS`
- `DEMO_COMPAT_CODEX_WARMUP_SECONDS`
