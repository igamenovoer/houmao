## ADDED Requirements

### Requirement: Retained `houmao.server` modules are internal implementation support only
Retained Python modules under `houmao.server` SHALL be treated as internal implementation support rather than as proof of a maintained standalone server product.

The repository MAY retain Python modules under `houmao.server` when maintained surfaces still use their models, clients, stores, parser adapters, process helpers, tmux helpers, or compatibility utilities.

Retaining those modules SHALL NOT expose or imply a maintained packaged `houmao-server` executable, standalone FastAPI application, `/cao/*` compatibility server, old-server CLI, or public old-server route contract.

Maintained code SHOULD move broadly shared old-server helpers to neutral packages in later cleanup changes when that move reduces coupling without blocking the executable retirement.

#### Scenario: Passive-server imports old-server models during transition
- **WHEN** `houmao-passive-server` imports a model or helper that still lives under `houmao.server`
- **THEN** that import remains an allowed internal implementation detail
- **AND THEN** packaging and active docs still do not expose standalone `houmao-server` as a supported executable

#### Scenario: Old server application routes are not public contract
- **WHEN** an implementation leaves an old FastAPI app module in the tree temporarily
- **THEN** tests and docs do not treat its `/cao/*` or `/houmao/*` routes as maintained public API
- **AND THEN** maintained API coverage belongs to `houmao-passive-server`

## REMOVED Requirements

### Requirement: `houmao-server` serves `/cao/*` through a Houmao-owned control core

**Reason**: Standalone `houmao-server` and its `/cao/*` compatibility server contract are retired as maintained public surfaces.

**Migration**: Use `houmao-passive-server` for maintained API-based agent discovery, observation, and management. Keep any still-useful CAO-compatible code internal only when retained modules need it.

### Requirement: `houmao-server` keeps root and `/houmao/*` namespaces Houmao-owned

**Reason**: The standalone old-server HTTP namespace is no longer a public API contract.

**Migration**: Implement maintained route ownership through `houmao-passive-server`.

### Requirement: `houmao-server` matches the full supported `cao-server` HTTP API

**Reason**: Houmao no longer maintains standalone `houmao-server` as a public CAO-compatible replacement server.

**Migration**: Remove public parity expectations for `/cao/*`; preserve internal adapters only where maintained manager/passive-server flows still need them.

### Requirement: `houmao-server` compatibility is pinned to one exact CAO source of truth

**Reason**: Public CAO parity verification for the retired standalone server is no longer required.

**Migration**: Retain pinned CAO references only for internal adapter tests when those adapters remain necessary.

### Requirement: `houmao-server` compatibility is defined within the supported Houmao pair

**Reason**: The `houmao-server + houmao-mgr` pair is no longer a supported public operator pair.

**Migration**: Use `houmao-mgr` for local workflows and `houmao-passive-server` for maintained server API workflows.

### Requirement: Houmao extensions on CAO-compatible routes are additive only

**Reason**: The public `/cao/*` compatibility extension contract is removed with the standalone server.

**Migration**: Passive-server routes define the maintained API behavior instead of extending CAO-compatible route shapes.

### Requirement: Pair-owned `houmao-server` clients keep persisted authority at the server root

**Reason**: Persisted public old-server authority is removed with `houmao_server_rest` and the standalone server executable.

**Migration**: Persist maintained passive-server or local runtime authority metadata through current manager/passive-server models.

### Requirement: `houmao-server` separates direct watch observation from CAO-compatible control delegation

**Reason**: Old standalone server watch/control ownership is no longer public API.

**Migration**: Passive-server observation and gateway-backed control own maintained API behavior; shared TUI helpers may remain internal.

### Requirement: `houmao-server` seeds known-session tracking from server-owned registrations

**Reason**: Old server-owned registration admission is no longer a maintained standalone server contract.

**Migration**: Use passive-server discovery/managed-headless authority and shared registry records for maintained server-side agent management.

### Requirement: `houmao-server` owns persistent background watch workers for live terminals

**Reason**: Standalone old-server background watch ownership is retired.

**Migration**: Use passive-server observation services or gateway-owned tracking for maintained live TUI state.

### Requirement: `houmao-server` classifies persistence into filesystem-authoritative, transitional compatibility, and memory-primary state

