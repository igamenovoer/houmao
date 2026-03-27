# Houmao Server Pair

`houmao-server` and `houmao-mgr` are the supported Houmao server architecture for managing agent lifecycles, gateways, and the TUI watch plane.

- `houmao-server` (`src/houmao/server/cli.py`) is the public HTTP authority — a FastAPI application created via the `create_app()` factory in `src/houmao/server/app.py`
- `houmao-mgr` (`src/houmao/srv_ctrl/cli.py`) is the manager CLI for lifecycle, agent, and server control

The two components form a single supported pair. `houmao-mgr` sends commands to `houmao-server`, which owns managed agents, gateway proxying, TUI tracking, and registry integration.

For the deeper explanation of live terminal tracking and managed-agent state, see the [Houmao Server Developer Guide](../developer/houmao-server/index.md).

## Commands

Primary entrypoints for the pair:

- `houmao-server`: serves Houmao-owned root routes, managed-agent routes, terminal-tracking routes, and a legacy `/cao/*` compatibility namespace
- `houmao-mgr`: exposes `server`, `agents`, `brains`, `mailbox`, and `admin` command groups
- `houmao-cli`: legacy runtime-local CLI, not part of the supported pair

Representative usage:

```bash
houmao-mgr server start --api-base-url http://127.0.0.1:9889
houmao-mgr server start --foreground --api-base-url http://127.0.0.1:9889
AGENTSYS_AGENT_DEF_DIR=/path/to/agents houmao-mgr agents launch --agents gpu-kernel-coder --agent-name gpu --provider codex
houmao-mgr server status --port 9889
houmao-mgr server sessions list --port 9889
houmao-mgr agents launch --agents gpu-kernel-coder --agent-name gpu --provider codex --headless
houmao-mgr agents launch --agents gpu-kernel-coder --agent-name gpu --provider claude_code
houmao-mgr agents join --agent-name gpu
houmao-mgr agents join --headless --agent-name reviewer --provider codex --launch-args exec --launch-args=--json --resume-id last
houmao-mgr mailbox init --mailbox-root tmp/shared-mail
houmao-mgr agents mailbox register --agent-name gpu --mailbox-root tmp/shared-mail
houmao-mgr agents mailbox status --agent-name gpu
houmao-mgr agents prompt --agent-name gpu --prompt "Summarize the current state."
houmao-mgr agents relaunch --agent-name gpu
houmao-mgr agents gateway attach --agent-name gpu
houmao-mgr agents gateway attach
houmao-mgr brains build --tool codex --skill skills/mailbox --config-profile dev --cred-profile openai
houmao-mgr admin cleanup-registry --grace-seconds 0
```

## Server Startup Controls

`houmao-mgr server start` is detached by default. It starts or reuses `houmao-server`, waits for health, emits one JSON startup result, and returns the terminal to the operator. Use `--foreground` when you intentionally want the old attached `houmao-server serve` behavior in the current process.

`houmao-mgr server start` and `houmao-server serve` still share the same server startup flag surface. That server-owned startup chain exposes:

- `--compat-shell-ready-timeout-seconds` with default `10.0`
- `--compat-shell-ready-poll-interval-seconds` with default `0.5`
- `--compat-provider-ready-timeout-seconds` with default `45.0`
- `--compat-provider-ready-poll-interval-seconds` with default `1.0`
- `--compat-codex-warmup-seconds` with default `2.0`

Setting `--compat-codex-warmup-seconds 0` disables the extra Codex warmup sleep. If you raise the server-side compatibility waits above the defaults, also raise `--compat-create-timeout-seconds` or `HOUMAO_COMPAT_CREATE_TIMEOUT_SECONDS` so the client budget remains larger than the server's bounded startup chain.

Example:

```bash
houmao-mgr server start \
  --api-base-url http://127.0.0.1:9889 \
  --compat-provider-ready-timeout-seconds 90 \
  --compat-codex-warmup-seconds 0
```

