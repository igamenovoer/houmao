## ADDED Requirements

### Requirement: Gateway operator-origin post defaults to operator mailbox replies
`POST /v1/mail/post` SHALL default omitted `reply_policy` fields to `operator_mailbox`.

The gateway mailbox post request model SHALL continue to accept explicit `reply_policy` values of `none` and `operator_mailbox`.

When `reply_policy` is omitted or set to `operator_mailbox`, the created operator-origin message SHALL record reply-enabled policy metadata and route replies to `HOUMAO-operator@houmao.localhost`.

When `reply_policy` is explicitly set to `none`, the created operator-origin message SHALL remain no-reply and later replies against that message SHALL fail explicitly.

Pair-managed mail-post proxy request models that inherit the live gateway mailbox post model SHALL preserve this same omitted-field default.

#### Scenario: Direct gateway post omitted policy creates a reply-enabled message
- **WHEN** a caller posts to `/v1/mail/post` with subject and body but without `reply_policy`
- **THEN** the gateway creates an operator-origin message with reply policy `operator_mailbox`
- **AND THEN** a later `/v1/mail/reply` against that message is accepted and routed to `HOUMAO-operator@houmao.localhost`

#### Scenario: Direct gateway explicit no-reply policy is honored
- **WHEN** a caller posts to `/v1/mail/post` with `reply_policy` set to `none`
- **THEN** the gateway creates an operator-origin message with no-reply policy metadata
- **AND THEN** a later `/v1/mail/reply` against that message fails explicitly

#### Scenario: Pair-managed proxy preserves gateway post default
- **WHEN** a pair-managed caller posts operator-origin mail without `reply_policy`
- **THEN** the pair-managed proxy forwards a request that resolves to the gateway's `operator_mailbox` default
- **AND THEN** the resulting message has the same reply-enabled behavior as direct `/v1/mail/post`
