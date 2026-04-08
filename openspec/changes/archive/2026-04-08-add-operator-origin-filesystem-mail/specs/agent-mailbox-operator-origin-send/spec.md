## ADDED Requirements

### Requirement: Operator-origin mailbox delivery uses the reserved Houmao system sender
The system SHALL support a distinct operator-origin mailbox delivery capability for filesystem-backed managed-agent mailboxes.

Operator-origin delivery SHALL remain distinct from ordinary mailbox `send` behavior:

- ordinary `send` continues to compose and deliver mail as the managed mailbox principal,
- operator-origin delivery composes and delivers one message from the reserved Houmao system sender `HOUMAO-operator@houmao.localhost`,
- the recipient remains the addressed managed-agent mailbox principal.

Operator-origin delivery SHALL preserve a real canonical sender principal rather than using anonymous or fake sender metadata.

#### Scenario: Operator-origin delivery uses the reserved Houmao sender
- **WHEN** an operator-origin mailbox action delivers a note to managed agent `research`
- **THEN** the resulting canonical mailbox message uses `from = HOUMAO-operator@houmao.localhost`
- **AND THEN** the recipient remains the mailbox principal bound to `research@houmao.localhost`
- **AND THEN** the operation is distinguishable from ordinary mailbox `send`

### Requirement: Operator-origin mailbox delivery is one-way and carries explicit provenance
Operator-origin mailbox delivery SHALL be a one-way mailbox capability in v1.

Messages created through that capability SHALL carry explicit provenance metadata indicating Houmao operator origin and no-reply semantics.

Reply flows against operator-origin messages SHALL fail explicitly rather than being routed to a hidden operator inbox or dropped silently.

#### Scenario: Reply to operator-origin message is rejected explicitly
- **WHEN** a caller attempts mailbox `reply` against a previously delivered operator-origin message
- **THEN** the system rejects that reply explicitly
- **AND THEN** it does not deliver a reply into `HOUMAO-operator@houmao.localhost`
- **AND THEN** the operator-origin message remains identifiable through explicit provenance metadata

### Requirement: Operator-origin mailbox delivery is filesystem-only in v1
In v1, operator-origin mailbox delivery SHALL be supported only for the filesystem mailbox transport.

When the resolved mailbox transport is not `filesystem`, the system SHALL fail the operator-origin request explicitly instead of pretending transport parity.

#### Scenario: Stalwart mailbox rejects operator-origin delivery in v1
- **WHEN** a caller requests operator-origin mailbox delivery for a managed agent whose resolved mailbox transport is `stalwart`
- **THEN** the system rejects that request explicitly as unsupported for the current transport
- **AND THEN** it does not attempt to synthesize a fake operator sender inside the Stalwart transport

