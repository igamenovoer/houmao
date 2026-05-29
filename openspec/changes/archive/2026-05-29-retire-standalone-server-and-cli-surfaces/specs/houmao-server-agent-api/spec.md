## ADDED Requirements

### Requirement: Maintained managed-agent API ownership belongs to `houmao-passive-server`
Maintained managed-agent HTTP API behavior SHALL be exposed through `houmao-passive-server` rather than standalone `houmao-server`.

When old server managed-agent models, clients, managed-headless records, or gateway/mail compatibility helpers are still useful, maintained passive-server code MAY import or move those helpers. Their old package location SHALL NOT imply that standalone `houmao-server` remains a maintained API authority.

#### Scenario: Passive-server owns managed-agent API documentation
- **WHEN** docs or tests describe maintained managed-agent HTTP routes
- **THEN** those routes are described as `houmao-passive-server` behavior
- **AND THEN** standalone `houmao-server` route families are not presented as current public API

#### Scenario: Retained models are internal compatibility support
- **WHEN** passive-server reuses response models that still live under `houmao.server.models`
- **THEN** that reuse remains an internal implementation detail
- **AND THEN** the maintained API authority remains `houmao-passive-server`

## REMOVED Requirements

### Requirement: `houmao-server` exposes a transport-neutral managed-agent read API

**Reason**: Standalone `houmao-server` is retired as a maintained managed-agent API authority.

**Migration**: Use passive-server managed-agent discovery, managed-state, detail, and history routes.

### Requirement: `houmao-server` exposes a native headless launch and stop API

**Reason**: Native headless launch/stop API ownership moves to passive-server.

**Migration**: Use passive-server managed-headless launch and stop routes.

### Requirement: Managed-agent stop supports TUI-backed agents

**Reason**: Old server-managed stop behavior is no longer the public API contract.

**Migration**: Use passive-server request/action routes or local manager lifecycle commands depending on authority.

### Requirement: Managed-agent lookup resolves through explicit aliases

**Reason**: Old server alias resolution is no longer maintained as public API.

**Migration**: Use passive-server agent resolution semantics.

### Requirement: Headless prompt control is modeled as turn resources

**Reason**: Headless turn API ownership moves to passive-server.

**Migration**: Use passive-server headless turn submit/status/events/artifact routes.

### Requirement: Headless turn inspection exposes structured events and durable artifacts

**Reason**: Old server turn inspection routes are retired.

**Migration**: Use passive-server managed-headless event and artifact routes.

### Requirement: Durable headless detail stays on per-turn resources rather than shared `/history`

**Reason**: This public route-family distinction now belongs to passive-server where maintained.

**Migration**: Use passive-server per-turn inspection routes for durable detail.

### Requirement: Managed headless turn events use canonical semantic event records

**Reason**: Old server event routes are retired.

**Migration**: Expose canonical semantic events through passive-server managed-headless routes.

### Requirement: Managed headless raw artifact routes remain provider-owned debug surfaces

**Reason**: Old server raw artifact routes are retired.

**Migration**: Use passive-server artifact routes for raw provider output.

### Requirement: Managed-agent summary state exposes gateway and mailbox posture and includes a detailed state route

**Reason**: Old server state/detail routes are retired.

**Migration**: Use passive-server managed-state and managed-state/detail compatibility routes.

### Requirement: Managed-agent control accepts transport-neutral request submission

**Reason**: Transport-neutral request submission is maintained through passive-server rather than old server.

**Migration**: Use passive-server request submission and interrupt routes.

### Requirement: `houmao-server` exposes gateway-mediated managed-agent request routes

**Reason**: Gateway-mediated managed-agent API ownership moves to passive-server/gateway paths.

**Migration**: Use passive-server gateway proxy routes or direct gateway routes according to current passive-server docs.

### Requirement: `houmao-server` exposes managed-agent gateway direct prompt-control routes

**Reason**: Old server gateway prompt-control proxy routes are retired.

**Migration**: Use passive-server gateway proxy behavior where maintained, or direct gateway routes for live gateway control.

### Requirement: `houmao-server` exposes managed-agent gateway headless chat-session state and next-prompt override routes

**Reason**: Old server gateway headless-control proxy routes are retired.

**Migration**: Use passive-server/gateway maintained routes for headless control state and prompt-session selection.

### Requirement: `houmao-server` exposes managed-agent gateway raw control-input routes

**Reason**: Old server raw control-input proxy routes are retired.

**Migration**: Use passive-server gateway proxy behavior where maintained, or direct gateway raw control-input routes.

### Requirement: `houmao-server` exposes managed-agent gateway TUI tracking routes

**Reason**: Old server gateway TUI tracking proxy routes are retired.

**Migration**: Use passive-server observation routes and gateway TUI routes.

### Requirement: `houmao-server` exposes pair-owned managed-agent mail routes

**Reason**: Old server mail proxy routes are retired.

**Migration**: Use passive-server mail proxy routes and maintained manager mailbox commands.

### Requirement: `houmao-server` exposes managed-agent gateway operational routes

**Reason**: Old server gateway lifecycle routes are retired.

**Migration**: Use passive-server gateway status/proxy behavior and local authority handling for attach/detach where passive-server delegates to the owning host.

### Requirement: Native headless launch accepts official mailbox options while gateway lifecycle remains separate

**Reason**: Public native headless launch ownership moves to passive-server.

**Migration**: Preserve official mailbox option handling in passive-server managed-headless launch.

### Requirement: Managed headless turn reconciliation is execution-owned

**Reason**: Old server execution ownership is retired as public API.

**Migration**: Keep execution-owned reconciliation in passive-server managed-headless control.

### Requirement: Managed headless restart recovery does not depend on tmux watch semantics

**Reason**: Old server restart-recovery route ownership is retired.

**Migration**: Keep equivalent managed-headless recovery behavior in passive-server.

### Requirement: Managed headless tmux inspectability keeps the agent in window 0

**Reason**: Old server-managed headless tmux topology is no longer public API.

**Migration**: Preserve inspectability guarantees in runtime/passive-server managed-headless behavior where applicable.

### Requirement: `houmao-server` preserves request-scoped headless execution overrides across managed prompt routes

**Reason**: Old server managed prompt routes are retired.

**Migration**: Preserve request-scoped overrides in passive-server managed prompt/turn routes where applicable.

### Requirement: Managed-agent gateway attach API accepts TUI tracking timings

**Reason**: Old server attach API is retired.

**Migration**: Apply tracking timing inputs to passive-server/local gateway attach behavior when that path remains supported.

### Requirement: Managed-agent API stop responses include durable cleanup locators

**Reason**: Old server stop responses are retired.

**Migration**: Preserve needed cleanup locator fields in passive-server stop responses where maintained.
