## MODIFIED Requirements

### Requirement: `houmao-mgr agents` is the preferred pair-native managed-agent command family
`houmao-mgr agents ...` SHALL be the preferred pair-native command family for managed-agent operations.

At minimum, the `agents` family SHALL include commands for:

- `launch`
- `join`
- `list`
- `state`
- `prompt`
- `interrupt`
- `relaunch`
- `stop`

Those commands SHALL target managed-agent identities rather than raw `terminal_id` or raw CAO session names as their normative addressing model.
Within that family, `join` SHALL adopt an existing tmux-backed agent session into managed-agent control without requiring `houmao-server` or raw tmux attach scripts.
Within that family, `state` SHALL present the operational summary view for supported managed-agent inspection.
The native `agents` family SHALL NOT advertise or require a detail-oriented `show` command or a generic `history` command as part of its supported managed-agent inspection contract.

#### Scenario: Operator inspects managed-agent state through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or the supported pair authority
- **AND THEN** the command returns the managed-agent state without requiring the operator to switch to raw CAO session or terminal identities

#### Scenario: Operator joins an existing tmux-backed session through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents join --agent-name coder` from a compatible tmux session
- **THEN** `houmao-mgr` adopts the existing tmux-backed session into managed-agent control through the native pair CLI
- **AND THEN** later `houmao-mgr agents state --agent-name coder` can resolve that managed agent without requiring raw tmux session names or manual manifest-path discovery

#### Scenario: Operator submits a prompt through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "..."`
- **THEN** `houmao-mgr` submits that request through registry-first discovery or the pair-managed agent control authority
- **AND THEN** the command does not require the operator to know whether the agent is server-backed or locally-backed

#### Scenario: Operator relaunches a managed tmux-backed session through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or tmux-local current-session authority
- **AND THEN** the command relaunches the existing tmux-backed managed session rather than constructing a new launch

#### Scenario: Help output does not advertise retired inspection commands
- **WHEN** an operator runs `houmao-mgr agents --help`
- **THEN** the help output does not list `show` or `history`
- **AND THEN** supported inspection guidance points operators to `state`, `agents gateway tui ...`, or `agents turn ...` rather than removed managed-agent inspection commands

### Requirement: `houmao-mgr agents gateway tui` exposes raw gateway-owned TUI tracking commands
`houmao-mgr` SHALL expose a native `agents gateway tui ...` command family for raw gateway-owned TUI tracking on managed agents.

At minimum, that family SHALL include:

- `state`
- `history`
- `watch`
- `note-prompt`

`agents gateway tui state` SHALL read the managed agent's live gateway-owned TUI state path rather than the transport-neutral managed-agent summary view.

`agents gateway tui history` SHALL read the managed agent's live gateway-owned bounded snapshot-history path rather than the coarse managed-agent `/history` surface.

`agents gateway tui note-prompt` SHALL target the managed agent's live gateway prompt-note tracking path rather than the queued gateway request path.

`agents gateway tui watch` SHALL act as an operator-facing repeated inspection surface over the same live gateway-owned TUI state path used by `agents gateway tui state`.

#### Scenario: Operator reads raw gateway-owned TUI state through the native `agents gateway tui` tree
- **WHEN** an operator runs `houmao-mgr agents gateway tui state --agent-id abc123`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-mgr` returns the raw gateway-owned TUI state for that managed agent
- **AND THEN** the command does not collapse that response to the transport-neutral `agents state` payload

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

### Requirement: Server-backed managed-agent commands accept passive server pair authorities
`houmao-mgr` server-backed managed-agent command paths SHALL accept `houmao-passive-server` as a supported pair authority and SHALL resolve their managed client through the pair-authority factory.

This SHALL cover the `agents`, `agents mail`, and `agents turn` families whenever those commands are operating through an explicit pair authority instead of a resumed local controller.

#### Scenario: Managed-agent summary inspection works through a passive server
- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123 --port 9891`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` returns the managed-agent summary view for `abc123`
- **AND THEN** the command does not fail only because the selected pair authority is passive

#### Scenario: Headless turn submission works through a passive server
- **WHEN** an operator runs `houmao-mgr agents turn submit --agent-id abc123 --port 9891 --prompt "..."`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` submits the turn through the passive server
- **AND THEN** the command returns the accepted turn identity needed for later inspection

