## ADDED Requirements

### Requirement: Filesystem mailbox transport uses an env-configurable mailbox content root with deterministic internal layout
The filesystem mailbox transport SHALL persist mailbox artifacts under a mailbox content root that is configurable through runtime-managed env bindings.

When no explicit mailbox content root is configured, the filesystem mailbox transport SHALL default that content root to a deterministic path under the configured runtime root.

That mailbox subtree SHALL include at minimum:

- `protocol-version.txt`
- a canonical message store
- a shared `rules/` directory for mailbox-local protocol guidance
- mailbox projection registrations by principal
- a SQLite index
- lock-file locations
- a staging area for in-progress writes

#### Scenario: Creating a filesystem mailbox initializes required layout at an explicit mailbox root
- **WHEN** a filesystem mailbox transport is initialized with an explicit mailbox content root binding
- **THEN** the system creates or validates the mailbox subtree under that effective mailbox content root
- **AND THEN** the mailbox subtree contains `protocol-version.txt` plus the required directories and index path for canonical messages, mailbox projections, locks, and staging

#### Scenario: Creating a filesystem mailbox falls back to runtime-root default
- **WHEN** a filesystem mailbox transport is initialized without an explicit mailbox content root binding
- **THEN** the system derives the effective mailbox content root from the configured runtime root
- **AND THEN** the resulting mailbox subtree uses that derived default location while preserving the same internal layout

### Requirement: Filesystem mailbox initialization is a runtime-owned bootstrap path
The system SHALL initialize a new filesystem mailbox root through package-internal runtime bootstrap code that does not depend on pre-existing helper scripts under `rules/scripts/`.

That bootstrap path SHALL create or validate at minimum:

- `protocol-version.txt`
- the SQLite schema
- the `rules/` tree and managed scripts
- the locks area
- the staging area
- any in-root principal mailbox directories and principal-registry entries being initialized

#### Scenario: Bootstrap materializes a new mailbox root without pre-existing helper scripts
- **WHEN** the runtime initializes a new filesystem mailbox root that does not yet contain shared mailbox helper scripts
- **THEN** the runtime performs bootstrap directly through package-internal code rather than invoking pre-existing `rules/scripts/` helpers
- **AND THEN** the resulting mailbox root contains the initialized SQLite schema, `protocol-version.txt`, and managed `rules/` content needed for later standardized mailbox operations

#### Scenario: Bootstrap creates initial in-root principal registration
- **WHEN** the runtime initializes mailbox support for a principal that uses an in-root mailbox directory
- **THEN** the runtime bootstrap path creates that principal's mailbox directory structure directly
- **AND THEN** the bootstrap path records the corresponding in-root principal registration in the mailbox index without requiring pre-existing shared helper scripts

### Requirement: Filesystem mailbox root publishes shared mailbox rules
The filesystem mailbox transport SHALL publish a `rules/` directory under the mailbox root as the mailbox-local source of truth for shared mailbox interaction guidance.

That `rules/` directory SHALL contain at minimum:

- a human-readable `README`
- mailbox protocol documentation
- helper scripts for standardized mailbox operations
- agent-skill materials for standardized mailbox operations

Sensitive mailbox operations that touch `index.sqlite` or `locks/` SHALL be represented by shared scripts under `rules/scripts/`.

Those scripts MAY be implemented in Python or shell. Python implementations SHALL assume only the Python standard library and Python version `>=3.11`.

In v1, the runtime-managed script set SHALL include `deliver_message.py`, `insert_standard_headers.py`, `update_mailbox_state.py`, and `repair_index.py` under `rules/scripts/`.

These filenames SHALL be treated as stable within a given `protocol-version.txt` value.

#### Scenario: Filesystem mailbox root exposes mailbox-local rules
- **WHEN** a participant inspects the shared filesystem mailbox root before mailbox interaction
- **THEN** the participant can find a `rules/` directory under that mailbox root
- **AND THEN** that `rules/` directory contains the shared mailbox interaction guidance and helper assets needed for standardized mailbox operations

#### Scenario: Sensitive mailbox scripts are available under rules/scripts
- **WHEN** a participant needs to perform a standardized mailbox operation that touches `index.sqlite` or `locks/`
- **THEN** the shared filesystem mailbox root provides a corresponding helper script under `rules/scripts/`
- **AND THEN** any Python-based helper script for that operation relies only on the Python standard library with Python version `>=3.11`

#### Scenario: Bootstrap materializes the managed script set
- **WHEN** the runtime initializes or upgrades a filesystem mailbox root for the current protocol version
- **THEN** `rules/scripts/` contains the managed filenames `deliver_message.py`, `insert_standard_headers.py`, `update_mailbox_state.py`, and `repair_index.py`
- **AND THEN** those managed filenames correspond to the mailbox root's `protocol-version.txt`

#### Scenario: Optional header helper script is available for standardized composition
- **WHEN** a shared filesystem mailbox wants to help participants standardize message headers or YAML front matter during composition
- **THEN** the shared mailbox MAY provide a helper script under `rules/scripts/` that accepts header-related parameters and inserts or normalizes those headers
- **AND THEN** that helper script acts as an optional lint-style tool rather than a required transport primitive

### Requirement: Filesystem mailbox groups support symlink-based principal registration
The filesystem mailbox transport SHALL allow each principal entry under `mailboxes/` to be either a concrete mailbox directory inside the mail-group root or a symlink to that principal's private mailbox directory outside the root.

A symlink-registered private mailbox directory SHALL expose the same mailbox substructure expected from an in-root mailbox directory.

In v1, `archive/` and `drafts/` are reserved placeholder directories in that substructure rather than defined archive or draft workflows.

