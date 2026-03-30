## MODIFIED Requirements

### Requirement: `houmao-mgr agents mail` exposes pair-native mailbox follow-up commands
`houmao-mgr` SHALL expose a native `agents mail ...` command family for mailbox discovery and follow-up on managed agents.

At minimum, that family SHALL include:

- `resolve-live`
- `status`
- `check`
- `send`
- `reply`
- `mark-read`

Those commands SHALL address managed agents by managed-agent reference and SHALL dispatch mailbox work by the resolved managed-agent authority:

- pair-managed targets SHALL use pair-owned mail authority,
- local managed targets SHALL use verified manager-owned local mail authority or verified gateway-backed authority when available,
- when a local live-TUI target lacks verified direct or gateway authority for a mailbox action, the command MAY fall back to TUI-mediated submission and SHALL preserve a non-authoritative submission result instead of claiming mailbox success,
- callers SHALL NOT be required to discover or call gateway endpoints directly themselves when using the CLI.

For commands in that family that operate on one managed agent, `houmao-mgr` SHALL support both explicit selectors and same-session current-session targeting:

- explicit `--agent-id` or `--agent-name` SHALL take precedence when provided,
- otherwise, when the caller runs the command inside the owning managed tmux session, `houmao-mgr` SHALL resolve the current managed agent through manifest-first discovery using `AGENTSYS_MANIFEST_PATH` with `AGENTSYS_AGENT_ID` as fallback,
- outside tmux without explicit selectors, the command SHALL fail explicitly rather than guessing from cwd or ambient shell state.

`resolve-live` SHALL return machine-readable mailbox binding and live gateway discovery data for the resolved managed agent.

For local managed targets, ordinary mailbox follow-up SHALL NOT require prompting the target agent to interpret mailbox instructions when verified manager-owned or gateway-backed mailbox execution is available.

#### Scenario: Same-session resolve-live succeeds without explicit selectors
- **WHEN** an operator or projected skill runs `houmao-mgr agents mail resolve-live` inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed agent through that tmux-local discovery contract
- **AND THEN** the command returns the current mailbox binding and any live gateway discovery data without requiring `--agent-id` or `--agent-name`

#### Scenario: Explicit selector wins over same-session discovery
- **WHEN** an operator runs `houmao-mgr agents mail status --agent-name alice` from inside a different managed tmux session
- **THEN** `houmao-mgr` targets the explicitly selected managed agent
- **AND THEN** the command does not silently replace that explicit target with the caller's current session

#### Scenario: Outside-tmux mail discovery fails without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents mail resolve-live` outside tmux
- **AND WHEN** the command is not given `--agent-id` or `--agent-name`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd, gateway listener bindings, or ambient shell state

#### Scenario: Local mail check uses manager-owned direct mailbox execution
- **WHEN** an operator runs `houmao-mgr agents mail check --agent-name alice`
- **AND WHEN** `alice` resolves to local managed-agent authority on the current host
- **THEN** `houmao-mgr` performs mailbox follow-up through manager-owned local mail authority
- **AND THEN** the command does not require prompting the target agent to interpret mailbox instructions for that ordinary mailbox check

#### Scenario: Local live-TUI send without verified direct authority returns submission-only fallback
- **WHEN** an operator runs `houmao-mgr agents mail send --agent-name alice --to bob@agents.localhost --subject "..." --body-content "..."`
- **AND WHEN** `alice` resolves to a local live-TUI managed-agent target
- **AND WHEN** verified manager-owned or gateway-backed mail execution is unavailable for that action
- **THEN** `houmao-mgr` returns a non-authoritative submission result for that mailbox request
- **AND THEN** the command does not claim verified mailbox success solely from TUI transcript recovery

#### Scenario: Pair-managed target still uses pair-owned mail authority
- **WHEN** an operator runs `houmao-mgr agents mail send --agent-id abc123 --to bob@agents.localhost --subject "..." --body-content "..."`
- **AND WHEN** `abc123` resolves through pair authority
- **THEN** `houmao-mgr` dispatches that mailbox action through the supported pair-owned mail authority
- **AND THEN** the operator does not need to discover or address the pair-owned gateway endpoint directly
