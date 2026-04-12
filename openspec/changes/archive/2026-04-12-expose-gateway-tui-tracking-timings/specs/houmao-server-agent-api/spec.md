## ADDED Requirements

### Requirement: Managed-agent gateway attach API accepts TUI tracking timings
`POST /houmao/agents/{agent_ref}/gateway/attach` SHALL accept optional gateway TUI tracking timing configuration in addition to the existing execution-mode selection.

When the attach request includes gateway TUI tracking timing configuration, `houmao-server` SHALL validate and forward those timing values to the runtime-owned gateway attach path for the addressed managed agent.

When the attach request omits gateway TUI tracking timing configuration, `houmao-server` SHALL preserve the existing attach behavior and SHALL NOT force timing values that override gateway desired configuration.

The server-owned attach route SHALL keep the gateway TUI timing fields optional so existing clients that only send `execution_mode` continue to attach gateways with default or persisted timing behavior.

#### Scenario: Server attach forwards gateway TUI timing overrides
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/attach` with valid gateway TUI tracking timing overrides
- **AND WHEN** the addressed managed agent can attach a live gateway
- **THEN** `houmao-server` forwards those timing overrides to the runtime gateway attach operation
- **AND THEN** the attached gateway uses those values for gateway-owned TUI tracking

#### Scenario: Existing server attach request remains valid
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/attach` with only the existing execution-mode selection or with an empty body
- **THEN** `houmao-server` accepts the request under the existing attach semantics
- **AND THEN** gateway TUI tracking uses persisted desired timing values or default timing values

#### Scenario: Server attach rejects invalid gateway TUI timing values
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/attach` with a gateway TUI timing value less than or equal to zero
- **THEN** `houmao-server` rejects the request with validation semantics before starting a gateway process
