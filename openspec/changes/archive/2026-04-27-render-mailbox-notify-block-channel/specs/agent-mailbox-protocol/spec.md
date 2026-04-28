## MODIFIED Requirements

### Requirement: Sender-marked notification block extends the canonical envelope
The canonical mailbox message envelope SHALL include an optional `notify_block` field carrying short sender-authored text intended for prominent receiver-side rendering by the gateway notifier.

`notify_block` SHALL be a structured value with fields `text: str` and `placement: Literal["append", "prepend"]`. `placement` SHALL default to `"append"` when omitted. The field SHALL remain part of the immutable canonical envelope content. Per-recipient mailbox state (`read`, `answered`, `archived`) SHALL NOT extend to `notify_block`.

Senders MAY author the notification text inline in `body_markdown` using a Markdown fenced code block with the info-string `houmao-notify`. Canonical-message construction SHALL extract the first such fenced block in `body_markdown` into `notify_block.text`, after stripping leading and trailing whitespace inside the fence. The original fence and its contents SHALL remain in `body_markdown` unchanged.

When more than one `houmao-notify` fence appears in `body_markdown`, canonical-message construction SHALL extract only the first occurrence as identified by lowest source offset. Subsequent fences SHALL remain in `body_markdown` and SHALL NOT be appended to `notify_block.text`.

Callers MAY supply `notify_block` directly through composition surfaces in addition to or instead of the body fence. When a caller supplies `notify_block` directly, canonical-message construction SHALL use that supplied value and SHALL NOT re-extract from the body fence.

The system SHALL enforce the **auto-mirror invariant**: when canonical-message construction stores a non-null `notify_block`, the same text SHALL appear verbatim in `body_markdown` inside a `houmao-notify` fenced code block. When the caller supplies `notify_block` directly and `body_markdown` does not already contain a `houmao-notify` fence, canonical-message construction SHALL synthesize one and insert it at the position indicated by `notify_block.placement` (`"prepend"` places the fence before existing body content; `"append"` places it after). Synthetic insertion SHALL leave existing body content otherwise unchanged. When `body_markdown` already contains a `houmao-notify` fence, canonical-message construction SHALL NOT insert a duplicate; the existing fence position is preserved and `placement` records the caller's metadata declaration.

When canonical-message construction extracts `notify_block` from a body fence and the caller did not supply an explicit `placement`, the system SHALL default `notify_block.placement` to `"append"`. This default reflects metadata for downstream rendering; it does not relocate the existing fence inside `body_markdown`.

The text portion of `notify_block` SHALL be at most 512 characters. Content longer than 512 characters SHALL be truncated to 511 characters plus a single trailing `…` (U+2026) before storage. Truncation SHALL produce a visible canonical value rather than a silent drop.

An empty fenced block (no non-whitespace content between the fence markers) SHALL produce no `notify_block` field; canonical-message construction SHALL treat the field as absent rather than storing a structure with empty `text`.

`notify_block` SHALL be conceptually a *priority surface*, not a *covert channel*: any caller or downstream observer that reads `body_markdown` SHALL be able to find the same text inside the wrapped fence. This invariant exists so that future transports without a privileged out-of-band notification slot (Stalwart JMAP projection, plain SMTP-bridged delivery, RFC 5322 mail readers, archival exports) preserve the same content surface for non-Houmao-aware receivers.

#### Scenario: Body fence extracts to canonical notify_block with default placement
- **WHEN** a sender composes a canonical mailbox message with `body_markdown` containing one fenced block with info-string `houmao-notify`
- **THEN** the persisted canonical envelope sets `notify_block.text` to the trimmed fence contents and `notify_block.placement` to `"append"`
- **AND THEN** the persisted `body_markdown` still contains the original fenced block

#### Scenario: Multiple notify fences extract first occurrence only
- **WHEN** a sender composes a canonical mailbox message with `body_markdown` containing two fenced blocks with info-string `houmao-notify`
- **THEN** the persisted canonical envelope sets `notify_block.text` to the contents of the first fence
- **AND THEN** the contents of subsequent fences remain in `body_markdown` only and do not appear in `notify_block.text`

#### Scenario: Caller-supplied notify_block bypasses body extraction
- **WHEN** a composition caller supplies `notify_block` explicitly and `body_markdown` also contains a `houmao-notify` fence
- **THEN** the persisted canonical envelope uses the caller-supplied `text` and `placement`
- **AND THEN** the body fence content is not re-extracted on top of the caller-supplied value

