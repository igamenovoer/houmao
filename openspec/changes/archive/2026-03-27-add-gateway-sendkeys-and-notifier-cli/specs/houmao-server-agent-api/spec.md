## ADDED Requirements

### Requirement: `houmao-server` exposes managed-agent gateway raw control-input routes
`houmao-server` SHALL expose a managed-agent gateway raw control-input route so callers can deliver live gateway `send-keys` operations without addressing gateway listener ports directly.

At minimum, that route family SHALL include:

- `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`

That route SHALL accept the same `GatewayControlInputRequestV1` payload shape used by the direct gateway route `POST /v1/control/send-keys` and SHALL return the same `GatewayControlInputResultV1` response shape.

The server SHALL satisfy that route by proxying an eligible attached live gateway rather than by introducing a second direct tmux-control-input path inside `houmao-server`.

If the addressed managed agent does not have an eligible live gateway attached, or if live gateway admission is blocked for that control-input request, the route SHALL reject the request explicitly rather than silently fabricating success.

The route SHALL remain distinct from `POST /houmao/agents/{agent_ref}/gateway/requests`; raw control input SHALL NOT be redefined as a queued semantic gateway request kind.

#### Scenario: Caller sends raw control input through the managed-agent API
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/send-keys` with a valid `GatewayControlInputRequestV1` body
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-server` returns the `GatewayControlInputResultV1` payload from that live gateway
- **AND THEN** the caller does not need to contact the gateway listener endpoint directly to deliver the control input

#### Scenario: Raw control input fails clearly when no live gateway is attached
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- **AND WHEN** the addressed managed agent does not have an eligible live gateway attached
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** the response does not claim that the control input was delivered

#### Scenario: Raw control input remains separate from queued gateway requests
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- **THEN** `houmao-server` proxies that request to the live gateway raw control-input route
- **AND THEN** it does not rewrite the request into `POST /houmao/agents/{agent_ref}/gateway/requests`