### Requirement: Repo-owned docs prefer `houmao-mgr` over `houmao-cli` for covered pair workflows
Repo-owned active documentation under `docs/` SHALL present `houmao-mgr` and `houmao-server` as the supported operator surfaces for current managed-agent and pair workflows.

References to `houmao-cli` MAY remain only in explicit migration, legacy, retirement, or historical contexts. Active documentation SHALL NOT retain `houmao-cli` as the default example for uncovered current workflows just because a native replacement has not been implemented yet.

Repo-owned documentation for managed-agent inspection SHALL NOT present `houmao-mgr agents show` or `houmao-mgr agents history` as supported native inspection surfaces.

#### Scenario: Active docs replace `houmao-cli` examples for supported workflows
- **WHEN** a repo-owned document under `docs/` describes a current managed-agent or pair workflow that is supported by `houmao-mgr` or `houmao-server`
- **THEN** that document uses `houmao-mgr` or `houmao-server` as the primary command example
- **AND THEN** it does not keep `houmao-cli` as the default example for that workflow

#### Scenario: Legacy `houmao-cli` references are explicitly marked as legacy
- **WHEN** a repo-owned document under `docs/` still mentions `houmao-cli`
- **THEN** that mention appears only in explicit migration, legacy, retirement, or historical guidance
- **AND THEN** it is not presented as an active default operator path

#### Scenario: Docs do not present retired managed-agent inspection commands
- **WHEN** repo-owned docs under `docs/` explain managed-agent inspection or long-running local/serverless operation
- **THEN** they use supported surfaces such as `houmao-mgr agents state`, gateway TUI state, or `houmao-mgr agents turn ...`
- **AND THEN** they do not present `houmao-mgr agents show` or `houmao-mgr agents history` as supported native inspection commands

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

- **WHEN** an operator runs `houmao-mgr agents state --agent-name gpu`
- **AND WHEN** exactly one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` targets that managed agent
- **AND THEN** the command succeeds without requiring the operator to spell the authoritative `agent_id`

#### Scenario: Friendly-name selector fails on ambiguity

- **WHEN** an operator runs `houmao-mgr agents prompt --agent-name gpu --prompt "..."`
- **AND WHEN** more than one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error directs the operator to retry with `--agent-id`

#### Scenario: Friendly-name miss reports local miss before remote-unavailable fallback

- **WHEN** an operator runs `houmao-mgr agents state --agent-name agent-test`
- **AND WHEN** no live local managed agent currently uses friendly name `agent-test`
- **AND WHEN** the default pair authority is unavailable for fallback lookup
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that no local managed agent matched friendly name `agent-test`
- **AND THEN** the error also states that remote pair-authority lookup could not complete
- **AND THEN** the error does not present pair-authority unavailability as the only problem

#### Scenario: Friendly-name selector that matches a tmux/session alias gives a corrective hint

- **WHEN** an operator runs `houmao-mgr agents state --agent-name agent-test`
- **AND WHEN** no live local managed agent currently uses friendly name `agent-test`
- **AND WHEN** exactly one live local managed agent uses tmux/session alias `agent-test`
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that `--agent-name` expects the friendly managed-agent name rather than the tmux/session alias
- **AND THEN** the error identifies the matching agent's published friendly name or authoritative `agent_id` as the retry target

#### Scenario: Missing selector fails when no current-session contract applies

- **WHEN** an operator runs `houmao-mgr agents stop` without `--agent-id` or `--agent-name`
- **AND WHEN** that command has no separate current-session targeting contract
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that exactly one of `--agent-id` or `--agent-name` is required
