## MODIFIED Requirements

### Requirement: `houmao-mgr mailbox` exposes local filesystem mailbox administration commands
`houmao-mgr` SHALL expose a top-level `mailbox` command family for local filesystem mailbox administration that does not require `houmao-server`.

At minimum, that family SHALL include:

- `init`
- `status`
- `register`
- `unregister`
- `repair`
- `cleanup`
- `clear-messages`
- `export`
- `accounts`
- `messages`

The family SHALL target the filesystem mailbox transport only in v1.

#### Scenario: Operator sees the local mailbox administration commands
- **WHEN** an operator runs `houmao-mgr mailbox --help`
- **THEN** the help output lists `init`, `status`, `register`, `unregister`, `repair`, `cleanup`, `clear-messages`, `export`, `accounts`, and `messages`
- **AND THEN** the command family is presented as a local mailbox administration surface rather than a server-backed API surface

## ADDED Requirements

### Requirement: `houmao-mgr mailbox export` writes a filesystem mailbox archive
`houmao-mgr mailbox export` SHALL export selected state from one resolved filesystem mailbox root into a portable archive directory without requiring `houmao-server`.

The command SHALL accept:

- `--output-dir <dir>`,
- either `--all-accounts` or one or more `--address <full-address>` values,
- `--symlink-mode materialize|preserve`.

The default `--symlink-mode` value SHALL be `materialize`.

The effective mailbox root SHALL resolve using the same project-aware root-selection contract as the generic `houmao-mgr mailbox` family.

When `--all-accounts` is present, the command SHALL export all mailbox registration rows and all canonical messages known to the shared mailbox index.

When one or more `--address` values are present, the command SHALL export registrations for those addresses and messages visible through projection rows for those registrations.

The command SHALL fail clearly when neither `--all-accounts` nor `--address` is provided.

The command SHALL fail clearly when `--all-accounts` and `--address` are both provided.

The command SHALL fail clearly when `--output-dir` already exists.

The command SHALL emit a structured payload identifying the resolved mailbox root, output directory, symlink mode, selected addresses, manifest path, summary counts, copied or materialized artifacts, skipped artifacts, and blocked artifacts.

#### Scenario: Export all accounts from an explicit mailbox root
- **WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive --all-accounts`
- **AND WHEN** `/tmp/shared-mail` contains registered accounts and delivered messages
- **THEN** the command writes a mailbox export archive under `/tmp/archive`
- **AND THEN** the result reports the archive manifest path
- **AND THEN** the default archive contains no symlink artifacts

#### Scenario: Export selected accounts from a project-aware mailbox root
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr mailbox export --output-dir /tmp/archive --address alice@houmao.localhost`
- **AND WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is unset
- **THEN** the command exports selected account state from `/repo/.houmao/mailbox`
- **AND THEN** the command does not inspect the shared global mailbox root

#### Scenario: Export requires explicit account scope
- **WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive`
- **THEN** the command fails clearly
- **AND THEN** the failure instructs the operator to choose `--all-accounts` or one or more `--address` values

#### Scenario: Export rejects conflicting account scope
- **WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive --all-accounts --address alice@houmao.localhost`
- **THEN** the command fails clearly before exporting
- **AND THEN** it does not create or modify `/tmp/archive`

#### Scenario: Preserve mode is explicit
- **WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive --all-accounts --symlink-mode preserve`
- **THEN** the command attempts to preserve supported archive-internal symlink relationships
- **AND THEN** the command reports the selected symlink mode in the structured payload

#### Scenario: Existing output directory fails
- **WHEN** `/tmp/archive` already exists
- **AND WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive --all-accounts`
- **THEN** the command fails clearly before writing archive content
- **AND THEN** the command does not merge new export artifacts into the existing directory
