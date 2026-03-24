# Houmao Server Pair

`houmao-server` and `houmao-srv-ctrl` are the supported Houmao-managed replacement pair for `cao-server` and `cao`.

The intent of this pair is narrow and explicit:

- `houmao-server` is the public HTTP authority.
- `houmao-srv-ctrl` is the pair CLI. Its top level is Houmao-owned, and its explicit `cao` subgroup carries the CAO-compatible command family.
- Mixed pairs such as `houmao-server + cao` or `cao-server + houmao-srv-ctrl` are unsupported in this change.

For the maintained deep explanation of the live state tracker, turn anchors, lifecycle authority, and state transition rules behind `GET /houmao/terminals/{terminal_id}/state`, see the [Houmao Server Developer Guide](../developer/houmao-server/index.md).

## Compatibility Source Of Truth

Compatibility for this change is pinned to one exact upstream CAO source:

- Repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- Commit: `0fb3e5196570586593736a21262996ca622f53b6`
- Tracked local checkout: `extern/tracked/cli-agent-orchestrator`

That exact commit is the parity oracle for the CAO-compatible HTTP and CLI behavior implemented here. Houmao does not treat a floating branch name or whatever `cao-server` happens to be installed on `PATH` as the compatibility definition.

## Commands

Primary entrypoints for the paired replacement:

- `houmao-server`: serves Houmao-owned root routes plus the explicit `/cao/*` CAO-compatibility namespace
- `houmao-srv-ctrl`: exposes top-level Houmao pair commands plus the explicit `cao` compatibility namespace
- `houmao-cli`: remains the runtime/agent lifecycle CLI and stays outside the CAO-compatible service-management surface

Representative usage:

```bash
houmao-server serve --api-base-url http://127.0.0.1:9889
houmao-srv-ctrl install projection-demo --provider codex --port 9889
houmao-srv-ctrl cao info --port 9889
houmao-srv-ctrl launch --port 9889 --agents gpu-kernel-coder --provider codex
houmao-srv-ctrl cao launch --port 9889 --agents gpu-kernel-coder --provider codex --headless
houmao-srv-ctrl launch --port 9889 --agents gpu-kernel-coder --provider claude_code --headless
houmao-srv-ctrl agent-gateway attach --agent cao-gpu --port 9889
houmao-srv-ctrl agent-gateway attach
```

## Pair-Managed Gateway Attach

For pair-managed terminal sessions, the supported public attach command is `houmao-srv-ctrl agent-gateway attach`.

Supported modes:

- explicit target mode: `houmao-srv-ctrl agent-gateway attach --agent <agent-ref> --port <public-port>`
- current-session mode: run `houmao-srv-ctrl agent-gateway attach` from inside the tmux session that owns the managed agent

Current-session mode is intentionally strict:

