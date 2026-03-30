## Purpose
Define late filesystem mailbox registration for existing local managed agents, including session binding persistence and activation-state reporting by runtime posture.

## Requirements
### Requirement: `houmao-mgr agents mailbox` exposes late mailbox registration for local managed agents
`houmao-mgr` SHALL expose an `agents mailbox` command family for late filesystem mailbox registration on existing local managed agents.

At minimum, that family SHALL include:

- `status`
- `register`
- `unregister`

The family SHALL resolve its target through local managed-agent discovery and SHALL NOT require `houmao-server` in v1.
If the selected managed agent is server-backed rather than locally controlled, the command SHALL fail explicitly instead of pretending that late local mailbox registration is available.

#### Scenario: Operator sees the late mailbox registration commands
- **WHEN** an operator runs `houmao-mgr agents mailbox --help`
- **THEN** the help output lists `status`, `register`, and `unregister`
- **AND THEN** the command family is presented as a local late mailbox registration surface for existing managed agents

### Requirement: `houmao-mgr agents mailbox register` creates shared registration and persists session mailbox binding
`houmao-mgr agents mailbox register` SHALL register filesystem mailbox support for an existing local managed agent after launch or join.

At minimum, the command SHALL:

1. resolve the local managed-agent controller,
2. resolve the filesystem mailbox root from explicit override, environment override, or default,
3. derive default mailbox principal and full address from the managed-agent identity when the operator does not supply explicit values,
4. ensure the target address has an active shared mailbox registration using safe registration semantics by default and requiring explicit operator confirmation before any destructive replacement,
5. attach the resolved mailbox binding to the managed session,
6. persist that mailbox binding into the session manifest and registry-visible mailbox summary.
7. accept `--yes` so an operator can confirm overwrite without an interactive prompt.

When the requested registration path would replace existing durable mailbox state, the CLI SHALL require explicit operator confirmation before applying the destructive replacement.
This confirmation requirement SHALL apply whether destructive replacement was requested explicitly through registration mode selection or reached from the default safe flow after conflict detection.
When `--yes` is absent and an interactive terminal is available, the CLI SHALL prompt before destructive replacement.
When `--yes` is absent and no interactive terminal is available, the CLI SHALL fail clearly before replacing shared mailbox state or mutating the managed session's mailbox binding.
If the operator declines the overwrite prompt, the command SHALL abort without replacing shared mailbox state and without mutating the managed session's mailbox binding.

After successful registration, later `houmao-mgr agents mail ...` commands SHALL treat the session as mailbox-enabled when the returned activation state is `active`.

#### Scenario: Headless local managed agent becomes mailbox-enabled immediately
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a local headless managed session
- **AND WHEN** no destructive replacement is required
- **THEN** the command safely registers `alice`'s mailbox address under `/tmp/shared-mail`
- **AND THEN** the session manifest persists the resulting mailbox binding
- **AND THEN** the command reports activation state `active`
- **AND THEN** later `houmao-mgr agents mail status --agent-name alice` succeeds without any launch-time mailbox flag

#### Scenario: Operator confirms overwrite for late mailbox registration
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **AND WHEN** an interactive terminal is available
- **AND WHEN** the operator confirms overwrite
- **THEN** the command applies the overwrite-confirmed registration path
- **AND THEN** it persists the resulting mailbox binding into the session manifest and registry-visible mailbox summary

#### Scenario: Non-interactive late registration conflict without yes fails clearly
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **AND WHEN** no interactive terminal is available
- **AND WHEN** `--yes` is not present
- **THEN** the command fails clearly before replacing shared mailbox state
- **AND THEN** it does not mutate the managed session's mailbox binding

