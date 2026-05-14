## ADDED Requirements

### Requirement: `houmao-mgr project mailbox messages clear` clears messages for one selected project mailbox address

`houmao-mgr project mailbox messages` SHALL expose a project-scoped wrapper for account-scoped message clearing:

```text
houmao-mgr project mailbox messages clear --address <full-address> [--dry-run] [--yes]
```

The command SHALL resolve the selected project overlay mailbox root using the same selected-overlay contract as the rest of the `houmao-mgr project mailbox` family and SHALL apply the account-scoped clear operation against:

```text
<overlay-root>/mailbox
```

The command SHALL mirror the generic `houmao-mgr mailbox messages clear` behavior after resolving the selected project mailbox root. It SHALL preserve project mailbox registrations and other project mailbox accounts' message visibility while clearing only the selected address.

The command SHALL accept `--dry-run` and `--yes` with the same safety semantics as the generic command.

The command SHALL include selected overlay details in the structured result using the same project mailbox result wording as the rest of the `houmao-mgr project mailbox` family.

#### Scenario: Project dry-run previews selected account clearing in the selected overlay

- **WHEN** `/repo/.houmao/mailbox` contains an active registration for `alice@houmao.localhost`
- **AND WHEN** that account has visible messages
- **AND WHEN** an operator runs `houmao-mgr project mailbox messages clear --address alice@houmao.localhost --dry-run` from `/repo`
- **THEN** the command reports planned selected-account clearing against `/repo/.houmao/mailbox`
- **AND THEN** it does not inspect or mutate the shared global mailbox root
- **AND THEN** it does not delete messages or unregister accounts

#### Scenario: Project selected account clear preserves other project accounts

- **WHEN** `/repo/.houmao/mailbox` contains active registrations for `alice@houmao.localhost` and `bob@houmao.localhost`
- **AND WHEN** one delivered message is projected to both accounts
- **AND WHEN** an operator runs `houmao-mgr project mailbox messages clear --address alice@houmao.localhost --yes` from `/repo/subdir`
- **THEN** the command removes the message from `alice@houmao.localhost` visibility under `/repo/.houmao/mailbox`
- **AND THEN** the command preserves `bob@houmao.localhost` visibility for the same message
- **AND THEN** the active project mailbox registrations remain registered for later delivery

#### Scenario: Project account clear preserves selected-overlay failure wording

- **WHEN** the selected project overlay mailbox root exists but is missing the shared mailbox index required for message clearing
- **AND WHEN** an operator runs `houmao-mgr project mailbox messages clear --address alice@houmao.localhost --dry-run`
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error recommends `houmao-mgr project mailbox init`
- **AND THEN** the operator does not see a Python traceback

#### Scenario: Project help lists account-scoped message clearing

- **WHEN** an operator runs `houmao-mgr project mailbox messages --help`
- **THEN** the help output lists `clear` as an account-scoped project mailbox message operation
- **AND THEN** the help output keeps `project mailbox clear-messages` as the all-account project mailbox-root reset
