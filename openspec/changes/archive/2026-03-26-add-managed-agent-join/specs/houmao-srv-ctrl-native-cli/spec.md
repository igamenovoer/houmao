## MODIFIED Requirements

### Requirement: `houmao-mgr agents` is the preferred pair-native managed-agent command family
`houmao-mgr agents ...` SHALL be the preferred pair-native command family for managed-agent operations.

At minimum, the `agents` family SHALL include commands for:

- `launch`
- `join`
- `list`
- `show`
- `state`
- `prompt`
- `interrupt`
- `relaunch`
- `stop`

Those commands SHALL target managed-agent identities rather than raw `terminal_id` or raw CAO session names as their normative addressing model.
Within that family, `join` SHALL adopt an existing tmux-backed agent session into managed-agent control without requiring `houmao-server` or raw tmux attach scripts.
Within that family, `show` SHALL present the detail-oriented managed-agent view, while `state` SHALL present the operational summary view.
The native `agents` family SHALL NOT advertise or require a generic `history` command as part of its supported managed-agent inspection contract.

#### Scenario: Operator inspects managed-agent state through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or the supported pair authority
- **AND THEN** the command returns the managed-agent state without requiring the operator to switch to raw CAO session or terminal identities

#### Scenario: Operator joins an existing tmux-backed session through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents join --agent-name coder` from a compatible tmux session
- **THEN** `houmao-mgr` adopts the existing tmux-backed session into managed-agent control through the native pair CLI
- **AND THEN** later `houmao-mgr agents state --agent-name coder` can resolve that managed agent without requiring raw tmux session names or manual manifest-path discovery

#### Scenario: Operator inspects managed-agent detail through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents show --agent-id abc123`
- **THEN** `houmao-mgr` returns the detail-oriented managed-agent view
- **AND THEN** the command does not collapse to an identity-only payload when a managed-agent detail view exists

#### Scenario: Operator submits a prompt through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "..." `
- **THEN** `houmao-mgr` submits that request through registry-first discovery or the pair-managed agent control authority
- **AND THEN** the command does not require the operator to know whether the agent is server-backed or locally-backed

#### Scenario: Operator relaunches a managed tmux-backed session through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or tmux-local current-session authority
- **AND THEN** the command relaunches the existing tmux-backed managed session rather than constructing a new launch

#### Scenario: Help output does not advertise a retired history command
- **WHEN** an operator runs `houmao-mgr agents --help`
- **THEN** the help output does not list `history`
- **AND THEN** supported inspection guidance points operators to `state`, `show`, or `agents turn ...` rather than a generic managed-agent history command
