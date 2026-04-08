## Purpose
Define the filesystem-backed mailbox transport layout, bootstrap rules, delivery model, locking model, and recovery guarantees for mailbox-enabled sessions.
## Requirements
### Requirement: Filesystem mailbox transport uses a configurable mailbox content root with deterministic internal layout
The filesystem mailbox transport SHALL persist mailbox artifacts under a mailbox content root that is configurable through runtime mailbox binding inputs rather than through mailbox-specific session env publication.

When no explicit mailbox content root is configured, the filesystem mailbox transport SHALL default that content root to the Houmao mailbox root `~/.houmao/mailbox` rather than deriving it from the runtime root.

When no explicit mailbox content root is configured and `HOUMAO_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the effective Houmao mailbox root SHALL be derived from that env-var override before runtime persists or resolves filesystem mailbox state for the session.

The filesystem mailbox transport SHALL require a symlink-capable local filesystem for address-based mailbox registration and mailbox projection writes.

#### Scenario: Mailbox-root env-var override redirects the default mailbox root
- **WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a filesystem mailbox transport is initialized without an explicit mailbox content root setting
- **THEN** the system derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the resulting mailbox subtree uses that env-var-selected location while preserving the same internal layout

### Requirement: Filesystem mailbox initialization is a runtime-owned bootstrap path
The system SHALL initialize a new filesystem mailbox root through package-internal runtime bootstrap code that does not depend on pre-existing helper scripts under `rules/scripts/`.

That bootstrap path SHALL create or validate at minimum:

- `protocol-version.txt`
- the SQLite schema
- the `rules/` tree and mailbox-local policy documents
- the locks area
- the staging area
- any in-root address-based mailbox directories and mailbox-registration entries being initialized

The runtime MAY also publish compatibility or diagnostic helper assets under `rules/scripts/`, but ordinary mailbox operation SHALL NOT depend on those assets being the public execution contract.

On an existing mailbox root, bootstrap SHALL validate `protocol-version.txt` before continuing and SHALL fail explicitly when the on-disk protocol version is unsupported.

#### Scenario: Bootstrap materializes a new mailbox root without pre-existing helper scripts
- **WHEN** the runtime initializes a new filesystem mailbox root that does not yet contain shared mailbox helper scripts
- **THEN** the runtime performs bootstrap directly through package-internal code rather than invoking pre-existing `rules/scripts/` helpers
- **AND THEN** the resulting mailbox root contains the initialized SQLite schema, `protocol-version.txt`, and mailbox-local `rules/` policy content needed for later mailbox operations

#### Scenario: Bootstrap creates initial in-root mailbox registration
- **WHEN** the runtime initializes mailbox support for a participant that uses an in-root mailbox directory for one full mailbox address
- **THEN** the runtime bootstrap path creates that mailbox directory structure directly
- **AND THEN** the bootstrap path records the corresponding in-root mailbox registration in the mailbox index without requiring pre-existing shared helper scripts

#### Scenario: Unsupported protocol version fails bootstrap
- **WHEN** the runtime encounters an existing filesystem mailbox root whose `protocol-version.txt` value is unsupported by the current implementation
- **THEN** bootstrap fails explicitly before mutating that mailbox root
- **AND THEN** the runtime does not proceed with partial initialization against the unsupported on-disk protocol

### Requirement: Filesystem mailbox root publishes shared mailbox rules
The filesystem mailbox transport SHALL publish a `rules/` directory under the mailbox root as the mailbox-local source of truth for shared mailbox policy guidance.

That `rules/` directory SHALL contain at minimum:

- a human-readable `README`
- mailbox-local markdown guidance

That guidance MAY cover:

- message formatting,
- reply or subject conventions,
- mailbox-local etiquette,
- other workflow hints specific to that mailbox.

The filesystem mailbox public contract SHALL NOT require `rules/` to carry the canonical execution protocol for ordinary send, reply, check, or mark-read operations.

The transport MAY publish compatibility or diagnostic assets under `rules/scripts/`, but it SHALL NOT require a stable public `rules/scripts/` filename set for ordinary agent or operator mailbox work.

#### Scenario: Filesystem mailbox root exposes mailbox-local policy guidance
- **WHEN** a participant inspects the shared filesystem mailbox root before mailbox interaction
- **THEN** the participant can find a `rules/` directory under that mailbox root
- **AND THEN** that `rules/` directory contains mailbox-local policy guidance that can refine formatting or workflow expectations without becoming the canonical execution protocol

#### Scenario: Ordinary mailbox workflow does not require shared scripts
- **WHEN** an agent or operator performs an ordinary filesystem mailbox action through the supported Houmao-owned workflow
- **THEN** the action can complete without requiring the caller to discover or invoke a mailbox-owned script under `rules/scripts/`
- **AND THEN** the participant does not need to reconstruct the mailbox protocol from script names or dependency manifests

### Requirement: Filesystem mailbox groups support symlink-based mailbox registration
The filesystem mailbox transport SHALL allow each full-address entry under `mailboxes/` to be either a concrete mailbox directory inside the mail-group root or a symlink to that address's private mailbox directory outside the root.

A symlink-registered private mailbox directory SHALL expose the same mailbox substructure expected from an in-root mailbox directory.

In v1, `archive/` and `drafts/` are reserved placeholder directories in that substructure rather than defined archive or draft workflows.

#### Scenario: Address joins filesystem mail group through symlink registration
- **WHEN** an agent or human participant wants to join an existing filesystem mail group without relocating its mailbox projection directory into the shared root
- **THEN** the system allows `mailboxes/<address>` to be created as a symlink to that participant's private mailbox directory
- **AND THEN** delivery and mailbox reads can use that registration as the effective mailbox location for that full mailbox address

#### Scenario: Delivery follows symlink-registered mailbox target
- **WHEN** a sender delivers a mailbox message to a mailbox address whose `mailboxes/<address>` entry is a symlink
- **THEN** the filesystem mailbox transport writes the mailbox projection through that symlink-resolved mailbox directory
- **AND THEN** the canonical message store, lock files, and shared SQLite index remain anchored under the shared mail-group root

### Requirement: Archive and drafts directories are reserved placeholders in v1
The filesystem mailbox transport SHALL reserve `archive/` and `drafts/` directories in address-based mailbox layouts for forward compatibility.

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

Standardized filesystem write flows executed by Houmao-owned code SHALL acquire all affected address locks in ascending lexicographic full-address order before acquiring `locks/index.lock`.

Ordinary agent-facing filesystem mailbox workflows SHALL reach those writes through gateway HTTP or `houmao-mgr agents mail ...` rather than through mailbox-owned scripts. When a manager fallback command returns `authoritative: false`, the caller SHALL verify outcome through manager-owned or transport-owned state instead of treating that submission result as the write itself.

#### Scenario: Sender delivers mail without a helper daemon
- **WHEN** a sender process writes a mailbox message through the filesystem transport
- **THEN** the sender performs delivery directly through filesystem and SQLite operations
- **AND THEN** the delivery does not depend on a persistent helper daemon being active

#### Scenario: Ordinary filesystem mailbox workflow uses Houmao-owned surfaces
- **WHEN** an agent sender interacts with a shared filesystem mailbox through the supported ordinary mailbox workflow
- **THEN** that workflow uses the shared gateway facade when present or `houmao-mgr agents mail ...` when it is not
- **AND THEN** the caller does not need to invoke a mailbox-owned script under `rules/scripts/` for the ordinary operation

#### Scenario: Submission-only manager fallback does not replace filesystem verification
- **WHEN** an ordinary filesystem mailbox action reaches `houmao-mgr agents mail ...`
- **AND WHEN** the command returns `authoritative: false`
- **THEN** the caller treats that result as request submission rather than as verified filesystem delivery or state mutation
- **AND THEN** the caller verifies the mailbox outcome through mailbox state or a follow-up manager-owned check instead of falling back to mailbox-owned scripts as the truth boundary

#### Scenario: Concurrent writers serialize conflicting mailbox updates
- **WHEN** two sender processes attempt to update the same mailbox address concurrently
- **THEN** the system serializes conflicting writes using deterministic lock files
- **AND THEN** recipients do not observe partially applied mailbox projections for a committed delivery

#### Scenario: Lock acquisition order avoids deadlock
- **WHEN** a standardized filesystem mailbox write affects multiple mailbox addresses
- **THEN** the Houmao-owned write flow acquires the corresponding address locks in ascending lexicographic full-address order before acquiring `locks/index.lock`
- **AND THEN** the operation fails explicitly rather than partially committing delivery if it cannot obtain the required lock set within its bounded timeout

#### Scenario: Missing symlink target causes explicit delivery failure
- **WHEN** a sender attempts delivery to a mailbox address whose `mailboxes/<address>` symlink target is missing or invalid
- **THEN** the filesystem mailbox transport fails that delivery explicitly
- **AND THEN** the system does not silently create a replacement mailbox directory at an unintended path

### Requirement: Filesystem mailbox SQLite stays in a non-WAL journal mode
The filesystem mailbox transport SHALL configure its shared SQLite index to use a non-WAL journal mode in v1.

#### Scenario: Filesystem mailbox index avoids WAL sidecar files
- **WHEN** the runtime bootstraps or opens the shared filesystem mailbox SQLite index
- **THEN** the runtime configures that index with a non-WAL journal mode for v1
- **AND THEN** the transport does not require `index.sqlite-wal` or `index.sqlite-shm` sidecar files for correct operation

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

#### Scenario: Marking a message read updates mailbox-local SQLite state without rewriting Markdown
- **WHEN** a recipient marks a delivered filesystem mailbox message as read
- **THEN** the system updates that recipient mailbox's local mailbox-state SQLite database
- **AND THEN** the canonical Markdown message file is not rewritten for that mailbox-state change

#### Scenario: Thread view is queryable without reparsing every mailbox file on each request
- **WHEN** a mailbox contains multiple related messages in one thread
- **THEN** the transport records thread relationships and summary inputs in durable SQLite state
- **AND THEN** the system can query thread-oriented mailbox views without reparsing every mailbox file on each request

#### Scenario: Per-mailbox unread thread counts are rebuilt locally
- **WHEN** the transport migrates or repairs mailbox-local state for one mailbox
- **THEN** unread thread counts are rebuilt from that mailbox's local message-state rows
- **AND THEN** any shared-root thread-summary data is treated as structural-only rather than as authoritative unread state

### Requirement: Filesystem transport supports recovery from the message corpus
The filesystem mailbox transport SHALL treat canonical Markdown message files as durable recovery artifacts and SHALL support rebuilding structural mailbox indexes from the message corpus when the SQLite index is missing or unusable.

Interrupted deliveries SHALL leave only staging artifacts that can be cleaned or quarantined without treating them as committed mail.

#### Scenario: Reindex rebuilds structural message catalog
- **WHEN** the SQLite mailbox index is missing or corrupted but canonical Markdown message files remain present
- **THEN** the system can rebuild the structural message and projection catalog from the filesystem mailbox corpus
- **AND THEN** rebuilt entries preserve the original canonical message ids and thread ancestry recorded in those message files

#### Scenario: Reindex initializes mailbox state when prior mutable state is unavailable
- **WHEN** the system rebuilds mailbox indexes from canonical message files without prior mutable mailbox-state records
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

#### Scenario: In-root mailbox gets a local mailbox-state database
- **WHEN** the runtime initializes or validates an in-root filesystem mailbox directory for one mailbox address
- **THEN** that mailbox directory contains a stable local mailbox-state SQLite database
- **AND THEN** mailbox-view state for that mailbox is stored there rather than only in shared-root SQLite state

#### Scenario: Symlink-registered mailbox keeps local state at the resolved mailbox target
- **WHEN** a mailbox address is registered through a symlink to a private mailbox directory outside the shared root
- **THEN** the mailbox-local SQLite state lives under that resolved private mailbox directory
- **AND THEN** recipient-local mailbox-view state follows the mailbox directory that owns that view

#### Scenario: Mailbox-local SQLite uses mailbox-scoped row identities
- **WHEN** the transport initializes or migrates one mailbox-local database
- **THEN** mutable message-view rows are identified by `message_id` and mailbox-local thread summary rows are identified by `thread_id`
- **AND THEN** the local database does not repeat shared-root `registration_id` as part of those primary identities

### Requirement: Per-mailbox state is not mirrored into shared aggregate recipient-status tables
The filesystem mailbox transport SHALL NOT require an authoritative shared-root aggregate recipient-status mirror for mailbox-view state such as read or unread.

If a caller needs to answer a cross-recipient question such as whether any recipient has read one message, that caller SHALL derive the answer by inspecting the relevant recipients' mailbox-local state rather than by relying on a shared aggregate read-state table.

#### Scenario: Cross-recipient read inspection fans out to mailbox-local state
- **WHEN** a tool needs to know whether any recipient of one message has marked it read
- **THEN** the tool inspects the relevant recipients' mailbox-local state records
- **AND THEN** the filesystem mailbox transport does not require a separate shared aggregate "anyone has read this" table to answer that question

### Requirement: Filesystem mailbox roots provision and protect the reserved operator account
The filesystem mailbox transport SHALL treat `HOUMAO-operator@houmao.localhost` as a reserved system mailbox registration under each initialized mailbox root.

That reserved registration SHALL use the Houmao-owned principal id `HOUMAO-operator` and SHALL be provisioned or confirmed as part of mailbox-root bootstrap.

When an otherwise valid filesystem mailbox root lacks that reserved registration later, operator-origin delivery flows MAY self-heal by recreating or confirming it before delivery.

Generic filesystem mailbox lifecycle operations SHALL protect the reserved operator registration:

- cleanup SHALL preserve it while it is active,
- generic unregister or purge flows SHALL reject destructive removal by default,
- account inspection MAY annotate it as a system account.

#### Scenario: Filesystem mailbox bootstrap creates the reserved operator registration
- **WHEN** the runtime bootstraps or validates a new filesystem mailbox root
- **THEN** the root contains an active registration for `HOUMAO-operator@houmao.localhost`
- **AND THEN** that registration uses the reserved Houmao-owned principal id rather than an ordinary managed-agent principal id

#### Scenario: Cleanup preserves the reserved operator registration
- **WHEN** an operator runs filesystem mailbox cleanup against a mailbox root that contains the active reserved operator registration
- **THEN** cleanup preserves that reserved registration
- **AND THEN** the cleanup flow does not report `HOUMAO-operator@houmao.localhost` as an inactive or disposable mailbox account

### Requirement: Filesystem self-addressed delivery starts unread for the recipient mailbox
When the filesystem mailbox transport delivers a message to one or more recipient mailboxes, initial mailbox-local unread or read state SHALL be determined by recipient membership for each mailbox rather than by sender role alone.

For one mailbox registration:

- if that mailbox registration is among the delivered recipients for the message, the initial mailbox-local state SHALL be unread,
- if that mailbox registration is not among the delivered recipients and only has the sender-side copy, the initial mailbox-local state SHALL be read.

When the sender and recipient resolve to the same active filesystem mailbox registration, the resulting mailbox-local state for that mailbox SHALL be unread until explicitly marked read.

Structural mailbox projections MAY still include both `sent/` and `inbox/` entries for that same mailbox. Those projection folders SHALL NOT override the mailbox-local unread state for the self-addressed message.

#### Scenario: Self-sent filesystem mail stays unread for the sender-recipient mailbox
- **WHEN** a filesystem mailbox participant sends one new message to its own mailbox address
- **THEN** the resulting message is projected structurally as mail for that same mailbox
- **AND THEN** that mailbox's mailbox-local actor state starts unread until the participant explicitly marks the message read

#### Scenario: Sender-only mailbox copy still starts read
- **WHEN** a filesystem mailbox participant sends one new message to some other mailbox address and does not include its own mailbox as a recipient
- **THEN** the sender mailbox keeps a sender-side copy for that message
- **AND THEN** that sender mailbox copy starts read by default

### Requirement: Filesystem mailbox state reconstruction preserves self-addressed unread defaults
Whenever the filesystem mailbox transport reconstructs, repairs, or lazily initializes mailbox-local message state for an already projected message, it SHALL preserve the same self-addressed unread semantics as fresh delivery.

That rule SHALL apply at minimum to:

- index or mailbox-local state repair from canonical message files,
- lazy insertion of mailbox-local message-state rows for an existing projected message,
- any other default mailbox-local read-state initialization path that recreates state without an explicit prior mailbox-local read record.

For a self-addressed message projected into the same mailbox as both sender and recipient, those reconstruction paths SHALL initialize that mailbox-local state as unread rather than deriving read state only from the existence of a `sent` projection.

#### Scenario: Repaired mailbox-local state keeps self-addressed mail unread
- **WHEN** the filesystem mailbox transport repairs or rebuilds mailbox-local state for a self-addressed message
- **THEN** the rebuilt mailbox-local state for that mailbox starts unread if no explicit prior mailbox-local read record exists
- **AND THEN** later actor-scoped unread checks continue to treat that self-addressed message as unread until explicitly marked read
