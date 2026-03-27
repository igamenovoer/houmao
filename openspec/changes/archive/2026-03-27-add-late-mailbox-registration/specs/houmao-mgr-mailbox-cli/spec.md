## ADDED Requirements

### Requirement: `houmao-mgr mailbox` exposes local filesystem mailbox administration commands
`houmao-mgr` SHALL expose a top-level `mailbox` command family for local filesystem mailbox administration that does not require `houmao-server`.

At minimum, that family SHALL include:

- `init`
- `status`
- `register`
- `unregister`
- `repair`

The family SHALL target the filesystem mailbox transport only in v1.

#### Scenario: Operator sees the local mailbox administration commands
- **WHEN** an operator runs `houmao-mgr mailbox --help`
- **THEN** the help output lists `init`, `status`, `register`, `unregister`, and `repair`
- **AND THEN** the command family is presented as a local mailbox administration surface rather than a server-backed API surface

### Requirement: `houmao-mgr mailbox init` bootstraps or validates one filesystem mailbox root
`houmao-mgr mailbox init` SHALL bootstrap or validate one filesystem mailbox root using the filesystem mailbox bootstrap contract.

The effective mailbox root SHALL resolve from:

1. explicit `--mailbox-root`,
2. `AGENTSYS_GLOBAL_MAILBOX_DIR`,
3. the default shared mailbox root.

A successful bootstrap SHALL create or validate the v1 filesystem mailbox layout, including protocol version, shared SQLite catalog, rules assets, mailbox directories root, locks root, and staging root.

#### Scenario: Operator bootstraps a mailbox root explicitly
- **WHEN** an operator runs `houmao-mgr mailbox init --mailbox-root /tmp/shared-mail`
- **THEN** the command bootstraps or validates `/tmp/shared-mail` as a filesystem mailbox root
- **AND THEN** the result reports that the mailbox root is ready for later mailbox registration workflows

#### Scenario: Init fails clearly on a stale unsupported mailbox root
- **WHEN** an operator runs `houmao-mgr mailbox init --mailbox-root /tmp/legacy-mail`
- **AND WHEN** `/tmp/legacy-mail` uses an unsupported stale mailbox layout
- **THEN** the command fails explicitly
- **AND THEN** the error directs the operator to delete and re-bootstrap that mailbox root instead of attempting in-place migration

### Requirement: `houmao-mgr mailbox status` reports filesystem mailbox root health and summary state
`houmao-mgr mailbox status` SHALL inspect one filesystem mailbox root and return a structured summary of its health and stored state.

At minimum, the summary SHALL report:

- the resolved mailbox root,
- whether the root is bootstrapped and supported,
- the protocol version when available,
- counts of active, inactive, and stashed mailbox registrations,
- whether shared mailbox structural state is readable.

#### Scenario: Operator inspects a healthy mailbox root
- **WHEN** an operator runs `houmao-mgr mailbox status --mailbox-root /tmp/shared-mail`
- **AND WHEN** `/tmp/shared-mail` is a healthy bootstrapped filesystem mailbox root
- **THEN** the command returns a structured summary for that root
- **AND THEN** the summary reports readable mailbox state rather than requiring the operator to inspect files manually

### Requirement: `houmao-mgr mailbox register` and `unregister` expose operator mailbox lifecycle control
`houmao-mgr mailbox register` and `houmao-mgr mailbox unregister` SHALL expose operator-facing mailbox lifecycle control for filesystem mailbox addresses.

`register` SHALL accept a full mailbox address and owner principal id and SHALL use explicit registration modes.
`unregister` SHALL accept a full mailbox address and SHALL use explicit deregistration modes, defaulting to `deactivate`.

The CLI SHALL fail explicitly when the requested lifecycle operation conflicts with the current mailbox registration state.

#### Scenario: Operator registers an in-root mailbox address safely
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **THEN** the command creates or reuses the active in-root mailbox registration for that address using safe registration semantics
- **AND THEN** the result reports the resulting active registration identity

#### Scenario: Operator unregisters a mailbox address without deleting canonical history
- **WHEN** an operator runs `houmao-mgr mailbox unregister --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost`
- **THEN** the command deactivates the active mailbox registration for that address by default
- **AND THEN** future delivery to that address requires a later active registration
- **AND THEN** canonical mailbox history remains preserved

### Requirement: `houmao-mgr mailbox repair` rebuilds filesystem mailbox index state locally
`houmao-mgr mailbox repair` SHALL rebuild one filesystem mailbox root's shared index state locally without requiring `houmao-server`.

The repair flow SHALL use the filesystem mailbox repair contract and SHALL report recovered registration or message state in a structured result.

#### Scenario: Operator repairs a mailbox root locally
- **WHEN** an operator runs `houmao-mgr mailbox repair --mailbox-root /tmp/shared-mail`
- **THEN** the command rebuilds filesystem mailbox index state for `/tmp/shared-mail`
- **AND THEN** the result reports repair outcomes without requiring manual SQLite intervention
