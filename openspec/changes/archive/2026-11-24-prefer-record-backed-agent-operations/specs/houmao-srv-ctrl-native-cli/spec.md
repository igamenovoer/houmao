# Spec Delta

## MODIFIED Requirements

### Requirement: `houmao-mgr agents gateway` exposes `--target-tmux-session` for explicit outside-tmux targeting
Gateway commands under `agents single` SHALL accept exactly one group-level agent ID, friendly name, or supported local tmux alias. `agents self gateway` SHALL use verified current-session authority.

#### Scenario: Gateway operations share the explicit tmux selector

- **WHEN** an operator uses a gateway alias on `agents single`
- **THEN** the option is a group-level selector for local gateway commands

#### Scenario: An explicit tmux session supplies local authority

- **WHEN** the caller's enclosing tmux server does not contain the selected session
- **THEN** a unique fresh registry match resolves the peer's local owner

#### Scenario: Outside-tmux gateway status resolves by explicit tmux session selector

- **WHEN** an operator runs `houmao-mgr agents single --target-tmux-session HOUMAO-gpu-coder-1-1775467167530 gateway status`
- **THEN** the command resolves a unique fresh local registry record for that alias
- **AND THEN** it returns the selected owner's recorded or verified gateway status

#### Scenario: Gateway prompt supports the tmux-session selector across the command family

- **WHEN** an operator runs `houmao-mgr agents single --target-tmux-session HOUMAO-gpu-coder-1-1775467167530 gateway prompt --prompt hi`
- **THEN** the command submits the gateway-mediated request to that selected target

#### Scenario: Pair ports apply only to identity selectors

- **WHEN** an operator supplies `--pair-port` with a selected-agent gateway command
- **THEN** the command accepts the override only with an explicit agent ID or name
- **AND THEN** the override selects the pair authority and is distinct from the gateway listener port

#### Scenario: Port override is rejected for tmux-session targeting

- **WHEN** an operator combines a tmux alias with `--pair-port`
- **THEN** the CLI reports that pair selection requires an explicit agent ID or name

#### Scenario: Explicit pair-authority override uses the clearer flag name

- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 gateway status --pair-port 9891`
- **THEN** the command targets the pair authority at port `9891`

### Requirement: `houmao-mgr agents gateway reminders` supports the same targeting contract as the rest of `agents gateway`
Gateway reminder operations SHALL use the same local registry aliases, explicit agent selectors, and verified self authority as other gateway operations. Explicit pair selection SHALL support the maintained passive server.

#### Scenario: Reminder operations accept the standard gateway selectors

- **WHEN** an operator lists reminders with an explicit local registry alias
- **THEN** the command uses the uniquely selected owner

#### Scenario: Current-session reminder inspection resolves the owning managed session

- **WHEN** an agent runs `houmao-mgr agents self gateway reminders list`
- **THEN** the command uses the current runtime's verified manifest and signer

#### Scenario: Pair-backed reminder creation works through passive-server authority

- **WHEN** an operator creates a reminder with an explicit agent ID and `--pair-port`
- **AND WHEN** the addressed pair authority reports `houmao_service == "houmao-passive-server"`
- **THEN** the manager routes the create request through the addressed agent's passive-server gateway proxy
