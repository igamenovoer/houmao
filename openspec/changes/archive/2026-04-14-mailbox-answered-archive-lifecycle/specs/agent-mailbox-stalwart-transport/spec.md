## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Stalwart-backed mailbox transport supports the shared mailbox operation set
**Reason**: The previous operation set was intentionally limited to status, `check`, `send`, and `reply`; the lifecycle design requires common read, answered, move, and archive behavior across filesystem and Stalwart transports.
**Migration**: No compatibility migration is required. Callers must use the expanded shared lifecycle operation names and payloads.
