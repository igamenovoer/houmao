## ADDED Requirements

### Requirement: Managed-agent stop supports TUI-backed agents
`POST /houmao/agents/{agent_ref}/stop` SHALL support both managed headless agents and managed TUI-backed agents.

For managed headless agents, the route SHALL continue using the native headless lifecycle stop path.

For managed TUI-backed agents, the route SHALL resolve the addressed managed agent to its pair-owned CAO session and stop it through the existing pair-managed session-delete lifecycle rather than requiring the caller to resolve and delete a raw CAO session separately.

The route SHALL keep using managed-agent alias resolution rather than forcing callers to switch from managed-agent references to raw session identifiers.

#### Scenario: TUI-backed managed agent stops through the shared managed-agent route
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/stop` for a managed TUI-backed agent
- **THEN** `houmao-server` stops that managed agent through the pair-owned TUI lifecycle
- **AND THEN** the caller does not need to issue a separate raw `/cao/sessions/{session_name}` delete request to stop that agent

### Requirement: `houmao-server` exposes gateway-mediated managed-agent request routes
`houmao-server` SHALL expose server-owned gateway-mediated managed-agent request routes in addition to the existing transport-neutral managed-agent request route.

At minimum, that route family SHALL include:

- `POST /houmao/agents/{agent_ref}/gateway/requests`

That route SHALL accept gateway request kinds compatible with the live gateway request surface, including at minimum:

- `submit_prompt`
- `interrupt`

The server SHALL resolve the managed agent, verify that an eligible live gateway is attached, and proxy the accepted request through the live gateway authority without requiring the caller to discover the gateway listener endpoint.

If no eligible live gateway is attached, the route SHALL reject the request explicitly rather than silently falling back to another transport path.

#### Scenario: Gateway-mediated prompt request is accepted through `houmao-server`
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/requests` with gateway request kind `submit_prompt`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-server` accepts that request through the managed agent's live gateway authority
- **AND THEN** the caller does not need direct knowledge of the gateway host or port

#### Scenario: Missing live gateway rejects gateway-mediated request explicitly
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/requests`
- **AND WHEN** the addressed managed agent does not have an eligible live gateway attached
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** it does not pretend that the gateway-mediated request was accepted for later execution

### Requirement: `houmao-server` exposes pair-owned managed-agent mail routes
`houmao-server` SHALL expose pair-owned managed-agent mail follow-up routes so callers can perform mailbox operations through the managed-agent API without directly addressing gateway listener ports.

At minimum, that route family SHALL include:

- `GET /houmao/agents/{agent_ref}/mail/status`
- `POST /houmao/agents/{agent_ref}/mail/check`
- `POST /houmao/agents/{agent_ref}/mail/send`
- `POST /houmao/agents/{agent_ref}/mail/reply`

In v1, the server SHALL satisfy those routes by proxying an attached eligible live gateway rather than by introducing a separate direct runtime-backed mailbox path.

Those routes SHALL coexist with the existing `/houmao/agents/{agent_ref}/gateway/mail-notifier` configuration routes rather than replacing them. The `gateway/mail-notifier` routes remain background notifier-configuration surfaces, while `mail/*` is the foreground mailbox-operation surface.

If the addressed managed agent does not expose pair-owned mailbox follow-up capability or does not have an eligible live gateway attached, the routes SHALL reject the request explicitly rather than silently fabricating success.

#### Scenario: Caller checks mail through the managed-agent API
- **WHEN** a caller requests `POST /houmao/agents/{agent_ref}/mail/check` for a managed agent that exposes pair-owned mailbox follow-up capability
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-server` returns the managed-agent mail-check result through its own API
- **AND THEN** the caller does not need to contact the gateway listener endpoint directly to perform that check

#### Scenario: Mail follow-up fails clearly when mailbox capability or live gateway access is unavailable
- **WHEN** a caller submits one of the managed-agent mail routes for an addressed agent that does not expose pair-owned mailbox follow-up capability or does not have an eligible live gateway attached
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** the response does not claim that the mailbox action succeeded
