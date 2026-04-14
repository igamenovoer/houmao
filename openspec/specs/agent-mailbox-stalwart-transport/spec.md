# agent-mailbox-stalwart-transport Specification

## Purpose
Define the real email-backed `stalwart` mailbox transport contract, including provisioning, shared mailbox operations, and the JMAP automation surface.
## Requirements
### Requirement: Stalwart-backed mailbox transport provisions mailbox principals through server-owned management surfaces
The system SHALL support a mailbox transport named `stalwart` for mailbox-enabled sessions.

When the `stalwart` transport is selected, the runtime SHALL provision or confirm the server-side mailbox prerequisites through Stalwart management surfaces rather than through filesystem mailbox registration flows.

At minimum, those prerequisites SHALL include:

- a local Stalwart-managed mail domain for the selected mailbox address,
- an individual mailbox account bound to the selected mailbox address,
- mailbox access credentials resolved through a secret-free `credential_ref` suitable for mailbox operations,
- idempotent re-entry behavior when the same mailbox principal is started again.

When Stalwart credential references are persisted for resume or gateway adapter construction, the persisted mailbox binding SHALL keep only the secret-free `credential_ref`; the credential material itself SHALL remain session-scoped outside the manifest payload and MAY be materialized as a runtime-owned file in v1.

The `stalwart` transport SHALL NOT require `safe`, `force`, `stash`, `deactivate`, or `purge` filesystem mailbox registration semantics in order to create or reuse a mailbox-enabled session.

#### Scenario: Starting a Stalwart-backed session provisions a missing mailbox account
- **WHEN** a developer starts a mailbox-enabled session with `transport=stalwart` for a mailbox address that is not yet present in the target Stalwart server
- **THEN** the runtime creates or confirms the required domain and mailbox account through Stalwart management surfaces
- **AND THEN** the resulting session can use that mailbox without creating a filesystem mailbox registration

#### Scenario: Restarting the same Stalwart-backed mailbox principal is idempotent
- **WHEN** a developer starts a second session for the same mailbox principal against the same Stalwart environment
- **THEN** the runtime reuses or confirms the existing server-side mailbox principal instead of creating a conflicting duplicate mailbox
- **AND THEN** mailbox enablement succeeds without invoking filesystem registration conflict modes

#### Scenario: Restarting the same Stalwart-backed mailbox principal reuses credential references without unnecessary rotation
- **WHEN** a developer resumes or starts the same mailbox principal again against the same Stalwart environment
- **THEN** the runtime reuses or confirms the existing secret-free `credential_ref` or equivalent credential material when it is still valid
- **AND THEN** mailbox enablement does not rotate credentials unnecessarily unless a later explicit refresh path requests it

### Requirement: Stalwart-backed mailbox transport delegates shared mailbox state and integrity to the mail server
For the `stalwart` transport, the system SHALL treat the Stalwart server as the authority for:

- delivered message storage,
- unread state used by shared mailbox `check` behavior,
- reply ancestry and transport-level threading metadata used by shared mailbox `reply` behavior,
- transport-level delivery integrity.

The `stalwart` transport SHALL NOT require Houmao to materialize a filesystem mailbox root with `rules/`, mailbox projection symlinks, mailbox lock files, or mailbox-local SQLite state in order to maintain mailbox correctness.

#### Scenario: Stalwart-backed mailbox operation does not require filesystem mailbox artifacts
- **WHEN** a mailbox-enabled session uses the `stalwart` transport
- **THEN** mailbox correctness comes from the Stalwart server rather than from a Houmao-managed mailbox root
- **AND THEN** the transport does not require `rules/`, projection symlinks, or mailbox-local SQLite artifacts to maintain read or unread or delivery integrity

### Requirement: Stalwart-backed mailbox transport uses JMAP as the primary automation surface for shared mailbox operations
The `stalwart` transport SHALL use JMAP as the primary automation surface for mailbox operations initiated by Houmao mailbox workflows.

At minimum, the `stalwart` transport SHALL support:

- discovering mailbox messages for `mail check`,
- composing and delivering a new message for `mail send`,
- replying to an existing message for `mail reply`.

SMTP submission and IMAP access MAY be supported for compatibility or debugging, but they SHALL NOT be the normative mailbox automation contract for Houmao mailbox operations in this change.

#### Scenario: Mail send uses JMAP-backed Stalwart delivery
- **WHEN** a mailbox-enabled session uses `mail send` through the `stalwart` transport
- **THEN** the mailbox workflow submits that message through JMAP-backed Stalwart mailbox operations
- **AND THEN** the operator-visible result describes the delivered message without requiring filesystem delivery helpers

#### Scenario: Mail reply uses Stalwart mailbox metadata to preserve reply ancestry
- **WHEN** a mailbox-enabled session uses `mail reply` through the `stalwart` transport
- **THEN** the mailbox workflow resolves the target message through Stalwart-backed mailbox metadata
- **AND THEN** the resulting reply preserves reply ancestry through real email reply headers rather than through filesystem-only thread reconstruction

### Requirement: Stalwart-backed mailbox transport supports shared lifecycle operations
For the `stalwart` transport, the system SHALL support the shared mailbox lifecycle operation set exposed through the gateway mailbox facade and direct mailbox workflows:

- mailbox availability or status,
- list messages from a supported mailbox box,
- peek one message body without marking it read,
- read one message body while marking it read,
- send,
- reply,
- manual mark for supported lifecycle state,
- move among supported mailbox boxes,
- archive selected messages.

The transport SHALL map shared read state to server-backed seen state, answered state to server-backed answered state or equivalent durable metadata, and archive/move behavior to server-backed mailbox membership.

#### Scenario: Stalwart read maps to server seen state
- **WHEN** a caller reads a Stalwart-backed mailbox message through the shared operation contract
- **THEN** the operation returns the selected message body
- **AND THEN** the transport updates the server-backed seen state for that mailbox account

#### Scenario: Stalwart reply maps to answered state
- **WHEN** a caller replies to a Stalwart-backed mailbox message
- **THEN** the transport preserves reply ancestry through email-compatible metadata
- **AND THEN** the transport records answered state for the replied message through server-backed state or equivalent durable metadata

#### Scenario: Stalwart archive moves to the archive mailbox
- **WHEN** a caller archives selected Stalwart-backed messages
- **THEN** the transport moves those messages out of the open inbox mailbox and into the Stalwart archive mailbox or equivalent configured archive target
- **AND THEN** the shared response reports the messages as archived and no longer open inbox work

### Requirement: Stalwart-backed mailbox transport uses JMAP for lifecycle state
The `stalwart` transport SHALL use JMAP as the primary automation surface for shared lifecycle operations whenever the needed state is expressible through JMAP.

SMTP submission and IMAP access MAY remain compatibility or debugging surfaces, but they SHALL NOT be the normative automation contract for list, peek, read, mark, move, archive, send, or reply behavior in this change.

#### Scenario: JMAP move updates mailbox membership
- **WHEN** a shared mailbox move operation targets a Stalwart-backed message
- **THEN** the transport performs the mailbox membership update through JMAP-backed Stalwart mailbox operations
- **AND THEN** the caller does not need to understand Stalwart-native object shapes or mailbox ids
