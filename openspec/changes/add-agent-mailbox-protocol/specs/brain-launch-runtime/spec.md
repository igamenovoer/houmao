## ADDED Requirements

### Requirement: Mailbox enablement is resolved before session start and persisted for resume
The runtime SHALL enable filesystem mailbox support through declarative recipe configuration and MAY allow explicit `start-session` CLI overrides for transport-specific ad hoc sessions.

The runtime SHALL resolve one effective mailbox configuration before building the launch plan, SHALL persist that resolved mailbox configuration in the session manifest, and SHALL restore it when resuming the session.

#### Scenario: Recipe configuration enables mailbox support
- **WHEN** a developer starts an agent session whose resolved recipe enables filesystem mailbox support
- **THEN** the runtime resolves that mailbox configuration before building the launch plan
- **AND THEN** the resolved session uses that mailbox transport and principal binding for subsequent mailbox-aware runtime work

#### Scenario: Start session CLI overrides mailbox transport or root
- **WHEN** a developer starts an agent session with explicit mailbox CLI overrides such as transport or filesystem root
- **THEN** the runtime applies those overrides to the effective mailbox configuration for that session
- **AND THEN** the resulting session manifest records the overridden mailbox transport and bindings rather than forcing resume to re-derive them from recipe defaults

#### Scenario: Resume restores persisted mailbox bindings
- **WHEN** a developer resumes a previously started mailbox-enabled session
- **THEN** the runtime restores the mailbox transport, principal binding, and transport-specific mailbox bindings from the persisted session manifest
- **AND THEN** runtime mailbox commands for that resumed session preserve the same sender principal and mailbox root unless an explicit refresh changes them later

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and mailbox env bindings
When filesystem mailbox support is enabled for a started session, the runtime SHALL project the platform-owned mailbox system skills into the active agent skillset under a reserved runtime-owned namespace and SHALL populate the filesystem mailbox binding env contract before mailbox-related work is expected from the agent.

#### Scenario: Start session projects mailbox system skills with filesystem bindings
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skills destination under the reserved runtime-owned namespace
- **AND THEN** the runtime starts the session with the filesystem mailbox binding env vars needed by those mailbox system skills
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to the effective mailbox content root for that session

#### Scenario: Start session defaults filesystem mailbox root from runtime root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the configured runtime root
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to that derived default path

### Requirement: Runtime sessions support filesystem mailbox binding refresh
The runtime SHALL support an explicit control path that refreshes filesystem mailbox binding env vars for an active session without requiring regeneration of the mailbox system skill templates.

#### Scenario: Refresh mailbox bindings for an active session
- **WHEN** a developer or orchestrator requests filesystem mailbox-binding refresh for an active session
- **THEN** the runtime updates the filesystem mailbox binding env vars for that session
- **AND THEN** the runtime updates the persisted session manifest to match the refreshed mailbox binding state
- **AND THEN** subsequent runtime-controlled work in that session uses the refreshed filesystem mailbox bindings

### Requirement: Runtime CLI exposes top-level agent-mediated mailbox operations for resumed sessions
The runtime CLI SHALL expose a top-level `mail` command surface for resumed mailbox-enabled sessions.

That `mail` command surface SHALL support at minimum the operations `check`, `send`, and `reply`, and SHALL target an existing live session through the same agent-identity or session-manifest resolution model used by other runtime session-control commands.

#### Scenario: Mail check targets a resumed mailbox-enabled session
- **WHEN** a developer invokes the runtime `mail check` command against a resumed mailbox-enabled session
- **THEN** the runtime resolves that target session through the normal runtime session-identity resolution path
- **AND THEN** the runtime asks that live agent session to perform one mailbox-check operation for its bound mailbox principal

#### Scenario: Mail send targets a resumed mailbox-enabled session
- **WHEN** a developer invokes the runtime `mail send` command against a resumed mailbox-enabled session with recipients and message content
- **THEN** the runtime asks that live agent session to compose and deliver one new mailbox message through its configured mailbox transport
- **AND THEN** the resulting mailbox operation preserves the sender principal bound to that session rather than allowing the operator to spoof an arbitrary sender principal

#### Scenario: Mail reply preserves existing thread ancestry
- **WHEN** a developer invokes the runtime `mail reply` command against a resumed mailbox-enabled session for an existing message
- **THEN** the runtime asks that live agent session to reply through the mailbox protocol rather than starting an unrelated new root message
- **AND THEN** the reply preserves the existing `thread_id`, `in_reply_to`, and `references` semantics for that thread

### Requirement: Runtime mail commands use skill-directed prompts with appended mailbox metadata and validate a sentinel-delimited result contract
The runtime SHALL translate each `mail` command invocation into a runtime-owned mailbox prompt delivered through the existing prompt-turn control path rather than directly manipulating mailbox files or mailbox SQLite state itself.

That mailbox prompt SHALL explicitly tell the agent which projected mailbox system skill to use for the mailbox operation and SHALL append structured mailbox metadata needed for the mailbox operation and result parsing.

The `mail` command handler SHALL validate exactly one structured mailbox result payload returned between `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` sentinels in the agent output and SHALL surface that result to the operator in a parseable form.

#### Scenario: Mail command uses skill-directed prompt with appended mailbox metadata
- **WHEN** a developer invokes a runtime `mail` command for a mailbox-enabled session
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the projected mailbox system skill the agent should use
- **AND THEN** that prompt tells the agent to inspect the shared mailbox `rules/` directory before interacting with shared mailbox state
- **AND THEN** that prompt tells the agent to use shared scripts from `rules/scripts/` for any mailbox step that touches `index.sqlite` or `locks/`
- **AND THEN** that prompt appends structured mailbox metadata for the mailbox operation and result contract

#### Scenario: Mail command returns structured mailbox result
- **WHEN** a mailbox-enabled agent completes a runtime `mail` request
- **THEN** the agent returns one structured mailbox result payload describing the mailbox operation outcome between the required sentinels
- **AND THEN** the runtime validates and prints that result in a parseable form for the operator

#### Scenario: Mail command fails on malformed sentinel payload
- **WHEN** a mailbox-enabled agent omits the required sentinels, emits malformed JSON, or returns more than one sentinel-delimited mailbox result payload
- **THEN** the runtime returns an explicit mailbox-result parsing error for that `mail` command
- **AND THEN** the runtime does not send an automatic retry prompt in v1

#### Scenario: Mail command fails fast when session cannot accept a new turn
- **WHEN** a developer invokes a runtime `mail` command for a session that is already busy or otherwise cannot safely accept a new prompt turn
- **THEN** the runtime returns an explicit mailbox-command error
- **AND THEN** the runtime does not silently queue hidden mailbox work for later execution