#### Scenario: Principal joins filesystem mail group through symlink registration
- **WHEN** an agent or human participant wants to join an existing filesystem mail group without relocating its mailbox projection directory into the shared root
- **THEN** the system allows `mailboxes/<principal>` to be created as a symlink to that participant's private mailbox directory
- **AND THEN** delivery and mailbox reads can use that registration as the effective mailbox location for that principal

#### Scenario: Delivery follows symlink-registered mailbox target
- **WHEN** a sender delivers a mailbox message to a principal whose `mailboxes/<principal>` entry is a symlink
- **THEN** the filesystem mailbox transport writes the mailbox projection through that symlink-resolved mailbox directory
- **AND THEN** the canonical message store, lock files, and shared SQLite index remain anchored under the shared mail-group root

### Requirement: Archive and drafts directories are reserved placeholders in v1
The filesystem mailbox transport SHALL reserve `archive/` and `drafts/` directories in principal mailbox layouts for forward compatibility.

This change SHALL NOT require archive or draft mailbox workflows beyond creating or validating those placeholder directories.

#### Scenario: Bootstrap provisions placeholder archive and drafts directories
- **WHEN** the runtime initializes an in-root filesystem mailbox directory for a principal
- **THEN** the resulting mailbox layout includes placeholder `archive/` and `drafts/` directories
- **AND THEN** the transport does not need to define archive or draft workflows to complete that initialization

#### Scenario: V1 mailbox workflows do not depend on archive or drafts semantics
- **WHEN** the v1 filesystem mailbox transport performs mailbox operations such as `check`, `send`, or `reply`
- **THEN** those operations succeed without requiring archive or draft folder behavior beyond placeholder directory presence
- **AND THEN** follow-up changes may define archive or draft workflows without changing the reserved directory names

### Requirement: Filesystem transport stores canonical messages as Markdown and projects them into mailbox folders
The filesystem mailbox transport SHALL persist each delivered canonical message as a Markdown file in the canonical message store under `messages/<YYYY-MM-DD>/<message-id>.md` and SHALL materialize mailbox-visible projections for sender and recipient folders as symlinks to that canonical message file.

At minimum, recipient delivery SHALL appear in the recipient `inbox` and sender delivery SHALL appear in the sender `sent` folder.

#### Scenario: Delivery creates canonical message and recipient inbox projection
- **WHEN** a sender delivers a mailbox message through the filesystem transport
- **THEN** the system writes one canonical Markdown message file for that logical message
- **AND THEN** the system materializes a symlink projection of that message in each recipient inbox
- **AND THEN** the system materializes a symlink projection of that message in the sender sent folder

#### Scenario: Multi-recipient delivery preserves one logical message id
- **WHEN** a mailbox message is delivered to multiple recipients through the filesystem transport
- **THEN** the system uses one canonical message id for that delivered message
- **AND THEN** each recipient mailbox projection is a symlink that resolves to the same canonical message file for that logical message

### Requirement: Filesystem transport stores managed attachments in attachment-id directories
When a sender chooses managed attachment storage, the filesystem mailbox transport SHALL copy that attachment into the shared mailbox root under an attachment-id-addressed directory.

The relationship between a message and a managed attachment SHALL be tracked in SQLite index state rather than being encoded in the managed attachment path name.

#### Scenario: Managed attachment is copied into an attachment-id directory
- **WHEN** a sender delivers a filesystem mailbox message using managed attachment storage
- **THEN** the system stores the copied attachment under `attachments/managed/<attachment-id>/...`
- **AND THEN** the managed attachment path does not need to encode the parent message id or thread id

### Requirement: Filesystem transport is daemon-free and synchronizes writes with lock files
The filesystem mailbox transport SHALL NOT require a background process for delivery or mailbox-state updates.

The transport SHALL coordinate concurrent filesystem writers using deterministic `.lock` files and SHALL combine multi-file delivery changes with transactional SQLite index updates.

#### Scenario: Sender delivers mail without a helper daemon
- **WHEN** a sender process writes a mailbox message through the filesystem transport
- **THEN** the sender performs delivery directly through filesystem and SQLite operations
- **AND THEN** the delivery does not depend on a persistent helper daemon being active

#### Scenario: Sender consults mailbox-local rules before standardized delivery
- **WHEN** an agent sender interacts with a shared filesystem mailbox through the standardized mailbox workflow
- **THEN** that workflow instructs the agent to consult the shared mailbox `rules/` directory before performing mailbox mutations
- **AND THEN** the transport behavior still remains daemon-free because those rules are read directly from the filesystem mailbox root

#### Scenario: Sensitive delivery steps use shared mailbox scripts
- **WHEN** a standardized filesystem mailbox operation needs to touch `index.sqlite` or `locks/`
- **THEN** the agent-facing workflow uses the shared script under `rules/scripts/` for that sensitive portion of the operation
- **AND THEN** the participant does not need to hand-author raw SQLite or lock-file manipulation for that step

#### Scenario: Concurrent writers serialize conflicting mailbox updates
- **WHEN** two sender processes attempt to update the same mailbox principal concurrently
- **THEN** the system serializes conflicting writes using deterministic lock files
- **AND THEN** recipients do not observe partially applied mailbox projections for a committed delivery

#### Scenario: Missing symlink target causes explicit delivery failure
- **WHEN** a sender attempts delivery to a principal whose `mailboxes/<principal>` symlink target is missing or invalid
- **THEN** the filesystem mailbox transport fails that delivery explicitly
- **AND THEN** the system does not silently create a replacement mailbox directory at an unintended path

### Requirement: SQLite indexes mailbox metadata and mutable recipient state
The filesystem mailbox transport SHALL maintain a SQLite index for mailbox metadata and mutable per-recipient state.

That index SHALL record at minimum:

- messages and their canonical ids
- recipient associations
- attachment metadata
- message-to-attachment associations
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
