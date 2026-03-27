## ADDED Requirements

### Requirement: Passive server provides a gateway raw control-input proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/control/send-keys` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayControlInputRequestV1` payload to `POST /v1/control/send-keys`.

The response body SHALL be a `GatewayControlInputResultV1` payload from the live gateway.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the existing passive gateway status and request-submission endpoints.

#### Scenario: Raw control-input proxy forwards to the gateway and returns the action result
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/send-keys` with a valid `GatewayControlInputRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayControlInputResultV1` payload from the gateway

#### Scenario: Raw control-input proxy returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/send-keys` with a valid body
- **THEN** the response status code is 502

### Requirement: Passive server provides gateway mail-notifier proxy endpoints
The passive server SHALL expose proxy routes for the gateway mail-notifier control surface:

- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`

Those routes SHALL resolve the agent, create a `GatewayClient`, and proxy the corresponding direct gateway mail-notifier calls.

The response body for each route SHALL be a `GatewayMailNotifierStatusV1` payload from the live gateway.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the existing passive gateway status and request-submission endpoints.

#### Scenario: Mail-notifier status returns the live gateway notifier payload
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway/mail-notifier`
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailNotifierStatusV1` payload from the gateway

#### Scenario: Mail-notifier enable forwards through the passive proxy
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `PUT /houmao/agents/abc123/gateway/mail-notifier` with a valid `GatewayMailNotifierPutV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the updated `GatewayMailNotifierStatusV1` payload from the gateway

#### Scenario: Mail-notifier disable returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `DELETE /houmao/agents/abc123/gateway/mail-notifier`
- **THEN** the response status code is 502
