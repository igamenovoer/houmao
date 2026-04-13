## MODIFIED Requirements

### Requirement: `houmao-mgr project mailbox` exposes the generic mailbox-root command family under project scope

`houmao-mgr` SHALL expose `houmao-mgr project mailbox ...` as a project-scoped wrapper over the generic mailbox-root command family.

At minimum, `project mailbox` SHALL expose the same verbs supported by the generic `houmao-mgr mailbox` surface for:

- root bootstrap and status
- mailbox-address lifecycle
- mailbox account inspection
- direct mailbox message listing and retrieval
- repair, cleanup, delivered-message clearing, and export

The help text SHALL present `project mailbox` as mailbox-root operations for the current repo-local project rather than as a managed-agent mailbox-binding surface.

#### Scenario: Project mailbox help mirrors the generic mailbox command model
- **WHEN** an operator runs `houmao-mgr project mailbox --help`
- **THEN** the help output exposes the project-scoped mailbox-root verbs that correspond to the generic `houmao-mgr mailbox` surface
- **AND THEN** the help output presents `project mailbox` as mailbox-root administration for the current project

## ADDED Requirements

### Requirement: `houmao-mgr project mailbox export` exports the selected overlay mailbox root
`houmao-mgr project mailbox export` SHALL expose the same mailbox export behavior as `houmao-mgr mailbox export` after resolving the selected project overlay mailbox root.

The command SHALL accept:

- `--output-dir <dir>`,
- either `--all-accounts` or one or more `--address <full-address>` values,
- `--symlink-mode materialize|preserve`.

The command SHALL apply the export operation against:

```text
<overlay-root>/mailbox
```

The command SHALL include selected overlay details in the structured result using the same project mailbox result wording as the rest of the `houmao-mgr project mailbox` family.

#### Scenario: Project mailbox export writes an all-account archive
- **WHEN** `/repo/.houmao/mailbox` contains registered accounts and delivered messages
- **AND WHEN** an operator runs `houmao-mgr project mailbox export --output-dir /tmp/archive --all-accounts` from `/repo`
- **THEN** the command exports mailbox state from `/repo/.houmao/mailbox`
- **AND THEN** the command writes a mailbox export archive under `/tmp/archive`
- **AND THEN** the structured result identifies `/repo/.houmao` as the selected overlay root

#### Scenario: Project mailbox export writes a selected-account archive
- **WHEN** `/repo/.houmao/mailbox` contains an account for `alice@houmao.localhost`
- **AND WHEN** an operator runs `houmao-mgr project mailbox export --output-dir /tmp/archive --address alice@houmao.localhost` from `/repo/subdir`
- **THEN** the command exports selected account state from `/repo/.houmao/mailbox`
- **AND THEN** the operator does not need to provide `--mailbox-root`

#### Scenario: Project mailbox export preserves root boundary
- **WHEN** `/repo/.houmao/mailbox` is the selected project mailbox root
- **AND WHEN** a different shared mailbox root exists under `HOUMAO_GLOBAL_MAILBOX_DIR`
- **AND WHEN** an operator runs `houmao-mgr project mailbox export --output-dir /tmp/archive --all-accounts`
- **THEN** the command exports from `/repo/.houmao/mailbox`
- **AND THEN** it does not inspect the generic shared mailbox root
