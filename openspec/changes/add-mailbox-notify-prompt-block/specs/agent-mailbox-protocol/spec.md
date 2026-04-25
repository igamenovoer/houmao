## MODIFIED Requirements

### Requirement: Canonical mailbox message envelope
The system SHALL preserve transport-neutral mailbox message semantics in a canonical model that includes at minimum:

- `message_id`
- `thread_id`
- `created_at_utc`
- sender identity
- recipient identities
- `subject`
- `body_markdown`
- attachment metadata
- extensible protocol headers
- optional `notify_block` carrying sender-marked notification text intended for prominent receiver-side rendering
- optional `notify_auth` carrying sender-supplied authentication metadata associated with `notify_block`

For transports that persist Houmao-owned canonical content, that canonical envelope SHALL be immutable after delivery except for transport-local projection metadata that is explicitly outside the canonical message content.

In v1, filesystem-backed canonical `message_id` values SHALL use the format `msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}`.

Shared mailbox operation surfaces used by runtime and gateway callers SHALL identify messages through transport-neutral references rather than requiring callers to understand transport-local storage ids.

The shared mailbox operation contract for this change SHALL include at minimum:

- opaque plain-string `message_ref`
- optional `thread_ref`
- `created_at_utc`
- sender identity
- recipient identities
- `subject`
- body content or body preview appropriate to the operation
- attachment metadata
- unread state when returned from `check`

The system SHALL preserve the logical mailbox semantics across transports, but it SHALL NOT require every transport to persist a Houmao-authored canonical document or to expose Houmao-generated identifiers as the public operation contract.

The system SHALL represent `message_ref` as a plain string in the shared gateway and runtime mailbox contracts. Callers SHALL treat the entire value as opaque and SHALL NOT derive behavior from transport-specific prefixes, encodings, or storage identifiers embedded inside that string.

Adapters MAY use transport-prefixed string encodings in v1 when that keeps later `reply` targeting stateless, provided the caller-visible contract still treats the whole value as an opaque string handle.

For the filesystem transport, shared mailbox operation refs MAY be derived from the existing canonical message ids and thread ids.

For non-filesystem mailbox transports such as `stalwart`, shared mailbox operation refs MAY be derived from transport-owned message identities, provided they still preserve stable reply targeting and transport-neutral ancestry semantics for Houmao mailbox operations.

When `notify_block` or `notify_auth` are present in a canonical envelope, transports that persist Houmao-owned canonical content SHALL preserve those fields immutably alongside the rest of the envelope. Transports that project the canonical envelope into transport-native shapes (for example `stalwart`) SHALL preserve the same fields through their existing canonical-content projection path.

#### Scenario: New root message receives a canonical envelope
- **WHEN** a sender creates a new mailbox message that does not reply to an earlier message
- **THEN** the system stores a canonical envelope containing all required fields
- **AND THEN** the stored root message uses its own `message_id` as the `thread_id`

#### Scenario: Reply message preserves canonical ancestry
- **WHEN** a sender replies to an existing mailbox message
- **THEN** the system stores a new canonical envelope with a new `message_id`
- **AND THEN** the new envelope sets `in_reply_to` to the direct parent message id
- **AND THEN** the new envelope preserves the existing thread by reusing the parent `thread_id`

#### Scenario: Generated message id uses timestamp plus UUID4 suffix
- **WHEN** the system creates a new canonical mailbox message
- **THEN** the generated `message_id` matches the v1 format `msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}`
- **AND THEN** that identifier remains suitable for canonical filesystem storage and future email `Message-ID` projection

#### Scenario: Filesystem transport exposes shared message references without exposing SQLite storage details
- **WHEN** a caller performs a shared mailbox operation against the filesystem transport
- **THEN** the transport returns stable `message_ref` values suitable for later `reply` targeting
- **AND THEN** the caller does not need to understand mailbox-local SQLite row identities or other transport-local storage details