#### Scenario: Auto-mirror appends synthetic fence when body has no fence
- **WHEN** a composition caller supplies `notify_block` with `text="continue current task"` and `placement="append"`
- **AND WHEN** `body_markdown` is `"Hello, please review."` and does not contain a `houmao-notify` fence
- **THEN** the persisted canonical envelope sets `notify_block.text="continue current task"` and `notify_block.placement="append"`
- **AND THEN** the persisted `body_markdown` is `"Hello, please review.\n\n` ` ` `houmao-notify\ncontinue current task\n` ` ` `"`

#### Scenario: Auto-mirror prepends synthetic fence when placement is prepend
- **WHEN** a composition caller supplies `notify_block` with `text="OPERATOR DIRECTIVE"` and `placement="prepend"`
- **AND WHEN** `body_markdown` is `"Hello, please review."` and does not contain a `houmao-notify` fence
- **THEN** the persisted `body_markdown` is `"` ` ` `houmao-notify\nOPERATOR DIRECTIVE\n` ` ` `\n\nHello, please review."`
- **AND THEN** the persisted `notify_block.placement` is `"prepend"`

#### Scenario: Auto-mirror does not duplicate an existing body fence
- **WHEN** a composition caller supplies `notify_block` with `text="X"` and `placement="prepend"`
- **AND WHEN** `body_markdown` already contains a `houmao-notify` fenced block
- **THEN** the persisted `body_markdown` is left unchanged
- **AND THEN** `notify_block.placement` records the caller's `"prepend"` declaration without relocating the existing fence

#### Scenario: Oversized notify_block content is truncated visibly
- **WHEN** a composition caller supplies `notify_block.text` longer than 512 characters
- **THEN** the persisted canonical envelope stores 511 characters of the original content followed by a single `…`
- **AND THEN** the truncation is visible in the stored field rather than silently dropped

#### Scenario: Empty notify fence produces no canonical notify_block
- **WHEN** a sender composes a canonical mailbox message with a `houmao-notify` fence that contains only whitespace
- **THEN** the persisted canonical envelope omits `notify_block`
- **AND THEN** the empty fence remains in `body_markdown` unchanged

#### Scenario: Receiver reading the body always sees the notify-block content
- **WHEN** a sender composes a canonical mailbox message with a non-null `notify_block`
- **AND WHEN** a receiver reads `body_markdown` through any transport-neutral mailbox surface
- **THEN** the receiver finds the same `notify_block.text` inside a `houmao-notify` fenced block in the body

### Requirement: Mailbox protocol version reflects the notify-aware canonical envelope
The system SHALL set `MAILBOX_PROTOCOL_VERSION` to `3` to reflect the typed `MailboxNotifyBlock` shape, the placement metadata, and the auto-mirror invariant.

Canonical envelopes that omit both `notify_block` and `notify_auth` SHALL remain valid under protocol version `3` because both fields are optional. Canonical-message validation under protocol version `3` SHALL reject envelopes whose `protocol_version` field does not match the current value.

Stored envelopes that originated under protocol version `1` and lack the new fields SHALL continue to be readable; readers SHALL treat absent `notify_block` and `notify_auth` fields as `None`. Envelopes that advertise `protocol_version=2` SHALL be rejected because the v2 string-shape `notify_block` was unreleased and is no longer accepted.

#### Scenario: Newly composed canonical envelope advertises protocol version 3
- **WHEN** the system composes a new canonical mailbox message
- **THEN** the persisted envelope records `protocol_version=3`
- **AND THEN** that value matches `MAILBOX_PROTOCOL_VERSION`

#### Scenario: Existing v1 canonical envelopes without notify fields remain valid
- **WHEN** a reader loads a canonical envelope authored under protocol version `1` that omits `notify_block` and `notify_auth`
- **THEN** the reader treats both fields as `None`
- **AND THEN** the rest of the envelope content is preserved unchanged

#### Scenario: Canonical envelopes advertising the wrong protocol version are rejected
- **WHEN** validation encounters a canonical envelope whose `protocol_version` field does not match `MAILBOX_PROTOCOL_VERSION`
- **THEN** validation rejects the envelope with an explicit protocol-version error
- **AND THEN** the system does not silently coerce the version field
