## ADDED Requirements

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
