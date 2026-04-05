## MODIFIED Requirements

### Requirement: `houmao-mgr` exposes a native pair-operations command tree
`houmao-mgr` SHALL expose a Houmao-owned top-level native command tree.

At minimum, that native tree SHALL include:

- `server`
- `agents`
- `brains`
- `admin`
- `mailbox`
- `project`
- `system-skills`

Those command families SHALL be documented as Houmao-owned pair commands or Houmao-owned local operator commands, as appropriate.

The root group SHALL use `invoke_without_command=True` so that running `houmao-mgr` without arguments prints help text instead of raising a Python exception.

The root group SHALL accept `--print-plain`, `--print-json`, and `--print-fancy` as mutually exclusive flag-value options that control the output formatting style for all subcommands. The resolved print style SHALL be stored in `click.Context.obj["output"]` as an `OutputContext` instance accessible to all subcommands.

Top-level `launch` and the explicit `cao` namespace SHALL NOT remain part of the supported command tree.

#### Scenario: Native help surface shows the new top-level command families
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `server`, `agents`, `brains`, `admin`, `mailbox`, `project`, and `system-skills`
- **AND THEN** the help output does NOT include `cao` or top-level `launch`

#### Scenario: Bare invocation prints help instead of raising an exception
- **WHEN** an operator runs `houmao-mgr` without any arguments
- **THEN** the CLI prints help text showing available command groups
- **AND THEN** the CLI does NOT raise a Python exception or print a stack trace

#### Scenario: Root group help shows print style flags
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output lists `--print-plain`, `--print-json`, and `--print-fancy` as available options
