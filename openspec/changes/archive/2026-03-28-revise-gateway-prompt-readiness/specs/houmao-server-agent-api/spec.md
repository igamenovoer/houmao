## ADDED Requirements

### Requirement: `houmao-server` exposes managed-agent gateway direct prompt-control routes

`houmao-server` SHALL expose a managed-agent gateway direct prompt-control route so callers can require immediate live prompt dispatch semantics without directly addressing gateway listener ports.

At minimum, that route family SHALL include:

- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`

That route SHALL accept the same `GatewayPromptControlRequestV1` payload shape used by the direct gateway route `POST /v1/control/prompt` and SHALL return the same `GatewayPromptControlResultV1` success payload shape.

The server SHALL satisfy that route by proxying an eligible attached live gateway rather than by introducing a second independent prompt-control implementation inside `houmao-server`.

If the addressed managed agent does not have an eligible live gateway attached, or if the live gateway rejects prompt control because the target is not ready, unavailable, unsupported, or otherwise refused, the route SHALL reject the request explicitly rather than fabricating queued acceptance.

The route SHALL remain distinct from `POST /houmao/agents/{agent_ref}/gateway/requests`; immediate prompt control SHALL NOT be redefined as queued semantic gateway request submission.

#### Scenario: Caller dispatches prompt through the managed-agent API

- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/prompt` with a valid `GatewayPromptControlRequestV1` body
- **AND WHEN** the addressed managed agent has an eligible live gateway attached and prompt-ready
- **THEN** `houmao-server` returns the `GatewayPromptControlResultV1` payload from that live gateway
- **AND THEN** the caller does not need to contact the gateway listener endpoint directly to send the prompt

#### Scenario: Prompt-control refusal is propagated explicitly

- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- **AND WHEN** the addressed live gateway refuses prompt control explicitly
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** the response does not claim that the prompt was accepted for later queued execution

#### Scenario: Direct prompt control remains separate from queued gateway requests

- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- **THEN** `houmao-server` proxies that request to the live gateway direct prompt-control route
- **AND THEN** it does not rewrite the request into `POST /houmao/agents/{agent_ref}/gateway/requests`
