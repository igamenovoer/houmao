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
- repair and cleanup

The help text SHALL present `project mailbox` as mailbox-root operations for the current repo-local project rather than as a managed-agent mailbox-binding surface.

#### Scenario: Project mailbox help mirrors the generic mailbox command model
- **WHEN** an operator runs `houmao-mgr project mailbox --help`
- **THEN** the help output exposes the project-scoped mailbox-root verbs that correspond to the generic `houmao-mgr mailbox` surface
- **AND THEN** the help output presents `project mailbox` as mailbox-root administration for the current project

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
- **THEN** the supported completion boundary is an actor-scoped command such as `houmao-mgr agents mail check --agent-name alice --unread-only`
- **AND THEN** `houmao-mgr project mailbox messages list|get` remains a structural inspection surface rather than the source of truth for that completion state

