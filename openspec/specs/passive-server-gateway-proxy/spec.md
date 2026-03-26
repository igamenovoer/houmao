# passive-server-gateway-proxy Specification

## Purpose
TBD - created by archiving change passive-server-gateway-proxy. Update Purpose after archive.

## Requirements

### Requirement: Passive server provides a gateway status proxy endpoint
The passive server SHALL expose `GET /houmao/agents/{agent_ref}/gateway` that resolves the agent, creates a `GatewayClient` from the registry record's gateway coordinates, and forwards the response from `GET /v1/status`.

The response body SHALL be a `GatewayStatusV1` payload from the live gateway.

If the agent is not found, the endpoint SHALL return 404. If the agent name is ambiguous, it SHALL return 409. If the agent has no live gateway attached, it SHALL return 502 with a descriptive message.

#### Scenario: Gateway status returns the live gateway's status
- **WHEN** the discovery index contains agent `abc123` with a live gateway at `127.0.0.1:9901`
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway`
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayStatusV1` payload from the gateway's `/v1/status`

#### Scenario: Gateway status returns 404 for unknown agent
- **WHEN** the discovery index contains no agent matching `unknown`
- **AND WHEN** a caller sends `GET /houmao/agents/unknown/gateway`
- **THEN** the response status code is 404

#### Scenario: Gateway status returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway (gateway field is None or host/port are None)
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway`
- **THEN** the response status code is 502
- **AND THEN** the response body contains a diagnostic message about the gateway not being attached

#### Scenario: Gateway status returns 502 when gateway is unreachable
- **WHEN** the discovery index contains agent `abc123` with gateway coordinates that are unreachable
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/gateway`
- **THEN** the response status code is 502
- **AND THEN** the response body contains the error detail from the failed gateway connection

### Requirement: Passive server provides a gateway request submission proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/requests` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayRequestCreateV1` payload to `POST /v1/requests`.

The response body SHALL be a `GatewayAcceptedRequestV1` payload from the live gateway.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the gateway status endpoint.

#### Scenario: Request submission forwards to the gateway and returns the accepted response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/requests` with a valid `GatewayRequestCreateV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayAcceptedRequestV1` payload from the gateway

#### Scenario: Request submission returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/requests` with a valid body
- **THEN** the response status code is 502

### Requirement: Passive server provides a mail status proxy endpoint
The passive server SHALL expose `GET /houmao/agents/{agent_ref}/mail/status` that resolves the agent, creates a `GatewayClient`, and forwards the response from `GET /v1/mail/status`.

The response body SHALL be a `GatewayMailStatusV1` payload.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern.

#### Scenario: Mail status returns the gateway's mailbox status
- **WHEN** the discovery index contains agent `abc123` with a live gateway that has mailbox bindings
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/mail/status`
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailStatusV1` payload

#### Scenario: Mail status returns 502 when no gateway is attached
- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `GET /houmao/agents/abc123/mail/status`
- **THEN** the response status code is 502

### Requirement: Passive server provides a mail check proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/check` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailCheckRequestV1` payload to `POST /v1/mail/check`.

The response body SHALL be a `GatewayMailCheckResponseV1` payload.

#### Scenario: Mail check forwards to the gateway and returns messages
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/check` with a valid `GatewayMailCheckRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailCheckResponseV1` payload from the gateway

### Requirement: Passive server provides a mail send proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/send` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailSendRequestV1` payload to `POST /v1/mail/send`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

#### Scenario: Mail send forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/send` with a valid `GatewayMailSendRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: Passive server provides a mail reply proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/reply` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailReplyRequestV1` payload to `POST /v1/mail/reply`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

#### Scenario: Mail reply forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/reply` with a valid `GatewayMailReplyRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

### Requirement: All gateway proxy endpoints use consistent agent resolution and error handling
All gateway proxy endpoints SHALL resolve the `{agent_ref}` path parameter using the same logic as `GET /houmao/agents/{agent_ref}`:
1. Try direct lookup by `agent_id`.
2. Fall back to canonical `agent_name` lookup.
3. Return 404 if not found, 409 if ambiguous.

When the resolved agent has no live gateway (gateway is None or host/port are None), all proxy endpoints SHALL return 502 with `detail` describing that the gateway is not attached.

When the `GatewayClient` call fails with a connection or HTTP error, all proxy endpoints SHALL return 502 with the upstream error detail forwarded.

#### Scenario: All proxy endpoints return 409 for ambiguous agent name
- **WHEN** the discovery index contains two agents both named `AGENTSYS-alpha` with different agent_id values
- **AND WHEN** a caller sends any gateway proxy request to `/houmao/agents/alpha/gateway`
- **THEN** the response status code is 409
- **AND THEN** the response body contains the ambiguous agent IDs
