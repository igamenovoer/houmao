## ADDED Requirements

### Requirement: Mailbox reference documentation explains the export archive workflow
The mailbox reference documentation SHALL document the supported filesystem mailbox export workflow.

At minimum, the documentation SHALL explain:

- `houmao-mgr mailbox export` for an arbitrary resolved filesystem mailbox root,
- `houmao-mgr project mailbox export` for the selected project overlay mailbox root,
- explicit account scope with `--all-accounts` or repeated `--address`,
- `--output-dir`,
- default symlink materialization,
- optional `--symlink-mode preserve`,
- that default exports contain no symlinks,
- the archive's `manifest.json` role,
- the high-level archive directory structure,
- managed-copy attachment copying,
- external `path_ref` attachment manifest-only behavior,
- why the maintained export command is preferred over raw recursive mailbox-root copying.

#### Scenario: Reader learns the maintained export commands
- **WHEN** a reader opens mailbox reference docs to archive filesystem mailbox state
- **THEN** the docs identify `houmao-mgr mailbox export` and `houmao-mgr project mailbox export` as the maintained command surfaces
- **AND THEN** the docs show how to choose all-account or selected-address export scope

#### Scenario: Reader understands default symlink materialization
- **WHEN** a reader needs an archive that can be moved to a filesystem without symlink support
- **THEN** the docs explain that default mailbox export materializes symlinks
- **AND THEN** the docs explain that `--symlink-mode preserve` is the explicit opt-in path for supported archive-internal symlinks

#### Scenario: Reader understands attachment boundaries
- **WHEN** a reader exports mailbox messages that reference attachments
- **THEN** the docs explain that managed-copy attachments under the mailbox root are copied
- **AND THEN** the docs explain that external `path_ref` targets are recorded in the manifest rather than copied by default
