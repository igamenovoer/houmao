## ADDED Requirements

### Requirement: Passive server provides a mail post proxy endpoint
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/mail/post` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayMailPostRequestV1` payload to `POST /v1/mail/post`.

The response body SHALL be a `GatewayMailActionResponseV1` payload.

#### Scenario: Mail post forwards to the gateway and returns the action response
- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/mail/post` with a valid `GatewayMailPostRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayMailActionResponseV1` payload from the gateway

