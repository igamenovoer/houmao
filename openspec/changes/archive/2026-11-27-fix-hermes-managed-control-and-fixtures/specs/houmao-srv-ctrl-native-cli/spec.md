# Spec Delta

## MODIFIED Requirements

### Requirement: `houmao-mgr agents mail` exposes pair-native mailbox follow-up commands
`houmao-mgr` SHALL expose managed-agent mailbox discovery and follow-up under `agents single ... mail` and `agents self mail`. It SHALL resolve mailbox execution from the selected managed-agent authority.

#### Scenario: Scoped mail exposes discovery and lifecycle operations
- **WHEN** a caller selects `agents single ... mail` or `agents self mail`
- **THEN** the scope exposes `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`
- **AND THEN** `resolve-live` returns machine-readable mailbox binding and live gateway discovery data

#### Scenario: Scoped selection follows the chosen identity
- **WHEN** a caller runs a scoped mail command
- **THEN** `agents single` requires `--agent-id` or `--agent-name` before `mail` and preserves that explicit target inside another managed session
- **AND THEN** `agents self` uses the verified current runtime, including its owning tmux session or a supported runtime-owned locator and native authority
- **AND THEN** self targeting fails when managed authority cannot be verified

#### Scenario: The CLI selects mailbox authority for the resolved agent
- **WHEN** a command has resolved the managed agent
- **THEN** pair-managed targets use pair-owned mail authority
- **AND THEN** local targets use verified manager-owned or gateway-backed execution when available
- **AND THEN** verified local execution does not require prompting the agent to interpret mailbox instructions
- **AND THEN** the caller does not have to discover or call a gateway endpoint

#### Scenario: TUI fallback preserves uncertainty
- **WHEN** a local live-TUI target lacks verified direct or gateway authority for an ordinary mailbox action such as `list`, `send`, `reply`, or `archive`
- **THEN** the CLI may use TUI-mediated submission but reports an non-authoritative submission result instead of claiming mailbox success
- **AND THEN** operator-origin `post` fails explicitly without verified manager-owned, pair-owned, or gateway-backed mail authority and never uses TUI submission

#### Scenario: Mailbox mutations and notifier controls require a channel
- **WHEN** a caller runs a mail lifecycle operation or notifier control
- **THEN** the command requires `--channel offline|online` and rejects missing input without inferring it from canonical mail precedence
- **AND THEN** only summary `mail status` and `resolve-live` return both channels without a selection

#### Scenario: Same-session resolve-live succeeds without explicit selectors
- **WHEN** an operator or projected skill runs `houmao-mgr agents self mail resolve-live` inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed agent through that tmux-local discovery contract
- **AND THEN** the command returns the current mailbox binding and any live gateway discovery data without requiring `--agent-id` or `--agent-name`

#### Scenario: Explicit selector wins over same-session discovery
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail status` from inside a different managed tmux session
- **THEN** `houmao-mgr` targets the explicitly selected managed agent
- **AND THEN** the command does not silently replace that explicit target with the caller's current session

#### Scenario: Outside-tmux mail discovery fails without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents self mail resolve-live` outside tmux
- **AND WHEN** the caller has no verified managed runtime authority
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd, gateway listener bindings, or ambient shell state

#### Scenario: Local mail list uses manager-owned direct mailbox execution
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail list --channel offline`
- **AND WHEN** `alice` resolves to local managed-agent authority on the current host
- **THEN** `houmao-mgr` performs mailbox follow-up through manager-owned local mail authority
- **AND THEN** the command does not require prompting the target agent to interpret mailbox instructions for that ordinary mailbox list

#### Scenario: Local live-TUI send without verified direct authority returns submission-only fallback
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail send --channel offline --to bob@houmao.localhost --subject "..." --body-content "..."`
- **AND WHEN** `alice` resolves to a local live-TUI managed-agent target
- **AND WHEN** verified manager-owned or gateway-backed mail execution is unavailable for that action
- **THEN** `houmao-mgr` returns a non-authoritative submission result for that mailbox request
- **AND THEN** the command does not claim verified mailbox success solely from TUI transcript recovery

#### Scenario: Local live-TUI post without verified authority fails explicitly
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail post --channel offline --subject "..." --body-content "..."`
- **AND WHEN** `alice` resolves to a local live-TUI managed-agent target
- **AND WHEN** verified manager-owned or gateway-backed mail execution is unavailable for that action
- **THEN** the command fails explicitly instead of returning a submission-only mailbox result
- **AND THEN** it does not ask the target agent to impersonate `HOUMAO-operator@houmao.localhost`

#### Scenario: Pair-managed target still uses pair-owned mail authority
- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 mail post --channel offline --subject "..." --body-content "..."`
- **AND WHEN** `abc123` resolves through pair authority
- **THEN** `houmao-mgr` dispatches that mailbox action through the supported pair-owned mail authority
- **AND THEN** the operator does not need to discover or address the pair-owned gateway endpoint directly

#### Scenario: A Detached Hermes Tool Resolves and Uses Its Own Mailbox

- **WHEN** an authorized tool of a current managed Hermes TUI or service runs `agents self mail resolve-live` outside tmux
- **THEN** the command reports the current agent's mailbox binding and available gateway discovery data without explicit selectors
- **AND THEN** its supported follow-up operations use the selected binding and the established self authorization
