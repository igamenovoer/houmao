## Purpose
Define the canonical mailbox message model, addressing rules, threading, attachments, and recipient-state semantics shared across mailbox transports.
## Requirements
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

### Requirement: Principal-based mailbox addressing
The system SHALL address mailbox participants by mailbox principal rather than by a transient session handle.

Each mailbox principal SHALL include:
- a stable `principal_id`, and
- an email-like address suitable for the selected transport.

For agent participants, the system SHALL use the canonical `HOUMAO-...` agent identity as the default `principal_id` unless an explicit mailbox binding overrides it.

#### Scenario: Agent mailbox uses canonical agent identity
- **WHEN** an agent participant with canonical identity `HOUMAO-research` is registered for mailbox delivery
- **THEN** the system addresses that participant using `principal_id=HOUMAO-research`
- **AND THEN** outbound mailbox messages preserve the participant's configured email-like address separately from any live session manifest path

#### Scenario: Human mailbox uses the same principal model
- **WHEN** a human participant is registered for mailbox delivery
- **THEN** the system assigns that participant a stable mailbox principal
- **AND THEN** messages to or from that participant use the same canonical sender and recipient fields as agent participants

### Requirement: Explicit thread ancestry
The system SHALL model threading explicitly with `thread_id`, `in_reply_to`, and `references` fields and SHALL NOT rely on subject-line heuristics as the authoritative thread identity.

#### Scenario: Subject changes do not break thread identity
- **WHEN** a sender replies to a message and changes the visible subject text
- **THEN** the system keeps the reply in the existing thread when `thread_id` and `in_reply_to` point to that thread
- **AND THEN** the changed subject text does not create a new thread by itself

#### Scenario: New thread starts with explicit root identity
- **WHEN** a sender starts a fresh conversation about a similar topic
- **THEN** the system creates a new message with a new `message_id`
- **AND THEN** the new message starts a new thread by setting `thread_id` to that new message id

### Requirement: Attachment references carry stable metadata
The system SHALL support mailbox attachments as structured references with stable metadata rather than requiring all transports to embed binary payloads inline.

Each attachment entry SHALL include:

- `attachment_id`
- attachment kind
- media type
- size metadata when available
- digest metadata when available
- a transport-appropriate local reference, managed-store locator, or transport-owned attachment locator

The mailbox protocol SHALL NOT require every transport to preserve a local absolute path reference after delivery.

#### Scenario: Path-reference attachment is preserved in the canonical message
- **WHEN** a sender attaches an existing local file by reference through the filesystem mailbox transport
- **THEN** the system records that attachment in the canonical message as a reference attachment
- **AND THEN** the recorded attachment metadata includes the referenced path and available file metadata

#### Scenario: Managed-copy attachment remains addressable
- **WHEN** a sender chooses managed attachment storage for a mailbox message
- **THEN** the system records the attachment as a managed-copy attachment in the canonical message
- **AND THEN** recipients can resolve the attachment through the managed-store locator recorded in that metadata

#### Scenario: Stalwart-backed transport replaces local composition paths with transport-owned attachment metadata
- **WHEN** a sender attaches a local file and delivers the message through the `stalwart` transport
- **THEN** the transport uploads or materializes that attachment through server-backed mail storage
- **AND THEN** the delivered attachment metadata is allowed to preserve the transport-owned attachment locator instead of the original local composition path

### Requirement: Per-recipient mailbox state is separate from immutable message content
The system SHALL track per-recipient mailbox state separately from canonical message content.

Per-recipient mailbox state SHALL include at minimum unread or read state and MAY include additional mailbox state such as starred, archived, or deleted markers.

#### Scenario: Marking a message read does not rewrite canonical content
- **WHEN** a recipient marks a delivered message as read
- **THEN** the system updates only that recipient's mailbox state
- **AND THEN** the canonical message envelope and body content remain unchanged

#### Scenario: Different recipients keep different mailbox state
- **WHEN** a message is delivered to multiple recipients
- **THEN** one recipient can mark the message read while another leaves it unread
- **AND THEN** the system preserves those mailbox states independently per recipient

### Requirement: Recipients can consume mailbox work asynchronously
The system SHALL make newly delivered messages discoverable through recipient-specific unread mailbox state so agents and humans can participate asynchronously.

#### Scenario: Agent poller finds new unread message
- **WHEN** an unread mailbox message is delivered to an agent principal
- **THEN** the system exposes that message through the recipient's unread mailbox view
- **AND THEN** an agent poller can discover it without requiring a synchronous sender-recipient rendezvous

#### Scenario: Human participant resumes the same conversation later
- **WHEN** a human participant returns to a mailbox thread after the original message delivery time
- **THEN** the system preserves the full message thread and the participant's mailbox state
- **AND THEN** the human can read or reply within the same thread asynchronously

