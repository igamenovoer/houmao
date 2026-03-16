## ADDED Requirements

### Requirement: Each resolved mailbox directory maintains local mailbox-view SQLite state
The filesystem mailbox transport SHALL maintain a mailbox-local SQLite database under each resolved mailbox directory.

That local mailbox-state database SHALL be stored at a stable path under the resolved mailbox directory and SHALL act as the authority for mailbox-view state that can vary per mailbox, including:

- read or unread,
- starred,
- archived,
- deleted,
- mailbox-local unread thread summaries.

For an in-root mailbox directory, the local mailbox-state database SHALL live under `mailboxes/<address>/...`. For a symlink-registered mailbox, the local mailbox-state database SHALL live under the symlink-resolved mailbox directory rather than under the shared root entry path only.

#### Scenario: In-root mailbox gets a local mailbox-state database
- **WHEN** the runtime initializes or validates an in-root filesystem mailbox directory for one mailbox address
- **THEN** that mailbox directory contains a stable local mailbox-state SQLite database
- **AND THEN** mailbox-view state for that mailbox is stored there rather than only in shared-root SQLite state

#### Scenario: Symlink-registered mailbox keeps local state at the resolved mailbox target
- **WHEN** a mailbox address is registered through a symlink to a private mailbox directory outside the shared root
- **THEN** the mailbox-local SQLite state lives under that resolved private mailbox directory
- **AND THEN** recipient-local mailbox-view state follows the mailbox directory that owns that view

### Requirement: Per-mailbox state is not mirrored into shared aggregate recipient-status tables
The filesystem mailbox transport SHALL NOT require an authoritative shared-root aggregate recipient-status mirror for mailbox-view state such as read or unread.

If a caller needs to answer a cross-recipient question such as whether any recipient has read one message, that caller SHALL derive the answer by inspecting the relevant recipients' mailbox-local state rather than by relying on a shared aggregate read-state table.

#### Scenario: Cross-recipient read inspection fans out to mailbox-local state
- **WHEN** a tool needs to know whether any recipient of one message has marked it read
- **THEN** the tool inspects the relevant recipients' mailbox-local state records
- **AND THEN** the filesystem mailbox transport does not require a separate shared aggregate "anyone has read this" table to answer that question

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

#### Scenario: Marking a message read updates mailbox-local SQLite state without rewriting Markdown
- **WHEN** a recipient marks a delivered filesystem mailbox message as read
- **THEN** the system updates that recipient mailbox's local mailbox-state SQLite database
- **AND THEN** the canonical Markdown message file is not rewritten for that mailbox-state change

#### Scenario: Thread view is queryable without reparsing every mailbox file on each request
- **WHEN** a mailbox contains multiple related messages in one thread
- **THEN** the transport records thread relationships and summary inputs in durable SQLite state
- **AND THEN** the system can query thread-oriented mailbox views without reparsing every mailbox file on each request
