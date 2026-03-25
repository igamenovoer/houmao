# Distributed Agent Architecture — Alternative Migration Path: Greenfield Passive Server

## Purpose

This note describes an alternative migration strategy: instead of incrementally refactoring `houmao-server` (as described in `distributed-agent-migration-path.md`), build a new `houmao-passive-server` from scratch that implements only the target architecture. The old server is left running during transition and retired once the new server is proven.

This is a "parallel replacement" strategy. Both servers can coexist because they share the same filesystem-based registry as their source of truth.

## Why Consider This Alternative

The incremental refactor strategy (Phase 0–5 in the other document) has a core tension: the existing `houmao-server` is ~3500 lines of service logic, deeply intertwined with CAO compatibility, registration-backed admission, child process management, and a compatibility control core. Phases 1–2 of that plan require surgically disabling and rewiring internals of a live system while keeping it functional.

The greenfield alternative sidesteps that tension:

- **No retirement choreography.** There are no CAO routes to disable, no feature flags to manage, no registration paths to sunset. The new server simply never has them.
- **Clean dependency graph.** The new server depends only on the shared registry, tmux, and optionally the gateway client. No `CompatibilityControlCore`, no `ChildCaoManager`, no `CaoRestClient`.
- **Smaller codebase.** Research shows that 5 of 23 current server endpoints are pure gateway proxies and the remaining 18 can be reimplemented against registry + tmux + gateway without CAO plumbing. The new server should be significantly smaller.
- **Parallel testing.** Both servers can run simultaneously (on different ports). The old server continues to serve existing workflows while the new one is validated against the target architecture.
- **Cleaner cut.** When the new server is ready, the old server and all its CAO-era code can be removed in one step rather than across multiple phased refactors.

The tradeoff is duplication of effort: some logic (TUI tracking, headless turn management) must be reimplemented rather than reused. The next sections assess whether that cost is justified.

## What The Passive Server Must Do

Based on analysis of the current server's 23 active endpoints and their state ownership:

### Tier 1 — Registry-driven agent discovery (replaces registration-backed admission)

The passive server's primary data source is the shared `LiveAgentRegistryRecordV2` registry. On startup and periodically, it scans the registry for fresh records with live tmux sessions.

Required capabilities:
- Scan `$HOUMAO_RUNTIME_ROOT/live_agents/*/record.json` for fresh records.
- Verify tmux liveness for each record's `terminal.session_name`.
- Build an in-memory `DiscoveredAgentIndex` keyed by `agent_id`, `agent_name`, and `tmux_session_name`.
- Evict agents whose registry records expire or whose tmux sessions disappear.
- Re-discover on startup (the server is stateless with respect to agent tracking).

This replaces: `KnownSessionRegistry`, registration file I/O, `TuiTrackingSupervisor` reconciliation against registration files.

### Tier 2 — Agent listing and identity (pure registry projection)

Endpoints:
- `GET /houmao/agents` — list discovered agents from the index.
- `GET /houmao/agents/{agent_ref}` — resolve by `agent_id` or `agent_name`.

These are thin projections of registry data. No CAO involvement.

### Tier 3 — TUI observation (reimplemented against tmux directly)

The current server's TUI tracking layer (`LiveSessionTracker`, probe snapshots, parsed TUI surface, diagnostics, stability metadata, recent transitions) is the most complex server-owned state. It cannot be proxied — it is the server's own observation of the tmux pane.

The passive server needs its own TUI observation layer. The good news: the underlying `shared_tui_tracking` library and TUI parser infrastructure are already decoupled from the server. The observation layer can be built by:

1. For each discovered agent, create a `TuiObserver` that polls the tmux pane.
2. Feed pane captures through the existing TUI parser (`houmao.shared_tui_tracking`).
3. Maintain in-memory state: current parsed surface, recent transitions, stability, diagnostics.

Endpoints:
- `GET /houmao/agents/{agent_ref}/state` — current TUI observation state.
- `GET /houmao/agents/{agent_ref}/state/detail` — detailed state with probe + parse + diagnostics.
- `GET /houmao/agents/{agent_ref}/history` — recent state transitions.

