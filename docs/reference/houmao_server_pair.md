# Houmao Server Pair

`houmao-server` and `houmao-mgr` are the supported Houmao-managed replacement pair for `cao-server` and `cao`.

The intent of this pair is narrow and explicit:

- `houmao-server` is the public HTTP authority
- `houmao-mgr` is the pair-management CLI
- mixed pairs such as `houmao-server + cao` or `cao-server + houmao-mgr` are unsupported

For the deeper explanation of live terminal tracking and managed-agent state, see the [Houmao Server Developer Guide](../developer/houmao-server/index.md).

## Compatibility Source Of Truth

Compatibility for this pair is pinned to one exact upstream CAO source:

- Repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- Commit: `0fb3e5196570586593736a21262996ca622f53b6`
- Tracked local checkout: `extern/tracked/cli-agent-orchestrator`

That exact commit is the parity oracle for the CAO-compatible HTTP and CLI behavior implemented here. It is not a runtime dependency for the supported pair.

## Commands

Primary entrypoints for the pair:

- `houmao-server`: serves Houmao-owned root routes plus the explicit `/cao/*` compatibility namespace
- `houmao-mgr`: exposes `server`, `agents`, `brains`, and `admin`
- `houmao-cli`: remains available for uncovered or intentionally runtime-local workflows

Representative usage:

```bash
houmao-mgr server start --api-base-url http://127.0.0.1:9889
houmao-mgr server start --foreground --api-base-url http://127.0.0.1:9889
AGENTSYS_AGENT_DEF_DIR=/path/to/agents houmao-mgr agents launch --agents gpu-kernel-coder --provider codex
houmao-mgr server status --port 9889
houmao-mgr server sessions list --port 9889
houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --headless
houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code
houmao-mgr agents prompt AGENTSYS-gpu --prompt "Summarize the current state."
houmao-mgr agents gateway attach AGENTSYS-gpu
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

Retired standalone surfaces:

- `houmao-cao-server`
- `python -m houmao.cao.tools.cao_server_launcher`
- standalone `houmao-cli` operator flows that would create or control raw `backend="cao_rest"` sessions

## Pair-Native CLI Tree

`houmao-mgr` now has one native top-level tree for covered pair workflows:

- `server`
- `agents`
- `brains`
- `admin`

Authority is split intentionally:

- `server ...` manages the houmao-server process and server-owned sessions
- `agents launch` builds and launches locally without `houmao-server`
- `agents ...` follow-up commands discover agents through the shared registry first and only hit `houmao-server` when needed
- `brains build` is a local brain-construction wrapper
- `admin cleanup-registry` is local shared-registry maintenance

For ordinary prompt submission, `houmao-mgr agents prompt <agent-ref> --prompt "..."` is the default documented path. `houmao-mgr agents gateway prompt <agent-ref> --prompt "..."` remains the explicit gateway-mediated alternative when queue admission and live-gateway execution semantics matter.

## Pair-Managed Gateway Attach

For pair-managed terminal sessions, the supported public attach command is `houmao-mgr agents gateway attach`.

Supported modes:

- explicit target mode: `houmao-mgr agents gateway attach <agent-ref> --port <public-port>`
- current-session mode: run `houmao-mgr agents gateway attach` from inside the tmux session that owns the managed agent

Current-session mode is intentionally strict:

- the tmux session must publish `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- those pointers must resolve to one readable runtime-owned `attach.json` and gateway root for the same tmux session
- the attach contract must use `backend = "houmao_server_rest"`
- persisted `backend_metadata.api_base_url` and `backend_metadata.session_name` are authoritative
- current-session attach becomes valid only after launch has both published gateway capability and completed managed-agent registration on that persisted `api_base_url`

Pair-managed tmux topology is intentionally narrow:

- tmux window `0` is the only contractual agent surface for `houmao_server_rest`
- same-session live gateway attach may create auxiliary non-zero windows inside that tmux session
- those auxiliary windows are not public contract by name, count, or order; the only authoritative non-zero window handle is the one recorded in `gateway/run/current-instance.json`

## Architecture

The pair now uses a Houmao-owned native compatibility control core behind the preserved `/cao/*` surface.

That control core owns:

- CAO-compatible session and terminal lifecycle
- tmux session and window creation
- provider bootstrap quirks for the supported pair launch surface
- terminal-scoped compatibility inbox behavior
- launch-time native selector resolution and compatibility sidecar projection
- compatibility registry persistence for sessions, terminals, and inbox messages

The watch and tracking plane remains Houmao-owned and separate from the compatibility control slice:

