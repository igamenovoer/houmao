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

### Requirement: Operator-origin send accepts notification block and authentication metadata
Operator-origin mailbox delivery SHALL accept the canonical envelope's `notify_block` and `notify_auth` fields through the same composition contract as ordinary mailbox `send`.

`notify_block` SHALL be supplied as the structured `MailboxNotifyBlock` shape with `text` and `placement` fields. Operator-origin composition SHALL apply the canonical extraction-and-validation rules without divergence:

- when an operator-origin caller supplies `notify_block` directly, the system SHALL store the supplied `text` and `placement` subject to the canonical 512-character cap and visible-truncation rule on `text`,
- when an operator-origin caller supplies `notify_block` directly and the supplied `body_markdown` does not contain a `houmao-notify` fenced block, canonical-message construction SHALL synthesize one and insert it into `body_markdown` at the requested `placement` so the auto-mirror invariant holds for operator-origin messages identically to ordinary send,
- when an operator-origin caller supplies `body_markdown` containing a fenced code block with info-string `houmao-notify` and does not supply `notify_block` directly, the system SHALL extract the first such fence into `notify_block.text` per the canonical rules and default `notify_block.placement` to `"append"`,
- the system SHALL accept `notify_auth.scheme="none"` and SHALL reject other `scheme` values per the canonical validation rules.

Operator-origin canonical messages SHALL preserve `notify_block` and `notify_auth` through the existing operator-origin provenance and reply-policy metadata without change to those policies.

#### Scenario: Operator-origin send accepts a caller-supplied notify_block and auto-mirrors into the body
- **WHEN** an operator-origin caller composes a message with `notify_block.text="continue current task"`, `notify_block.placement="append"`, `notify_auth.scheme="none"`, and `body_markdown="Operator note inline."`
- **THEN** the resulting operator-origin canonical message preserves `notify_block` and `notify_auth` immutably
- **AND THEN** the persisted `body_markdown` contains both the original `"Operator note inline."` and an appended `houmao-notify` fenced block whose contents match `notify_block.text`
- **AND THEN** the message remains identifiable through operator-origin provenance metadata

#### Scenario: Operator-origin send extracts a houmao-notify body fence with default placement
- **WHEN** an operator-origin caller composes a message with `body_markdown` containing one fenced code block with info-string `houmao-notify`
- **AND WHEN** the caller does not supply `notify_block` directly
- **THEN** the resulting operator-origin canonical message sets `notify_block.text` to the trimmed fence contents and `notify_block.placement` to `"append"`
- **AND THEN** the persisted `body_markdown` still contains the original fenced block

#### Scenario: Operator-origin send rejects unsupported notify_auth schemes
- **WHEN** an operator-origin caller composes a message with `notify_auth.scheme` set to `shared-token`, `hmac-sha256`, or `jws`
- **THEN** the system rejects the operator-origin send with an explicit "verifier not yet supported" error
- **AND THEN** the system does not persist a partial operator-origin canonical message

