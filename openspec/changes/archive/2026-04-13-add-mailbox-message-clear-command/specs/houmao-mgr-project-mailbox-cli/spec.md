## ADDED Requirements

### Requirement: `houmao-mgr project mailbox clear-messages` clears selected overlay messages while preserving registrations
`houmao-mgr project mailbox clear-messages` SHALL expose the same delivered-message clearing behavior as `houmao-mgr mailbox clear-messages` after resolving the selected project overlay mailbox root.

The command SHALL resolve the project mailbox root using the same selected-overlay contract as the rest of the `houmao-mgr project mailbox` family and SHALL apply the message-clear operation against:

```text
<overlay-root>/mailbox
```

The command SHALL preserve project mailbox account registrations and mailbox account directories while removing delivered message content and derived message state from the selected project mailbox root.

The command SHALL accept `--dry-run` and `--yes` with the same safety semantics as the generic command.

#### Scenario: Project dry-run previews selected overlay message clearing
- **WHEN** `/repo/.houmao/` exists
- **AND WHEN** `/repo/.houmao/mailbox` contains registered mailbox accounts and delivered messages
- **AND WHEN** an operator runs `houmao-mgr project mailbox clear-messages --dry-run` from `/repo`
- **THEN** the command reports planned clearing against `/repo/.houmao/mailbox`
- **AND THEN** it does not inspect or mutate the shared global mailbox root
- **AND THEN** it does not delete messages or unregister accounts

#### Scenario: Project clear preserves selected overlay accounts
- **WHEN** `/repo/.houmao/` exists
- **AND WHEN** `/repo/.houmao/mailbox` contains active mailbox registrations and delivered messages
- **AND WHEN** an operator runs `houmao-mgr project mailbox clear-messages --yes` from `/repo/subdir`
- **THEN** the command removes delivered message content and derived message state from `/repo/.houmao/mailbox`
- **AND THEN** the active project mailbox registrations remain registered for later delivery

#### Scenario: Project help lists clear-messages
- **WHEN** an operator runs `houmao-mgr project mailbox --help`
- **THEN** the help output lists `clear-messages` as a project-scoped mailbox-root operation
- **AND THEN** the help output keeps `cleanup` and `clear-messages` as separate project mailbox command verbs