- the tmux session must publish `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- those pointers must resolve to one readable runtime-owned `attach.json` and gateway root for the same tmux session
- the attach contract must use `backend = "houmao_server_rest"`
- persisted `backend_metadata.api_base_url` and `backend_metadata.session_name` are authoritative; no-`--agent` attach does not retarget to another server
- current-session attach becomes valid only after delegated pair launch has both published gateway capability and completed managed-agent registration on that persisted `api_base_url`

Pair-managed tmux topology is also intentionally narrow:

- tmux window `0` is the only contractual agent surface for `houmao_server_rest`
- same-session live gateway attach may create auxiliary non-zero windows inside that tmux session
- those auxiliary windows are not public contract by name, count, or order; the only authoritative non-zero window handle is the one currently recorded in `gateway/run/current-instance.json` for the live gateway

## Architecture

The pair still uses a supervised child `cao-server` for CAO-compatible control routes, but live TUI tracking no longer goes through that child. `houmao-server` now owns the watch plane directly:

- direct tmux pane resolution and capture
- live process-tree inspection to determine whether the supported TUI is up or down
- official parser selection through the shared parser stack
- continuous in-memory live state and bounded recent transitions

The public contract stays Houmao-owned:

- callers talk to `houmao-server`
- runtime-owned `houmao_server_rest` sessions persist the public Houmao server base URL and terminal identity
- child CAO details stay behind the public contract for the delegated control plane
- terminal-keyed Houmao extension routes resolve through Houmao-owned tracked-session identity instead of making `terminal_id` the internal watch authority

The pair now exposes three public server surfaces:

- Houmao-owned root routes and terminal-tracking routes:
  - `/health`
  - `/houmao/terminals/{terminal_id}/*`
- explicit CAO-compatible routes:
  - `/cao/health`
  - `/cao/sessions/*`
  - `/cao/terminals/*`
  - `/cao/terminals/{terminal_id}/working-directory`
- shared managed-agent routes for TUI-backed managed agents and Houmao-launched native headless agents:
  - `GET /houmao/agents`
  - `GET /houmao/agents/{agent_ref}`
  - `GET /houmao/agents/{agent_ref}/state`
  - `GET /houmao/agents/{agent_ref}/state/detail`
  - `GET /houmao/agents/{agent_ref}/history`
  - `POST /houmao/agents/{agent_ref}/requests`
  - `GET /houmao/agents/{agent_ref}/gateway`
  - `POST /houmao/agents/{agent_ref}/gateway/attach`
  - `POST /houmao/agents/{agent_ref}/gateway/detach`
  - `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`
  - `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`
  - `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`
- native headless lifecycle and durable turn routes:
  - `POST /houmao/agents/headless/launches`
  - `POST /houmao/agents/{agent_ref}/stop`
  - `POST /houmao/agents/{agent_ref}/turns`
  - `GET /houmao/agents/{agent_ref}/turns/{turn_id}`
  - `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`
  - `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`
  - `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr`
  - `POST /houmao/agents/{agent_ref}/interrupt`

Root `/sessions/*` and `/terminals/*` are intentionally not public in this boundary reset.

For managed-agent lifecycle, the intent is now explicit:

- `POST /houmao/agents/headless/launches` launches the managed headless agent and may carry mailbox overrides.
- `GET /houmao/agents/{agent_ref}/state` stays the coarse shared state surface and now includes redacted mailbox and gateway posture when those capabilities are known.
- `GET /houmao/agents/{agent_ref}/state/detail` is the transport-specific inspection route, with curated TUI projection for terminal-backed agents and execution-centric detail for headless agents.
- `POST /houmao/agents/{agent_ref}/requests` is the transport-neutral submit path for prompt and interrupt work across both transports.
- gateway lifecycle is post-launch and runs through `/houmao/agents/{agent_ref}/gateway/*` rather than through launch-time gateway flags.
- native headless `/turns/*` and `/interrupt` remain the durable headless-only turn and artifact surface rather than being collapsed into the shared `/history` route.
- mailbox send, check, and reply stay on the live gateway `/v1/mail/*` surface and are not proxied through `houmao-server` in this change.

For exact payloads, request semantics, and the split between shared managed-agent routes and headless-only turn routes, use [Managed-Agent API](managed_agent_api.md).

The child listener address is derived mechanically as `public_port + 1` and stays loopback-only. There is no separate user-facing child-port override in this design.

Pair-targeted profile installation follows the same boundary:

- `houmao-srv-ctrl install --port <public-port> ...` identifies one public `houmao-server`
- raw local CAO install remains under `houmao-srv-ctrl cao install ...`
- `houmao-server` resolves the child-managed CAO home internally
- callers do not compute or mutate hidden `child_cao` filesystem paths directly

## Persistence Boundary

The v1 boundary is intentionally split into three groups.

Filesystem-authoritative artifacts:

- runtime-owned session roots and manifests
- shared-registry `live_agents/<agent-id>/record.json` pointers while the registry bridge remains in use
- delegated `houmao-srv-ctrl launch` manifests and session roots written under the normal runtime-owned `sessions/houmao_server_rest/...` layout
- native headless authority records under `state/managed_agents/<tracked_agent_id>/authority.json`
- native headless active-turn admission under `state/managed_agents/<tracked_agent_id>/active_turn.json`
- native headless coarse per-turn records under `state/managed_agents/<tracked_agent_id>/turns/<turn_id>.json`

Filesystem-backed compatibility, debug, or migration views:

- `houmao-server` current-instance and pid files
- child launcher config, pid, ownership, and runtime artifacts under the internal child root
- delegated-launch `sessions/<session>/registration.json` under the server root
- runtime-owned headless turn artifacts under the launched session root, which are served back out through the managed-agent per-turn routes rather than through the shared `/history` surface

Memory-primary live control-plane state:

- known-session registry entries rebuilt from registration records and verified against live tmux
- active watch-worker ownership
- explicit transport/process/parse state for tracked sessions
- latest parsed supported-TUI surface, derived operator state, stability metadata, and bounded recent transitions
- rebuilt managed-agent alias resolution across TUI registrations and native headless authority records

Live terminal state is now authoritative in server memory. `houmao-server` no longer writes per-terminal `current.json`, `samples.ndjson`, or `transitions.ndjson` files for the tracker contract.

## `houmao_server_rest` Runtime Identity

Runtime-owned sessions that use the server-backed mode persist `backend = "houmao_server_rest"`.

That backend uses dedicated persisted sections instead of overloading the older `cao_rest` contract:

- session manifests write a `houmao_server` section with `api_base_url`, `session_name`, `terminal_id`, `parsing_mode`, optional `tmux_window_name`, and `turn_index`
- gateway attach contracts use Houmao-specific backend metadata
- shared-registry records still point back to the runtime-owned manifest and session root instead of copying runtime state into the registry

This keeps child CAO adapter details out of the runtime-owned public contract while preserving existing discovery and gateway flows during the transition.

## Hidden Child Storage Model

`houmao-server` provisions the child CAO support state under a Houmao-owned per-server root instead of introducing a user-facing CAO home contract for the pair.

For one public base URL, the server-owned tree lives under:

```text
<runtime-root>/houmao_servers/<host>-<port>/
```

The child-specific subtree is:

```text
<server-root>/child_cao/
  launcher.toml
  runtime/
```

This subtree is internal Houmao-managed support state. Operators may inspect it for debugging, but it is not the public control surface.

That includes agent-profile installation. The supported pair-owned path is:

```bash
houmao-srv-ctrl install <agent-source> --provider <provider> --port <public-port>
```

The install request is routed through `houmao-server`, which performs the child-CAO mutation inside the managed support subtree without promoting that subtree into a caller-facing contract.

The pair CLI stays narrow on purpose. `houmao-srv-ctrl launch --headless` launches the agent, but it does not grow gateway attach flags in this change. Gateway attach remains a later lifecycle action because the sidecar can be started against the same tmux-backed session from published session env and manifest-backed attach metadata.

## Transitional Registry Bridge

Delegated terminal-backed `houmao-srv-ctrl launch` flows still publish shared-registry pointers in v1 when the current runtime/gateway flows require those pointers.

Those registry records remain pointer-oriented:

- they reference the Houmao-owned manifest and session root
- they do not become a second copy of runtime state
- they remain a compatibility bridge while future discovery moves toward server-owned query surfaces

## Migration Direction

This pair is a migration strategy, not the final architecture.

The public names and persisted backend identity are already Houmao-owned so that future native Houmao terminal backends can replace the child CAO adapter without forcing another public rename or persisted-contract reset.

For headless agents, that future shape is already visible now: launch and turn control no longer depend on CAO terminal ids, and the server-owned control-plane truth lives in the managed-agent authority subtree plus the shared `/houmao/agents/*` API.

## Source References

- [`src/houmao/server/app.py`](../../src/houmao/server/app.py)
- [`src/houmao/server/client.py`](../../src/houmao/server/client.py)
- [`src/houmao/server/service.py`](../../src/houmao/server/service.py)
- [`src/houmao/server/managed_agents.py`](../../src/houmao/server/managed_agents.py)
- [`src/houmao/server/child_cao.py`](../../src/houmao/server/child_cao.py)
- [`src/houmao/server/models.py`](../../src/houmao/server/models.py)
- [`src/houmao/srv_ctrl/commands/launch.py`](../../src/houmao/srv_ctrl/commands/launch.py)
- [`src/houmao/srv_ctrl/commands/runtime_artifacts.py`](../../src/houmao/srv_ctrl/commands/runtime_artifacts.py)
- [`src/houmao/agents/realm_controller/manifest.py`](../../src/houmao/agents/realm_controller/manifest.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/cao/pinned.py`](../../src/houmao/cao/pinned.py)
