## Purpose
Define passive-server compatibility contracts that let pair-facing Houmao clients treat `houmao-passive-server` as a supported managed authority.

## Requirements

### Requirement: Pair-authority client detection accepts `houmao-passive-server`
The system SHALL provide a pair-authority client factory that probes `GET /health` and accepts `houmao_service == "houmao-passive-server"` as a supported pair authority alongside `houmao-server`.

The factory SHALL return a passive-server-aware managed client for `houmao-passive-server`, SHALL return the existing old-server client for `houmao-server`, and SHALL reject raw CAO or unknown service identities with an explicit unsupported-pair error.

#### Scenario: Passive server health selects the passive client
- **WHEN** a pair-facing consumer resolves a client for a base URL whose `GET /health` response is `{"status": "ok", "houmao_service": "houmao-passive-server"}`
- **THEN** the factory returns a passive-server-aware managed client
- **AND THEN** the caller does not reject the passive server as an unsupported authority

#### Scenario: Unknown pair identity is rejected explicitly
- **WHEN** a pair-facing consumer resolves a client for a base URL whose health identity is neither `houmao-server` nor `houmao-passive-server`
- **THEN** client resolution fails explicitly
- **AND THEN** the error does not pretend the target is a supported Houmao pair authority

### Requirement: Passive server exposes managed-agent compatibility views for pair consumers
`houmao-passive-server` SHALL expose the following compatibility routes for pair-managed consumers:

- `GET /houmao/agents/{agent_ref}/managed-state`
- `GET /houmao/agents/{agent_ref}/managed-state/detail`
- `GET /houmao/agents/{agent_ref}/managed-history`

These routes SHALL return `HoumaoManagedAgentStateResponse`, `HoumaoManagedAgentDetailResponse`, and `HoumaoManagedAgentHistoryResponse` payloads from `houmao.server.models`.

For TUI-backed agents, the compatibility routes SHALL project the passive server's observation state into the managed-agent summary/detail/history models without removing or redefining the existing observation routes.

For headless agents managed by the passive server instance, the compatibility routes SHALL project managed headless summary/detail/history from the live authority handle and persisted turn metadata so pair consumers can inspect current status without first knowing a turn id.

#### Scenario: TUI agent managed-state returns managed summary
- **WHEN** a caller sends `GET /houmao/agents/{agent_ref}/managed-state` for a discovered TUI-backed agent
- **THEN** the response status code is 200
- **AND THEN** the response body is a `HoumaoManagedAgentStateResponse` whose `identity.transport` is `"tui"`

#### Scenario: Headless agent managed-state detail returns managed headless view
- **WHEN** a caller sends `GET /houmao/agents/{agent_ref}/managed-state/detail` for a headless agent managed by the passive server
- **THEN** the response status code is 200
- **AND THEN** the response body is a `HoumaoManagedAgentDetailResponse` whose `detail.transport` is `"headless"`
- **AND THEN** the detail includes current prompt-admission and last-turn fields derived from managed headless runtime state

#### Scenario: Compatibility routes preserve standard lookup errors
- **WHEN** a caller sends one of the compatibility route requests for an unknown or ambiguous `agent_ref`
- **THEN** the passive server returns the same 404 or 409 lookup semantics used by its other agent-resolution routes
- **AND THEN** the server does not return a success-shaped compatibility payload

### Requirement: Passive-server-aware managed clients normalize passive routes into pair-managed operations
The passive-server-aware managed client SHALL expose the pair-managed operations consumed by `houmao-mgr` and gateway-managed headless adapters.

At minimum, that client SHALL provide:

- lifecycle operations for health, current-instance, and shutdown
- managed-agent list and resolve operations projected from passive discovery routes
- managed-agent state, detail, and history operations backed by the compatibility routes
- prompt, interrupt, and stop operations backed by the passive request/action routes
- gateway status and gateway request operations backed by the passive gateway routes
- mailbox status/check/send/reply operations backed by the passive mail routes
- headless turn submit/status/events/artifact operations backed by the passive headless routes

Where the passive server returns passive-specific payloads, the client SHALL normalize them into the existing `HoumaoManagedAgent*` or `HoumaoHeadless*` models expected by pair consumers.

#### Scenario: Passive discovery is normalized into managed identities
- **WHEN** the passive-server-aware client lists or resolves managed agents through the passive discovery routes
- **THEN** it returns `HoumaoManagedAgentIdentity` projections usable by existing pair command code
- **AND THEN** callers do not need passive-server-specific identity parsing

#### Scenario: Passive prompt submission returns a managed request acceptance view
- **WHEN** a caller submits a prompt through the passive-server-aware managed client
- **THEN** the client returns a managed request acceptance model compatible with existing pair command handling
- **AND THEN** the caller does not need to inspect passive-server-specific response types directly

### Requirement: Managed-api-base-url consumers support passive server managed authorities
Any runtime component that uses `managed_api_base_url` metadata to create a managed client SHALL resolve that client through the pair-authority client factory and SHALL support both `houmao-server` and `houmao-passive-server`.

#### Scenario: Gateway-managed headless adapter talks to a passive server
- **WHEN** a gateway-managed headless adapter receives `managed_api_base_url` metadata pointing to a passive server
- **THEN** it creates a passive-server-aware managed client through the pair-authority factory
- **AND THEN** it can inspect managed-agent detail and submit prompt or interrupt requests without requiring `HoumaoServerClient`
