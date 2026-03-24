## Purpose
Define the Houmao-owned native `houmao-srv-ctrl` command tree for covered pair workflows, including server-backed managed-agent operations and local utility commands.

## Requirements

### Requirement: `houmao-srv-ctrl` exposes a native pair-operations command tree
`houmao-srv-ctrl` SHALL expose a Houmao-owned top-level native command tree in addition to top-level `launch`, `install`, and the explicit `cao` compatibility namespace.

At minimum, that native tree SHALL include:

- `agents`
- `brains`
- `admin`

Those command families SHALL be documented as Houmao-owned pair commands rather than as CAO-compatible vocabulary.

#### Scenario: Native help surface shows the new top-level command families
- **WHEN** an operator runs `houmao-srv-ctrl --help`
- **THEN** the help output includes `agents`, `brains`, and `admin`
- **AND THEN** those commands appear alongside the existing native pair shortcuts and the explicit `cao` namespace

### Requirement: `houmao-srv-ctrl agents` is the preferred pair-native managed-agent command family
`houmao-srv-ctrl agents ...` SHALL be the preferred pair-native command family for managed-agent operations.

At minimum, the `agents` family SHALL include commands for:

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
- **WHEN** an operator runs `houmao-srv-ctrl agents state <agent-ref>`
- **THEN** `houmao-srv-ctrl` resolves that managed-agent reference through the supported pair authority
- **AND THEN** the command returns the managed-agent state without requiring the operator to switch to raw CAO session or terminal identities

#### Scenario: Operator inspects managed-agent detail through the native `agents` tree
- **WHEN** an operator runs `houmao-srv-ctrl agents show <agent-ref>`
- **THEN** `houmao-srv-ctrl` returns the detail-oriented managed-agent view through the supported pair authority
- **AND THEN** the command does not collapse to an identity-only payload when a managed-agent detail view exists

#### Scenario: Operator submits a prompt through the native `agents` tree
- **WHEN** an operator runs `houmao-srv-ctrl agents prompt <agent-ref> --prompt "..." `
- **THEN** `houmao-srv-ctrl` submits that request through the pair-managed agent control authority
- **AND THEN** the command does not require the operator to use `houmao-cli send-prompt` for the preferred pair-native workflow

### Requirement: `houmao-srv-ctrl agents gateway` exposes gateway lifecycle and gateway-mediated request commands
`houmao-srv-ctrl` SHALL expose a native `agents gateway ...` command family for managed-agent gateway operations.

At minimum, that family SHALL include:

- `attach`
- `detach`
- `status`
- `prompt`
- `interrupt`

`agents gateway prompt` and `agents gateway interrupt` SHALL target the managed agent's live gateway-mediated request path rather than the transport-neutral managed-agent request path.
The documented default prompt path for ordinary pair-native prompt submission SHALL remain `houmao-srv-ctrl agents prompt ...`. `agents gateway prompt` SHALL be documented as the explicit gateway-mediated path for operators who want live gateway admission and queue semantics.

#### Scenario: Operator attaches a gateway through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-srv-ctrl agents gateway attach <agent-ref>`
- **THEN** `houmao-srv-ctrl` resolves that managed agent through the supported pair authority
- **AND THEN** the command attaches or reuses the live gateway for that managed agent

#### Scenario: Operator submits a gateway-mediated prompt through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-srv-ctrl agents gateway prompt <agent-ref> --prompt "..." `
- **THEN** `houmao-srv-ctrl` delivers that request through the managed agent's live gateway-mediated request path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Ordinary prompt guidance points operators to the transport-neutral path by default
- **WHEN** repo-owned help text or docs explain how to submit an ordinary prompt through the native pair CLI
- **THEN** they present `houmao-srv-ctrl agents prompt ...` as the default documented path
- **AND THEN** they present `houmao-srv-ctrl agents gateway prompt ...` as the explicit gateway-managed alternative rather than the default

