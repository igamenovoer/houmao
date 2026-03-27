## MODIFIED Requirements

### Requirement: `houmao-mgr` exposes a native pair-operations command tree
`houmao-mgr` SHALL expose a Houmao-owned top-level native command tree.

At minimum, that native tree SHALL include:

- `server`
- `agents`
- `brains`
- `admin`
- `mailbox`

Those command families SHALL be documented as Houmao-owned pair commands or Houmao-owned local operator commands, as appropriate.

The root group SHALL use `invoke_without_command=True` so that running `houmao-mgr` without arguments prints help text instead of raising a Python exception.

Top-level `launch` and the explicit `cao` namespace SHALL NOT remain part of the supported command tree.

#### Scenario: Native help surface shows the new top-level command families
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `server`, `agents`, `brains`, `admin`, and `mailbox`
- **AND THEN** the help output does NOT include `cao` or top-level `launch`

#### Scenario: Bare invocation prints help instead of raising an exception
- **WHEN** an operator runs `houmao-mgr` without any arguments
- **THEN** the CLI prints help text showing available command groups
- **AND THEN** the CLI does NOT raise a Python exception or print a stack trace

## ADDED Requirements

### Requirement: `houmao-mgr agents mailbox` exposes local late mailbox registration commands
`houmao-mgr` SHALL expose a native `agents mailbox ...` command family for late mailbox registration on existing local managed-agent sessions.

At minimum, that family SHALL include:

- `status`
- `register`
- `unregister`

Those commands SHALL target local managed-agent authority rather than pair-owned server mail authority.

#### Scenario: Operator uses a native late mailbox registration path under `agents`
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **THEN** `houmao-mgr` resolves `alice` through the local managed-agent discovery path
- **AND THEN** the command uses the local late mailbox registration workflow instead of requiring `houmao-server`
