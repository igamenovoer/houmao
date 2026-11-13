# Spec Delta

## MODIFIED Requirements

### Requirement: Shared gateway mailbox facade exposes lifecycle routes
For loopback-bound gateways, the shared mailbox facade SHALL expose `GET /v1/mail/status` as a summary of both optional bindings and the derived canonical mail identity. Mailbox-disabled agents SHALL receive a normal empty-binding summary.

The gateway SHALL expose channel-selected lifecycle routes under `/v1/mail/{channel}/` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, where `channel` is `offline` or `online`. The former unqualified lifecycle routes SHALL NOT infer a channel from the canonical mail identity.

List SHALL return triage metadata without marking read. Peek SHALL return selected content without changing read state. Read SHALL return content and mark read. Mark SHALL support recipient-local read/answered state. Move SHALL update supported boxes. Archive SHALL close inbox work through the selected backend.

All lifecycle requests SHALL identify their expected binding ID, obtained from status or current round context, and use runtime-owned authority and scoped references. A replaced binding SHALL fail explicitly even for send/post requests without a message reference. Unsupported operations, absent bindings, and backend failures SHALL be explicit. Callers SHALL NOT need filesystem indexes, mailbox scripts, or provider-native objects. Mail operations SHALL retain the existing loopback listener policy.

#### Scenario: Peek does not mutate read state through the gateway
- **WHEN** a caller peeks through the selected channel using a matching scoped reference
- **THEN** it receives that message's content without changing recipient read state

#### Scenario: Read mutates read state through the gateway
- **WHEN** a caller reads through the selected channel using a matching scoped reference
- **THEN** it receives that message's content and read state becomes true for that mailbox owner

#### Scenario: Archive shortcut remains available
- **WHEN** a caller archives selected references through their matching channel
- **THEN** the selected backend reports them archived and no longer open inbox work

#### Scenario: Channel omission does not use canonical precedence
- **WHEN** a caller uses an unqualified lifecycle operation without selecting a channel
- **THEN** the request fails explicitly instead of selecting the preferred online address

#### Scenario: Empty status remains readable
- **WHEN** an agent has no offline or online binding
- **THEN** summary status reports both slots absent and no canonical mail identity
- **AND THEN** ordinary core status and control remain available

#### Scenario: A new send pins its intended mailbox
- **WHEN** an account is replaced after a caller observes its binding ID but before a send begins
- **THEN** the send fails with a binding conflict
- **AND THEN** it is not submitted from the replacement account

### Requirement: Gateway reply marks the parent message answered
When a channel-selected gateway reply succeeds, the adapter SHALL mark the parent message `answered=true` and `read=true` for the owning mailbox. Reply SHALL preserve originating channel and binding scope and SHALL NOT archive the parent message.

#### Scenario: Gateway reply acknowledges without closing the mail
- **WHEN** a caller replies through the matching channel and binding
- **THEN** the parent becomes read and answered for that owner
- **AND THEN** it remains open inbox work until archive or a closing move succeeds
