## ADDED Requirements

### Requirement: Stalwart-backed mailbox transport provisions mailbox principals through server-owned management surfaces
The system SHALL support a mailbox transport named `stalwart` for mailbox-enabled sessions.

When the `stalwart` transport is selected, the runtime SHALL provision or confirm the server-side mailbox prerequisites through Stalwart management surfaces rather than through filesystem mailbox registration flows.

At minimum, those prerequisites SHALL include:

- a local Stalwart-managed mail domain for the selected mailbox address,
- an individual mailbox account bound to the selected mailbox address,
- mailbox access credentials or credential references suitable for mailbox operations,
- idempotent re-entry behavior when the same mailbox principal is started again.

The `stalwart` transport SHALL NOT require `safe`, `force`, `stash`, `deactivate`, or `purge` filesystem mailbox registration semantics in order to create or reuse a mailbox-enabled session.

#### Scenario: Starting a Stalwart-backed session provisions a missing mailbox account
- **WHEN** a developer starts a mailbox-enabled session with `transport=stalwart` for a mailbox address that is not yet present in the target Stalwart server
- **THEN** the runtime creates or confirms the required domain and mailbox account through Stalwart management surfaces
- **AND THEN** the resulting session can use that mailbox without creating a filesystem mailbox registration

#### Scenario: Restarting the same Stalwart-backed mailbox principal is idempotent
- **WHEN** a developer starts a second session for the same mailbox principal against the same Stalwart environment
- **THEN** the runtime reuses or confirms the existing server-side mailbox principal instead of creating a conflicting duplicate mailbox
- **AND THEN** mailbox enablement succeeds without invoking filesystem registration conflict modes

### Requirement: Stalwart-backed mailbox transport delegates mailbox integrity and mailbox state to the mail server
For the `stalwart` transport, the system SHALL treat the Stalwart server as the authority for:

- delivered message storage,
- mailbox folders such as inbox and sent,
- read or unread mailbox state,
- reply ancestry and transport-level threading metadata,
- transport-level delivery integrity.

The `stalwart` transport SHALL NOT require Houmao to materialize a filesystem mailbox root with `rules/`, mailbox projection symlinks, mailbox lock files, or mailbox-local SQLite state in order to maintain mailbox correctness.

#### Scenario: Stalwart-backed mailbox operation does not require filesystem mailbox artifacts
- **WHEN** a mailbox-enabled session uses the `stalwart` transport
- **THEN** mailbox correctness comes from the Stalwart server rather than from a Houmao-managed mailbox root
- **AND THEN** the transport does not require `rules/`, projection symlinks, or mailbox-local SQLite artifacts to maintain read or unread or delivery integrity

### Requirement: Stalwart-backed mailbox transport uses JMAP as the primary automation surface
The `stalwart` transport SHALL use JMAP as the primary automation surface for mailbox operations initiated by Houmao mailbox workflows.

At minimum, the `stalwart` transport SHALL support:

- discovering mailbox messages for `mail check`,
- composing and delivering a new message for `mail send`,
- replying to an existing message for `mail reply`,
- updating recipient mailbox state when a mailbox workflow marks a message read.

SMTP submission and IMAP access MAY be supported for compatibility or debugging, but they SHALL NOT be the normative mailbox automation contract for Houmao mailbox operations in this change.

#### Scenario: Mail send uses JMAP-backed Stalwart delivery
- **WHEN** a mailbox-enabled session uses `mail send` through the `stalwart` transport
- **THEN** the mailbox workflow submits that message through JMAP-backed Stalwart mailbox operations
- **AND THEN** the operator-visible result describes the delivered message without requiring filesystem delivery helpers

#### Scenario: Mail reply uses Stalwart mailbox metadata to preserve reply ancestry
- **WHEN** a mailbox-enabled session uses `mail reply` through the `stalwart` transport
- **THEN** the mailbox workflow resolves the target message through Stalwart-backed mailbox metadata
- **AND THEN** the resulting reply preserves reply ancestry through real email reply headers rather than through filesystem-only thread reconstruction

### Requirement: Stalwart-backed mailboxes publish a welcome thread for shared mailbox conventions
When the runtime provisions or confirms a mailbox under the `stalwart` transport, it SHALL ensure that mailbox participants can discover a mailbox-resident welcome message or welcome thread carrying shared Houmao mailbox conventions that do not need hard transport enforcement.

That welcome content SHALL be suitable for carrying:

- mailbox usage conventions,
- structured reply expectations,
- thread or subject conventions,
- references to Houmao mailbox documentation.

The welcome thread SHALL be guidance for mailbox participants rather than the runtime’s only source of infrastructure truth for transport bindings.

#### Scenario: Newly provisioned Stalwart mailbox receives welcome guidance
- **WHEN** the runtime provisions a mailbox account for a new `stalwart` mailbox principal
- **THEN** the runtime creates or confirms mailbox-resident welcome guidance for that mailbox
- **AND THEN** mailbox participants can inspect that guidance through the real mail system instead of through a filesystem `rules/` tree

#### Scenario: Missing welcome thread does not erase runtime mailbox bindings
- **WHEN** a mailbox-enabled `stalwart` session resumes and the welcome message has been moved or deleted
- **THEN** the runtime still restores the mailbox binding from runtime-owned transport metadata
- **AND THEN** the missing welcome thread is treated as missing guidance rather than as missing transport configuration
