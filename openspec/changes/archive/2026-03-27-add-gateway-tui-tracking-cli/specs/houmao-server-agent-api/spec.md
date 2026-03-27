## ADDED Requirements

### Requirement: `houmao-server` exposes managed-agent gateway TUI tracking routes
`houmao-server` SHALL expose managed-agent gateway TUI tracking routes so callers can inspect raw gateway-owned TUI state and history or record prompt-note evidence without directly addressing gateway listener ports.

At minimum, that route family SHALL include:

- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`

Those routes SHALL operate only through an eligible live gateway attached to the addressed managed agent.

`GET /houmao/agents/{agent_ref}/gateway/tui/state` SHALL return the same raw gateway-owned TUI state shape used by the direct gateway TUI state route.

`GET /houmao/agents/{agent_ref}/gateway/tui/history` SHALL return the same bounded recent gateway-owned TUI snapshot-history shape used by the direct gateway TUI history route.

`POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt` SHALL accept prompt-note input for the live gateway tracking surface without reinterpreting that request as a queued gateway prompt.

If the addressed managed agent does not have an eligible live gateway attached, the routes SHALL reject the request explicitly rather than silently falling back to another transport path.

#### Scenario: Caller reads gateway-owned TUI state through the managed-agent API
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-server` returns the raw gateway-owned TUI state for that managed agent
- **AND THEN** the caller does not need direct knowledge of the gateway host or port

#### Scenario: Caller reads bounded gateway-owned TUI snapshot history through the managed-agent API
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-server` returns the bounded recent gateway-owned TUI snapshot history for that managed agent
- **AND THEN** the caller does not need direct knowledge of the gateway host or port

#### Scenario: Caller records prompt-note evidence through the managed-agent API
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt` with valid prompt-note input
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-server` records that prompt-note evidence through the live gateway tracking surface
- **AND THEN** it does not rewrite that request into `POST /houmao/agents/{agent_ref}/gateway/requests`
