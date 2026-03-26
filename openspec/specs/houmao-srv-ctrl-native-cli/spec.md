## Purpose
Define the Houmao-owned native `houmao-mgr` command tree for covered pair workflows, including server-backed managed-agent operations and local utility commands.

## Requirements

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

### Requirement: `houmao-mgr agents gateway` exposes gateway lifecycle and gateway-mediated request commands
`houmao-mgr` SHALL expose a native `agents gateway ...` command family for managed-agent gateway operations.

At minimum, that family SHALL include:

- `attach`
- `detach`
- `status`
- `prompt`
- `interrupt`

`agents gateway prompt` and `agents gateway interrupt` SHALL target the managed agent's live gateway-mediated request path rather than the transport-neutral managed-agent request path.
The documented default prompt path for ordinary pair-native prompt submission SHALL remain `houmao-mgr agents prompt ...`. `agents gateway prompt` SHALL be documented as the explicit gateway-mediated path for operators who want live gateway admission and queue semantics.

#### Scenario: Operator attaches a gateway through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway attach <agent-ref>`
- **THEN** `houmao-mgr` resolves that managed agent through the supported pair authority
- **AND THEN** the command attaches or reuses the live gateway for that managed agent

#### Scenario: Operator submits a gateway-mediated prompt through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway prompt <agent-ref> --prompt "..." `
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway-mediated request path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Ordinary prompt guidance points operators to the transport-neutral path by default
- **WHEN** repo-owned help text or docs explain how to submit an ordinary prompt through the native pair CLI
- **THEN** they present `houmao-mgr agents prompt ...` as the default documented path
- **AND THEN** they present `houmao-mgr agents gateway prompt ...` as the explicit gateway-managed alternative rather than the default

### Requirement: `houmao-mgr agents mail` exposes pair-native mailbox follow-up commands
`houmao-mgr` SHALL expose a native `agents mail ...` command family for pair-managed mailbox follow-up on managed agents.

At minimum, that family SHALL include:

- `status`
- `check`
- `send`
- `reply`

Those commands SHALL address managed agents by managed-agent reference and SHALL use pair-owned mail authority rather than requiring direct gateway endpoint discovery from the caller.

#### Scenario: Operator inspects mail status through the native `agents mail` tree
- **WHEN** an operator runs `houmao-mgr agents mail status <agent-ref>`
- **THEN** `houmao-mgr` resolves that managed agent through the supported pair authority
- **AND THEN** the command returns pair-owned mailbox status without requiring the operator to reach the gateway port directly

#### Scenario: Operator checks mail through the native `agents mail` tree
- **WHEN** an operator runs `houmao-mgr agents mail check <agent-ref>`
- **THEN** `houmao-mgr` resolves that managed agent through the supported pair authority
- **AND THEN** the command returns pair-owned mailbox follow-up results without requiring the operator to reach the gateway port directly

#### Scenario: Mail command fails clearly when pair-owned mail follow-up is unavailable
- **WHEN** an operator runs `houmao-mgr agents mail send <agent-ref> ...`
- **AND WHEN** the addressed managed agent does not expose pair-owned mail follow-up capability
- **THEN** the command fails with explicit availability guidance
- **AND THEN** it does not silently claim that the mailbox action succeeded

### Requirement: `houmao-mgr agents turn` exposes managed headless turn commands
`houmao-mgr` SHALL expose a native `agents turn ...` command family for managed headless turn submission and inspection.

At minimum, that family SHALL include:

- `submit`
- `status`
- `events`
- `stdout`
- `stderr`

Those commands SHALL use the managed headless turn routes exposed by the supported pair authority.

#### Scenario: Operator submits a managed headless turn through the native `agents turn` tree
- **WHEN** an operator runs `houmao-mgr agents turn submit <agent-ref> --prompt "..." `
- **THEN** `houmao-mgr` submits that prompt through the managed headless turn authority
- **AND THEN** the command returns the accepted turn identity needed for later inspection

#### Scenario: TUI-backed agent rejects native headless turn submission
- **WHEN** an operator runs `houmao-mgr agents turn submit <agent-ref> --prompt "..." `
- **AND WHEN** the addressed managed agent is TUI-backed
- **THEN** the command fails explicitly
- **AND THEN** it does not pretend that the TUI-backed agent supports the headless turn contract

### Requirement: `houmao-mgr brains build` exposes local brain construction
`houmao-mgr` SHALL expose a native `brains build` command for local brain construction.

`brains build` SHALL remain a local artifact-building command rather than a `houmao-server` API operation.

