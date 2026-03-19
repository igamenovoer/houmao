## MODIFIED Requirements

### Requirement: Canonical mailbox message envelope
The system SHALL represent mailbox messages through a transport-neutral logical envelope that includes at minimum:

- `message_id`,
- `thread_id`,
- `created_at_utc`,
- sender identity,
- recipient identities,
- `subject`,
- `body_markdown`,
- attachment metadata,
- extensible protocol headers.

The system SHALL preserve the logical envelope semantics across mailbox transports, but it SHALL NOT require every transport to persist that envelope as a Houmao-authored canonical document or to use Houmao-generated identifiers as the transport’s storage authority.

In v1, the filesystem transport SHALL continue to generate `message_id` values using the format `msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}`.

Non-filesystem mailbox transports MAY use transport-owned delivery identifiers as the authoritative server-side message reference, provided they still preserve stable reply targeting and transport-neutral ancestry semantics for Houmao mailbox operations.

#### Scenario: Filesystem transport keeps Houmao-generated canonical message ids
- **WHEN** the filesystem mailbox transport creates a new mailbox message
- **THEN** the logical envelope uses the v1 `msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}` identifier format
- **AND THEN** that filesystem transport persists that message through its canonical filesystem message model

#### Scenario: Stalwart-backed transport preserves logical ancestry without requiring filesystem-style message storage
- **WHEN** the `stalwart` mailbox transport creates or reads a mailbox message
- **THEN** the transport preserves the logical sender, recipient, subject, body, and reply ancestry semantics needed by Houmao mailbox operations
- **AND THEN** the transport is not required to persist that message as a Houmao-authored canonical Markdown document or to use the Houmao logical id as the authoritative server-side storage id

### Requirement: Attachment references carry stable metadata
The system SHALL support mailbox attachments as structured metadata that can describe either local composition inputs or transport-owned delivered artifacts.

Each attachment entry SHALL include:

- `attachment_id`,
- attachment kind,
- media type,
- size metadata when available,
- digest metadata when available,
- a transport-appropriate local reference, managed-store locator, or transport-owned attachment locator.

The mailbox protocol SHALL NOT require every transport to preserve a local absolute path reference after delivery.

#### Scenario: Filesystem transport preserves a path-reference attachment
- **WHEN** a sender attaches an existing local file by reference through the filesystem mailbox transport
- **THEN** the system records that attachment as a reference attachment in mailbox metadata
- **AND THEN** the attachment metadata can retain the referenced local path when that is valid for the filesystem transport

#### Scenario: Stalwart-backed transport replaces local composition paths with transport-owned attachment metadata
- **WHEN** a sender attaches a local file and delivers the message through the `stalwart` transport
- **THEN** the transport uploads or materializes that attachment through server-backed mail storage
- **AND THEN** the delivered attachment metadata is allowed to preserve the transport-owned attachment locator instead of the original local composition path
