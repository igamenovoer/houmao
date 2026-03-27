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
4. ensure the target address has an active shared mailbox registration using safe registration semantics by default,
5. attach the resolved mailbox binding to the managed session,
6. persist that mailbox binding into the session manifest and registry-visible mailbox summary.

After successful registration, later `houmao-mgr agents mail ...` commands SHALL treat the session as mailbox-enabled when the returned activation state is `active`.

#### Scenario: Headless local managed agent becomes mailbox-enabled immediately
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a local headless managed session
- **THEN** the command safely registers `alice`'s mailbox address under `/tmp/shared-mail`
- **AND THEN** the session manifest persists the resulting mailbox binding
- **AND THEN** the command reports activation state `active`
- **AND THEN** later `houmao-mgr agents mail status --agent-name alice` succeeds without any launch-time mailbox flag

### Requirement: Late mailbox registration reports activation state by runtime posture
Late mailbox registration SHALL report activation state based on the target runtime posture rather than claiming that every successful registration is immediately usable by the live provider process.

The supported activation outcomes SHALL include:

- `active`
- `pending_relaunch`
- `unsupported_joined_session`

Headless local managed sessions SHALL report `active`.
Long-lived local interactive managed sessions SHALL report `pending_relaunch`.
Joined sessions whose relaunch posture is unavailable SHALL fail explicitly with `unsupported_joined_session`.

#### Scenario: Interactive local managed session requires relaunch after registration
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a local interactive managed session whose provider process is already running
- **THEN** the command persists the mailbox binding successfully
- **AND THEN** the command reports activation state `pending_relaunch`
- **AND THEN** the operator is told to relaunch before treating runtime-owned mailbox actions as active on that live TUI process

#### Scenario: Joined session without relaunch posture is rejected
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a joined managed session whose relaunch posture is unavailable
- **THEN** the command fails explicitly with `unsupported_joined_session`
- **AND THEN** it does not publish a new mailbox binding for that session

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
- a persisted mailbox registration that still requires relaunch.

#### Scenario: Status reports a relaunch requirement after interactive registration
- **WHEN** an operator runs `houmao-mgr agents mailbox status --agent-name alice`
- **AND WHEN** `alice` has a persisted mailbox binding that was registered on a long-lived local interactive session without relaunch yet
- **THEN** the command reports the persisted mailbox identity
- **AND THEN** the command reports activation state `pending_relaunch`
