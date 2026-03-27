## ADDED Requirements

### Requirement: Passive server provides a gateway direct prompt-control proxy endpoint

The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/control/prompt` that resolves the agent, creates a `GatewayClient`, and forwards the request body as a `GatewayPromptControlRequestV1` payload to `POST /v1/control/prompt`.

The response body SHALL be a `GatewayPromptControlResultV1` payload from the live gateway.

Agent-not-found (404), ambiguous (409), and no-gateway (502) error handling SHALL follow the same pattern as the passive gateway status endpoint. If the live gateway itself refuses prompt control explicitly, the passive server SHALL return that refusal explicitly rather than converting it into queued acceptance.

#### Scenario: Direct prompt-control proxy forwards to the gateway and returns the live result

- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with a valid `GatewayPromptControlRequestV1` body
- **THEN** the response status code is 200
- **AND THEN** the response body is the `GatewayPromptControlResultV1` payload from the gateway

#### Scenario: Direct prompt-control proxy returns 502 when no gateway is attached

- **WHEN** the discovery index contains agent `abc123` with no live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt` with a valid body
- **THEN** the response status code is 502

#### Scenario: Direct prompt-control refusal is forwarded explicitly

- **WHEN** the discovery index contains agent `abc123` with a live gateway
- **AND WHEN** a caller sends `POST /houmao/agents/abc123/gateway/control/prompt`
- **AND WHEN** the live gateway refuses that prompt-control request explicitly
- **THEN** the passive server returns that refusal explicitly
- **AND THEN** it does not claim that the prompt was accepted for later queued execution
