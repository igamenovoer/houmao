# Stalwart Mailbox Transport Delta

## MODIFIED Requirements

### Requirement: Stalwart-backed mailbox transport delegates shared mailbox state and integrity to the mail server

For the `stalwart` transport, the system SHALL treat the Stalwart server as the authority for:

- delivered message storage and the provider's Inbox delivery rules,
- unread state used by shared mailbox `check` behavior,
- reply ancestry and transport-level threading metadata used by shared mailbox `reply` behavior,
- transport-level delivery integrity.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The `stalwart` transport SHALL NOT require Houmao to materialize a filesystem mailbox root with `rules/`, mailbox projection symlinks, mailbox lock files, or mailbox-local SQLite state in order to maintain mailbox correctness.

#### Scenario: Stalwart-backed mailbox operation does not require filesystem mailbox artifacts

- **WHEN** a mailbox-enabled session uses the `stalwart` transport
- **THEN** mailbox correctness comes from the Stalwart server rather than from a Houmao-managed mailbox root
- **AND THEN** the transport does not require `rules/`, projection symlinks, or mailbox-local SQLite artifacts to maintain read or unread or delivery integrity

#### Scenario: Stalwart applies its own rules before depositing online mail

- **WHEN** Stalwart receives mail for an agent through an external client or Houmao submission
- **THEN** the provider controls Inbox placement under its active native rules
- **AND THEN** any supported Houmao-managed rule is applied through the independent trusted management path and remains effective while the gateway is unavailable

### Requirement: Stalwart-backed mailbox transport uses JMAP as the primary automation surface for shared mailbox operations

The `stalwart` transport SHALL use JMAP as the primary automation surface for mailbox operations initiated by Houmao mailbox workflows.

At minimum, the `stalwart` transport SHALL support:

- discovering mailbox messages for `mail list`,
- composing and submitting a new message for `mail send`,
- replying to an existing message for `mail reply`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

SMTP submission and IMAP access MAY be supported for compatibility or debugging, but they SHALL NOT be the normative mailbox automation contract for Houmao mailbox operations in this change.

#### Scenario: Mail send uses JMAP-backed Stalwart delivery

- **WHEN** a mailbox-enabled session uses `mail send` through the `stalwart` transport
- **THEN** the mailbox workflow submits that message through JMAP-backed Stalwart mailbox operations
- **AND THEN** the operator-visible result records provider-confirmed submission, refusal, or uncertainty without filesystem delivery helpers
- **AND THEN** a confirmed submission supplies no evidence of recipient Inbox placement, notification, or processing

#### Scenario: Mail reply uses Stalwart mailbox metadata to preserve reply ancestry

- **WHEN** a mailbox-enabled session uses `mail reply` through the `stalwart` transport
- **THEN** the mailbox workflow resolves the target message through Stalwart-backed mailbox metadata
- **AND THEN** the resulting reply preserves reply ancestry through real email reply headers rather than through filesystem-only thread reconstruction

### Requirement: Stalwart-backed mailbox transport supports shared lifecycle operations

The Stalwart transport SHALL expose status, list, peek, read, send, reply, manual mark, move, and archive through the shared mailbox facade and direct mailbox workflows within the caller's scope. The transport SHALL preserve protected placement by restricting move, archive, and archived-state updates to the independent trusted authority.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The transport SHALL map shared read to server-backed seen state, answered to server-backed answered state or equivalent durable metadata, and archive and move to server-backed mailbox membership.

#### Scenario: Stalwart read maps to server seen state

- **WHEN** a caller reads a Stalwart-backed mailbox message through the shared operation contract
- **THEN** the operation returns the selected message body
- **AND THEN** the transport updates the server-backed seen state for that mailbox account

#### Scenario: Stalwart reply maps to answered state

- **WHEN** a caller replies to a Stalwart-backed mailbox message
- **THEN** the transport preserves reply ancestry through email-compatible metadata
- **AND THEN** the transport records answered state through server-backed state or equivalent durable metadata

#### Scenario: Stalwart archive moves to the archive mailbox

- **WHEN** a caller with placement authority archives selected Stalwart-backed messages
- **THEN** the transport moves those messages out of the open Inbox into the Stalwart Archive or equivalent configured archive target
- **AND THEN** the response reports them as archived and no longer open Inbox work

### Requirement: Stalwart-backed mailbox transport uses JMAP for lifecycle state

The Stalwart transport SHALL use JMAP as the primary automation surface for shared lifecycle operations whenever the needed state is expressible through JMAP. SMTP submission and IMAP access MAY remain compatibility or debugging surfaces. The independent trusted management path SHALL use the provider-native controls required for protected placement.

#### Scenario: JMAP move updates mailbox membership

- **WHEN** an authorized shared mailbox move targets a Stalwart-backed message and is expressible through JMAP
- **THEN** the transport performs the membership update through JMAP-backed Stalwart mailbox operations
- **AND THEN** the caller can use the shared operation without supplying provider-native object shapes or mailbox IDs

### Requirement: Stalwart readiness validates the mailbox resources used by Houmao

A ready account SHALL support writable JMAP submission, authorize the sending identity, and identify an unambiguous Inbox, Sent, and Archive. Credentials SHALL support the claimed mode's operations. For a protected mode, readiness SHALL verify ordinary mailbox rights separately from the independent management authority's placement rights.

#### Scenario: The account has a usable role map

- **WHEN** validation resolves the sending identity and role map
- **THEN** ordinary readiness verifies Inbox read, seen and keyword updates, and removal rights plus Sent and Archive add rights
- **AND THEN** protected readiness requires the runtime rights needed for submission and authorized reads and updates and verifies placement rights through the trusted authority

#### Scenario: A mailbox with the name Archive lacks the role

- **WHEN** validation finds a folder named Archive without the provider's `archive` role
- **THEN** readiness reports the missing role and asks the operator to repair it

#### Scenario: A permission prevents normal mailbox operations

- **WHEN** a permission required for the selected mode is missing or denied
- **THEN** readiness identifies the relevant role and right before declaring the account ready for that mode

## ADDED Requirements

### Requirement: Protected Stalwart placement requires independent provider control

Stalwart SHALL support protected blocklists only when an independent trusted management path can verify owner-signed rule changes and configure native delivery directly to Archive for matches. Management credentials SHALL stay outside the gateway and ordinary mail runtime. Runtime credentials SHALL lack provider rights to change rules or override protected placement.

#### Scenario: Stalwart accepts an owner-authorized mail policy

- **WHEN** the independent management authority verifies an owner-signed update scoped to the exact provider account and binding
- **THEN** it commits the supported rules through provider-native controls
- **AND THEN** the provider files matching new arrivals directly in Archive, skipping Inbox even while the gateway is unavailable
- **AND THEN** prior messages retain their current folders when the provider accepts the update

#### Scenario: Provider authority falls short of protected placement

- **WHEN** the provider cannot match the configured sender and file directly in Archive on delivery, or the runtime credentials can change rules or override protected placement through any provider access path
- **THEN** the management path reports protected operation as unsupported
- **AND THEN** ordinary mailbox attachment and use remain available under their existing checks
- **AND THEN** the request leaves the provider's active rules and existing folder placement intact