At minimum, that command SHALL support the local build inputs and outputs needed to construct a brain home and return its manifest and launch-helper pointers.

#### Scenario: Operator builds a brain without requiring `houmao-server`
- **WHEN** an operator runs `houmao-mgr brains build ...`
- **THEN** `houmao-mgr` materializes the requested local brain artifacts on the local host
- **AND THEN** the command does not require a running `houmao-server` instance just to build those artifacts

### Requirement: `houmao-mgr admin cleanup-registry` exposes local shared-registry cleanup
`houmao-mgr` SHALL expose a native `admin cleanup-registry` command for stale shared-registry cleanup.

That command SHALL remain a local maintenance operation over local runtime-owned registry state.

#### Scenario: Operator runs local shared-registry cleanup through the native admin tree
- **WHEN** an operator runs `houmao-mgr admin cleanup-registry`
- **THEN** `houmao-mgr` performs stale shared-registry cleanup on the local host
- **AND THEN** the command does not require a new `houmao-server` admin endpoint to complete that maintenance

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

### Requirement: Repo-owned docs prefer `houmao-mgr` over `houmao-cli` for covered pair workflows
Repo-owned documentation under `docs/` SHALL prefer `houmao-mgr` over `houmao-cli` whenever the new native pair command tree covers the documented workflow.

This change SHALL NOT erase valid `houmao-cli` documentation for workflows that remain uncovered by `houmao-mgr` or that are intentionally runtime-local rather than pair-managed.
Repo-owned documentation for managed-agent history SHALL explain where history is retained so operators can understand what accumulates during long-running tasks.

#### Scenario: Docs replace `houmao-cli` examples for covered pair workflows
- **WHEN** a repo-owned document under `docs/` describes a pair-managed workflow now covered by `houmao-mgr`
- **THEN** that document uses `houmao-mgr` as the primary command example
- **AND THEN** it does not keep `houmao-cli` as the default example for that covered workflow

#### Scenario: Docs retain `houmao-cli` only for uncovered workflows
- **WHEN** a repo-owned document under `docs/` describes a workflow that `houmao-mgr` still does not cover
- **THEN** that document may continue using `houmao-cli`
- **AND THEN** the retained `houmao-cli` usage is limited to those uncovered or intentionally runtime-local workflows

#### Scenario: Docs explain managed-agent history retention and storage
- **WHEN** repo-owned docs under `docs/` explain `houmao-mgr agents history` or long-running managed-agent operation
- **THEN** they state whether the relevant history is retained in memory or persisted on disk
- **AND THEN** they distinguish the bounded in-memory recent-transition history of TUI-managed agents from the persisted turn-record history of managed headless agents
- **AND THEN** they give operators enough guidance to understand what can accumulate over time on a long-running server

### Requirement: Managed-agent-targeting native CLI commands use explicit identity selectors

`houmao-mgr agents` commands that target one managed agent SHALL accept explicit identity selectors instead of relying on one positional managed-agent reference.

At minimum, managed-agent-targeting commands in the `agents`, `agents gateway`, `agents mail`, and `agents turn` families SHALL accept:

- `--agent-id <id>`
- `--agent-name <name>`

For these commands, callers SHALL provide exactly one of those selectors unless the command defines a separate current-session targeting contract.

`--agent-id` SHALL target the authoritative globally unique managed-agent identity.

`--agent-name` SHALL target the friendly managed-agent name and SHALL only succeed when the relevant authority can prove that exactly one live managed agent currently uses that name.

#### Scenario: Exact selector by agent id is accepted

- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` targets the managed agent whose authoritative identity is `abc123`
- **AND THEN** the operator does not need to rely on friendly-name uniqueness for that control action

#### Scenario: Friendly-name selector succeeds only when unique

- **WHEN** an operator runs `houmao-mgr agents show --agent-name gpu`
- **AND WHEN** exactly one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` targets that managed agent
- **AND THEN** the command succeeds without requiring the operator to spell the authoritative `agent_id`

#### Scenario: Friendly-name selector fails on ambiguity

- **WHEN** an operator runs `houmao-mgr agents prompt --agent-name gpu --prompt "..."`
- **AND WHEN** more than one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error directs the operator to retry with `--agent-id`

#### Scenario: Missing selector fails when no current-session contract applies

- **WHEN** an operator runs `houmao-mgr agents stop` without `--agent-id` or `--agent-name`
- **AND WHEN** that command has no separate current-session targeting contract
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that exactly one of `--agent-id` or `--agent-name` is required
