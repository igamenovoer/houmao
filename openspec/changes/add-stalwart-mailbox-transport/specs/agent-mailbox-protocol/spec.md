## MODIFIED Requirements

### Requirement: Canonical mailbox message envelope
The system SHALL preserve transport-neutral mailbox message semantics, but shared mailbox operation surfaces used by runtime and gateway callers SHALL identify messages through transport-neutral references rather than requiring callers to understand transport-local storage ids.

The shared mailbox operation contract for this change SHALL include at minimum:

- opaque plain-string `message_ref`,
- optional `thread_ref`,
- `created_at_utc`,
- sender identity,
- recipient identities,
- `subject`,
- body content or body preview appropriate to the operation,
- attachment metadata,
- unread state when returned from `check`.

The system SHALL preserve the logical mailbox semantics across transports, but it SHALL NOT require every transport to persist a Houmao-authored canonical document or to expose Houmao-generated identifiers as the public operation contract.

The system SHALL represent `message_ref` as a plain string in the shared gateway and runtime mailbox contracts. Callers SHALL treat the entire value as opaque and SHALL NOT derive behavior from transport-specific prefixes, encodings, or storage identifiers embedded inside that string.

Adapters MAY use transport-prefixed string encodings in v1 when that keeps later `reply` targeting stateless, provided the caller-visible contract still treats the whole value as an opaque string handle.

For the filesystem transport, shared mailbox operation refs MAY be derived from the existing canonical message ids and thread ids.

For non-filesystem mailbox transports such as `stalwart`, shared mailbox operation refs MAY be derived from transport-owned message identities, provided they still preserve stable reply targeting and transport-neutral ancestry semantics for Houmao mailbox operations.

#### Scenario: Filesystem transport exposes shared message references without exposing SQLite storage details
- **WHEN** a caller performs a shared mailbox operation against the filesystem transport
- **THEN** the transport returns stable `message_ref` values suitable for later `reply` targeting
- **AND THEN** the caller does not need to understand mailbox-local SQLite row identities or other transport-local storage details

#### Scenario: Stalwart-backed transport exposes reply-capable shared message references
- **WHEN** the `stalwart` mailbox transport creates or reads a mailbox message through the shared mailbox operation contract
- **THEN** the transport returns a stable `message_ref` suitable for later `reply` targeting
- **AND THEN** the caller does not need to understand Stalwart-native object shapes to continue the mailbox workflow

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