### Requirement: `houmao-srv-ctrl agents mail` exposes pair-native mailbox follow-up commands
`houmao-srv-ctrl` SHALL expose a native `agents mail ...` command family for pair-managed mailbox follow-up on managed agents.

At minimum, that family SHALL include:

- `status`
- `check`
- `send`
- `reply`

Those commands SHALL address managed agents by managed-agent reference and SHALL use pair-owned mail authority rather than requiring direct gateway endpoint discovery from the caller.

#### Scenario: Operator inspects mail status through the native `agents mail` tree
- **WHEN** an operator runs `houmao-srv-ctrl agents mail status <agent-ref>`
- **THEN** `houmao-srv-ctrl` resolves that managed agent through the supported pair authority
- **AND THEN** the command returns pair-owned mailbox status without requiring the operator to reach the gateway port directly

#### Scenario: Operator checks mail through the native `agents mail` tree
- **WHEN** an operator runs `houmao-srv-ctrl agents mail check <agent-ref>`
- **THEN** `houmao-srv-ctrl` resolves that managed agent through the supported pair authority
- **AND THEN** the command returns pair-owned mailbox follow-up results without requiring the operator to reach the gateway port directly

#### Scenario: Mail command fails clearly when pair-owned mail follow-up is unavailable
- **WHEN** an operator runs `houmao-srv-ctrl agents mail send <agent-ref> ...`
- **AND WHEN** the addressed managed agent does not expose pair-owned mail follow-up capability
- **THEN** the command fails with explicit availability guidance
- **AND THEN** it does not silently claim that the mailbox action succeeded

### Requirement: `houmao-srv-ctrl agents turn` exposes managed headless turn commands
`houmao-srv-ctrl` SHALL expose a native `agents turn ...` command family for managed headless turn submission and inspection.

At minimum, that family SHALL include:

- `submit`
- `status`
- `events`
- `stdout`
- `stderr`

Those commands SHALL use the managed headless turn routes exposed by the supported pair authority.

#### Scenario: Operator submits a managed headless turn through the native `agents turn` tree
- **WHEN** an operator runs `houmao-srv-ctrl agents turn submit <agent-ref> --prompt "..." `
- **THEN** `houmao-srv-ctrl` submits that prompt through the managed headless turn authority
- **AND THEN** the command returns the accepted turn identity needed for later inspection

#### Scenario: TUI-backed agent rejects native headless turn submission
- **WHEN** an operator runs `houmao-srv-ctrl agents turn submit <agent-ref> --prompt "..." `
- **AND WHEN** the addressed managed agent is TUI-backed
- **THEN** the command fails explicitly
- **AND THEN** it does not pretend that the TUI-backed agent supports the headless turn contract

### Requirement: `houmao-srv-ctrl brains build` exposes local brain construction
`houmao-srv-ctrl` SHALL expose a native `brains build` command for local brain construction.

`brains build` SHALL remain a local artifact-building command rather than a `houmao-server` API operation.

At minimum, that command SHALL support the local build inputs and outputs needed to construct a brain home and return its manifest and launch-helper pointers.

#### Scenario: Operator builds a brain without requiring `houmao-server`
- **WHEN** an operator runs `houmao-srv-ctrl brains build ...`
- **THEN** `houmao-srv-ctrl` materializes the requested local brain artifacts on the local host
- **AND THEN** the command does not require a running `houmao-server` instance just to build those artifacts

### Requirement: `houmao-srv-ctrl admin cleanup-registry` exposes local shared-registry cleanup
`houmao-srv-ctrl` SHALL expose a native `admin cleanup-registry` command for stale shared-registry cleanup.

That command SHALL remain a local maintenance operation over local runtime-owned registry state.

