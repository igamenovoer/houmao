## ADDED Requirements

### Requirement: Managed-agent detailed state preserves one public shape while switching live backing source
`GET /houmao/agents/{agent_ref}/state/detail` SHALL preserve one public detail-route envelope and one transport-discriminated detail payload family regardless of whether the addressed managed agent is currently backed by an attached gateway or by the direct fallback path.

When an eligible live gateway is attached for the addressed managed agent, `houmao-server` SHALL prefer the gateway-owned per-agent live state for current detail projection.

When no eligible live gateway is attached, `houmao-server` SHALL continue serving the detail route through its direct fallback detail path for that managed agent.

This backing-source switch SHALL remain caller-transparent in this phase: the detail route SHALL NOT require callers to choose different route shapes or route keys based on whether the agent currently has an attached gateway.

#### Scenario: Attached TUI agent detail is projected from gateway-owned state
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed TUI agent with an eligible attached live gateway
- **THEN** `houmao-server` returns the existing managed-agent detail envelope for that agent
- **AND THEN** the TUI-specific detail payload is projected from the gateway-owned live state for that agent rather than requiring the caller to query the gateway directly

#### Scenario: Attached headless agent detail is projected from gateway-owned live posture
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed headless agent with an eligible attached live gateway
- **THEN** `houmao-server` returns the existing managed-agent detail envelope for that agent
- **AND THEN** current live execution posture in that detail response is projected from the gateway-backed per-agent control state while preserving the existing headless detail shape

#### Scenario: No-gateway fallback detail remains available
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` for a managed agent with no eligible attached live gateway
- **THEN** `houmao-server` continues serving the same managed-agent detail route through its direct fallback state path
- **AND THEN** the caller does not need a gateway sidecar to use the supported detail route
