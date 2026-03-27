## ADDED Requirements

### Requirement: `houmao-mgr agents gateway tui` exposes raw gateway-owned TUI tracking commands
`houmao-mgr` SHALL expose a native `agents gateway tui ...` command family for raw gateway-owned TUI tracking on managed agents.

At minimum, that family SHALL include:

- `state`
- `history`
- `watch`
- `note-prompt`

`agents gateway tui state` SHALL read the managed agent's live gateway-owned TUI state path rather than the transport-neutral managed-agent detail view.

`agents gateway tui history` SHALL read the managed agent's live gateway-owned bounded snapshot-history path rather than the coarse managed-agent `/history` surface.

`agents gateway tui note-prompt` SHALL target the managed agent's live gateway prompt-note tracking path rather than the queued gateway request path.

`agents gateway tui watch` SHALL act as an operator-facing repeated inspection surface over the same live gateway-owned TUI state path used by `agents gateway tui state`.

#### Scenario: Operator reads raw gateway-owned TUI state through the native `agents gateway tui` tree
- **WHEN** an operator runs `houmao-mgr agents gateway tui state --agent-id abc123`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-mgr` returns the raw gateway-owned TUI state for that managed agent
- **AND THEN** the command does not collapse that response to the transport-neutral `agents show` payload

#### Scenario: Operator reads bounded snapshot history through the native `agents gateway tui` tree
- **WHEN** an operator runs `houmao-mgr agents gateway tui history --agent-id abc123`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-mgr` returns the gateway-owned bounded recent TUI snapshot history for that managed agent
- **AND THEN** the command does not reinterpret that history as coarse managed-agent `/history`

#### Scenario: Operator records explicit prompt provenance without queue submission
- **WHEN** an operator runs `houmao-mgr agents gateway tui note-prompt --agent-id abc123 --prompt "..."`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-mgr` records prompt-note evidence through the live gateway TUI tracking path
- **AND THEN** the command does not submit a queued gateway prompt request

### Requirement: `houmao-mgr agents gateway tui` supports the same managed-agent targeting contract as the rest of `agents gateway`
Gateway-targeting `houmao-mgr agents gateway tui ...` commands that operate on one managed agent SHALL support both explicit managed-agent selectors and same-session current-session targeting.

At minimum, this SHALL apply to:

- `state`
- `history`
- `watch`
- `note-prompt`

When an operator omits explicit selectors and runs one of those commands inside the owning tmux session, `houmao-mgr` SHALL resolve the target through the same manifest-first current-session discovery contract used by the rest of `agents gateway`.

When an operator runs one of those commands outside tmux without explicit selectors, the command SHALL fail explicitly rather than guessing from cwd, gateway listener bindings, or ambient shell state.

#### Scenario: Same-session gateway TUI state resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway tui state` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed session through that tmux-local discovery contract
- **AND THEN** it reads the live gateway-owned TUI state without requiring `--agent-id` or `--agent-name`

#### Scenario: Outside-tmux gateway TUI watch fails without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway tui watch` outside tmux
- **AND WHEN** the command is not given `--agent-id`, `--agent-name`, or `--current-session`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd or ambient shell state
