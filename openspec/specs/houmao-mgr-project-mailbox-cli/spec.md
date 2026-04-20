# houmao-mgr-project-mailbox-cli Specification

## Purpose
Define the project-scoped `houmao-mgr project mailbox` workflow as a wrapper over the generic mailbox-root command family for the current repo-local project.
## Requirements
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

### Requirement: `project mailbox` resolves the current project's `.houmao/mailbox` root automatically

`houmao-mgr project mailbox ...` SHALL resolve the active overlay root in this order:

1. `HOUMAO_PROJECT_OVERLAY_DIR` when set,
2. nearest-ancestor project discovery from the caller's current working directory.

When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.

After resolving the active overlay root, `houmao-mgr project mailbox ...` SHALL apply the selected mailbox-root operation against:

```text
<overlay-root>/mailbox
```

The operator SHALL NOT need to pass `--mailbox-root` for ordinary project-scoped mailbox work.

If no project overlay is discovered under the selected overlay root, `project mailbox ...` SHALL fail explicitly rather than silently falling back to the shared global mailbox root.

#### Scenario: Register uses the env-selected project mailbox root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project mailbox register --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice` from `/repo/subdir`
- **THEN** the command applies mailbox registration against `/tmp/ci-overlay/mailbox`
- **AND THEN** the operator does not need to provide an explicit `--mailbox-root`

#### Scenario: Messages list reads from the env-selected project mailbox root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/mailbox` contains an active mailbox registration for `AGENTSYS-alice@agents.localhost`
- **AND WHEN** an operator runs `houmao-mgr project mailbox messages list --address AGENTSYS-alice@agents.localhost` from `/repo`
- **THEN** the command lists messages for that address from `/tmp/ci-overlay/mailbox`
- **AND THEN** it does not inspect the shared global mailbox root instead

#### Scenario: Missing overlay under env-selected overlay root fails clearly
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` does not exist
- **AND WHEN** an operator runs `houmao-mgr project mailbox status`
- **THEN** the command fails explicitly
- **AND THEN** it does not silently inspect the shared global mailbox root

#### Scenario: Register uses the discovered project mailbox root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project mailbox register --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice` from `/repo/subdir`
- **THEN** the command applies mailbox registration against `/repo/.houmao/mailbox`
- **AND THEN** the operator does not need to provide an explicit `--mailbox-root`

### Requirement: `project mailbox register` mirrors the generic mailbox overwrite-confirmation contract
`houmao-mgr project mailbox register` SHALL apply the same overwrite-confirmation contract as `houmao-mgr mailbox register` after resolving the current project's mailbox root automatically.

The project-scoped register command SHALL accept `--yes`.
When the requested registration path would replace existing durable mailbox state under the resolved project mailbox root, the command SHALL prompt interactively before destructive replacement unless `--yes` is present.
When no interactive terminal is available and `--yes` is absent, the command SHALL fail clearly before destructive replacement.

