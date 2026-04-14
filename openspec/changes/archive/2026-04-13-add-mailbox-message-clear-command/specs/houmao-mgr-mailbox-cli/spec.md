## ADDED Requirements

### Requirement: `houmao-mgr mailbox clear-messages` clears delivered messages while preserving registrations
`houmao-mgr mailbox clear-messages` SHALL clear delivered filesystem mailbox message content under one resolved mailbox root without requiring `houmao-server`.

The effective mailbox root SHALL resolve using the same project-aware root-selection contract as the generic `houmao-mgr mailbox` family.

The command SHALL preserve:

- all mailbox registration rows and their active, inactive, or stashed lifecycle state,
- registered mailbox account directories and symlinked private mailbox account targets,
- mailbox root protocol, rules, locks, staging, and mailbox directory layout.

The command SHALL remove delivered mail content and derived message state, including:

- canonical mailbox messages under `messages/`,
- mailbox projection artifacts for cleared messages,
- shared index rows for messages, recipients, message attachments, projections, mailbox state, and thread summaries,
- mailbox-local `mailbox.sqlite` message and thread state for registered accounts,
- managed-copy attachment artifacts owned by the mailbox root for cleared messages.

The command SHALL NOT delete external `path_ref` attachment targets.

The command SHALL accept `--dry-run`. In dry-run mode, it SHALL report planned message-clear actions without deleting files or mutating SQLite state.

The command SHALL require explicit destructive confirmation before applying changes. When `--yes` is present, the command SHALL apply without prompting. When `--yes` is absent and an interactive terminal is available, the command SHALL prompt before clearing delivered messages. When `--yes` is absent and no interactive terminal is available, the command SHALL fail clearly before clearing messages and direct the operator to rerun with `--yes` or `--dry-run`.

The command SHALL be idempotent: rerunning it against an already-cleared mailbox root SHALL preserve registrations and report no remaining delivered messages to clear.

#### Scenario: Dry-run previews mailbox-wide message clearing
- **WHEN** an operator runs `houmao-mgr mailbox clear-messages --mailbox-root /tmp/shared-mail --dry-run`
- **AND WHEN** `/tmp/shared-mail` contains registered mailbox accounts and delivered messages
- **THEN** the command reports planned clearing of delivered messages and derived message state
- **AND THEN** it does not delete canonical message files, projection artifacts, account registrations, or mailbox-local state

#### Scenario: Yes clears messages and preserves accounts
- **WHEN** an operator runs `houmao-mgr mailbox clear-messages --mailbox-root /tmp/shared-mail --yes`
- **AND WHEN** `/tmp/shared-mail` contains active registered mailbox accounts and delivered messages
- **THEN** the command removes delivered message content and derived message state from the mailbox root
- **AND THEN** the active mailbox registrations remain registered for later delivery
- **AND THEN** the registered mailbox account directories remain present

#### Scenario: Non-interactive apply without yes fails before clearing
- **WHEN** an operator runs `houmao-mgr mailbox clear-messages --mailbox-root /tmp/shared-mail` without `--yes`
- **AND WHEN** no interactive terminal is available
- **THEN** the command fails clearly before deleting delivered message content
- **AND THEN** the failure tells the operator to rerun with `--yes` or `--dry-run`

#### Scenario: External attachment targets are preserved
- **WHEN** a delivered mailbox message references an external `path_ref` attachment target
- **AND WHEN** an operator runs `houmao-mgr mailbox clear-messages --mailbox-root /tmp/shared-mail --yes`
- **THEN** the command removes mailbox-owned message metadata for that attachment
- **AND THEN** it does not delete the external attachment target path

#### Scenario: Existing cleanup command remains registration-scoped
- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail`
- **THEN** the cleanup command remains limited to inactive or stashed registration cleanup
- **AND THEN** it does not clear delivered messages or canonical mailbox history

#### Scenario: Mailbox help lists the clear-messages command
- **WHEN** an operator runs `houmao-mgr mailbox --help`
- **THEN** the help output lists `clear-messages` alongside the maintained filesystem mailbox administration commands
- **AND THEN** the help output keeps `cleanup` and `clear-messages` as separate command verbs