### Requirement: Default managed mailbox addresses use `houmao.localhost` and reserve `HOUMAO-*`
The system SHALL derive new default managed-agent mailbox addresses as `<agentname>@houmao.localhost`.

Mailbox local parts beginning with `HOUMAO-` SHALL be reserved for Houmao-owned system principals rather than ordinary managed-agent or human-participant defaults.

The reserved namespace SHALL include `HOUMAO-operator@houmao.localhost`.

This requirement changes the default address-derivation policy only. Explicit mailbox bindings that already use another valid address remain valid unless later reconfigured.

#### Scenario: New managed agent derives a human-readable Houmao mailbox address
- **WHEN** the system derives the default mailbox address for managed agent `research`
- **THEN** the derived default address is `research@houmao.localhost`
- **AND THEN** the principal id remains independently tracked from that email-like address

#### Scenario: Reserved `HOUMAO-*` mailbox local part is rejected for ordinary agent naming
- **WHEN** an ordinary managed-agent mailbox binding or default-address derivation would produce `HOUMAO-alpha@houmao.localhost`
- **THEN** the system rejects that ordinary participant address as reserved for Houmao-owned system principals
- **AND THEN** only Houmao-owned reserved principals may use the `HOUMAO-*` mailbox local-part namespace

### Requirement: Shared mailbox lifecycle state separates read, answered, and archived semantics
The shared mailbox protocol SHALL distinguish message visibility from task completion.

Per-recipient mailbox state exposed through runtime-owned and gateway-owned mailbox surfaces SHALL include at minimum:

- `read`, meaning the recipient consumed the message body through a mutating read workflow or explicitly marked it read,
- `answered`, meaning the recipient replied to or acknowledged the message,
- `archived`, meaning the recipient moved the message out of the open inbox workflow into archive,
- the current mailbox box or boxes for that recipient.

The shared protocol SHALL NOT treat `read=true` or `answered=true` as completion. A message remains open work while it is in the recipient inbox and is not archived or otherwise closed.

#### Scenario: Acknowledged mail remains open until archived
- **WHEN** an agent replies to a mailbox message with an acknowledgement before completing the requested work
- **THEN** the parent message is marked `answered=true`
- **AND THEN** the parent message remains open inbox work until the agent archives it

#### Scenario: Reading mail does not close it
- **WHEN** a recipient reads a mailbox message body
- **THEN** the recipient-local state records `read=true`
- **AND THEN** the message remains open inbox work unless it has also been archived or moved out of the inbox workflow

### Requirement: Shared mailbox operations support list, peek, read, mark, move, and archive
The shared mailbox operation contract exposed through runtime-owned and gateway-owned mailbox surfaces SHALL include transport-neutral operations for:

- listing messages from a named mailbox box,
- peeking a message body without mutating read state,
- reading a message body while marking it read,
- manually marking supported recipient-local state fields,
- moving messages among supported mailbox boxes,
- archiving selected messages as a shortcut for moving them to the archive box.

All operations that target existing messages SHALL use opaque plain-string `message_ref` values. Callers SHALL treat the entire value as opaque and SHALL NOT derive behavior from transport-specific prefixes, paths, encodings, or storage identifiers.

The shared archive operation SHALL accept one or more opaque message references, SHALL move those messages to the recipient archive box, SHALL mark them archived, and SHALL mark them read by default. It SHALL NOT mark them answered unless a separate reply or mark operation did so.

#### Scenario: Peek returns content without marking read
- **WHEN** a caller peeks a mailbox message through the shared mailbox operation contract
- **THEN** the operation returns the selected message body and metadata
- **AND THEN** recipient-local `read` state for that message does not change

#### Scenario: Read returns content and marks read
- **WHEN** a caller reads a mailbox message through the shared mailbox operation contract
- **THEN** the operation returns the selected message body and metadata
- **AND THEN** recipient-local `read` state for that message is set to `true`

#### Scenario: Archive closes selected inbox work
- **WHEN** a caller archives selected inbox messages by opaque `message_ref`
- **THEN** the messages are moved to the recipient archive box
- **AND THEN** recipient-local state records those messages as archived and no longer open inbox work

### Requirement: Replies automatically mark the replied message answered
When a recipient successfully sends a reply to a mailbox message through the shared mailbox operation contract, the system SHALL mark the replied message `answered=true` for that recipient.

The reply transition SHALL also mark the replied message read for that recipient. It SHALL NOT archive the replied message.

This requirement applies to substantive replies and acknowledgement replies alike.

#### Scenario: Reply marks parent answered without archiving it
- **WHEN** an agent replies to an existing mailbox message
- **THEN** the replied message is marked `answered=true` and `read=true` for that agent
- **AND THEN** the replied message remains in its current box until an explicit move or archive operation succeeds

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