#### Scenario: Operator runs local shared-registry cleanup through the native admin tree
- **WHEN** an operator runs `houmao-srv-ctrl admin cleanup-registry`
- **THEN** `houmao-srv-ctrl` performs stale shared-registry cleanup on the local host
- **AND THEN** the command does not require a new `houmao-server` admin endpoint to complete that maintenance

### Requirement: Native `houmao-srv-ctrl` expansion retires legacy `agent-gateway` while keeping the supported pair CLI surface coherent
Expanding `houmao-srv-ctrl` SHALL keep the supported pair CLI surface coherent by moving pair-owned gateway operations to the native `agents gateway ...` tree and retiring the legacy top-level `agent-gateway` command family.

This change SHALL NOT remove or repurpose existing `houmao-cli` runtime commands.

Existing top-level `houmao-srv-ctrl` commands such as `launch`, `install`, and `cao ...` SHALL remain supported.

The public `houmao-srv-ctrl` command tree SHALL NOT continue exposing `agent-gateway` as a supported top-level command family after this change.

Repo-owned docs, tests, examples, and scripts SHALL use `houmao-srv-ctrl agents gateway attach` rather than `houmao-srv-ctrl agent-gateway attach`.

#### Scenario: Existing `houmao-cli` runtime workflow remains available during native `srv-ctrl` expansion
- **WHEN** an operator continues using `houmao-cli` after this change
- **THEN** the existing `houmao-cli` command surface remains available
- **AND THEN** the new native `houmao-srv-ctrl` tree expands pair-native workflows without requiring immediate retirement of `houmao-cli`

#### Scenario: Native help output no longer advertises `agent-gateway`
- **WHEN** an operator runs `houmao-srv-ctrl --help` after this change
- **THEN** the public help output does not include `agent-gateway` as a supported top-level command family
- **AND THEN** gateway attach guidance points operators to `houmao-srv-ctrl agents gateway attach`

#### Scenario: Repo-owned command usage migrates to `agents gateway attach`
- **WHEN** repo-owned docs, tests, examples, or scripts need to invoke the pair-managed gateway attach flow
- **THEN** they use `houmao-srv-ctrl agents gateway attach`
- **AND THEN** they do not continue using `houmao-srv-ctrl agent-gateway attach`

### Requirement: Repo-owned docs prefer `houmao-srv-ctrl` over `houmao-cli` for covered pair workflows
Repo-owned documentation under `docs/` SHALL prefer `houmao-srv-ctrl` over `houmao-cli` whenever the new native pair command tree covers the documented workflow.

This change SHALL NOT erase valid `houmao-cli` documentation for workflows that remain uncovered by `houmao-srv-ctrl` or that are intentionally runtime-local rather than pair-managed.
Repo-owned documentation for managed-agent history SHALL explain where history is retained so operators can understand what accumulates during long-running tasks.

#### Scenario: Docs replace `houmao-cli` examples for covered pair workflows
- **WHEN** a repo-owned document under `docs/` describes a pair-managed workflow now covered by `houmao-srv-ctrl`
- **THEN** that document uses `houmao-srv-ctrl` as the primary command example
- **AND THEN** it does not keep `houmao-cli` as the default example for that covered workflow

#### Scenario: Docs retain `houmao-cli` only for uncovered workflows
- **WHEN** a repo-owned document under `docs/` describes a workflow that `houmao-srv-ctrl` still does not cover
- **THEN** that document may continue using `houmao-cli`
- **AND THEN** the retained `houmao-cli` usage is limited to those uncovered or intentionally runtime-local workflows

#### Scenario: Docs explain managed-agent history retention and storage
- **WHEN** repo-owned docs under `docs/` explain `houmao-srv-ctrl agents history` or long-running managed-agent operation
- **THEN** they state whether the relevant history is retained in memory or persisted on disk
- **AND THEN** they distinguish the bounded in-memory recent-transition history of TUI-managed agents from the persisted turn-record history of managed headless agents
- **AND THEN** they give operators enough guidance to understand what can accumulate over time on a long-running server
