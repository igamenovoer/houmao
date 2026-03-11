## ADDED Requirements

### Requirement: Canonical mailbox message envelope
The system SHALL represent every mailbox message in a transport-neutral canonical envelope that includes at minimum:

- `message_id`
- `thread_id`
- `created_at_utc`
- sender identity
- recipient identities
- `subject`
- `body_markdown`
- attachment metadata
- extensible protocol headers

The canonical envelope SHALL be immutable after delivery except for transport-local projection metadata that is explicitly outside the canonical message content.

#### Scenario: New root message receives a canonical envelope
- **WHEN** a sender creates a new mailbox message that does not reply to an earlier message
- **THEN** the system stores a canonical envelope containing all required fields
- **AND THEN** the stored root message uses its own `message_id` as the `thread_id`

#### Scenario: Reply message preserves canonical ancestry
- **WHEN** a sender replies to an existing mailbox message
- **THEN** the system stores a new canonical envelope with a new `message_id`
- **AND THEN** the new envelope sets `in_reply_to` to the direct parent message id
- **AND THEN** the new envelope preserves the existing thread by reusing the parent `thread_id`

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
- a path or managed-store locator appropriate to the attachment kind

#### Scenario: Path-reference attachment is preserved in the canonical message
- **WHEN** a sender attaches an existing local file by reference
- **THEN** the system records that attachment in the canonical message as a reference attachment
- **AND THEN** the recorded attachment metadata includes the referenced path and available file metadata

#### Scenario: Managed-copy attachment remains addressable
- **WHEN** a sender chooses managed attachment storage for a mailbox message
- **THEN** the system records the attachment as a managed-copy attachment in the canonical message
- **AND THEN** recipients can resolve the attachment through the managed-store locator recorded in that metadata

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
