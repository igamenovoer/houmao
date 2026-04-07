## ADDED Requirements

### Requirement: `project easy instance launch` defaults gateway attach with explicit per-launch overrides
`houmao-mgr project easy instance launch` SHALL request launch-time gateway attach by default unless the operator explicitly passes `--no-gateway`.

For that default attached path, the easy launch surface SHALL use an opinionated gateway listener request of loopback host plus system-assigned port rather than requiring persisted specialist gateway config.

When an operator passes `--gateway-port <port>`, the easy launch surface SHALL request launch-time gateway attach for that explicit port on the current launch instead of using a system-assigned port.

`--no-gateway` and `--gateway-port` SHALL be mutually exclusive on this surface.

If launch-time gateway attach fails after the managed session has already started, `project easy instance launch` SHALL keep the session running and SHALL report the attach failure explicitly together with the launched session identity needed for retry.

#### Scenario: Default easy launch attaches a loopback gateway with a system-assigned port
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **AND WHEN** the addressed specialist launch resolves to a gateway-capable supported backend
- **THEN** the command requests launch-time gateway attach by default
- **AND THEN** it requests loopback binding with a system-assigned port for that launch
- **AND THEN** the launch result reports the resolved gateway host and bound gateway port

#### Scenario: Operator skips launch-time gateway attach explicitly
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --no-gateway`
- **THEN** the command does not request launch-time gateway attach for that launch
- **AND THEN** the launch result does not claim that a live gateway endpoint was attached automatically

#### Scenario: Operator requests a fixed gateway port for one easy launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --gateway-port 43123`
- **THEN** the command requests launch-time gateway attach for that launch
- **AND THEN** it requests gateway listener port `43123` instead of a system-assigned port
- **AND THEN** a successful launch reports the resolved gateway endpoint for that session

#### Scenario: Conflicting gateway launch flags fail clearly
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --no-gateway --gateway-port 43123`
- **THEN** the command fails explicitly before launch
- **AND THEN** the error states that `--no-gateway` and `--gateway-port` cannot be combined

#### Scenario: Gateway auto-attach failure preserves the launched session
- **WHEN** `houmao-mgr project easy instance launch` starts the managed session successfully
- **AND WHEN** launch-time gateway attach fails afterward for that launch
- **THEN** the managed session remains running
- **AND THEN** the command reports the gateway attach failure explicitly
- **AND THEN** the failure surface includes the launched session identity or manifest path needed for later retry or stop
