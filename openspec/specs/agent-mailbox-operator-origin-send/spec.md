# agent-mailbox-operator-origin-send Specification

## Purpose
Define operator-origin mailbox delivery semantics for managed-agent mailboxes.
## Requirements
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

### Requirement: Operator-origin mailbox delivery is filesystem-only in v1
In v1, operator-origin mailbox delivery SHALL be supported only for the filesystem mailbox transport.

When the resolved mailbox transport is not `filesystem`, the system SHALL fail the operator-origin request explicitly instead of pretending transport parity.

#### Scenario: Stalwart mailbox rejects operator-origin delivery in v1
- **WHEN** a caller requests operator-origin mailbox delivery for a managed agent whose resolved mailbox transport is `stalwart`
- **THEN** the system rejects that request explicitly as unsupported for the current transport
- **AND THEN** it does not attempt to synthesize a fake operator sender inside the Stalwart transport

### Requirement: Operator-origin mailbox delivery accepts replies by default and carries explicit provenance
Operator-origin mailbox delivery SHALL carry explicit provenance metadata and explicit reply-policy metadata in v1.

Supported operator-origin reply policies SHALL include at minimum:

- `none`,
- `operator_mailbox`.

New operator-origin mailbox messages created without an explicit reply policy SHALL use `operator_mailbox`.

When the operator-origin reply policy is `operator_mailbox`, reply flows against that operator-origin message SHALL target the reserved operator mailbox `HOUMAO-operator@houmao.localhost`.

When the operator-origin reply policy is explicitly `none`, reply flows against that operator-origin message SHALL fail explicitly rather than being routed to a hidden operator inbox or dropped silently.

Stored operator-origin messages with missing, malformed, or unrecognized reply-policy metadata SHALL continue to resolve as `none`.

Messages created through either reply policy SHALL remain identifiable through explicit operator-origin provenance metadata.

#### Scenario: Default operator-origin message routes replies to the reserved operator mailbox
- **WHEN** a caller creates an operator-origin mailbox message without specifying a reply policy
- **THEN** the resulting message records `x-houmao-reply-policy: operator_mailbox`
- **AND THEN** its `reply_to` targets `HOUMAO-operator@houmao.localhost`
- **AND THEN** a later mailbox `reply` against that message is accepted as a reply to the reserved operator mailbox

#### Scenario: Explicit no-reply operator-origin message still rejects replies
- **WHEN** a caller creates an operator-origin mailbox message with reply policy `none`
- **THEN** a later mailbox `reply` against that message is rejected explicitly
- **AND THEN** it does not silently route that reply into `HOUMAO-operator@houmao.localhost`

#### Scenario: Legacy missing policy remains no-reply
- **WHEN** a reader or tool inspects an older operator-origin message whose headers do not explicitly carry `x-houmao-reply-policy: operator_mailbox`
- **THEN** the message resolves as no-reply
- **AND THEN** the system does not retroactively reinterpret that stored message as reply-enabled

#### Scenario: Reply-enabled operator-origin message remains explicitly identifiable
- **WHEN** a reader or tool inspects an operator-origin message whose reply policy is `operator_mailbox`
- **THEN** the message still carries explicit operator-origin provenance metadata
- **AND THEN** the reply-enabled policy does not cause the message to masquerade as ordinary mailbox participation

