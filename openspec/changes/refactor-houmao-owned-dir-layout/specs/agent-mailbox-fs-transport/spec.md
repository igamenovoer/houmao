## MODIFIED Requirements

### Requirement: Filesystem mailbox transport uses an env-configurable mailbox content root with deterministic internal layout
The filesystem mailbox transport SHALL persist mailbox artifacts under a mailbox content root that is configurable through runtime-managed env bindings.

When no explicit mailbox content root is configured, the filesystem mailbox transport SHALL default that content root to the Houmao mailbox root `~/.houmao/mailbox` rather than deriving it from the runtime root.

When no explicit mailbox content root is configured and `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the effective Houmao mailbox root SHALL be derived from that env-var override before runtime publishes the mailbox content root through env bindings such as `AGENTSYS_MAILBOX_FS_ROOT`.

The filesystem mailbox transport SHALL require a symlink-capable local filesystem for address-based mailbox registration and mailbox projection writes.

That mailbox subtree SHALL include at minimum:

- `protocol-version.txt`
- a canonical message store
- a shared `rules/` directory for mailbox-local protocol guidance
- mailbox projection registrations by full mailbox address
- a SQLite index
- lock-file locations
- a staging area for in-progress writes

#### Scenario: Creating a filesystem mailbox initializes required layout at an explicit mailbox root
- **WHEN** a filesystem mailbox transport is initialized with an explicit mailbox content root binding
- **THEN** the system creates or validates the mailbox subtree under that effective mailbox content root
- **AND THEN** the mailbox subtree contains `protocol-version.txt` plus the required directories and index path for canonical messages, mailbox projections, locks, and staging

#### Scenario: Creating a filesystem mailbox falls back to the Houmao mailbox root
- **WHEN** a filesystem mailbox transport is initialized without an explicit mailbox content root binding
- **THEN** the system derives the effective filesystem mailbox content root from the Houmao mailbox root default
- **AND THEN** the resulting mailbox subtree uses that derived default location while preserving the same internal layout

#### Scenario: Mailbox-root env-var override redirects the default mailbox root
- **WHEN** `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a filesystem mailbox transport is initialized without an explicit mailbox content root binding
- **THEN** the system derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the resulting mailbox subtree uses that env-var-selected location while preserving the same internal layout

#### Scenario: Unsupported symlink capability fails explicitly
- **WHEN** the effective mailbox filesystem cannot create or resolve the symlinks required for mailbox registration or inbox and sent projections
- **THEN** the filesystem mailbox transport fails initialization or delivery explicitly
- **AND THEN** the transport does not silently replace those symlinks with copied or duplicated message files
