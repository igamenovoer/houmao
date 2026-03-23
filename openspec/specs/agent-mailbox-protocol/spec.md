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

### Requirement: Principal-based mailbox addressing
The system SHALL address mailbox participants by mailbox principal rather than by a transient session handle.

Each mailbox principal SHALL include:

- a stable `principal_id`, and
- an email-like address suitable for the selected transport.

For agent participants, the system SHALL use the canonical `AGENTSYS-...` agent identity as the default `principal_id` unless an explicit mailbox binding overrides it.

#### Scenario: Agent mailbox uses canonical agent identity
- **WHEN** an agent participant with canonical identity `AGENTSYS-research` is registered for mailbox delivery
- **THEN** the system addresses that participant using `principal_id=AGENTSYS-research`
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

### Requirement: Shared mailbox read-state updates target opaque message references
The shared mailbox operation contract exposed through runtime-owned and gateway-owned mailbox surfaces SHALL include `check`, `send`, `reply`, and explicit per-recipient read-state update by opaque `message_ref`.

Callers SHALL treat that `message_ref` as the entire targeting contract and SHALL NOT derive transport-local message identifiers from embedded prefixes, encodings, or storage details.

For this change, the shared read-state update contract SHALL support setting `read=true` for one processed message after successful mailbox handling and SHALL NOT expand to broader mailbox-state flag editing.

Applying a shared read-state update SHALL mutate recipient-local mailbox state without rewriting immutable canonical message content.

#### Scenario: Filesystem shared read-state update uses opaque target
- **WHEN** a caller marks one filesystem-backed message read through a shared mailbox surface using `message_ref`
- **THEN** the mailbox system resolves that opaque target without requiring the caller to supply the underlying filesystem `message_id`
- **AND THEN** the recipient-local read state changes while the canonical message document remains unchanged

#### Scenario: Stalwart shared read-state update uses the same opaque target shape
- **WHEN** a caller marks one `stalwart`-backed message read through a shared mailbox surface using `message_ref`
- **THEN** the caller uses the same opaque shared targeting contract as the filesystem transport
- **AND THEN** transport-owned identifiers remain hidden behind that shared mailbox operation contract

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
