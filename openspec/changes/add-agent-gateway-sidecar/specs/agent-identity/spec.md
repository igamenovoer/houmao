## ADDED Requirements

### Requirement: Gateway-capable tmux-backed sessions expose stable attach pointers via tmux session environment
For gateway-capable tmux-backed sessions, the system SHALL set tmux session environment variables named:

- `AGENTSYS_GATEWAY_ATTACH_PATH`
- `AGENTSYS_GATEWAY_ROOT`

`AGENTSYS_GATEWAY_ATTACH_PATH` SHALL be the absolute path of the secret-free attach-contract file for that session.

`AGENTSYS_GATEWAY_ROOT` SHALL be the absolute path of the per-agent gateway root for that session.

When a live gateway instance is currently attached, the system SHALL additionally set:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

`AGENTSYS_AGENT_GATEWAY_HOST` SHALL be the active gateway bind host for the currently running gateway instance for that session. Allowed values in this change are exactly `127.0.0.1` and `0.0.0.0`.

`AGENTSYS_AGENT_GATEWAY_PORT` SHALL be the decimal port number of the active HTTP gateway listener for that running gateway instance.

`AGENTSYS_GATEWAY_STATE_PATH` SHALL be the absolute path of the current gateway state artifact for the running gateway instance.

`AGENTSYS_GATEWAY_PROTOCOL_VERSION` SHALL identify the gateway protocol version expected for that session's gateway root, including the shared schema for `state.json` and `GET /v1/status`.

When tmux-backed backend code later resumes control of the same live session with effective attach or live gateway bindings available, it SHALL re-publish the same gateway discovery pointers into the tmux session environment.

#### Scenario: Session start sets stable attach pointers
- **WHEN** the runtime starts a gateway-capable tmux-backed session with tmux session name `AGENTSYS-gpu`
- **THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`
- **AND THEN** those pointers are absolute paths for that session's attach contract and gateway root even if no gateway instance is currently running

#### Scenario: Live gateway attach sets active gateway pointers
- **WHEN** a gateway instance is attached to tmux session `AGENTSYS-gpu`
- **THEN** the tmux session environment contains `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those pointers describe the currently running gateway instance

#### Scenario: Resume re-publishes attach pointers
- **WHEN** the runtime resumes control of gateway-capable tmux session `AGENTSYS-gpu`
- **AND WHEN** resume has already determined the effective attach metadata for that control operation
- **THEN** the tmux session environment contains `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`

### Requirement: Name-resolved tmux identities allow optional gateway discovery for gateway-aware tools
When a caller resolves a non-path-like `--agent-identity` value to a live tmux-backed session, gateway-aware tools SHALL be able to discover stable gateway attachability and, when present, live gateway bindings from that tmux session environment.

Missing gateway pointers SHALL NOT make legacy non-gateway session resolution fail by themselves.

When a caller uses a gateway-aware lifecycle or control path that requires attachability or a live gateway instance and the required gateway pointers are missing or invalid, the system SHALL fail with an explicit gateway-discovery error rather than silently bypassing gateway discovery.

#### Scenario: Legacy session still resolves without gateway pointers
- **WHEN** a caller resolves a live tmux-backed session that publishes no gateway attach metadata
- **AND WHEN** `AGENTSYS_GATEWAY_ATTACH_PATH`, `AGENTSYS_GATEWAY_ROOT`, and related gateway pointers are absent from that tmux session environment
- **THEN** the existing non-gateway agent-identity resolution still succeeds
- **AND THEN** gateway-pointer absence alone does not make that legacy resolution fail

#### Scenario: Attach-aware resolution fails explicitly on missing attach metadata
- **WHEN** a caller uses a gateway attach-aware lifecycle path for a live tmux-backed session that is expected to be gateway-capable
- **AND WHEN** the tmux session environment is missing or contains invalid required attach pointers such as `AGENTSYS_GATEWAY_ATTACH_PATH`
- **THEN** the system fails that lifecycle path with an explicit gateway-discovery error
- **AND THEN** it does not silently guess unrelated attach metadata for that session