**Reason**: The classification was anchored to the retired standalone server authority.

**Migration**: Keep storage contracts on active runtime, gateway, and passive-server capabilities; move any reusable storage helpers behind maintained modules.

### Requirement: Tracked-state routes expose simplified turn and last-turn semantics

**Reason**: Old server tracked-state routes are no longer maintained public routes.

**Migration**: Use passive-server observation or gateway TUI state routes for maintained inspection.

### Requirement: `houmao-server` publishes Houmao-owned terminal state and history as explicit extension routes

**Reason**: Terminal-keyed old-server extension routes are removed from the public API surface.

**Migration**: Use passive-server observation and gateway route families for maintained state/history access.

### Requirement: `houmao-server` keeps TUI registration separate from native headless launch

**Reason**: Old server-owned TUI registration versus headless launch is no longer a maintained public server distinction.

**Migration**: Use passive-server managed-headless launch and passive discovery for maintained authority.

### Requirement: `houmao-server` persists native headless authority under the server-owned state tree

**Reason**: Native headless server authority moves to passive-server-managed authority.

**Migration**: Use passive-server managed-headless state and store contracts.

### Requirement: `houmao-server` persists active headless turn authority and reconciles it across restart

**Reason**: Old server-owned active-turn authority is no longer the maintained API authority.

**Migration**: Use passive-server managed-headless turn records and reconciliation behavior.

### Requirement: `houmao-server` maintains a managed-agent registry that includes headless agents

**Reason**: Managed-agent API ownership moves to passive-server.

**Migration**: Use passive-server discovery plus passive-server-managed headless authority.

### Requirement: Existing CAO-compatible and terminal-keyed routes remain TUI-specific compatibility surfaces

**Reason**: Public CAO-compatible and terminal-keyed old-server routes are retired.

**Migration**: Use passive-server and gateway route families instead of fake CAO/session route compatibility.

### Requirement: `houmao-server` keeps registration bridge storage contained under the server-owned sessions root

**Reason**: Old server registration bridge storage is no longer public server behavior.

**Migration**: Keep equivalent path-containment checks only in retained internal stores or passive-server storage where needed.

### Requirement: `houmao-server` keeps background tracking resilient across unexpected runtime failures

**Reason**: The standalone old-server tracking supervisor is no longer a maintained public component.

**Migration**: Apply resilience requirements to passive-server observation and gateway tracking capabilities.

### Requirement: `houmao-server` removes live-state aliases when a tracked session leaves live authority

**Reason**: Old server live-state alias maps are no longer a public contract.

**Migration**: Maintain equivalent cleanup semantics in passive-server observation/gateway authority where applicable.

### Requirement: `houmao-server` preserves tracked pane identity during registration-seeded admission

**Reason**: Registration-seeded admission through standalone `houmao-server` is retired.

**Migration**: Preserve pane identity through passive-server discovery records or gateway tracking metadata where maintained.

### Requirement: `houmao-server` uses replaceable upstream adapters and v1 SHALL support a native CAO-compatible engine

**Reason**: Replaceable CAO-compatible engine support is no longer a public standalone server requirement.

**Migration**: Keep adapter boundaries internal only when needed by retained helper code.

### Requirement: `houmao-server` is designed to outgrow CAO rather than permanently mirror it

**Reason**: The public standalone server evolution track is retired.

**Migration**: Passive-server is the maintained CAO-free server direction.

### Requirement: `houmao-server` compatibility SHALL be verified against a real `cao-server`

**Reason**: Public CAO parity verification for standalone `houmao-server` is no longer required.

**Migration**: Remove public parity tests; retain focused internal adapter tests only if maintained code still uses the adapter.

### Requirement: Session detail responses preserve terminal summary metadata needed by pair clients

**Reason**: Old server session-detail responses are no longer maintained public payloads.

**Migration**: Preserve needed metadata through passive-server managed-agent summaries or gateway/passive observation payloads.

### Requirement: `houmao-server` headless authority cleanup stays within the server-owned state tree

**Reason**: Old server-owned headless cleanup is retired as public behavior.

**Migration**: Enforce cleanup containment in passive-server managed-headless storage.
