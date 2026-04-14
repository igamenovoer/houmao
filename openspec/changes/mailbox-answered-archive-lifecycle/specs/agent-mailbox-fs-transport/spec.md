## ADDED Requirements

### Requirement: Filesystem archive is an active per-account mailbox box
The filesystem mailbox transport SHALL treat each account's `archive/` directory as an active mailbox box rather than as a placeholder.

Archiving a message SHALL remove or deactivate that recipient's inbox projection for the message, SHALL materialize the recipient's archive projection, and SHALL update mailbox-local state so the message is no longer open inbox work.

The filesystem transport SHALL continue to preserve canonical message Markdown content as immutable delivered-message content during archive, move, read, answered, and manual mark operations.

#### Scenario: Archive creates an archive projection without rewriting canonical content
- **WHEN** a recipient archives a filesystem-backed inbox message
- **THEN** the recipient's archive box exposes a projection for that message
- **AND THEN** the recipient's open inbox view no longer treats that message as actionable work
- **AND THEN** the canonical Markdown message file is not rewritten for the archive state change

### Requirement: Filesystem mailbox-local state stores read, answered, archived, and box state
The filesystem mailbox transport SHALL store recipient-local lifecycle state in mailbox-local durable state rather than in canonical message Markdown.

That recipient-local lifecycle state SHALL include at minimum `read`, `answered`, `archived`, and the message's active mailbox box membership for the recipient.

Filesystem mailbox state updates for read, answered, move, and archive operations SHALL be serialized with the same address-lock and index-lock discipline used by existing filesystem mailbox mutations.

#### Scenario: Reply state is recipient-local
- **WHEN** one recipient replies to a filesystem-backed message that was delivered to multiple recipients
- **THEN** the replying recipient's mailbox-local state records `answered=true`
- **AND THEN** other recipients do not inherit that answered state merely because they received the same canonical message

#### Scenario: Moving a message updates box membership atomically
- **WHEN** a caller moves a filesystem-backed message from `inbox` to `archive`
- **THEN** the filesystem transport updates the affected mailbox projection and mailbox-local state under the mailbox write lock discipline
- **AND THEN** readers do not observe a committed message in both open inbox work and archive as a partial move result

## MODIFIED Requirements

### Requirement: Filesystem mailbox groups support symlink-based mailbox registration
The filesystem mailbox transport SHALL allow each full-address entry under `mailboxes/` to be either a concrete mailbox directory inside the mail-group root or a symlink to that address's private mailbox directory outside the root.

A symlink-registered private mailbox directory SHALL expose the same mailbox substructure expected from an in-root mailbox directory.

The `archive/` directory in that substructure SHALL be an active mailbox box. The `drafts/` directory MAY remain reserved until a later draft workflow defines it.

#### Scenario: Address joins filesystem mail group through symlink registration
- **WHEN** an agent or human participant wants to join an existing filesystem mail group without relocating its mailbox projection directory into the shared root
- **THEN** the system allows `mailboxes/<address>` to be created as a symlink to that participant's private mailbox directory
- **AND THEN** delivery and mailbox reads can use that registration as the effective mailbox location for that full mailbox address

#### Scenario: Delivery follows symlink-registered mailbox target
- **WHEN** a sender delivers a mailbox message to a mailbox address whose `mailboxes/<address>` entry is a symlink
- **THEN** the filesystem mailbox transport writes the mailbox projection through that symlink-resolved mailbox directory
- **AND THEN** the canonical message store, lock files, and shared SQLite index remain anchored under the shared mail-group root

#### Scenario: Symlink-registered mailbox exposes active archive box
- **WHEN** a symlink-registered mailbox receives and archives a message
- **THEN** the archive projection is written through the symlink-resolved mailbox directory
- **AND THEN** the shared mailbox operation surface does not treat that `archive/` directory as a placeholder

## REMOVED Requirements

### Requirement: Archive and drafts directories are reserved placeholders in v1
**Reason**: `archive/` is now part of the active mailbox lifecycle and is the explicit completion target for processed mail.
**Migration**: No compatibility migration is required. Existing filesystem mailbox roots and fixtures may be recreated or updated in place for the active archive workflow.
