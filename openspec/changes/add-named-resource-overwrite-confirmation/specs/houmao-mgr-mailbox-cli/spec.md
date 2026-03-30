## MODIFIED Requirements

### Requirement: `houmao-mgr mailbox register` and `unregister` expose operator mailbox lifecycle control
`houmao-mgr mailbox register` and `houmao-mgr mailbox unregister` SHALL expose operator-facing mailbox lifecycle control for filesystem mailbox addresses.

`register` SHALL accept a full mailbox address and owner principal id, SHALL use explicit registration modes, and SHALL accept `--yes` for non-interactive overwrite confirmation.
`unregister` SHALL accept a full mailbox address and SHALL use explicit deregistration modes, defaulting to `deactivate`.

When a requested registration path would replace existing durable mailbox state or an existing mailbox entry artifact, the CLI SHALL require explicit operator confirmation before applying the destructive replacement.
This confirmation requirement SHALL apply whether destructive replacement was requested explicitly through `--mode force` or reached from the default safe registration flow after conflict detection.
When `--yes` is present, the CLI SHALL apply the overwrite-confirmed registration path without prompting.
When `--yes` is absent and an interactive terminal is available, the CLI SHALL prompt the operator before applying the destructive replacement.
When `--yes` is absent and no interactive terminal is available, the CLI SHALL fail clearly before destructive replacement and direct the operator to rerun with `--yes` or choose a non-destructive registration mode.
If the operator declines the overwrite prompt, the command SHALL abort without replacing the existing durable mailbox state.
The CLI SHALL preserve the established `safe`, `force`, and `stash` registration-mode vocabulary; this change SHALL NOT reinterpret `stash` as an automatic fallback for overwrite conflicts.

#### Scenario: Operator registers an in-root mailbox address safely
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **AND WHEN** no destructive replacement is required
- **THEN** the command creates or reuses the active in-root mailbox registration for that address using safe registration semantics
- **AND THEN** the result reports the resulting active registration identity

#### Scenario: Operator confirms overwrite after a safe registration conflict
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **AND WHEN** the default safe registration flow detects a replaceable conflict for that mailbox address
- **AND WHEN** an interactive terminal is available
- **AND WHEN** the operator confirms overwrite
- **THEN** the command applies destructive replacement semantics for that request
- **AND THEN** the result reports the resulting active registration identity

#### Scenario: Operator declines overwrite after a safe registration conflict
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **AND WHEN** the default safe registration flow detects a replaceable conflict for that mailbox address
- **AND WHEN** an interactive terminal is available
- **AND WHEN** the operator declines overwrite
- **THEN** the command aborts
- **AND THEN** the existing mailbox state remains unchanged

#### Scenario: Non-interactive conflict without yes fails before replacement
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **AND WHEN** no interactive terminal is available
- **AND WHEN** `--yes` is not present
- **THEN** the command fails clearly before destructive replacement
- **AND THEN** the existing mailbox state remains unchanged

#### Scenario: Yes skips overwrite prompt
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice --yes`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **THEN** the command applies the overwrite-confirmed registration path without prompting
- **AND THEN** the result reports the resulting active registration identity

#### Scenario: Operator unregisters a mailbox address without deleting canonical history
- **WHEN** an operator runs `houmao-mgr mailbox unregister --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost`
- **THEN** the command deactivates the active mailbox registration for that address by default
- **AND THEN** future delivery to that address requires a later active registration
- **AND THEN** canonical mailbox history remains preserved
