## ADDED Requirements

### Requirement: `houmao-mgr agents` manages verified agents by identity through scoped commands
`houmao-mgr agents` SHALL be the preferred pair-native family for managing agents by identity. Local lifecycle authority SHALL come from a supported Houmao launch. `state` SHALL present the operational summary for managed-agent inspection.

#### Scenario: The agents family exposes managed operations
- **WHEN** a caller works through the native agents family
- **THEN** it exposes `list`, `state`, `prompt`, `interrupt`, `relaunch`, and `stop` through the appropriate agent scopes
- **AND THEN** managed-agent identity is the addressing model rather than raw `terminal_id` or a raw CAO session name
- **AND THEN** the family provides no manual session adoption command
- **AND THEN** managed-agent inspection does not require or advertise `show` or `history`

#### Scenario: Operator inspects managed-agent state through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or the supported pair authority
- **AND THEN** the command returns the managed-agent state without requiring the operator to switch to raw CAO session or terminal identities

#### Scenario: Operator inspects an agent after managed launch
- **WHEN** an operator launches an agent named `coder` through a supported Houmao launch
- **THEN** `houmao-mgr agents single --agent-name coder state` resolves the managed agent without requiring a raw tmux session name or manual manifest-path discovery

#### Scenario: Operator submits a prompt through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "..." `
- **THEN** `houmao-mgr` submits that request through registry-first discovery or the pair-managed agent control authority
- **AND THEN** the command does not require the operator to know whether the agent is server-backed or locally-backed

#### Scenario: Operator relaunches a managed tmux-backed session through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or tmux-local current-session authority
- **AND THEN** the command relaunches the existing tmux-backed managed session rather than constructing a new launch

#### Scenario: Help output does not advertise retired inspection commands
- **WHEN** an operator runs `houmao-mgr agents --help`
- **THEN** the help output does not list `show` or `history`
- **AND THEN** supported inspection guidance points operators to `state`, `agents gateway tui ...`, or `agents turn ...` rather than removed managed-agent inspection commands

## REMOVED Requirements

### Requirement: `houmao-mgr agents` is the preferred pair-native managed-agent command family

**Reason:** The native agent command family no longer supports manual adoption.

**Migration:** Use a supported Houmao launch to start an agent. Use the appropriate `agents` scope for follow-up operations.
