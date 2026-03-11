## ADDED Requirements

### Requirement: Filesystem mailbox transport uses an env-configurable mailbox content root with deterministic internal layout
The filesystem mailbox transport SHALL persist mailbox artifacts under a mailbox content root that is configurable through runtime-managed env bindings.

When no explicit mailbox content root is configured, the filesystem mailbox transport SHALL default that content root to a deterministic path under the configured runtime root.

That mailbox subtree SHALL include at minimum:

- a canonical message store
- mailbox projection directories by principal
- a SQLite index
- lock-file locations
- a staging area for in-progress writes

#### Scenario: Creating a filesystem mailbox initializes required layout at an explicit mailbox root
- **WHEN** a filesystem mailbox transport is initialized with an explicit mailbox content root binding
- **THEN** the system creates or validates the mailbox subtree under that effective mailbox content root
- **AND THEN** the mailbox subtree contains the required directories and index path for canonical messages, mailbox projections, locks, and staging

#### Scenario: Creating a filesystem mailbox falls back to runtime-root default
- **WHEN** a filesystem mailbox transport is initialized without an explicit mailbox content root binding
- **THEN** the system derives the effective mailbox content root from the configured runtime root
- **AND THEN** the resulting mailbox subtree uses that derived default location while preserving the same internal layout

### Requirement: Filesystem transport stores canonical messages as Markdown and projects them into mailbox folders
The filesystem mailbox transport SHALL persist each delivered canonical message as a Markdown file in the canonical message store and SHALL materialize mailbox-visible projections for sender and recipient folders.

At minimum, recipient delivery SHALL appear in the recipient `inbox` and sender delivery SHALL appear in the sender `sent` folder.

#### Scenario: Delivery creates canonical message and recipient inbox projection
- **WHEN** a sender delivers a mailbox message through the filesystem transport
- **THEN** the system writes one canonical Markdown message file for that logical message
- **AND THEN** the system materializes a mailbox projection of that message in each recipient inbox
- **AND THEN** the system materializes a mailbox projection of that message in the sender sent folder

#### Scenario: Multi-recipient delivery preserves one logical message id
- **WHEN** a mailbox message is delivered to multiple recipients through the filesystem transport
- **THEN** the system uses one canonical message id for that delivered message
- **AND THEN** each recipient mailbox projection refers to the same logical message id even if the projection mechanism differs by filesystem capability

### Requirement: Filesystem transport is daemon-free and synchronizes writes with lock files
The filesystem mailbox transport SHALL NOT require a background process for delivery or mailbox-state updates.

The transport SHALL coordinate concurrent filesystem writers using deterministic `.lock` files and SHALL combine multi-file delivery changes with transactional SQLite index updates.

#### Scenario: Sender delivers mail without a helper daemon
- **WHEN** a sender process writes a mailbox message through the filesystem transport
- **THEN** the sender performs delivery directly through filesystem and SQLite operations
- **AND THEN** the delivery does not depend on a persistent helper daemon being active

#### Scenario: Concurrent writers serialize conflicting mailbox updates
- **WHEN** two sender processes attempt to update the same mailbox principal concurrently
- **THEN** the system serializes conflicting writes using deterministic lock files
- **AND THEN** recipients do not observe partially applied mailbox projections for a committed delivery

### Requirement: SQLite indexes mailbox metadata and mutable recipient state
The filesystem mailbox transport SHALL maintain a SQLite index for mailbox metadata and mutable per-recipient state.

That index SHALL record at minimum:

- messages and their canonical ids
- recipient associations
- mailbox folder projections
- per-recipient mailbox state
- thread summary metadata

#### Scenario: Marking a message read updates SQLite state without rewriting Markdown
- **WHEN** a recipient marks a delivered filesystem mailbox message as read
- **THEN** the system updates the recipient's mailbox state in SQLite
- **AND THEN** the canonical Markdown message file is not rewritten for that mailbox-state change

#### Scenario: Thread view is queryable from the filesystem mailbox index
- **WHEN** a mailbox contains multiple related messages in one thread
- **THEN** the SQLite index records those thread relationships
- **AND THEN** the system can query thread-oriented mailbox views without reparsing every mailbox file on each request

### Requirement: Filesystem transport supports recovery from the message corpus
The filesystem mailbox transport SHALL treat canonical Markdown message files as durable recovery artifacts and SHALL support rebuilding structural mailbox indexes from the message corpus when the SQLite index is missing or unusable.

#### Scenario: Reindex rebuilds structural message catalog
- **WHEN** the SQLite mailbox index is missing or corrupted but canonical Markdown message files remain present
- **THEN** the system can rebuild the structural message and projection catalog from the filesystem mailbox corpus
- **AND THEN** rebuilt entries preserve the original canonical message ids and thread ancestry recorded in those message files

#### Scenario: Reindex initializes mailbox state when prior mutable state is unavailable
- **WHEN** the system rebuilds mailbox indexes from canonical message files without prior mutable mailbox-state records
- **THEN** the system recreates mailbox catalog entries for the recovered messages
- **AND THEN** the system initializes per-recipient mailbox state using deterministic defaults rather than silently dropping the recovered messages