#### Scenario: Stalwart-backed transport exposes reply-capable shared message references
- **WHEN** the `stalwart` mailbox transport creates or reads a mailbox message through the shared mailbox operation contract
- **THEN** the transport returns a stable `message_ref` suitable for later `reply` targeting
- **AND THEN** the caller does not need to understand Stalwart-native object shapes to continue the mailbox workflow

#### Scenario: Canonical envelope carrying notify_block survives transport persistence
- **WHEN** a sender composes a canonical mailbox message with a non-empty `notify_block`
- **THEN** the persisted canonical envelope preserves `notify_block` immutably alongside `body_markdown`
- **AND THEN** later peek and read flows return the same `notify_block` value

#### Scenario: Canonical envelope carrying notify_auth survives transport persistence
- **WHEN** a sender composes a canonical mailbox message with a non-null `notify_auth`
- **THEN** the persisted canonical envelope preserves `notify_auth` immutably alongside `notify_block`
- **AND THEN** later peek and read flows return the same `notify_auth` value

## ADDED Requirements

### Requirement: Sender-marked notification block extends the canonical envelope
The canonical mailbox message envelope SHALL include an optional `notify_block` string field carrying short sender-authored text intended for prominent receiver-side rendering by future notification surfaces.

`notify_block` SHALL remain part of the immutable canonical envelope content. Per-recipient mailbox state (`read`, `answered`, `archived`) SHALL NOT extend to `notify_block`.

Senders MAY author the notification text inline in `body_markdown` using a Markdown fenced code block with the info-string `houmao-notify`. Canonical-message construction SHALL extract the first such fenced block in `body_markdown` into `notify_block`, after stripping leading and trailing whitespace inside the fence. The original fence and its contents SHALL remain in `body_markdown` unchanged.

When more than one `houmao-notify` fence appears in `body_markdown`, canonical-message construction SHALL extract only the first occurrence as identified by lowest source offset. Subsequent fences SHALL remain in `body_markdown` and SHALL NOT be appended to `notify_block`.

Callers MAY supply `notify_block` directly through composition surfaces in addition to or instead of the body fence. When a caller supplies `notify_block` directly, canonical-message construction SHALL use that value and SHALL NOT re-extract from the body fence.

Extracted or caller-supplied `notify_block` content SHALL be at most 512 characters. Content longer than 512 characters SHALL be truncated to 511 characters plus a single trailing `…` (U+2026) before storage. Truncation SHALL produce a visible canonical value rather than a silent drop.

An empty fenced block (no non-whitespace content between the fence markers) SHALL produce no `notify_block` field; canonical-message construction SHALL treat the field as absent rather than storing an empty string.

#### Scenario: Body fence extracts to canonical notify_block
- **WHEN** a sender composes a canonical mailbox message with `body_markdown` containing one fenced block with info-string `houmao-notify`
- **THEN** the persisted canonical envelope sets `notify_block` to the trimmed fence contents
- **AND THEN** the persisted `body_markdown` still contains the original fenced block

#### Scenario: Multiple notify fences extract first occurrence only
- **WHEN** a sender composes a canonical mailbox message with `body_markdown` containing two fenced blocks with info-string `houmao-notify`
- **THEN** the persisted canonical envelope sets `notify_block` to the contents of the first fence
- **AND THEN** the contents of subsequent fences remain in `body_markdown` only and do not appear in `notify_block`

#### Scenario: Caller-supplied notify_block bypasses body extraction
- **WHEN** a composition caller supplies `notify_block` explicitly and `body_markdown` also contains a `houmao-notify` fence
- **THEN** the persisted canonical envelope uses the caller-supplied value for `notify_block`
- **AND THEN** the body fence content is not re-extracted on top of the caller-supplied value

#### Scenario: Oversized notify_block content is truncated visibly
- **WHEN** a composition caller supplies `notify_block` content longer than 512 characters
- **THEN** the persisted canonical envelope stores 511 characters of the original content followed by a single `…`
- **AND THEN** the truncation is visible in the stored field rather than silently dropped