Detached startup result fields:

- `success`, `running`, `mode`, `api_base_url`, and `detail`
- `pid`, `server_root`, `started_at_utc`, and `current_instance` when a server instance is known
- `reused_existing` when the command reports an already-healthy listener instead of spawning a duplicate process
- `log_paths.stdout` and `log_paths.stderr`, which point at the owned files under `<runtime-root>/houmao_servers/<host>-<port>/logs/`

If detached startup fails before health, inspect:

- `<runtime-root>/houmao_servers/<host>-<port>/logs/houmao-server.stdout.log`
- `<runtime-root>/houmao_servers/<host>-<port>/logs/houmao-server.stderr.log`

Retired standalone surfaces (legacy):

- `houmao-cao-server`
- `python -m houmao.cao.tools.cao_server_launcher`
- standalone `houmao-cli` operator flows that created or controlled raw `backend="cao_rest"` sessions

## Pair-Native CLI Tree

`houmao-mgr` now has one native top-level tree for covered pair workflows:

- `server`
- `agents`
- `brains`
- `mailbox`
- `admin`

Authority is split intentionally:

- `server ...` manages the houmao-server process and server-owned sessions
- `agents launch` builds and launches locally without `houmao-server`
- `agents join` adopts an existing tmux-backed TUI or headless logical session into the same managed-agent control plane without pretending Houmao launched the current process itself
- `mailbox ...` manages the shared filesystem mailbox root and address lifecycle without `houmao-server`
- `agents mailbox ...` attaches or removes one late filesystem mailbox binding on an existing local managed agent
- `agents ...` follow-up commands discover agents through the shared registry first and only hit `houmao-server` when needed
- `brains build` is a local brain-construction wrapper
- `admin cleanup-registry` is local shared-registry maintenance

For ordinary prompt submission, `houmao-mgr agents prompt --agent-name <friendly-name> --prompt "..."` is the default documented path. `houmao-mgr agents gateway prompt --agent-name <friendly-name> --prompt "..."` remains the explicit gateway-mediated alternative when queue admission and live-gateway execution semantics matter. Retry with `--agent-id <authoritative-id>` when the friendly name is not unique.

For local serverless mailbox usage, the preferred `houmao-mgr` workflow is:

1. `houmao-mgr mailbox init --mailbox-root <path>`
2. `houmao-mgr agents launch ...` or `houmao-mgr agents join ...`
3. `houmao-mgr agents mailbox register --agent-name <friendly-name> --mailbox-root <path>`
4. `houmao-mgr agents mail ...`

This keeps `agents launch` and `agents join` mailbox-agnostic. For supported tmux-backed managed sessions, including sessions adopted through `agents join`, `agents mailbox register` and `agents mailbox unregister` refresh the live mailbox projection without requiring relaunch solely for mailbox binding refresh. That includes joined sessions whose relaunch posture is unavailable, as long as Houmao can still update the durable session state and the owning tmux live mailbox projection safely. When direct mailbox work needs the current binding set explicitly, resolve it through `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live`.

## Adopting Existing Sessions With `agents join`

`houmao-mgr agents join` is the operator path for taking a user-started tmux session and making Houmao treat it like a normal managed agent from that point onward.

Use it when:

- the provider TUI is already running and you do not want Houmao to restart it
- you already have a native headless tmux session and want later `turn submit`, `state`, `show`, or `interrupt` commands to target it through the normal managed-agent flow

V1 assumptions are intentionally narrow:

- run the command from inside the target tmux session
- tmux window `0`, pane `0` is the adopted agent surface
- TUI join auto-detects one supported provider from that pane: `claude_code`, `codex`, or `gemini_cli`
- headless join requires explicit `--provider` plus recorded `--launch-args`

Examples:

