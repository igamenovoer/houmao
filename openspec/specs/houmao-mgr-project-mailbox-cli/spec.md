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

`houmao-mgr project mailbox ...` SHALL discover the nearest project overlay and apply the selected mailbox-root operation against:

```text
<project-root>/.houmao/mailbox
```

The operator SHALL NOT need to pass `--mailbox-root` for ordinary project-scoped mailbox work.

If no project overlay is discovered, `project mailbox ...` SHALL fail explicitly rather than silently falling back to the shared global mailbox root.

#### Scenario: Register uses the discovered project mailbox root
- **WHEN** `/repo/.houmao/` exists
- **AND WHEN** an operator runs `houmao-mgr project mailbox register --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice` from `/repo/subdir`
- **THEN** the command applies mailbox registration against `/repo/.houmao/mailbox`
- **AND THEN** the operator does not need to provide an explicit `--mailbox-root`

#### Scenario: Messages list reads from the discovered project mailbox root
- **WHEN** `/repo/.houmao/mailbox` contains an active mailbox registration for `AGENTSYS-alice@agents.localhost`
- **AND WHEN** an operator runs `houmao-mgr project mailbox messages list --address AGENTSYS-alice@agents.localhost` from `/repo`
- **THEN** the command lists messages for that address from `/repo/.houmao/mailbox`
- **AND THEN** it does not inspect the shared global mailbox root instead

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
