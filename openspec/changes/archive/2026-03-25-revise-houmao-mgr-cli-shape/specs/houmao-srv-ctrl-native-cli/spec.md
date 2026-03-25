## MODIFIED Requirements

### Requirement: `houmao-mgr` exposes a native pair-operations command tree
`houmao-mgr` SHALL expose a Houmao-owned top-level native command tree.

At minimum, that native tree SHALL include:

- `server`
- `agents`
- `brains`
- `admin`

Those command families SHALL be documented as Houmao-owned pair commands.

The root group SHALL use `invoke_without_command=True` so that running `houmao-mgr` without arguments prints help text instead of raising a Python exception.

Top-level `launch` and the explicit `cao` namespace SHALL NOT remain part of the supported command tree.

#### Scenario: Native help surface shows the new top-level command families
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `server`, `agents`, `brains`, and `admin`
- **AND THEN** the help output does NOT include `cao` or top-level `launch`

#### Scenario: Bare invocation prints help instead of raising an exception
- **WHEN** an operator runs `houmao-mgr` without any arguments
- **THEN** the CLI prints help text showing available command groups
- **AND THEN** the CLI does NOT raise a Python exception or print a stack trace

### Requirement: `houmao-mgr agents` is the preferred pair-native managed-agent command family
`houmao-mgr agents ...` SHALL be the preferred pair-native command family for managed-agent operations.

At minimum, the `agents` family SHALL include commands for:

- `launch`
- `list`
- `show`
- `state`
- `history`
- `prompt`
- `interrupt`
- `stop`

Those commands SHALL target managed-agent references rather than raw `terminal_id` or raw CAO session names as their normative addressing model.
Within that family, `show` SHALL present the detail-oriented managed-agent view, while `state` SHALL present the operational summary view.

#### Scenario: Operator inspects managed-agent state through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents state <agent-ref>`
- **THEN** `houmao-mgr` resolves that managed-agent reference through registry-first discovery or the supported pair authority
- **AND THEN** the command returns the managed-agent state without requiring the operator to switch to raw CAO session or terminal identities

#### Scenario: Operator inspects managed-agent detail through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents show <agent-ref>`
- **THEN** `houmao-mgr` returns the detail-oriented managed-agent view
- **AND THEN** the command does not collapse to an identity-only payload when a managed-agent detail view exists

#### Scenario: Operator submits a prompt through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents prompt <agent-ref> --prompt "..." `
- **THEN** `houmao-mgr` submits that request through registry-first discovery or the pair-managed agent control authority
- **AND THEN** the command does not require the operator to know whether the agent is server-backed or locally-backed

### Requirement: Native `houmao-mgr` expansion retires `cao` namespace and top-level `launch`
Expanding `houmao-mgr` SHALL retire the `cao` command group and the top-level `launch` command entirely.

- `houmao-mgr cao *` commands SHALL be removed from the supported command tree.
- Top-level `houmao-mgr launch` SHALL be removed. Agent launch moves to `houmao-mgr agents launch`.
- The `server` group replaces server-lifecycle commands previously under `cao` (info, shutdown).
- The `agents launch` command replaces `cao launch` and top-level `launch`.

Repo-owned docs, tests, examples, and scripts SHALL use `houmao-mgr agents launch` and `houmao-mgr server *` rather than `cao launch` or top-level `launch`.

#### Scenario: `cao` namespace is no longer available
- **WHEN** an operator runs `houmao-mgr cao launch --agents ...`
- **THEN** the command fails because `cao` is not a recognized command group
- **AND THEN** help text does not list `cao` as an option

#### Scenario: Top-level launch is no longer available
- **WHEN** an operator runs `houmao-mgr launch --agents ...`
- **THEN** the command fails because `launch` is not a recognized top-level command
- **AND THEN** the operator is directed to use `houmao-mgr agents launch` instead

#### Scenario: Repo-owned scripts use the new command paths
- **WHEN** repo-owned scripts, tests, or docs reference agent launch
- **THEN** they use `houmao-mgr agents launch` rather than `houmao-mgr cao launch` or `houmao-mgr launch`
