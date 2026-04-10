## MODIFIED Requirements

### Requirement: Operator-origin mailbox delivery is one-way and carries explicit provenance
Operator-origin mailbox delivery SHALL carry explicit provenance metadata and explicit reply-policy metadata in v1.

Supported operator-origin reply policies SHALL include at minimum:

- `none`,
- `operator_mailbox`.

When the operator-origin reply policy is `none`, reply flows against that operator-origin message SHALL fail explicitly rather than being routed to a hidden operator inbox or dropped silently.

When the operator-origin reply policy is `operator_mailbox`, reply flows against that operator-origin message SHALL target the reserved operator mailbox `HOUMAO-operator@houmao.localhost`.

Messages created through either reply policy SHALL remain identifiable through explicit operator-origin provenance metadata.

#### Scenario: Default operator-origin message still rejects reply explicitly
- **WHEN** a caller attempts mailbox `reply` against a previously delivered operator-origin message whose reply policy is `none`
- **THEN** the system rejects that reply explicitly
- **AND THEN** it does not silently route that reply into `HOUMAO-operator@houmao.localhost`

#### Scenario: Reply-enabled operator-origin message routes reply to the reserved operator mailbox
- **WHEN** a caller attempts mailbox `reply` against a previously delivered operator-origin message whose reply policy is `operator_mailbox`
- **THEN** the system accepts that reply as a reply to the reserved operator mailbox
- **AND THEN** it does not require the caller to synthesize a fresh unrelated mailbox send action

#### Scenario: Reply-enabled operator-origin message remains explicitly identifiable
- **WHEN** a reader or tool inspects an operator-origin message whose reply policy is `operator_mailbox`
- **THEN** the message still carries explicit operator-origin provenance metadata
- **AND THEN** the reply-enabled policy does not cause the message to masquerade as ordinary mailbox participation