This replaces: `LiveSessionTracker`, `TuiTrackingSupervisor`, `SessionWatchWorker`, and the terminal state/history endpoints.

The `/houmao/terminals/{terminal_id}/*` endpoints from the old server can be dropped. The new server addresses agents by `agent_ref`, not by CAO terminal ID.

### Tier 4 — Gateway proxy (thin forwarding, minimal reimplementation)

Five current endpoints are pure forwards to agent gateways. The passive server replicates this by:

1. Reading gateway bindings from the registry record's `gateway` field (host, port).
2. Creating a `GatewayClient` pointing to the live gateway.
3. Forwarding requests and responses.

Endpoints:
- `GET /houmao/agents/{agent_ref}/gateway` — gateway status (forward to gateway `/v1/status`).
- `POST /houmao/agents/{agent_ref}/gateway/requests` — prompt submission (forward to gateway `/v1/requests`).
- `GET /houmao/agents/{agent_ref}/mail/status` — forward to gateway `/v1/mail/status`.
- `POST /houmao/agents/{agent_ref}/mail/check` — forward to gateway `/v1/mail/check`.
- `POST /houmao/agents/{agent_ref}/mail/send` — forward to gateway `/v1/mail/send`.
- `POST /houmao/agents/{agent_ref}/mail/reply` — forward to gateway `/v1/mail/reply`.

The existing `GatewayClient` class can be reused directly.

### Tier 5 — Gateway lifecycle (attach/detach)

Gateway attach/detach currently requires calling `RuntimeSessionController.attach_gateway()` locally, which creates the gateway subprocess and updates the registry record.

Two options:

**Option A — Delegate to `houmao-mgr`.** The passive server does not attach gateways itself. Instead, `houmao-mgr agents gateway attach <agent-ref>` remains the authoritative attach command (it already works locally without a server). The passive server only reads gateway status from the registry.

**Option B — Reimplement attach.** The passive server loads the session manifest from the registry record's `runtime.manifest_path`, reconstructs a `RuntimeSessionController`, and calls `attach_gateway()`. This is more code but provides server-initiated gateway management.

Recommendation: **Option A for the initial version.** Gateway attach is a local operation. The server's value is coordination and observation, not subprocess management. If server-initiated attach becomes needed later, add it as an extension.

Endpoints (Option A):
- `GET /houmao/agents/{agent_ref}/gateway` — read-only status from registry + gateway probe.
- `POST /houmao/agents/{agent_ref}/gateway/attach` — return error directing user to `houmao-mgr`.
- `POST /houmao/agents/{agent_ref}/gateway/detach` — return error directing user to `houmao-mgr`.

### Tier 6 — Request submission (TUI prompt delivery)

The current server submits prompts to TUI agents through two paths:
- If gateway is attached: forward to gateway request queue.
- If no gateway: send directly to the CAO terminal via the compatibility layer.

The passive server simplifies this:
- If gateway is attached: forward to gateway (same as Tier 4).
- If no gateway: the passive server does not have direct tmux send-keys authority. Return an error explaining that the agent needs a gateway for remote prompt delivery, or the user should use `houmao-mgr` locally.

This is a deliberate design choice. The passive server observes and coordinates; it does not directly type into tmux panes. Direct tmux input is `houmao-mgr`'s job.

Endpoints:
- `POST /houmao/agents/{agent_ref}/requests` — forward to gateway if available, error if not.
- `POST /houmao/agents/{agent_ref}/interrupt` — forward interrupt to gateway if available, error if not.
- `POST /houmao/agents/{agent_ref}/stop` — terminate tmux session and remove registry record (this is the one case where the server takes direct tmux action, because stop is a coordination-level authority).

### Tier 7 — Headless agent management

Server-managed headless agents are the most server-dependent feature. The current implementation:
- Launches headless agents via `start_runtime_session()`.
- Maintains `ManagedHeadlessAuthorityRecord` on disk.
- Manages turn execution (provision turn, spawn worker thread or forward to gateway, reconcile completion).
- Stores turn artifacts (stdout, stderr, exitcode) on disk.
- Rebuilds state on server restart from persisted authority records.

