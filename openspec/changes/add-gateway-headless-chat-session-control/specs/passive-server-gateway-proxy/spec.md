## ADDED Requirements

### Requirement: Passive server provides gateway headless chat-session state and next-prompt override proxy endpoints
The passive server SHALL expose proxy routes for the gateway headless chat-session control surface:

- `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`
- `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway headless control calls.

The response body for each route SHALL be the live gateway headless control-state payload.

Agent-not-found (`404`), ambiguous (`409`), and no-gateway (`502`) error handling SHALL follow the same pattern as the existing passive gateway status and request-submission endpoints.

If the live gateway rejects the request because the addressed target is not headless, the passive server SHALL forward that validation failure explicitly rather than pretending that a headless proxy surface exists.

#### Scenario: Headless control state returns the live gateway payload
- **WHEN** the discovery index contains agent `abc123` with a live headless gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/control/headless/state`
- **THEN** the response status code is `200`
- **AND THEN** the response body is the live gateway headless control-state payload

#### Scenario: Next-prompt override proxy returns the updated headless control state
- **WHEN** the discovery index contains agent `abc123` with a live headless gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/headless/next-prompt-session` with `mode = new`
- **THEN** the response status code is `200`
- **AND THEN** the response body reports a pending one-shot next-prompt override

#### Scenario: TUI-backed gateway target returns validation failure through the proxy
- **WHEN** the discovery index contains agent `abc123` with a live TUI gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/control/headless/state` or `POST /houmao/agents/abc123/gateway/control/headless/next-prompt-session`
- **THEN** the passive server forwards the live gateway validation failure explicitly
- **AND THEN** it does not pretend that a headless proxy surface exists for that target

## MODIFIED Requirements

### Requirement: Passive server provides a gateway direct prompt-control proxy endpoint

The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/control/prompt` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayPromptControlRequestV1` payload to `POST /v1/control/prompt`.

For headless targets, the proxied request body MAY include optional structured `chat_session` with the same semantics as the direct gateway route:

- `mode = auto | new | current | tool_last_or_new | exact`
- `id` required only when `mode = exact`

The response body SHALL be a `GatewayPromptControlResultV1` payload from the live gateway.

Agent-not-found (`404`), ambiguous (`409`), and no-gateway (`502`) error handling SHALL follow the same pattern as the passive gateway status endpoint. If the live gateway itself refuses prompt control explicitly, including validation rejection of unsupported `chat_session` modes for a TUI target, the passive server SHALL return that refusal explicitly rather than converting it into queued acceptance.

#### Scenario: Direct prompt-control proxy forwards to the gateway and returns the live result
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with a valid `GatewayPromptControlRequestV1` body
- **THEN** the response status code is `200`
- **AND THEN** the response body is the `GatewayPromptControlResultV1` payload from the gateway

#### Scenario: Direct prompt-control proxy returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with a valid body
- **THEN** the response status code is `502`

#### Scenario: Direct prompt-control refusal is forwarded explicitly
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt`
- **AND WHEN** the live gateway refuses that prompt-control request explicitly
- **THEN** the passive server returns that refusal explicitly
- **AND THEN** it does not claim that the prompt was accepted for later queued execution

#### Scenario: Structured headless session selector is forwarded unchanged through the proxy
- **WHEN** the discovery index contains agent `abc123` with a live headless gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with `chat_session.mode = tool_last_or_new`
- **THEN** the passive server forwards that selector unchanged to the live gateway
- **AND THEN** the passive server does not reinterpret the selector as a passive-server-local session choice

#### Scenario: TUI new-session reset selector is forwarded unchanged through the proxy
- **WHEN** the discovery index contains agent `abc123` with a live TUI gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with `chat_session.mode = new`
- **THEN** the passive server forwards that selector unchanged to the live gateway
- **AND THEN** the passive server does not reinterpret the selector as passive-server-local TUI control logic
