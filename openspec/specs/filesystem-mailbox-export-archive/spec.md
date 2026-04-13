## Purpose
Define the portable filesystem mailbox export archive contract, including account selection, archive structure, manifest metadata, attachment handling, and symlink materialization policy.

## Requirements

### Requirement: Filesystem mailbox export archives are portable by default
The system SHALL export a filesystem mailbox snapshot into a regular directory tree that is portable across filesystems by default.

The default export mode SHALL materialize source symlink artifacts as regular directories or regular files in the output archive.

The default export mode SHALL verify that the final output archive contains no symlinks.

The export archive SHALL contain a `manifest.json` file at its root.

At minimum, the export archive SHALL contain these top-level paths when matching source artifacts exist:

- `messages/` for exported canonical message files,
- `accounts/` for exported account-local artifacts and per-registration metadata,
- `attachments/managed/` for exported mailbox-owned managed-copy attachments.

#### Scenario: Default export contains no symlinks
- **WHEN** a mailbox root contains canonical messages, projection symlinks, and a symlink-backed private mailbox registration
- **AND WHEN** an operator exports that mailbox root without requesting symlink preservation
- **THEN** the archive contains regular files for exported mailbox projections
- **AND THEN** the archive contains regular directories for exported symlink-backed mailbox accounts
- **AND THEN** the archive tree contains no symlink artifacts

#### Scenario: Export archive contains manifest and materialized account tree
- **WHEN** an operator exports a filesystem mailbox root with delivered mail
- **THEN** the output directory contains `manifest.json`
- **AND THEN** the output directory contains exported canonical messages under `messages/`
- **AND THEN** the output directory contains exported account metadata and mailbox-local state under `accounts/`

### Requirement: Filesystem mailbox export supports explicit account selection
The system SHALL require export scope to be explicit.

An export SHALL select either:

- all registration rows in the mailbox index, or
- every registration row whose address matches one of the explicitly selected full mailbox addresses.

When exporting all accounts, the system SHALL include every canonical message known to the shared mailbox `messages` table.

When exporting selected addresses, the system SHALL include messages visible through `mailbox_projections` for the selected registrations.

When a selected projection references a missing canonical message file, the system SHALL record a blocked artifact in the export result and manifest rather than silently dropping that message.

#### Scenario: All-account export includes every indexed canonical message
- **WHEN** a filesystem mailbox root contains multiple registered accounts and delivered messages
- **AND WHEN** the operator exports all accounts
- **THEN** the export selects every mailbox registration row from the shared mailbox index
- **AND THEN** the export includes every canonical message known to the shared `messages` table

#### Scenario: Selected-address export includes visible messages for that address
- **WHEN** a filesystem mailbox root contains messages visible to `alice@houmao.localhost` and `bob@houmao.localhost`
- **AND WHEN** the operator exports only `alice@houmao.localhost`
- **THEN** the export includes registrations for `alice@houmao.localhost`
- **AND THEN** the export includes messages visible through projection rows for those selected registrations
- **AND THEN** the export does not copy mailbox-local account artifacts for `bob@houmao.localhost`

### Requirement: Filesystem mailbox export records source and archive mappings in a manifest
The export manifest SHALL record enough metadata to audit what was copied, materialized, preserved, skipped, or blocked.

At minimum, `manifest.json` SHALL record:

- manifest schema version,
- source mailbox root,
- source mailbox protocol version,
- export timestamp,
- account selection mode,
- symlink mode,
- selected addresses,
- exported registration metadata,
- original registration mailbox path and mailbox entry path,
- archive-relative account paths,
- exported message ids and archive-relative canonical message paths,
- exported projection mappings,
- exported mailbox-local SQLite paths,
- copied managed-copy attachment mappings,
- manifest-only external `path_ref` attachment mappings,
- skipped artifacts,
- blocked artifacts.

#### Scenario: Manifest records original symlink-backed account paths
- **WHEN** an exported registration uses `mailbox_kind` `symlink`
- **THEN** the manifest records the original mailbox entry path
- **AND THEN** the manifest records the resolved source mailbox path
- **AND THEN** the manifest records the archive-relative materialized account path

#### Scenario: Manifest records projection materialization
- **WHEN** a source mailbox projection is materialized as a regular file in the archive
- **THEN** the manifest records the original projection path
- **AND THEN** the manifest records the canonical source message path
- **AND THEN** the manifest records the archive-relative materialized projection path

### Requirement: Filesystem mailbox export supports bounded symlink preservation
The system SHALL support an explicit symlink preservation mode for export targets that support symlinks.

When symlink preservation is requested, the exporter SHALL preserve only symlink relationships whose targets are also represented inside the archive.

Preserved symlinks SHALL be archive-internal relative symlinks.

When symlink preservation is requested and the target filesystem cannot create symlinks, the export SHALL fail clearly rather than silently falling back to materialization.

External symlink-backed mailbox account targets SHALL be materialized unless a later feature defines a separate external-symlink preservation mode.

#### Scenario: Preserve mode uses relative links for exported projections
- **WHEN** a source projection symlink points to a canonical message file that is exported into the archive
- **AND WHEN** the operator requests symlink preservation
- **THEN** the archive may contain a relative symlink for that projection
- **AND THEN** the symlink target resolves inside the archive tree

#### Scenario: Preserve mode fails when symlinks are unsupported
- **WHEN** the operator requests symlink preservation
- **AND WHEN** the target filesystem rejects symlink creation
- **THEN** the export fails clearly
- **AND THEN** the export does not report a materialized archive as though preserve mode succeeded

### Requirement: Filesystem mailbox export handles attachments conservatively
The exporter SHALL copy mailbox-owned managed-copy attachment artifacts that resolve under the mailbox root's managed attachment directory.

The exporter SHALL NOT copy external `path_ref` attachment targets by default.

For external `path_ref` attachment targets, the exporter SHALL record attachment metadata in `manifest.json`, including the original path and whether the target existed at export time.

When a managed-copy attachment path recorded in the mailbox index resolves outside the mailbox root's managed attachment directory, the exporter SHALL record a blocked artifact rather than copying that path.

#### Scenario: Managed-copy attachments are copied into the archive
- **WHEN** a delivered message references a managed-copy attachment under the mailbox root's managed attachment directory
- **AND WHEN** that message is included in the export
- **THEN** the export copies that attachment under `attachments/managed/`
- **AND THEN** the manifest records the source attachment path and archive-relative attachment path

#### Scenario: Path-ref attachments remain manifest-only by default
- **WHEN** a delivered message references an external `path_ref` attachment target
- **AND WHEN** that message is included in the export
- **THEN** the export does not copy the external target by default
- **AND THEN** the manifest records the external target path and whether it existed at export time

### Requirement: Filesystem mailbox export uses a consistent snapshot boundary
The exporter SHALL acquire mailbox locks before reading and copying selected mailbox state.

The exporter SHALL acquire selected address locks in lexicographic full-address order before acquiring `locks/index.lock`.

The exporter SHALL re-read selected mailbox index state while the lock set is held.

The exporter SHALL write to a temporary directory before publishing the final output directory.

The exporter SHALL fail when the requested output directory already exists.

#### Scenario: Export locks selected accounts before copying
- **WHEN** an operator exports selected mailbox addresses
- **THEN** the exporter acquires those address locks in sorted order
- **AND THEN** the exporter acquires the shared index lock before copying selected state

#### Scenario: Existing output directory is rejected
- **WHEN** the requested export output directory already exists
- **THEN** the export fails clearly before writing archive content into that directory
- **AND THEN** the exporter does not merge fresh export content with stale archive content
