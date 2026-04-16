## ADDED Requirements

### Requirement: Filesystem mailbox format incompatibilities are hard-reset only before 1.0
Filesystem mailbox bootstrap SHALL create the current mailbox root protocol, shared SQLite schema, registration rows, and mailbox-local SQLite state when the mailbox root is new.

When an existing mailbox root uses an unsupported protocol version or obsolete persisted format, Houmao SHALL fail explicitly and direct the operator to delete and re-bootstrap the mailbox root. Houmao SHALL NOT transform unsupported old mailbox state into the current format through an in-place migration.

#### Scenario: Fresh mailbox root initializes current state
- **WHEN** an operator bootstraps filesystem mailbox support from scratch
- **THEN** Houmao creates the mailbox root using the current protocol and SQLite schemas
- **AND THEN** no old-format migration path is needed for mailbox operation

#### Scenario: Unsupported mailbox root fails with rebootstrap guidance
- **WHEN** Houmao opens an existing filesystem mailbox root that uses an unsupported persisted format
- **THEN** mailbox bootstrap fails before mutating that root
- **AND THEN** the diagnostic directs the operator to delete and re-bootstrap the mailbox root instead of promising in-place migration

## MODIFIED Requirements

### Requirement: SQLite indexes mailbox metadata and mutable recipient state
The filesystem mailbox transport SHALL maintain a shared mailbox-root SQLite index for mailbox metadata and structural mailbox state, while storing mailbox-view state that can differ per mailbox in mailbox-local SQLite databases.

The shared mailbox-root SQLite index SHALL record at minimum:

- messages and their canonical ids
- recipient associations
- attachment metadata
- message-to-attachment associations
- mailbox folder projections

The shared mailbox-root SQLite index SHALL NOT be the authoritative store for per-mailbox read, starred, archived, deleted, or unread thread-summary state once mailbox-local SQLite is available.

If the shared mailbox-root SQLite index retains thread-summary rows for structural query support, those rows SHALL be structural-only and SHALL NOT remain authoritative for per-mailbox `unread_count` once mailbox-local SQLite is available.

If the shared mailbox-root SQLite index retains obsolete mutable mailbox-state rows from an older development format, those rows SHALL NOT be used as a migration source for mailbox-local SQLite state.

#### Scenario: Marking a message read updates mailbox-local SQLite state without rewriting Markdown
- **WHEN** a recipient marks a delivered filesystem mailbox message as read
- **THEN** the system updates that recipient mailbox's local mailbox-state SQLite database
- **AND THEN** the canonical Markdown message file is not rewritten for that mailbox-state change

#### Scenario: Thread view is queryable without reparsing every mailbox file on each request
- **WHEN** a mailbox contains multiple related messages in one thread
- **THEN** the transport records thread relationships and summary inputs in durable SQLite state
- **AND THEN** the system can query thread-oriented mailbox views without reparsing every mailbox file on each request

#### Scenario: Per-mailbox unread thread counts are rebuilt locally
- **WHEN** the transport repairs or rebuilds mailbox-local state for one current-format mailbox
- **THEN** unread thread counts are rebuilt from that mailbox's local message-state rows
- **AND THEN** any shared-root thread-summary data is treated as structural-only rather than as authoritative unread state

#### Scenario: Obsolete shared mutable state is ignored
- **WHEN** an existing shared mailbox-root SQLite index contains old shared mutable mailbox-state rows
- **AND WHEN** Houmao initializes or validates mailbox-local SQLite state
- **THEN** Houmao does not copy those old shared mutable rows into mailbox-local SQLite
- **AND THEN** mailbox-local state is created only from current-format authoritative inputs or deterministic defaults

### Requirement: Filesystem transport supports recovery from the message corpus
The filesystem mailbox transport SHALL treat canonical Markdown message files as durable recovery artifacts and SHALL support rebuilding structural mailbox indexes from the message corpus when the SQLite index is missing or unusable.

Interrupted deliveries SHALL leave only staging artifacts that can be cleaned or quarantined without treating them as committed mail.

Recovery from canonical Markdown files SHALL rebuild supported current-format structural state. It SHALL NOT migrate unsupported old mutable mailbox-state schemas into current mailbox-local SQLite state.

#### Scenario: Reindex rebuilds structural message catalog
- **WHEN** the SQLite mailbox index is missing or corrupted but canonical Markdown message files remain present
- **THEN** the system can rebuild the structural message and projection catalog from the filesystem mailbox corpus
- **AND THEN** rebuilt entries preserve the original canonical message ids and thread ancestry recorded in those message files

#### Scenario: Reindex initializes mailbox state when prior current-format mutable state is unavailable
- **WHEN** the system rebuilds mailbox indexes from canonical message files without prior current-format mailbox-local mutable state records
- **THEN** the system recreates mailbox catalog entries for the recovered messages
- **AND THEN** the system initializes per-recipient mailbox state using deterministic defaults rather than silently dropping the recovered messages

#### Scenario: Repair cleans orphaned staging artifacts after interrupted delivery
- **WHEN** a delivery attempt terminates after writing staging artifacts but before committing the canonical message and SQLite transaction
- **THEN** repair or cleanup logic removes or quarantines those orphaned staging artifacts without treating them as delivered mail
- **AND THEN** subsequent delivery or reindex flows can proceed without confusing orphaned staging files for committed mailbox messages

### Requirement: Each resolved mailbox directory maintains local mailbox-view SQLite state
The filesystem mailbox transport SHALL maintain a mailbox-local SQLite database under each resolved mailbox directory.

That local mailbox-state database SHALL be stored at a stable path under the resolved mailbox directory and SHALL act as the authority for mailbox-view state that can vary per mailbox, including:

- read or unread,
- starred,
- archived,
- deleted,
- mailbox-local unread thread summaries.

For an in-root mailbox directory, the local mailbox-state database SHALL live under `mailboxes/<address>/...`. For a symlink-registered mailbox, the local mailbox-state database SHALL live under the symlink-resolved mailbox directory rather than under the shared root entry path only.

Within each mailbox-local database, mutable message-view rows SHALL be keyed by `message_id`, and mailbox-local thread summary rows SHALL be keyed by `thread_id`. Because the database already scopes to one resolved mailbox, those local tables SHALL NOT require `registration_id` as part of their row identity.

Mailbox-local SQLite initialization SHALL create the current schema when the local database is missing. It SHALL NOT populate that local database by migrating obsolete shared-root mutable mailbox-state rows.

#### Scenario: In-root mailbox gets a local mailbox-state database
- **WHEN** the runtime initializes or validates an in-root filesystem mailbox directory for one mailbox address
- **THEN** that mailbox directory contains a stable local mailbox-state SQLite database
- **AND THEN** mailbox-view state for that mailbox is stored there rather than only in shared-root SQLite state

#### Scenario: Symlink-registered mailbox keeps local state at the resolved mailbox target
- **WHEN** a mailbox address is registered through a symlink to a private mailbox directory outside the shared root
- **THEN** the mailbox-local SQLite state lives under that resolved private mailbox directory
- **AND THEN** recipient-local mailbox-view state follows the mailbox directory that owns that view

#### Scenario: Mailbox-local SQLite uses mailbox-scoped row identities
- **WHEN** the transport initializes or validates one mailbox-local database
- **THEN** mutable message-view rows are identified by `message_id` and mailbox-local thread summary rows are identified by `thread_id`
- **AND THEN** the local database does not repeat shared-root `registration_id` as part of those primary identities