#### Scenario: Project mailbox register prompts before overwrite
- **WHEN** `/repo/.houmao/` exists
- **AND WHEN** an operator runs `houmao-mgr project mailbox register --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **AND WHEN** the resolved project mailbox root contains a replaceable conflict for that mailbox address
- **AND WHEN** an interactive terminal is available
- **THEN** the command prompts before destructive replacement
- **AND THEN** any confirmed replacement is applied against `/repo/.houmao/mailbox`

#### Scenario: Project mailbox register accepts yes for non-interactive overwrite
- **WHEN** `/repo/.houmao/` exists
- **AND WHEN** an operator runs `houmao-mgr project mailbox register --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice --yes`
- **AND WHEN** the resolved project mailbox root contains a replaceable conflict for that mailbox address
- **THEN** the command applies the overwrite-confirmed registration path without prompting
- **AND THEN** it applies that change against `/repo/.houmao/mailbox`

### Requirement: `houmao-mgr project mailbox messages` is structural inspection, not participant-local state reporting

The native `houmao-mgr project mailbox messages list` and `houmao-mgr project mailbox messages get` commands SHALL expose structural inspection over the current project's mailbox root for one explicitly selected mailbox address.

Those commands MAY return canonical message metadata and address-scoped projection metadata for the selected address, including message identity, thread identity, projection folder, projection path, canonical path, sender metadata, recipient metadata, body content, headers, and attachments.

Those commands SHALL NOT report participant-local mutable mailbox view-state fields such as `read`, `starred`, `archived`, or `deleted`, even though the command is scoped to one explicit address.

When an operator needs workflow state such as whether a processed message is still actionable unread mail for one agent, the supported surface SHALL be actor-scoped mail commands such as `houmao-mgr agents mail ...` rather than `houmao-mgr project mailbox messages ...`.

#### Scenario: Project mailbox message list omits participant-local mutable state

- **WHEN** an operator runs `houmao-mgr project mailbox messages list --address alice@agents.localhost`
- **THEN** the command returns structural message summaries for that selected project-local address projection
- **AND THEN** each message summary may include fields such as `message_id`, `thread_id`, `subject`, `folder`, `projection_path`, and `canonical_path`
- **AND THEN** the payload does not include `read`, `starred`, `archived`, or `deleted`

#### Scenario: Project mailbox message get omits participant-local mutable state

- **WHEN** an operator runs `houmao-mgr project mailbox messages get --address alice@agents.localhost --message-id msg-123`
- **THEN** the command returns canonical message details together with the selected project-local address projection metadata
- **AND THEN** the payload may include sender, recipients, headers, body content, attachments, `folder`, and `projection_path`
- **AND THEN** the payload does not claim a single authoritative participant-local read, starred, archived, or deleted state

#### Scenario: Project mailbox verification guidance points operators to actor-scoped mail state

- **WHEN** an operator needs to verify that one managed agent has finished processing mailbox work and no longer has actionable unread mail
- **THEN** the supported completion boundary is an actor-scoped command such as `houmao-mgr agents mail list --agent-name alice --read-state unread`
- **AND THEN** `houmao-mgr project mailbox messages list|get` remains a structural inspection surface rather than the source of truth for that completion state

### Requirement: Project mailbox wording describes the selected overlay mailbox root
Maintained `houmao-mgr project mailbox ...` help text, failures, and operator-facing result wording SHALL describe the mailbox scope as the selected overlay mailbox root rather than as a hard-coded current-project `.houmao/mailbox` path.

When `project mailbox init` or another stateful project-mailbox command bootstraps the selected overlay implicitly, the operator-facing result SHALL surface that bootstrap outcome explicitly.

When a non-creating project-mailbox command cannot resolve an active overlay, the failure SHALL describe the selected overlay root for that invocation and that the command did not fall back to the generic shared mailbox root.

#### Scenario: Help text describes the selected overlay mailbox root
- **WHEN** an operator runs `houmao-mgr project mailbox --help`
- **THEN** the help output describes the surface as mailbox-root operations against `mailbox/` under the selected project overlay
- **AND THEN** it does not imply that the command only targets a caller-local literal `.houmao/mailbox` path

#### Scenario: Missing overlay failure stays tied to the selected overlay root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** no project overlay exists there
- **AND WHEN** an operator runs a maintained non-creating `houmao-mgr project mailbox ...` command
- **THEN** the failure identifies `/tmp/ci-overlay` as the selected overlay root for that invocation
- **AND THEN** it states that the command did not fall back to the generic shared mailbox root

### Requirement: `houmao-mgr project mailbox` mirrors the reserved operator mailbox behavior
The project-scoped mailbox CLI SHALL mirror the reserved operator mailbox-account behavior of the generic filesystem mailbox CLI under the selected project mailbox root.

`houmao-mgr project mailbox init` SHALL provision or confirm `HOUMAO-operator@houmao.localhost` under the selected overlay mailbox root.

`houmao-mgr project mailbox accounts list|get` SHALL expose that reserved account as project-local mailbox registration state instead of hiding it.

Project-scoped destructive lifecycle commands SHALL protect that reserved account in the same way as the generic mailbox CLI.

#### Scenario: Project mailbox init confirms the reserved operator account
- **WHEN** an operator runs `houmao-mgr project mailbox init`
- **THEN** the selected project mailbox root contains the reserved account `HOUMAO-operator@houmao.localhost`
- **AND THEN** the project-scoped mailbox CLI can inspect that account through `accounts list|get`

#### Scenario: Project mailbox cleanup preserves the reserved operator account
- **WHEN** an operator runs `houmao-mgr project mailbox cleanup`
- **AND WHEN** the selected project mailbox root contains the active reserved operator account
- **THEN** cleanup preserves that account
- **AND THEN** the project mailbox root keeps the operator-origin sender registration available for later mailbox delivery
