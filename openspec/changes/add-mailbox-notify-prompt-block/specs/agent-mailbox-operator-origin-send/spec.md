## ADDED Requirements

### Requirement: Operator-origin send accepts notification block and authentication metadata
Operator-origin mailbox delivery SHALL accept the canonical envelope's `notify_block` and `notify_auth` fields through the same composition contract as ordinary mailbox `send`.

Operator-origin composition SHALL apply the canonical extraction-and-validation rules without divergence:

- when an operator-origin caller supplies `notify_block` directly, the system SHALL store that value subject to the canonical 512-character cap and visible-truncation rule,
- when an operator-origin caller supplies `body_markdown` containing a fenced code block with info-string `houmao-notify` and does not supply `notify_block` directly, the system SHALL extract the first such fence into `notify_block` per the canonical rules,
- the system SHALL accept `notify_auth.scheme="none"` and SHALL reject other `scheme` values per the canonical validation rules.

Operator-origin canonical messages SHALL preserve `notify_block` and `notify_auth` through the existing operator-origin provenance and reply-policy metadata without change to those policies.

#### Scenario: Operator-origin send accepts a caller-supplied notify_block
- **WHEN** an operator-origin caller composes a message with `notify_block` supplied directly and `notify_auth.scheme="none"`
- **THEN** the resulting operator-origin canonical message preserves `notify_block` and `notify_auth` immutably
- **AND THEN** the message remains identifiable through operator-origin provenance metadata

#### Scenario: Operator-origin send extracts a houmao-notify body fence
- **WHEN** an operator-origin caller composes a message with `body_markdown` containing one fenced code block with info-string `houmao-notify`
- **AND WHEN** the caller does not supply `notify_block` directly
- **THEN** the resulting operator-origin canonical message sets `notify_block` to the trimmed fence contents
- **AND THEN** the persisted `body_markdown` still contains the original fenced block

#### Scenario: Operator-origin send rejects unsupported notify_auth schemes
- **WHEN** an operator-origin caller composes a message with `notify_auth.scheme` set to `shared-token`, `hmac-sha256`, or `jws`
- **THEN** the system rejects the operator-origin send with an explicit "verifier not yet supported" error
- **AND THEN** the system does not persist a partial operator-origin canonical message
