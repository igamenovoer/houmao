## ADDED Requirements

### Requirement: `houmao-mgr mailbox messages clear` clears messages for one selected mailbox address

`houmao-mgr mailbox messages` SHALL expose an account-scoped destructive clear command:

```text
houmao-mgr mailbox messages clear --address <full-address> [--mailbox-root <path>] [--dry-run] [--yes]
```

The command SHALL resolve the effective mailbox root using the same project-aware root-selection contract as the rest of the generic `houmao-mgr mailbox` family.

The command SHALL require `--address` to identify one active mailbox registration under the resolved mailbox root. If the address does not resolve to an active registration, the command SHALL fail before mutating filesystem or SQLite state.

The command SHALL preserve:

- the selected mailbox registration,
- all other mailbox registrations,
- other registered accounts' message projections and mailbox-local message state,
- canonical message files and shared message index rows for messages that remain projected to at least one other account,
- external `path_ref` attachment targets.

The command SHALL remove or clear:

- mailbox projection artifacts for the selected address,
- shared projection rows for the selected address,
- mailbox-local message and thread state for the selected address,
- canonical message files and shared message index rows only when the selected address held the last remaining projection for those messages,
- mailbox-owned managed-copy attachment artifacts only when no retained message references them.

The command SHALL accept `--dry-run`. In dry-run mode, it SHALL report planned, preserved, and blocked actions without deleting files or mutating SQLite state.

The command SHALL require explicit destructive confirmation before applying changes. When `--yes` is present, the command SHALL apply without prompting. When `--yes` is absent and an interactive terminal is available, the command SHALL prompt before clearing selected account messages. When `--yes` is absent and no interactive terminal is available, the command SHALL fail clearly before clearing messages and direct the operator to rerun with `--yes` or `--dry-run`.

The command SHALL return a structured cleanup-style payload whose scope distinguishes account-scoped message clearing from the existing all-account `houmao-mgr mailbox clear-messages` operation.

The existing `houmao-mgr mailbox clear-messages` command SHALL remain the all-account mailbox-root delivered-message reset.

#### Scenario: Dry-run previews selected account message clearing

- **WHEN** `/tmp/shared-mail` contains an active registration for `alice@houmao.localhost`
- **AND WHEN** delivered messages are visible to `alice@houmao.localhost`
- **AND WHEN** an operator runs `houmao-mgr mailbox messages clear --mailbox-root /tmp/shared-mail --address alice@houmao.localhost --dry-run`
- **THEN** the command reports planned clearing actions for `alice@houmao.localhost`
- **AND THEN** the command does not delete projection artifacts, canonical message files, managed-copy attachments, account registrations, or mailbox-local SQLite state

#### Scenario: Yes clears one account while preserving another account's visibility

- **WHEN** `/tmp/shared-mail` contains active registrations for `alice@houmao.localhost` and `bob@houmao.localhost`
- **AND WHEN** one delivered message is projected to both accounts
- **AND WHEN** an operator runs `houmao-mgr mailbox messages clear --mailbox-root /tmp/shared-mail --address alice@houmao.localhost --yes`
- **THEN** `houmao-mgr mailbox messages list --mailbox-root /tmp/shared-mail --address alice@houmao.localhost` no longer lists that message
- **AND THEN** `houmao-mgr mailbox messages list --mailbox-root /tmp/shared-mail --address bob@houmao.localhost` still lists that message
- **AND THEN** the canonical message file remains present for `bob@houmao.localhost`

#### Scenario: Last projection clear removes shared mailbox-owned artifacts

- **WHEN** `/tmp/shared-mail` contains an active registration for `alice@houmao.localhost`
- **AND WHEN** a delivered message is projected only to `alice@houmao.localhost`
- **AND WHEN** that message has a mailbox-owned managed-copy attachment and an external `path_ref` attachment
- **AND WHEN** an operator runs `houmao-mgr mailbox messages clear --mailbox-root /tmp/shared-mail --address alice@houmao.localhost --yes`
- **THEN** the command removes the selected account projection artifact
- **AND THEN** the command removes the canonical message file and shared message index rows for the message
- **AND THEN** the command removes the unreferenced mailbox-owned managed-copy attachment artifact
- **AND THEN** the command preserves the external `path_ref` attachment target

#### Scenario: Non-interactive apply without yes fails before selected account clearing

- **WHEN** `/tmp/shared-mail` contains messages visible to `alice@houmao.localhost`
- **AND WHEN** no interactive terminal is available
- **AND WHEN** an operator runs `houmao-mgr mailbox messages clear --mailbox-root /tmp/shared-mail --address alice@houmao.localhost` without `--yes`
- **THEN** the command fails clearly before deleting delivered message content
- **AND THEN** the error text directs the operator to rerun with `--yes` or `--dry-run`

#### Scenario: Missing active account fails before mutation

- **WHEN** `/tmp/shared-mail` does not contain an active registration for `missing@houmao.localhost`
- **AND WHEN** an operator runs `houmao-mgr mailbox messages clear --mailbox-root /tmp/shared-mail --address missing@houmao.localhost --yes`
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the command does not delete files or mutate mailbox SQLite state
