## ADDED Requirements

### Requirement: Gateway-enabled tmux-backed sessions expose gateway discovery pointers via tmux session environment
For gateway-enabled tmux-backed sessions, the system SHALL set tmux session environment variables named:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_ROOT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

`AGENTSYS_AGENT_GATEWAY_HOST` SHALL be the active gateway bind host for that session. Allowed values in this change are exactly `127.0.0.1` and `0.0.0.0`.

`AGENTSYS_AGENT_GATEWAY_PORT` SHALL be the decimal port number of the active HTTP gateway listener for that session.

`AGENTSYS_GATEWAY_ROOT` SHALL be the absolute path of the per-agent gateway root for that session.

`AGENTSYS_GATEWAY_STATE_PATH` SHALL be the absolute path of the current gateway state artifact for that session.

`AGENTSYS_GATEWAY_PROTOCOL_VERSION` SHALL identify the gateway protocol version expected for that session's gateway root.

When tmux-backed backend code later resumes control of the same live session with effective gateway bindings available, it SHALL re-publish the same gateway discovery pointers into the tmux session environment.

#### Scenario: Session start sets gateway discovery pointers
- **WHEN** the runtime starts a gateway-enabled tmux-backed session with tmux session name `AGENTSYS-gpu`
- **THEN** the tmux session environment contains `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_ROOT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** `AGENTSYS_AGENT_GATEWAY_HOST` and `AGENTSYS_AGENT_GATEWAY_PORT` identify the active HTTP gateway listener for that session
- **AND THEN** `AGENTSYS_GATEWAY_ROOT` and `AGENTSYS_GATEWAY_STATE_PATH` are absolute paths for that session's active gateway root and current state artifact

#### Scenario: Resume re-publishes gateway discovery pointers
- **WHEN** the runtime resumes control of gateway-enabled tmux session `AGENTSYS-gpu`
- **AND WHEN** resume has already determined the effective gateway bindings for that control operation
- **THEN** the tmux session environment contains `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_ROOT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

### Requirement: Name-resolved tmux identities allow optional gateway discovery for gateway-aware tools
When a caller resolves a non-path-like `--agent-identity` value to a live tmux-backed session, gateway-aware tools SHALL be able to discover the gateway host, gateway port, and related gateway pointers from that tmux session environment when those values are present.

Missing gateway pointers SHALL NOT make legacy non-gateway session resolution fail by themselves.

When a caller uses a gateway-aware control path that requires gateway discovery for a gateway-enabled session and the required gateway pointers are missing or invalid, the system SHALL fail with an explicit gateway-discovery error rather than silently bypassing gateway discovery.

#### Scenario: Legacy session still resolves without gateway pointers
- **WHEN** a caller resolves a live tmux-backed session that is not gateway-enabled
- **AND WHEN** `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_ROOT`, and related gateway pointers are absent from that tmux session environment
- **THEN** the existing non-gateway agent-identity resolution still succeeds
- **AND THEN** gateway-pointer absence alone does not make that legacy resolution fail

#### Scenario: Gateway-aware resolution fails explicitly on missing required gateway pointers
- **WHEN** a caller uses a gateway-aware control path for a live tmux-backed session that is expected to be gateway-enabled
- **AND WHEN** the tmux session environment is missing or contains invalid required gateway discovery pointers such as `AGENTSYS_AGENT_GATEWAY_HOST` or `AGENTSYS_AGENT_GATEWAY_PORT`
- **THEN** the system fails that gateway-aware control path with an explicit gateway-discovery error
- **AND THEN** it does not silently fall back to bypassing gateway discovery for that gateway-managed request
