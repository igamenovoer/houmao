## MODIFIED Requirements

### Requirement: `houmao-mgr agents` is the preferred pair-native managed-agent command family
`houmao-mgr agents ...` SHALL be the preferred pair-native command family for managed-agent operations.

At minimum, the `agents` family SHALL include commands for:

- `launch`
- `list`
- `show`
- `state`
- `prompt`
- `interrupt`
- `stop`

Those commands SHALL target managed-agent references rather than raw `terminal_id` or raw CAO session names as their normative addressing model.
Within that family, `show` SHALL present the detail-oriented managed-agent view, while `state` SHALL present the operational summary view.
The native `agents` family SHALL NOT advertise or require a generic `history` command as part of its supported managed-agent inspection contract.

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

#### Scenario: Help output does not advertise a retired history command
- **WHEN** an operator runs `houmao-mgr agents --help`
- **THEN** the help output does not list `history`
- **AND THEN** supported inspection guidance points operators to `state`, `show`, or `agents turn ...` rather than a generic managed-agent history command

### Requirement: Repo-owned docs prefer `houmao-mgr` over `houmao-cli` for covered pair workflows
Repo-owned documentation under `docs/` SHALL prefer `houmao-mgr` over `houmao-cli` whenever the new native pair command tree covers the documented workflow.

This change SHALL NOT erase valid `houmao-cli` documentation for workflows that remain uncovered by `houmao-mgr` or that are intentionally runtime-local rather than pair-managed.
Repo-owned documentation for managed-agent inspection SHALL NOT present `houmao-mgr agents history` as a supported native inspection surface.

#### Scenario: Docs replace `houmao-cli` examples for covered pair workflows
- **WHEN** a repo-owned document under `docs/` describes a pair-managed workflow now covered by `houmao-mgr`
- **THEN** that document uses `houmao-mgr` as the primary command example
- **AND THEN** it does not keep `houmao-cli` as the default example for that covered workflow

#### Scenario: Docs retain `houmao-cli` only for uncovered workflows
- **WHEN** a repo-owned document under `docs/` describes a workflow that `houmao-mgr` still does not cover
- **THEN** that document may continue using `houmao-cli`
- **AND THEN** the retained `houmao-cli` usage is limited to those uncovered or intentionally runtime-local workflows

#### Scenario: Docs do not present retired managed-agent history as a supported native path
- **WHEN** repo-owned docs under `docs/` explain managed-agent inspection or long-running local/serverless operation
- **THEN** they use supported surfaces such as `houmao-mgr agents state`, `houmao-mgr agents show`, gateway TUI state, or `houmao-mgr agents turn ...`
- **AND THEN** they do not present `houmao-mgr agents history` as a supported native inspection command
