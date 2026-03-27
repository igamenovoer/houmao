## ADDED Requirements

### Requirement: Passive server provides gateway TUI tracking proxy endpoints
The passive server SHALL expose managed-agent gateway TUI tracking proxy routes for:

- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway TUI tracking calls.

The TUI state response body SHALL match the live gateway's TUI state payload.

The TUI history response body SHALL match the live gateway's bounded recent TUI snapshot-history payload.

The prompt-note response body SHALL match the live gateway's updated TUI state payload after prompt-note recording.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the existing passive gateway proxy endpoints.

#### Scenario: Passive server returns live gateway-owned TUI state
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/tui/state`
- **THEN** the response status code is 200
- **AND THEN** the response body is the live gateway's TUI state payload

#### Scenario: Passive server returns live gateway-owned bounded TUI snapshot history
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/tui/history`
- **THEN** the response status code is 200
- **AND THEN** the response body is the live gateway's bounded recent TUI snapshot-history payload

#### Scenario: Passive server forwards gateway prompt-note tracking
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/tui/note-prompt` with valid prompt-note input
- **THEN** the response status code is 200
- **AND THEN** the response body is the updated TUI state payload returned by the live gateway
