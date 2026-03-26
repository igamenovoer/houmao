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
- `relaunch`
- `stop`

Those commands SHALL target managed-agent identities rather than raw `terminal_id` or raw CAO session names as their normative addressing model.
Within that family, `show` SHALL present the detail-oriented managed-agent view, while `state` SHALL present the operational summary view.
The native `agents` family SHALL NOT advertise or require a generic `history` command as part of its supported managed-agent inspection contract.

#### Scenario: Operator inspects managed-agent state through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or the supported pair authority
- **AND THEN** the command returns the managed-agent state without requiring the operator to switch to raw CAO session or terminal identities

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

### Requirement: Repo-owned docs prefer `houmao-mgr` over `houmao-cli` for covered pair workflows
Repo-owned active documentation under `docs/` SHALL present `houmao-mgr` and `houmao-server` as the supported operator surfaces for current managed-agent and pair workflows.

References to `houmao-cli` MAY remain only in explicit migration, legacy, retirement, or historical contexts. Active documentation SHALL NOT retain `houmao-cli` as the default example for uncovered current workflows just because a native replacement has not been implemented yet.

Repo-owned documentation for managed-agent inspection SHALL NOT present `houmao-mgr agents history` as a supported native inspection surface.

#### Scenario: Active docs replace `houmao-cli` examples for supported workflows
- **WHEN** a repo-owned document under `docs/` describes a current managed-agent or pair workflow that is supported by `houmao-mgr` or `houmao-server`
- **THEN** that document uses `houmao-mgr` or `houmao-server` as the primary command example
- **AND THEN** it does not keep `houmao-cli` as the default example for that workflow

#### Scenario: Legacy `houmao-cli` references are explicitly marked as legacy
- **WHEN** a repo-owned document under `docs/` still mentions `houmao-cli`
- **THEN** that mention appears only in explicit migration, legacy, retirement, or historical guidance
- **AND THEN** it is not presented as an active default operator path

#### Scenario: Docs do not present retired managed-agent history as a supported native path
- **WHEN** repo-owned docs under `docs/` explain managed-agent inspection or long-running operation
- **THEN** they use supported surfaces such as `houmao-mgr agents state`, `houmao-mgr agents show`, gateway TUI state, or `houmao-mgr agents turn ...`
- **AND THEN** they do not present `houmao-mgr agents history` as a supported native inspection command

## ADDED Requirements

### Requirement: `houmao-mgr agents relaunch` exposes tmux-backed managed-session recovery
`houmao-mgr` SHALL expose `agents relaunch` as the native managed-session recovery command for tmux-backed managed agents.

`agents relaunch` SHALL support both explicit targeting by managed-agent identity and a current-session mode when the operator runs the command from inside the owning tmux session.

The command SHALL resolve the target session through manifest-first discovery, SHALL reuse the persisted session and built home, and SHALL NOT route through build-time `houmao-mgr agents launch`.

The command SHALL fail explicitly when the target is not tmux-backed, lacks valid manifest-owned relaunch authority, or cannot be resolved through supported selector or current-session discovery.

#### Scenario: Current-session relaunch uses tmux-local discovery
- **WHEN** an operator runs `houmao-mgr agents relaunch` from inside a tmux-backed managed session
- **THEN** `houmao-mgr` resolves that session through `AGENTSYS_MANIFEST_PATH` or `AGENTSYS_AGENT_ID`
- **AND THEN** it relaunches the managed agent surface without requiring an explicit selector

#### Scenario: Explicit relaunch uses managed-agent identity
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **THEN** `houmao-mgr` resolves that live agent through registry-first discovery or the supported pair authority
- **AND THEN** it relaunches the existing tmux-backed managed session instead of creating a new launch

#### Scenario: Non-tmux-backed target fails clearly
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved managed agent is not a tmux-backed relaunchable session
- **THEN** the command fails explicitly
- **AND THEN** it does not pretend that build-time launch or a raw CAO path is a supported replacement
