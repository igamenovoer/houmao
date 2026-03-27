## ADDED Requirements

### Requirement: `houmao-mgr admin cleanup` exposes grouped local cleanup commands
`houmao-mgr` SHALL expose a native `admin cleanup` command group for local cleanup operations.

At minimum, the documented grouped cleanup tree SHALL include:

- `registry`
- `runtime sessions`
- `runtime builds`
- `runtime logs`
- `runtime mailbox-credentials`

This grouped cleanup tree SHALL be documented as local maintenance over local Houmao-owned state rather than as a pair-managed server API surface.

#### Scenario: Native help surface shows grouped cleanup commands
- **WHEN** an operator runs `houmao-mgr admin cleanup --help`
- **THEN** the help output lists `registry` and the `runtime` cleanup family
- **AND THEN** the grouped cleanup surface is presented as local maintenance rather than a server-backed admin API

### Requirement: `houmao-mgr agents cleanup` exposes local managed-session cleanup commands
`houmao-mgr` SHALL expose a native `agents cleanup` command family for local managed-session cleanup.

At minimum, that family SHALL include:

- `session`
- `logs`
- `mailbox`

These commands SHALL operate through local runtime-owned authority rather than a pair-managed server authority.

When the operator does not pass an explicit cleanup target and runs the command from inside the owning tmux session, the command family SHALL support current-session targeting through manifest-first discovery.

#### Scenario: Native help surface shows agent-scoped cleanup commands
- **WHEN** an operator runs `houmao-mgr agents cleanup --help`
- **THEN** the help output lists `session`, `logs`, and `mailbox`
- **AND THEN** the family is described as local managed-session cleanup rather than as a remote pair-managed request path

#### Scenario: Agent-scoped cleanup can default to current-session authority
- **WHEN** an operator runs `houmao-mgr agents cleanup logs` from inside the tmux session that hosts the managed agent
- **THEN** `houmao-mgr` resolves that cleanup target through supported current-session manifest authority
- **AND THEN** the operator does not need to spell the target session again just to clean its local artifacts