```bash
# Adopt a live TUI already running in window 0, pane 0.
houmao-mgr agents join --agent-name gpu

# Record relaunch options for a joined TUI.
houmao-mgr agents join \
  --agent-name gpu \
  --provider codex \
  --launch-args=--model \
  --launch-args gpt-5 \
  --launch-env CODEX_HOME \
  --launch-env OPENAI_API_KEY

# Adopt a native headless logical session between turns.
houmao-mgr agents join --headless \
  --agent-name reviewer \
  --provider codex \
  --launch-args exec \
  --launch-args=--json \
  --launch-env CODEX_HOME \
  --resume-id last
```

Operational behavior after a successful join:

- Houmao creates the normal runtime envelope: session root, `manifest.json`, placeholder artifacts, `gateway/`, and workspace-local `job_dir`
- the tmux session publishes the same discovery pointers as a native launch: `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, `AGENTSYS_AGENT_DEF_DIR`, and `AGENTSYS_JOB_DIR`
- the joined session is published into the shared registry immediately and becomes eligible for normal `agents state`, `agents show`, `agents prompt`, `agents interrupt`, `agents gateway attach`, and headless turn flows as appropriate

Relaunch posture is explicit:

- joined TUI sessions without recorded `--launch-args` and `--launch-env` remain controllable while live, but `agents relaunch` fails explicitly because Houmao does not know how to restart that provider honestly
- `--launch-env` follows Docker `--env` style: `NAME=value` stores a literal secret-free binding, while `NAME` means relaunch resolves that variable from the tmux session environment later
- headless `--resume-id` is optional: omitted means fresh chat, `last` means resume the latest known chat, and any other non-empty value means one exact provider session id

## Pair-Managed Gateway Attach

For pair-managed terminal sessions, the supported public attach command is `houmao-mgr agents gateway attach`.

Supported modes:

- explicit target mode: `houmao-mgr agents gateway attach --agent-name <friendly-name> --port <public-port>`
- exact-target mode: `houmao-mgr agents gateway attach --agent-id <authoritative-id> --port <public-port>`
- current-session mode: run `houmao-mgr agents gateway attach` from inside the tmux session that owns the managed agent

Current-session mode is intentionally strict:

- the tmux session must publish `AGENTSYS_MANIFEST_PATH` or, failing that, `AGENTSYS_AGENT_ID` plus a fresh shared-registry `runtime.manifest_path`
- the resolved manifest must belong to the current tmux session
- the resolved manifest must use `backend = "houmao_server_rest"`
- manifest-declared attach authority is authoritative
- current-session attach becomes valid only after launch has completed managed-agent registration on that persisted `api_base_url`

The matching relaunch surface is `houmao-mgr agents relaunch`.

- explicit relaunch resolves either `--agent-name <friendly-name>` or `--agent-id <authoritative-id>` through the managed-agent selector contract first
- current-session relaunch runs inside the owning tmux session, resolves the manifest through `AGENTSYS_MANIFEST_PATH` or shared-registry fallback from `AGENTSYS_AGENT_ID`, and refreshes the tmux-backed runtime surface without rebuilding the managed-agent home

Pair-managed tmux topology is intentionally narrow:

- tmux window `0` is the only contractual agent surface for `houmao_server_rest`
- same-session live gateway attach may create auxiliary non-zero windows inside that tmux session
- those auxiliary windows are not public contract by name, count, or order; use `houmao-mgr agents gateway status` for the authoritative live `gateway_tmux_window_index`, or inspect `gateway/run/current-instance.json` directly when you need the full tmux execution handle

## Architecture

The pair uses a Houmao-owned control core for session and terminal lifecycle management.

The control core owns:

- session and terminal lifecycle (creation, bootstrap, teardown)
- tmux session and window creation
- provider bootstrap quirks for the supported launch surface
- terminal-scoped inbox behavior
- launch-time native selector resolution
- registry persistence for sessions, terminals, and inbox messages

The watch and tracking plane is Houmao-owned and separate from the control core:

- direct tmux pane resolution and capture
- process-tree inspection for supported TUI availability
- official parser selection through the shared parser stack
- continuous in-memory terminal state and bounded recent transitions

The public server contract is Houmao-owned:

- callers talk to `houmao-server`
- legacy `/cao/*` routes are served locally by `houmao-server` for backward compatibility, not reverse-proxied to a child process
- runtime-owned `houmao_server_rest` sessions persist the public Houmao server base URL and session identity
- root `GET /health` reports `houmao_service="houmao-server"`
- terminal-keyed Houmao extension routes resolve through Houmao-owned tracked-session identity

The pair exposes three public server surfaces:

- Houmao-owned root and terminal-tracking routes:
  - `/health`
  - `/houmao/terminals/{terminal_id}/*`
- legacy compatibility routes (preserved for `cao_rest` backend sessions):
  - `/cao/health`
  - `/cao/sessions/*`
  - `/cao/terminals/*`
  - `/cao/terminals/{terminal_id}/working-directory`
- shared managed-agent routes:
  - `GET /houmao/agents`
  - `GET /houmao/agents/{agent_ref}`
  - `GET /houmao/agents/{agent_ref}/state`
  - `GET /houmao/agents/{agent_ref}/state/detail`
  - `GET /houmao/agents/{agent_ref}/history`
  - `POST /houmao/agents/{agent_ref}/requests`
  - `GET /houmao/agents/{agent_ref}/gateway`
  - `POST /houmao/agents/{agent_ref}/gateway/attach`
  - `POST /houmao/agents/{agent_ref}/gateway/detach`
  - `POST /houmao/agents/{agent_ref}/gateway/requests`
  - `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`
  - `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`
  - `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`
  - `GET /houmao/agents/{agent_ref}/mail/status`
  - `POST /houmao/agents/{agent_ref}/mail/check`
  - `POST /houmao/agents/{agent_ref}/mail/send`
  - `POST /houmao/agents/{agent_ref}/mail/reply`
- native headless lifecycle and durable turn routes:
  - `POST /houmao/agents/headless/launches`
  - `POST /houmao/agents/{agent_ref}/stop`
  - `POST /houmao/agents/{agent_ref}/turns`
  - `GET /houmao/agents/{agent_ref}/turns/{turn_id}`
  - `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`
  - `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`
  - `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr`
  - `POST /houmao/agents/{agent_ref}/interrupt`

Root `/sessions/*` and `/terminals/*` are intentionally not public at this boundary.

## Provider Surface

The preserved pair launch provider surface is explicit:

- `kiro_cli`
- `claude_code`
- `codex`
- `gemini_cli`
- `kimi_cli`
- `q_cli`

If a provider is retired later, that narrowing must be explicit. The absorption change does not narrow provider support implicitly.

## Persistence Boundary

The pair boundary is intentionally split into three groups.

Filesystem-authoritative artifacts:

- runtime-owned session roots and manifests
- runtime-owned manifest-backed gateway authority plus live gateway execution records
- shared-registry `live_agents/<agent-id>/record.json` pointers while the bridge remains in use
- server-backed managed-session manifests and session roots under `sessions/houmao_server_rest/...`
- native headless authority and per-turn records under `state/managed_agents/<tracked_agent_id>/`

Filesystem-backed debug views:

- `run/current-instance.json` and `run/houmao-server.pid`
- delegated-launch `sessions/<session-name>/registration.json`
- registry snapshot under `state/registry.json`
- launch-scoped sidecars under `state/launch_projection/`

Memory-primary live state:

- known-session registry entries rebuilt from registration records and verified against live tmux
- active watch-worker ownership
- explicit transport/process/parse state for tracked sessions
- latest parsed supported-TUI surface, derived operator state, stability metadata, and bounded recent transitions
- rebuilt managed-agent alias resolution across TUI registrations and native headless authority records

Live terminal tracking remains authoritative in server memory. `houmao-server` does not write per-terminal tracker logs for the public contract.

Managed-agent history retention is intentionally split:

- TUI-backed `GET /houmao/agents/{agent_ref}/history` is a bounded in-memory projection built from the live tracker's recent transitions. It disappears when the server process forgets or loses that tracked live state.
- Headless `GET /houmao/agents/{agent_ref}/history` is still coarse, but it is derived from persisted server-owned turn records under `state/managed_agents/<tracked_agent_id>/`.
- Durable headless stdout, stderr, event streams, and return codes remain on `/houmao/agents/{agent_ref}/turns/*`, not on `/history`.

## `houmao_server_rest` Runtime Identity

Runtime-owned sessions that use the pair-backed mode persist `backend = "houmao_server_rest"`.

That backend uses dedicated persisted sections instead of overloading the older legacy backend contract:

- session manifests write a `houmao_server` section with `api_base_url`, `session_name`, `terminal_id`, `parsing_mode`, optional `tmux_window_name`, and `turn_index`
- internal gateway bootstrap artifacts use Houmao-specific backend metadata
- shared-registry records still point back to the runtime-owned manifest and session root instead of copying runtime state into the registry

This keeps the pair-owned compatibility transport details out of the persisted public contract while preserving existing discovery and gateway flows.

## Storage Model

`houmao-server` provisions control state under a Houmao-owned per-server root:

```text
<runtime-root>/houmao_servers/<host>-<port>/
  state/
    registry.json
    launch_projection/
      <session-name>/
        <terminal-id>/
          context.md
```

Launch-time native homes and manifests remain runtime-owned under the shared runtime root:

```bash
<runtime-root>/homes/<tool>-brain-*/
<runtime-root>/manifests/<tool>-brain-*.yaml
```

Those paths are internal implementation details. The supported operator workflow launches directly from native selectors (`--agents`) resolved from the effective agent-definition root.

## Supported Operator Workflow

The supported operator workflow is the pair itself:

- `houmao-server` as the HTTP authority
- `houmao-mgr` as the management CLI

The legacy `/cao/*` compatibility routes remain as server-owned transport shims for existing `cao_rest` sessions. The following entrypoints are retired: `houmao-mgr cao ...`, top-level `houmao-mgr launch`, standalone `houmao-cao-server`, and raw standalone `cao_rest` operator entrypoints.

## Source References

- [`src/houmao/server/app.py`](../../src/houmao/server/app.py)
- [`src/houmao/server/cli.py`](../../src/houmao/server/cli.py)
- [`src/houmao/server/config.py`](../../src/houmao/server/config.py)
- [`src/houmao/server/service.py`](../../src/houmao/server/service.py)
- [`src/houmao/server/control_core/core.py`](../../src/houmao/server/control_core/core.py)
- [`src/houmao/server/control_core/provider_adapters.py`](../../src/houmao/server/control_core/provider_adapters.py)
- [`src/houmao/server/managed_agents.py`](../../src/houmao/server/managed_agents.py)
- [`src/houmao/agents/native_launch_resolver.py`](../../src/houmao/agents/native_launch_resolver.py)
- [`src/houmao/srv_ctrl/cli.py`](../../src/houmao/srv_ctrl/cli.py)
- [`src/houmao/srv_ctrl/commands/admin.py`](../../src/houmao/srv_ctrl/commands/admin.py)
- [`src/houmao/srv_ctrl/commands/brains.py`](../../src/houmao/srv_ctrl/commands/brains.py)
- [`src/houmao/srv_ctrl/commands/agents/core.py`](../../src/houmao/srv_ctrl/commands/agents/core.py)
- [`src/houmao/srv_ctrl/commands/agents/gateway.py`](../../src/houmao/srv_ctrl/commands/agents/gateway.py)
- [`src/houmao/srv_ctrl/commands/agents/mail.py`](../../src/houmao/srv_ctrl/commands/agents/mail.py)
- [`src/houmao/srv_ctrl/commands/agents/turn.py`](../../src/houmao/srv_ctrl/commands/agents/turn.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../src/houmao/agents/realm_controller/runtime.py)
