## ADDED Requirements

### Requirement: Filesystem mailbox system skills instruct agents to mark processed mail read explicitly
The system SHALL require the projected filesystem mailbox system skill to distinguish between discovering unread mail and marking a message read after processing.

That skill SHALL instruct agents to mark a message read only after the agent has actually processed that message successfully through the mailbox-managed helper boundary.

The skill SHALL NOT instruct agents to mark a message read merely because unread mail was detected or because a gateway-generated reminder prompt mentioned the message.

#### Scenario: Agent marks processed message read through the managed helper boundary
- **WHEN** an agent finishes processing an unread mailbox message successfully
- **THEN** the projected filesystem mailbox system skill instructs the agent to update mailbox read state explicitly through the managed mailbox helper boundary
- **AND THEN** the agent does not need gateway participation to complete that read-state update

#### Scenario: Reminder prompt does not imply read-state mutation
- **WHEN** the agent receives a gateway-owned reminder that unread mail exists
- **THEN** the projected filesystem mailbox system skill does not treat that reminder itself as a read-state change
- **AND THEN** the unread message remains unread until the agent explicitly marks it read after processing

## MODIFIED Requirements

### Requirement: Mailbox system skills use a stable env-var binding contract
The system SHALL require runtime-owned mailbox system skills to resolve mailbox bindings through runtime-managed env vars rather than through literal paths, URLs, or mailbox addresses embedded in the projected skill text.

At minimum, the runtime SHALL provide the following common mailbox binding env vars for started sessions:

- `AGENTSYS_MAILBOX_TRANSPORT`
- `AGENTSYS_MAILBOX_PRINCIPAL_ID`
- `AGENTSYS_MAILBOX_ADDRESS`
- `AGENTSYS_MAILBOX_BINDINGS_VERSION`

The runtime SHALL additionally provide filesystem-specific mailbox binding env vars required by the implemented filesystem transport.

Filesystem-specific mailbox binding env vars SHALL use the `AGENTSYS_MAILBOX_FS_` prefix.

For filesystem mailbox sessions, those runtime-managed bindings SHALL include at minimum:

- `AGENTSYS_MAILBOX_FS_ROOT` for the shared mailbox root,
- `AGENTSYS_MAILBOX_FS_SQLITE_PATH` for the shared mailbox-root catalog SQLite path,
- `AGENTSYS_MAILBOX_FS_INBOX_DIR` for the resolved mailbox inbox directory,
- `AGENTSYS_MAILBOX_FS_MAILBOX_DIR` for the resolved mailbox directory,
- `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH` for the mailbox-local SQLite path.

Reserved future mail-system-compatible mailbox binding env vars SHALL use the `AGENTSYS_MAILBOX_EMAIL_` prefix when a true-email adapter is added in a follow-up change.

#### Scenario: Filesystem mailbox skill resolves bindings from env vars
- **WHEN** the runtime starts an agent session with the filesystem mailbox transport
- **THEN** the projected mailbox system skill refers to the filesystem mailbox through runtime-managed env vars
- **AND THEN** the started session environment includes the filesystem mailbox binding env vars needed by that skill, including the transport kind, the shared mailbox locations, and the resolved mailbox-local state locations
- **AND THEN** those filesystem-specific binding env vars use the `AGENTSYS_MAILBOX_FS_` prefix
- **AND THEN** the filesystem mailbox content root is provided through `AGENTSYS_MAILBOX_FS_ROOT` rather than being inferred from a fixed run-directory location

#### Scenario: Filesystem mailbox skill receives explicit local mailbox-state bindings
- **WHEN** the runtime starts or refreshes a filesystem mailbox-enabled session
- **THEN** the runtime publishes explicit env bindings for the resolved mailbox directory and mailbox-local SQLite path
- **AND THEN** the agent does not need to reconstruct mailbox-local state paths heuristically from the inbox path

#### Scenario: Reserved future mail-system prefix stays distinct
- **WHEN** the system documents mailbox bindings for a future true-email-compatible adapter
- **THEN** those future mail-system-compatible binding env vars use the `AGENTSYS_MAILBOX_EMAIL_` prefix
- **AND THEN** they remain distinct from the implemented filesystem mailbox binding env vars

### Requirement: Filesystem mailbox system skills direct sensitive operations to shared scripts
The system SHALL require the projected filesystem mailbox system skill to direct agents to use shared helper scripts from `rules/scripts/` for mailbox operations that touch shared-root SQLite, mailbox-local SQLite, or `locks/`.

#### Scenario: Filesystem mailbox skill points sensitive work to rules/scripts
- **WHEN** an agent uses the projected filesystem mailbox system skill for a mailbox operation that touches shared-root `index.sqlite`, mailbox-local `mailbox.sqlite`, or `locks/`
- **THEN** that skill instructs the agent to use the corresponding shared helper script from `rules/scripts/`
- **AND THEN** the agent is not instructed to improvise raw SQLite or lock-file manipulation for that sensitive portion of the work
