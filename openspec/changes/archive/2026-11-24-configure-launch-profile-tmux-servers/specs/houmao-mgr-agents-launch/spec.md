# Spec Delta

## ADDED Requirements

### Requirement: Project birth resolves tmux selection as one launch input

`houmao-mgr project agents launch` SHALL accept `--tmux-server` and `--tmux-socket-path` as a one-shot selector. An explicit selector SHALL replace the stored profile selector for that birth. When both are omitted, the existing execution scope and shell selection SHALL apply. `--session-name` SHALL name the session on the resolved server.

#### Scenario: A one-shot selector overrides the stored choice

- **GIVEN** a launch profile with `server: socket` and an absolute `socket_path`
- **WHEN** a new birth specifies `--tmux-server houmao-default`
- **THEN** the runtime uses the Houmao default server for that birth
- **AND THEN** profile inspection still reports the stored socket selector

#### Scenario: Launch without a selector retains the enclosing server

- **WHEN** a current-account launch has no explicit execution scope and both tmux selectors are omitted inside a tmux session
- **THEN** the launch uses the enclosing server

### Requirement: Project birth validates tmux selection before takeover

The execution owner SHALL validate the effective tmux selector and its startup permission before force takeover or creation of agent runtime state. An admitted executor’s socket binding SHALL constrain the result. An invalid or incompatible selection or an unavailable existing-only server SHALL fail before stopping a predecessor.

#### Scenario: A selector conflicts with the admitted executor

- **WHEN** a delegated project launch requests a tmux socket different from the admitted owner’s bound socket
- **THEN** the owner reports the conflict and leaves both servers and any predecessor untouched

#### Scenario: The requested existing server is unavailable before a force launch

- **WHEN** a force replacement selects `socket` and the execution owner cannot reach that server during preflight
- **THEN** launch fails at the specified socket and the existing agent continues on its original binding

#### Scenario: A replacement would stop the selected existing-only server

- **GIVEN** the force predecessor owns the only session on an existing-only server that exits when empty
- **WHEN** a force replacement selects that same server
- **THEN** the launch either preserves the running server through handoff or rejects the replacement before stopping the predecessor