#### Scenario: Empty notify fence produces no canonical notify_block
- **WHEN** a sender composes a canonical mailbox message with a `houmao-notify` fence that contains only whitespace
- **THEN** the persisted canonical envelope omits `notify_block`
- **AND THEN** the empty fence remains in `body_markdown` unchanged

### Requirement: Notification authentication metadata travels with notification blocks
The canonical mailbox message envelope SHALL include an optional `notify_auth` field carrying sender-supplied authentication metadata associated with `notify_block`.

`notify_auth` SHALL be a structured value with fields `scheme`, `token`, `iss`, `iat`, and `exp`. `scheme` SHALL be one of `none`, `shared-token`, `hmac-sha256`, or `jws`. `token`, `iss`, `iat`, and `exp` SHALL each be optional strings.

In this change, canonical-message validation SHALL accept only `scheme="none"`. Validation SHALL reject any other `scheme` value with an explicit "verifier not yet supported" error and SHALL NOT silently accept or normalize the rejected value.

The presence of the `scheme`, `shared-token`, `hmac-sha256`, and `jws` enum members in the protocol SHALL serve as forward-compatibility for follow-on verifier work and SHALL NOT cause this change to ship any verifier behavior.

`notify_auth` MAY be present without `notify_block`, but transports and downstream consumers SHALL treat such envelopes as carrying authentication metadata that has no notification block to authenticate.

#### Scenario: notify_auth with scheme none is accepted at validation
- **WHEN** a composition caller supplies `notify_auth` with `scheme="none"` and any combination of optional `token`, `iss`, `iat`, and `exp`
- **THEN** canonical-message validation accepts the message
- **AND THEN** the persisted canonical envelope preserves the supplied `notify_auth` value immutably

#### Scenario: notify_auth with scheme other than none is rejected at validation
- **WHEN** a composition caller supplies `notify_auth` with `scheme` set to `shared-token`, `hmac-sha256`, or `jws`
- **THEN** canonical-message validation rejects the message with an explicit "verifier not yet supported" error
- **AND THEN** the system does not persist the canonical envelope

#### Scenario: notify_auth without notify_block is preserved
- **WHEN** a composition caller supplies `notify_auth` with `scheme="none"` and no `notify_block`
- **THEN** the persisted canonical envelope preserves the supplied `notify_auth`
- **AND THEN** transports and downstream consumers see authentication metadata with no associated notification block

### Requirement: Mailbox protocol version reflects the notify-aware canonical envelope
The system SHALL set `MAILBOX_PROTOCOL_VERSION` to `2` to reflect the addition of the `notify_block` and `notify_auth` canonical envelope fields.

Canonical envelopes that omit both `notify_block` and `notify_auth` SHALL remain valid under protocol version `2` because both fields are optional. Stored envelopes that originated under protocol version `1` and lack the new fields SHALL continue to be readable; readers SHALL treat absent `notify_block` and `notify_auth` fields as `None`.

Canonical-message validation under protocol version `2` SHALL reject envelopes whose `protocol_version` field does not match the current value.

#### Scenario: Newly composed canonical envelope advertises protocol version 2
- **WHEN** the system composes a new canonical mailbox message
- **THEN** the persisted envelope records `protocol_version=2`
- **AND THEN** that value matches `MAILBOX_PROTOCOL_VERSION`

#### Scenario: Existing canonical envelopes without notify fields remain valid
- **WHEN** a reader loads a canonical envelope authored before this change that omits `notify_block` and `notify_auth`
- **THEN** the reader treats both fields as `None`
- **AND THEN** the rest of the envelope content is preserved unchanged

#### Scenario: Canonical envelopes advertising the wrong protocol version are rejected
- **WHEN** validation encounters a canonical envelope whose `protocol_version` field does not match `MAILBOX_PROTOCOL_VERSION`
- **THEN** validation rejects the envelope with an explicit protocol-version error
- **AND THEN** the system does not silently coerce the version field
