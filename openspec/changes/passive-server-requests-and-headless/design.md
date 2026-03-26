## Context

The `houmao-passive-server` package (`src/houmao/passive_server/`) implements a lightweight, registry-first server for distributed agent coordination. Steps 1–4 of the greenfield migration delivered: FastAPI scaffold with CLI entrypoint (port 9891), registry-driven discovery (`RegistryDiscoveryService`), gateway proxy (6 forwarding endpoints), TUI observation (`TuiObservationService` with per-agent polling), and server lifecycle (health, current-instance, shutdown).

The old `houmao-server` (`src/houmao/server/`) still provides request submission, gateway attach/detach, headless agent launch, and headless turn lifecycle. These features depend on CAO compatibility layers (`CompatibilityControlCore`, `ChildCaoManager`, `KnownSessionRegistry`) and server-owned `RuntimeSessionController` handles. The passive server must provide equivalent capabilities without any CAO plumbing.

Key existing infrastructure the passive server can reuse:
- `ManagedHeadlessStore` (`houmao.server.managed_agents`) — self-contained filesystem persistence for authority records, active turns, and completed turns. No CAO dependencies.
- `start_runtime_session()` and `RuntimeSessionController` (`houmao.agents.realm_controller.runtime`) — backend-agnostic session launch and control.
- `kill_tmux_session()` (`houmao.agents.realm_controller.backends.tmux_runtime`) — direct tmux session termination.
- `GatewayClient` (`houmao.agents.realm_controller.gateway_client`) — already used by the passive server's gateway proxy tier.
- `load_brain_manifest()`, `load_role_package()` (`houmao.agents.realm_controller.manifest`, `launch_plan`) — manifest and role loading for headless launches.

## Goals / Non-Goals

**Goals:**
- Implement all Tier 5 (gateway attach/detach stubs), Tier 6 (request submission, interrupt, stop), and Tier 7 (headless launch + turn lifecycle) endpoints on the passive server.
- Reuse `ManagedHeadlessStore` for headless authority and turn persistence so headless agents survive passive server restarts.
- Maintain the passive server's design principle: observe and coordinate, do not directly type into tmux panes. Prompt delivery goes through gateways; stop is the sole exception (coordination-level authority).
- Keep the passive server runnable in parallel with the old server (shared registry, different ports) for Step 7 validation.

**Non-Goals:**
- Server-initiated gateway attach/detach (deferred per design doc Option A).
- Direct tmux send-keys for prompt delivery (gateway-mediated only).
- Client compatibility updates (`HoumaoServerClient` or new `PassiveServerClient`) — deferred to Step 6.
- Retiring the old server or removing CAO code (Step 8).
- TUI-transport managed agent support (the passive server's `/requests` endpoint works only for gateway-attached agents).

## Decisions

### Decision 1: Gateway attach/detach returns 501 Not Implemented

The passive server delegates gateway lifecycle to `houmao-mgr`. The `POST .../gateway/attach` and `POST .../gateway/detach` endpoints return `501 Not Implemented` with a detail message directing the caller to `houmao-mgr agents gateway attach <agent-ref>`.

**Alternative considered:** Silently proxy to `houmao-mgr` via subprocess. Rejected because the passive server should not manage child processes — that is `houmao-mgr`'s local concern.

### Decision 2: Request submission is gateway-only

`POST /houmao/agents/{agent_ref}/requests` resolves the agent, checks for a live gateway, and forwards the prompt via `GatewayClient.create_request()`. If no gateway is attached, it returns `502 Bad Gateway` with a message explaining that the agent needs a gateway for remote prompt delivery.

**Alternative considered:** Fall back to `tmux send-keys` for non-gateway agents. Rejected because the passive server's design principle is that it does not type into tmux panes directly. Local prompt delivery is `houmao-mgr`'s job.

### Decision 3: Stop uses direct tmux kill

`POST /houmao/agents/{agent_ref}/stop` calls `kill_tmux_session()` directly and then clears the shared registry record. For headless agents managed by this server, it also cleans up the `ManagedHeadlessStore` authority and in-memory handle. This is the one case where the passive server takes direct tmux action, as stop is coordination-level authority, not a prompt-level operation.

### Decision 4: Interrupt is gateway-mediated for discovered agents, direct for server-managed headless

For agents discovered from the registry (not launched by this server), interrupt goes through the gateway if available. For headless agents launched by this server and held in-memory, interrupt uses the `RuntimeSessionController` handle to signal the headless backend directly.

### Decision 5: New `HeadlessAgentService` in `headless.py`

A new module `src/houmao/passive_server/headless.py` encapsulates:
- In-memory handle map (`dict[str, _HeadlessAgentHandle]`) containing the `RuntimeSessionController` and tracked metadata.
- `ManagedHeadlessStore` instance for disk persistence.
- Launch, turn submission, turn status/events/artifacts, interrupt, and stop methods.
- Startup rebuild: on server start, scan persisted authority records and attempt to resume `RuntimeSessionController` handles for live agents.

The service is owned by `PassiveServerService` and started/stopped during the lifespan.

**Alternative considered:** Putting headless logic directly in `PassiveServerService`. Rejected because the old server's service.py grew to ~2800 lines by mixing concerns. Separating headless management into its own service keeps the passive server's service layer thin.

### Decision 6: Reuse `ManagedHeadlessStore` without forking

The existing `ManagedHeadlessStore` in `houmao.server.managed_agents` is a self-contained filesystem persistence layer with no CAO or old-server dependencies. The passive server imports and uses it directly. The store root is derived from `PassiveServerConfig.server_root / "managed_agents"`.

### Decision 7: Response model strategy

For endpoints that mirror the old server's API, reuse the same response model types from `houmao.server.models` where they have no CAO-specific fields (e.g., `HoumaoHeadlessTurnStatusResponse`, `HoumaoHeadlessTurnEventsResponse`). For the request submission and action endpoints, define new passive-server models in `passive_server/models.py` that are structurally compatible but do not extend `CaoSuccessResponse`.

## Risks / Trade-offs

- **[Risk] `ManagedHeadlessStore` import couples passive server to old server package** → Mitigation: The store has no service-layer dependencies; if the old server is deleted in Step 8, the store can be moved to a shared location or into the passive server package. This is an acceptable short-term coupling.
- **[Risk] Headless agent handle rebuild on restart may fail for agents whose tmux sessions disappeared** → Mitigation: Log a warning and skip; the discovery service will also evict the agent from the index. The authority record can optionally be cleaned up.
- **[Risk] Stop endpoint kills tmux sessions for any discovered agent, including agents launched by the old server** → Mitigation: This is intentional — stop is coordination-level. Both servers share the registry and tmux; either can stop any agent. The registry record cleanup is idempotent.
- **[Trade-off] Gateway-only request submission means the passive server cannot prompt non-gateway agents** → Accepted per design principle. Local users use `houmao-mgr` for direct tmux interaction.