This is inherently a server-owned lifecycle. The passive server can reimplement it cleanly because:
- `start_runtime_session()` and `RuntimeSessionController` are in `realm_controller`, not in the server. They are reusable.
- `ManagedHeadlessStore` is a self-contained persistence layer. It can be reused or reimplemented.
- Turn execution logic (provision, worker thread, reconciliation) is ~400 lines in the current server. It can be extracted and cleaned up.

Endpoints:
- `POST /houmao/agents/headless/launches` — launch headless agent, publish to registry.
- `POST /houmao/agents/{agent_ref}/turns` — submit turn.
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}` — turn status.
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` — turn events.
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/{name}` — turn artifacts.

### Tier 8 — Server lifecycle

- `GET /health` — health check.
- `GET /houmao/server/current-instance` — PID, API base URL, server root.
- `POST /houmao/server/shutdown` — graceful shutdown.

## What The Passive Server Does NOT Have

- No `/cao/*` routes.
- No `CompatibilityControlCore` or `LocalCompatibilityTransportBridge`.
- No `ChildCaoManager` or supervised child CAO process.
- No `KnownSessionRegistry` or registration file I/O.
- No `houmao_server_rest` backend support.
- No launch registration endpoint (`/houmao/launches/register`).
- No CAO terminal ID addressing (`/houmao/terminals/{terminal_id}/*`).
- No direct tmux send-keys for TUI prompts (gateway-mediated only).

## Migration Path

### Step 1 — Scaffold `houmao-passive-server`

Create a new package `src/houmao/passive_server/` with:

```
passive_server/
  __init__.py
  app.py              # FastAPI application factory
  config.py           # PassiveServerConfig (simpler than HoumaoServerConfig)
  service.py          # PassiveServerService (core logic)
  discovery.py        # RegistryDiscoveryService (scan + liveness + index)
  observation.py      # TuiObservationService (per-agent tmux polling + parsing)
  headless.py         # HeadlessAgentService (launch + turn lifecycle)
  models.py           # Request/response models (reuse existing where possible)
```

Add a CLI entrypoint `houmao-passive-server` (or reuse `houmao-server` with a `--mode passive` flag).

**Dependencies from existing code (reuse, not copy):**
- `houmao.agents.realm_controller.registry_storage` — registry I/O.
- `houmao.agents.realm_controller.registry_models` — record schema.
- `houmao.agents.realm_controller.gateway_client` — gateway HTTP client.
- `houmao.agents.realm_controller.gateway_models` — gateway request/response types.
- `houmao.agents.realm_controller.runtime` — `start_runtime_session()`, `RuntimeSessionController`.
- `houmao.agents.realm_controller.manifest` — manifest I/O.
- `houmao.shared_tui_tracking` — TUI parser infrastructure.
- `houmao.server.managed_agents` — `ManagedHeadlessStore` (reuse or fork).
- `houmao.server.models` — response models for agent state, history, etc. (reuse subset).

**New code (written fresh):**
- `RegistryDiscoveryService` — periodic registry scan + tmux liveness check + agent index.
- `TuiObservationService` — per-agent tmux pane polling, parser integration, state tracking.
- Route handlers — thin wiring between HTTP endpoints and service methods.
- `PassiveServerConfig` — minimal config (listen address, runtime root, poll intervals).

### Step 2 — Implement Tiers 1–2 (Discovery + Listing)

Build `RegistryDiscoveryService`:
- Periodic scan of shared registry (configurable interval, default 5s).
- Tmux liveness verification via `libtmux`.
- In-memory `DiscoveredAgentIndex` with `agent_id` → record mapping.
- Name-based resolution: `agent_name` → record (reject ambiguous if multiple matches).

Implement `GET /houmao/agents` and `GET /houmao/agents/{agent_ref}`.

**Validation:** Launch an agent via `houmao-mgr agents launch`, then query the passive server's `/houmao/agents` endpoint. The agent should appear.

### Step 3 — Implement Tier 4 (Gateway Proxy)

Wire gateway proxy endpoints. This is straightforward: resolve agent from index, read gateway bindings from registry record, create `GatewayClient`, forward.

**Validation:** Launch an agent with `--gateway-auto-attach`, submit a prompt via the passive server's gateway proxy endpoint. Verify the prompt reaches the agent.

### Step 4 — Implement Tier 3 (TUI Observation)

Build `TuiObservationService`:
- For each discovered agent with `terminal.kind == "tmux"`, spawn a polling loop.
- Capture tmux pane content periodically.
- Feed through the appropriate TUI parser (tool-specific).
- Maintain in-memory state: current snapshot, recent transitions, stability.

Implement state/detail/history endpoints.

**Validation:** Launch an interactive agent, query state via passive server. Verify parsed TUI surface matches what the agent is showing.

This is the most labor-intensive step because TUI observation is the server's most complex feature. However, the parser infrastructure exists in `shared_tui_tracking`. The work is integration, not algorithm design.

### Step 5 — Implement Tiers 6–7 (Request Submission + Headless)

Implement prompt delivery (gateway-mediated), interrupt, and stop.

Implement headless agent launch and turn management. Reuse `ManagedHeadlessStore` and `RuntimeSessionController` from existing code.

**Validation:** Launch a headless agent through the passive server. Submit a turn. Verify completion, artifacts, and events.

### Step 6 — Implement Tier 8 (Server Lifecycle) + Client Compatibility

Add health, current-instance, and shutdown endpoints.

Update `HoumaoServerClient` (or create a new `PassiveServerClient`) to point at the new server. Update `houmao-mgr` commands that currently go through the server to work with the passive server.

Key client change: `houmao-mgr` agent discovery currently checks the registry first for local agents and falls back to the server. With the passive server, the server itself reads from the registry, so the resolution strategy is consistent.

### Step 7 — Parallel Validation

Run both servers simultaneously:
- Old `houmao-server` on its default port (9889).
- New `houmao-passive-server` on a different port (e.g., 9891).

Verify that:
- Agents launched by `houmao-mgr` appear on both servers.
- The passive server's agent state matches the old server's (for agents that both can see).
- Gateway proxy works through the passive server.
- Headless agents launched on the passive server are visible on the old server (via shared registry).
- Stopping an agent on the passive server removes it from both servers' views.

### Step 8 — Switch Default + Retire Old Server

- Change the default `houmao-server` entrypoint to launch the passive server.
- Move the old server code to `src/houmao/legacy_server/` or delete it.
- Remove all CAO-era dependencies: `CompatibilityControlCore`, `ChildCaoManager`, `KnownSessionRegistry`, registration file I/O, `/cao/*` route handlers.
- Remove `houmao_server_rest` backend.
- Update docs and tests to reflect the new server.

## Effort Estimate

| Step | Scope | New Code | Reused Code | Risk |
|------|-------|----------|-------------|------|
| 1 — Scaffold | Small | ~200 lines (config, app factory) | — | Low |
| 2 — Discovery + Listing | Medium | ~300 lines (discovery service, index, routes) | `registry_storage`, `registry_models` | Low |
| 3 — Gateway Proxy | Small | ~150 lines (proxy routes) | `gateway_client`, `gateway_models` | Low |
| 4 — TUI Observation | Large | ~500 lines (observation service, polling, state) | `shared_tui_tracking`, TUI parsers | Medium |
| 5 — Requests + Headless | Large | ~400 lines (headless service, turn lifecycle) | `runtime`, `ManagedHeadlessStore` | Medium |
| 6 — Lifecycle + Client | Small | ~150 lines (health, client updates) | `HoumaoServerClient` | Low |
| 7 — Parallel Validation | Medium | Test scripts only | — | Low |
| 8 — Retire Old Server | Large | Deletion, not creation | — | Medium |

Total new code: ~1700 lines (rough estimate), compared to ~3500 lines in the current `houmao-server`.

## Comparison With Incremental Refactor

| Dimension | Incremental Refactor | Greenfield Passive Server |
|-----------|---------------------|---------------------------|
| **Risk during migration** | Higher — modifying live system internals | Lower — old system untouched until switchover |
| **Total effort** | Lower — reuses existing code in place | Higher — reimplements observation + headless |
| **Time to first value** | Phase 1 (route retirement) is fast | Step 2 (discovery) is fast, but full value requires Step 5 |
| **Codebase clarity** | Gradual improvement; legacy scaffolding persists during transition | Clean break; new server has no legacy code |
| **Parallel testing** | Difficult — one server, being modified | Easy — two servers, side by side |
| **Rollback safety** | Feature flags provide rollback | Old server is untouched; rollback = keep using it |
| **CAO code removal** | Phased, across multiple milestones | One-step deletion when old server is retired |
| **Maintenance during transition** | Must maintain both old paths and new paths in the same codebase | Two separate codebases, but old one is frozen (no new features) |

## When To Prefer This Alternative

Choose the greenfield path if:
- The team is confident that the current server's TUI observation logic can be cleanly reimplemented using `shared_tui_tracking` without deep coupling to CAO internals.
- The cost of maintaining CAO compatibility code during a multi-phase refactor is higher than the cost of reimplementing ~1700 lines.
- Parallel testing (two servers running side by side) is more valuable than in-place feature flags.
- A clean architectural break is preferred over gradual evolution.

Choose the incremental refactor if:
- The TUI observation layer is too tightly coupled to reimplement without significant duplication.
- The team wants to ship partial value (route retirement) before committing to the full authority refactor.
- There is not enough bandwidth to build and validate a new server in parallel.

## Recommended Sequencing If This Path Is Chosen

```text
Step 1 (Scaffold)
  ↓
Step 2 (Discovery + Listing)  ──→  Step 7a (validate discovery)
  ↓
Step 3 (Gateway Proxy)  ──→  Step 7b (validate proxy)
  ↓
Step 4 (TUI Observation)  ──→  Step 7c (validate observation)
  ↓
Step 5 (Requests + Headless)  ──→  Step 7d (validate headless)
  ↓
Step 6 (Lifecycle + Client)  ──→  Step 7e (full parallel validation)
  ↓
Step 8 (Retire Old Server)
```

Each step can be validated independently against the old server. The old server remains the production default until Step 8.

## Design Decisions To Make Before Starting

1. **Separate package or replace in place?** Recommendation: separate package (`src/houmao/passive_server/`) during development, then rename to `src/houmao/server/` at Step 8.

2. **Separate CLI entrypoint or flag?** Recommendation: `houmao-server --mode passive` during development, then drop the flag and make passive the only mode at Step 8.

3. **Reuse `ManagedHeadlessStore` or rewrite?** Recommendation: reuse. It is a self-contained persistence layer with no CAO dependencies. The only coupling is the filesystem layout, which is fine.

4. **Reuse `HoumaoServerClient` or create new client?** Recommendation: reuse and extend. The client is a thin HTTP wrapper. Add methods for new endpoints, deprecate methods for removed endpoints.

5. **Direct tmux send-keys for stop?** Recommendation: yes. The passive server should be able to stop agents by killing the tmux session, even though it delegates prompt delivery to gateways. Stop is a coordination-level authority, not a prompt-level operation.

6. **TUI observation: per-agent thread or shared polling loop?** Recommendation: shared polling loop with configurable interval. One thread that iterates over all discovered agents each cycle. Simpler than per-agent threads and sufficient for the expected agent count.

## Summary

The greenfield `houmao-passive-server` strategy builds a new, smaller server that implements only the target distributed-agent architecture. It avoids the complexity of incrementally disabling and rewiring CAO internals in the existing server.

The migration path is:
1. Scaffold the new server package.
2. Implement registry-driven discovery and agent listing.
3. Add gateway proxy endpoints.
4. Build TUI observation against `shared_tui_tracking`.
5. Implement headless agent lifecycle.
6. Wire up server lifecycle and client compatibility.
7. Validate in parallel with the old server.
8. Retire the old server and all CAO-era code.

Estimated new code: ~1700 lines. The old server's ~3500 lines of service logic (plus CAO dependencies) are deleted in one step at the end.