#### Scenario: Yes skips overwrite prompt for late mailbox registration
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail --yes`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **THEN** the command applies the overwrite-confirmed registration path without prompting
- **AND THEN** it persists the resulting mailbox binding into the session manifest and registry-visible mailbox summary

### Requirement: Late mailbox registration reports activation state by runtime posture
Late mailbox registration SHALL report activation state based on whether the target runtime posture becomes live-mailbox-actionable after the mutation, rather than claiming that every successful registration is immediately usable by the live provider process.

The supported activation outcomes SHALL include:

- `active`
- `pending_relaunch`

Headless local managed sessions SHALL report `active`.
Tmux-backed local interactive managed sessions SHALL report `active` when the runtime refreshes the owning tmux live mailbox projection successfully.
Joined tmux-backed managed sessions SHALL follow the same activation rule even when their relaunch posture is unavailable.
The runtime SHALL NOT fail late mailbox registration or unregistration solely because a joined tmux session lacks relaunch posture when the runtime can still update both the durable mailbox state and the owning tmux live mailbox projection safely.
The runtime SHALL report `pending_relaunch` only when the resulting mailbox binding is persisted durably but the current live session posture is not yet live-mailbox-actionable.

#### Scenario: Interactive local managed session becomes active after tmux live projection refresh
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a tmux-backed local interactive managed session whose owning tmux session is reachable
- **THEN** the command persists the mailbox binding successfully
- **AND THEN** it refreshes the owning tmux live mailbox projection for that binding
- **AND THEN** the command reports activation state `active`

#### Scenario: Joined session without relaunch posture becomes active after registration
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a joined tmux-backed managed session whose relaunch posture is unavailable
- **AND WHEN** the runtime can still update the session manifest and the owning tmux session environment for `alice`
- **THEN** the command persists the mailbox binding successfully
- **AND THEN** it refreshes the owning tmux live mailbox projection for that binding
- **AND THEN** the command reports activation state `active`

### Requirement: `houmao-mgr agents mailbox unregister` removes the session binding and unregisters the address
`houmao-mgr agents mailbox unregister` SHALL remove late filesystem mailbox support from an existing local managed agent.

At minimum, the command SHALL:

1. resolve the local managed-agent controller,
2. load the current filesystem mailbox binding from the session,
3. deregister the active mailbox address using explicit deregistration semantics that default to `deactivate`,
4. remove the session mailbox binding from the managed session manifest and registry-visible mailbox summary.

After successful unregistration, runtime-owned `houmao-mgr agents mail ...` commands SHALL treat that session as not mailbox-enabled.

#### Scenario: Unregister deactivates the mailbox and clears the session binding
- **WHEN** an operator runs `houmao-mgr agents mailbox unregister --agent-name alice`
- **AND WHEN** `alice` currently has an active filesystem mailbox binding
- **THEN** the command deactivates the active mailbox registration by default
- **AND THEN** it removes the session mailbox binding from the manifest
- **AND THEN** later `houmao-mgr agents mail status --agent-name alice` fails clearly because the session is no longer mailbox-enabled

### Requirement: `houmao-mgr agents mailbox status` reports late mailbox registration posture
`houmao-mgr agents mailbox status` SHALL report whether an existing local managed agent currently has a late mailbox registration and whether that registration is active for runtime-owned mailbox use.

At minimum, the status output SHALL distinguish:

- no mailbox registration,
- an active filesystem mailbox registration,
- a persisted mailbox registration whose live mailbox projection is not yet current.

#### Scenario: Status reports pending_relaunch when live mailbox projection is not current
- **WHEN** an operator runs `houmao-mgr agents mailbox status --agent-name alice`
- **AND WHEN** `alice` has a persisted mailbox binding whose live mailbox projection is not yet current for runtime-owned mailbox work
- **THEN** the command reports the persisted mailbox identity
- **AND THEN** the command reports activation state `pending_relaunch`

#### Scenario: Status reports active for a joined session after late registration
- **WHEN** an operator runs `houmao-mgr agents mailbox status --agent-name alice`
- **AND WHEN** `alice` has a persisted mailbox binding on a joined tmux-backed managed session
- **AND WHEN** the owning tmux session environment publishes the current mailbox projection for that binding
- **THEN** the command reports the persisted mailbox identity
- **AND THEN** the command reports activation state `active`
