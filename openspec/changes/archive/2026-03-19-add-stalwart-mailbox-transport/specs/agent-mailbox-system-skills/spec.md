## MODIFIED Requirements

### Requirement: Mailbox system skills use a stable env-var binding contract
The system SHALL require runtime-owned mailbox system skills to resolve mailbox bindings through runtime-managed env vars rather than through literal filesystem paths, URLs, or mailbox addresses embedded in projected skill text.

At minimum, the runtime SHALL provide the following common mailbox binding env vars for started sessions:

- `AGENTSYS_MAILBOX_TRANSPORT`,
- `AGENTSYS_MAILBOX_PRINCIPAL_ID`,
- `AGENTSYS_MAILBOX_ADDRESS`,
- `AGENTSYS_MAILBOX_BINDINGS_VERSION`.

The runtime SHALL additionally provide transport-specific mailbox binding env vars required by the selected transport, and it MAY expose live gateway discovery bindings through the existing gateway env contract when a live gateway is attached.

Filesystem-specific mailbox binding env vars SHALL continue to use the `AGENTSYS_MAILBOX_FS_` prefix.

Email-backed mailbox binding env vars for real-mail transports SHALL use the `AGENTSYS_MAILBOX_EMAIL_` prefix.

For `stalwart` mailbox sessions, those runtime-managed bindings SHALL include at minimum:

- a JMAP endpoint or JMAP base URL for mailbox operations,
- the mailbox login identity needed for mailbox access,
- a runtime-managed authentication reference suitable for mailbox access without persisting secrets in the manifest payload.

That runtime-managed authentication reference SHALL be secret-free in the persisted mailbox binding and MAY resolve to a session-owned credential file path in v1.

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

When a live gateway exposes the shared `/v1/mail/*` mailbox surface for the session, the projected mailbox system skill SHALL prefer that gateway surface for the shared mailbox operations in this change: `check`, `send`, and `reply`.

When no live gateway mailbox facade is available, the projected mailbox system skill MAY fall back to direct transport-specific mailbox behavior appropriate to the selected transport.

#### Scenario: Gateway-aware mailbox skill uses the shared gateway mail surface
- **WHEN** a mailbox-enabled session has a live attached gateway that exposes `/v1/mail/*`
- **AND WHEN** the runtime delivers a mailbox-operation prompt such as `check`, `send`, or `reply`
- **THEN** the projected mailbox system skill prefers the gateway mailbox surface for that shared mailbox operation
- **AND THEN** the agent does not need to reason about filesystem versus Stalwart transport details to perform that shared operation

#### Scenario: Filesystem mailbox skill falls back to direct filesystem behavior when no gateway is attached
- **WHEN** the runtime delivers a mailbox-operation prompt to a filesystem mailbox-enabled session with no live gateway mailbox surface
- **THEN** the launched agent can satisfy that request through the projected filesystem mailbox system skills and filesystem mailbox env bindings
- **AND THEN** that mailbox operation does not depend on mailbox-specific behavior being restated inside the role or recipe

#### Scenario: Stalwart mailbox skill falls back to direct real-mail behavior when no gateway is attached
- **WHEN** the runtime delivers a mailbox-operation prompt to a `stalwart` mailbox-enabled session with no live gateway mailbox surface
- **THEN** the launched agent can satisfy that request through the projected Stalwart mailbox system skills and runtime-managed email mailbox bindings
- **AND THEN** that mailbox operation does not require the role or recipe to define transport-specific Stalwart instructions
