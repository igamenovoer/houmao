## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Operator-origin mailbox delivery is one-way and carries explicit provenance
**Reason**: Operator-origin notes now default to reply-enabled behavior so managed agents can answer the operator without requiring the sender to remember an opt-in flag.

**Migration**: Use `reply_policy=none` when a one-way operator-origin note is required. Existing delivered messages keep their stored headers and continue to follow their recorded or conservatively inferred reply policy.