- direct tmux pane resolution and capture
- process-tree inspection for supported TUI availability
- official parser selection through the shared parser stack
- continuous in-memory terminal state and bounded recent transitions

The public server contract stays Houmao-owned:

- callers talk to `houmao-server`
- `/cao/*` is served locally by `houmao-server`, not reverse-proxied to a child `cao-server`
- runtime-owned `houmao_server_rest` sessions persist the public Houmao server base URL and session identity
- root `GET /health` keeps `service="cli-agent-orchestrator"` and adds `houmao_service="houmao-server"` without `child_cao`
- terminal-keyed Houmao extension routes resolve through Houmao-owned tracked-session identity instead of through child-process state

The pair exposes three public server surfaces:

- Houmao-owned root and terminal-tracking routes:
  - `/health`
  - `/houmao/terminals/{terminal_id}/*`
- explicit CAO-compatible routes:
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
- runtime-owned gateway attach contracts and live gateway execution records
- shared-registry `live_agents/<agent-id>/record.json` pointers while the bridge remains in use
- server-backed managed-session manifests and session roots under `sessions/houmao_server_rest/...`
- native headless authority and per-turn records under `state/managed_agents/<tracked_agent_id>/`

Filesystem-backed compatibility and debug views:

- `run/current-instance.json` and `run/houmao-server.pid`
- delegated-launch `sessions/<session-name>/registration.json`
- compatibility registry snapshot under `state/cao_compat/registry.json`
- launch-scoped compatibility sidecars under `state/cao_compat/launch_projection/`

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

That backend uses dedicated persisted sections instead of overloading the older `cao_rest` contract:

- session manifests write a `houmao_server` section with `api_base_url`, `session_name`, `terminal_id`, `parsing_mode`, optional `tmux_window_name`, and `turn_index`
- gateway attach contracts use Houmao-specific backend metadata
- shared-registry records still point back to the runtime-owned manifest and session root instead of copying runtime state into the registry

This keeps the pair-owned compatibility transport details out of the persisted public contract while preserving existing discovery and gateway flows.

## Compatibility Storage Model

`houmao-server` provisions compatibility control state under a Houmao-owned per-server root:

```text
<runtime-root>/houmao_servers/<host>-<port>/
  state/
    cao_compat/
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

## Migration Direction

This pair is a migration strategy with Houmao as the public authority.

The supported operator workflow is the pair itself:

- `houmao-server`
- `houmao-mgr`

The explicit `/cao/*` compatibility routes remain server-owned transport shims, but `houmao-mgr cao ...`, top-level `houmao-mgr launch`, standalone `houmao-cao-server`, and raw standalone `cao_rest` operator entrypoints are retired.

## Source References

- [`src/houmao/server/app.py`](../../src/houmao/server/app.py)
- [`src/houmao/server/config.py`](../../src/houmao/server/config.py)
- [`src/houmao/server/service.py`](../../src/houmao/server/service.py)
- [`src/houmao/server/control_core/core.py`](../../src/houmao/server/control_core/core.py)
- [`src/houmao/server/control_core/provider_adapters.py`](../../src/houmao/server/control_core/provider_adapters.py)
- [`src/houmao/server/managed_agents.py`](../../src/houmao/server/managed_agents.py)
- [`src/houmao/agents/native_launch_resolver.py`](../../src/houmao/agents/native_launch_resolver.py)
- [`src/houmao/srv_ctrl/commands/admin.py`](../../src/houmao/srv_ctrl/commands/admin.py)
- [`src/houmao/srv_ctrl/commands/brains.py`](../../src/houmao/srv_ctrl/commands/brains.py)
- [`src/houmao/srv_ctrl/commands/agents/core.py`](../../src/houmao/srv_ctrl/commands/agents/core.py)
- [`src/houmao/srv_ctrl/commands/agents/gateway.py`](../../src/houmao/srv_ctrl/commands/agents/gateway.py)
- [`src/houmao/srv_ctrl/commands/agents/mail.py`](../../src/houmao/srv_ctrl/commands/agents/mail.py)
- [`src/houmao/srv_ctrl/commands/agents/turn.py`](../../src/houmao/srv_ctrl/commands/agents/turn.py)
- [`src/houmao/srv_ctrl/commands/cao.py`](../../src/houmao/srv_ctrl/commands/cao.py)
- [`src/houmao/srv_ctrl/commands/local_compat.py`](../../src/houmao/srv_ctrl/commands/local_compat.py)
- [`src/houmao/srv_ctrl/commands/launch.py`](../../src/houmao/srv_ctrl/commands/launch.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/cao/pinned.py`](../../src/houmao/cao/pinned.py)
