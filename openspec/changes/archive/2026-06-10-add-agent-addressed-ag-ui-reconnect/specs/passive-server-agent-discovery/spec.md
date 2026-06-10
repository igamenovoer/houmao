## ADDED Requirements

### Requirement: Passive server resolves agent-address AG-UI attachment state
The passive server SHALL expose a read-only agent-address resolution surface for GUI clients that target an agent by `agent_id` or friendly `agent_name`.

The resolution surface SHALL return a deterministic state for each request:

- `unknown` when no known agent matches the reference;
- `ambiguous` when a friendly name matches multiple known agents;
- `offline` when the agent is known but no live record is currently usable;
- `live_without_gateway` when the agent is live but no gateway coordinates are available;
- `live_with_gateway` when the agent is live and current gateway coordinates are available.

When the agent is known, the response SHALL include the authoritative `agent_id` and canonical `agent_name`. When the agent is live with a gateway, the response SHALL include current gateway host, port, and protocol metadata as volatile live presence.

The resolution surface SHALL NOT start, stop, launch, restart, interrupt, shut down, or otherwise control the agent lifecycle.

#### Scenario: GUI resolves a live agent with current gateway
- **WHEN** the passive server can resolve `agent_id=abc123` to a live registry record with gateway host and port
- **AND WHEN** the GUI requests the agent-address resolution surface for `abc123`
- **THEN** the response state is `live_with_gateway`
- **AND THEN** the response includes the current gateway coordinates

#### Scenario: GUI resolves a known offline agent
- **WHEN** the passive server can resolve `agent_id=abc123` as known but no live registry record is usable
- **AND WHEN** the GUI requests the agent-address resolution surface for `abc123`
- **THEN** the response state is `offline`
- **AND THEN** the response includes the authoritative `agent_id` without gateway coordinates

#### Scenario: Ambiguous friendly name returns conflict
- **WHEN** friendly name `alpha` matches multiple known agent ids
- **AND WHEN** the GUI requests the agent-address resolution surface for `alpha`
- **THEN** the passive server returns an ambiguous result or conflict response
- **AND THEN** the response lists enough safe agent identity metadata for the user to disambiguate

### Requirement: Passive server may proxy AG-UI requests by resolved agent address
If the passive server exposes browser-friendly AG-UI proxy routes by resolved agent address, those routes SHALL accept an `agent_ref`, resolve the current gateway, and forward AG-UI requests to that gateway.

When such proxy routes are present, they SHALL resolve the gateway on each new connection or request rather than caching a stale gateway URL as the durable target.

When no current gateway is available, proxy routes SHALL return a deterministic offline or gateway-unavailable response and SHALL NOT wait forever inside a request unless the route explicitly documents streaming wait semantics.

Proxy routes SHALL preserve the lifecycle boundary: proxying AG-UI connect, run, detach, or event publish requests SHALL NOT start, stop, restart, interrupt, or shut down the agent.

#### Scenario: Proxy resolves gateway at connection time
- **WHEN** an agent's gateway port changes after a restart
- **AND WHEN** a GUI opens a new AG-UI proxy connection by `agent_id`
- **THEN** the passive server resolves the current gateway coordinates before forwarding
- **AND THEN** it does not forward to the old port

#### Scenario: Proxy reports unavailable gateway without lifecycle control
- **WHEN** an agent is known but has no live gateway
- **AND WHEN** a GUI submits an AG-UI proxy request for that agent
- **THEN** the passive server reports that the gateway is unavailable
- **AND THEN** it does not launch, stop, restart, interrupt, or shut down the agent
