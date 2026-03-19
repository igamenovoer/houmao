## MODIFIED Requirements

### Requirement: Mailbox system skills use a stable env-var binding contract
The system SHALL require runtime-owned mailbox system skills to resolve mailbox bindings through runtime-managed env vars rather than through literal filesystem paths, URLs, or mailbox addresses embedded in projected skill text.

At minimum, the runtime SHALL provide the following common mailbox binding env vars for started sessions:

- `AGENTSYS_MAILBOX_TRANSPORT`,
- `AGENTSYS_MAILBOX_PRINCIPAL_ID`,
- `AGENTSYS_MAILBOX_ADDRESS`,
- `AGENTSYS_MAILBOX_BINDINGS_VERSION`.

The runtime SHALL additionally provide transport-specific mailbox binding env vars required by the selected transport.

Filesystem-specific mailbox binding env vars SHALL continue to use the `AGENTSYS_MAILBOX_FS_` prefix.

Email-backed mailbox binding env vars for real-mail transports SHALL use the `AGENTSYS_MAILBOX_EMAIL_` prefix.

For `stalwart` mailbox sessions, those runtime-managed bindings SHALL include at minimum:

- a JMAP endpoint or JMAP base URL for mailbox operations,
- the mailbox login identity needed for mailbox access,
- a runtime-managed authentication reference suitable for mailbox access without persisting secrets in the manifest payload.

#### Scenario: Filesystem mailbox skill resolves filesystem bindings from env vars
- **WHEN** the runtime starts an agent session with the filesystem mailbox transport
- **THEN** the projected mailbox system skill refers to the filesystem mailbox through runtime-managed filesystem env vars
- **AND THEN** those filesystem-specific binding env vars use the `AGENTSYS_MAILBOX_FS_` prefix

#### Scenario: Stalwart mailbox skill resolves real-mail bindings from env vars
- **WHEN** the runtime starts an agent session with the `stalwart` mailbox transport
- **THEN** the projected mailbox system skill refers to that mailbox through runtime-managed email transport env vars
- **AND THEN** those transport-specific binding env vars use the `AGENTSYS_MAILBOX_EMAIL_` prefix instead of inheriting filesystem path bindings

### Requirement: Runtime-owned mailbox commands rely on projected mailbox system skills
The system SHALL allow runtime-owned mailbox command surfaces to rely on projected, transport-specific mailbox system skills plus runtime-managed mailbox bindings, without requiring mailbox-specific instructions to be authored in the role or recipe.

For filesystem sessions, the projected mailbox system skills MAY continue to direct agents to shared filesystem mailbox rules and managed helper scripts.

For `stalwart` sessions, the projected mailbox system skills SHALL direct agents to the Stalwart-backed mailbox transport bindings and mailbox-resident conventions appropriate to the real mail system instead of to filesystem-only repair machinery.

#### Scenario: Runtime mail request uses projected filesystem mailbox system skills
- **WHEN** the runtime delivers a mailbox-operation prompt to a filesystem mailbox-enabled session
- **THEN** the launched agent can satisfy that request through the projected filesystem mailbox system skills and filesystem mailbox env bindings
- **AND THEN** that mailbox operation does not depend on mailbox-specific behavior being restated inside the role or recipe

#### Scenario: Runtime mail request uses projected Stalwart mailbox system skills
- **WHEN** the runtime delivers a mailbox-operation prompt to a `stalwart` mailbox-enabled session
- **THEN** the launched agent can satisfy that request through the projected Stalwart mailbox system skills and runtime-managed email mailbox bindings
- **AND THEN** that mailbox operation does not require the role or recipe to define transport-specific Stalwart instructions

## ADDED Requirements

### Requirement: Email-backed mailbox system skills use mailbox-resident guidance instead of filesystem mailbox rules
For real-mail transports such as `stalwart`, the projected mailbox system skill SHALL instruct agents to use mailbox-resident welcome guidance and runtime-managed mailbox bindings rather than a filesystem mailbox `rules/` tree as the first transport-specific guidance surface.

The projected email-backed mailbox system skill SHALL NOT require `rules/`, `rules/scripts/`, mailbox lock files, or mailbox-local SQLite as prerequisites for mailbox correctness.

#### Scenario: Stalwart mailbox skill points agent to welcome guidance instead of rules directory
- **WHEN** an agent uses the projected mailbox system skill for a `stalwart` mailbox session
- **THEN** that skill instructs the agent to consult mailbox-resident welcome guidance and runtime-managed bindings for transport-specific conventions
- **AND THEN** the skill does not require a filesystem `rules/` directory to use the mailbox correctly

### Requirement: Email-backed mailbox system skills do not direct agents to server administration surfaces
For real-mail transports such as `stalwart`, projected mailbox system skills SHALL distinguish participant mailbox operations from server administration.

Those skills SHALL allow mailbox read, send, and reply behavior through runtime-managed participant mailbox bindings, but they SHALL NOT instruct ordinary mailbox participants to use Stalwart management APIs for routine mailbox operations.

#### Scenario: Stalwart mailbox skill avoids management API usage for ordinary message work
- **WHEN** an agent uses the projected mailbox system skill to check or send mail through a `stalwart` mailbox session
- **THEN** the skill uses participant mailbox bindings suitable for mailbox operations
- **AND THEN** the skill does not direct the agent to use server administration APIs to read, send, or reply to ordinary mailbox messages
