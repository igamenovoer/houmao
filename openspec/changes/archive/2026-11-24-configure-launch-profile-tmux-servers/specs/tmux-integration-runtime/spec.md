# Spec Delta

## ADDED Requirements

### Requirement: A selected tmux server has an explicit startup policy

`user-default` SHALL select the execution account’s native default independently of the enclosing tmux session. `new` SHALL allocate a fresh owner-private socket for each new instance. Both modes and `houmao-default` SHALL allow startup at their selected address. `socket` SHALL require an existing server for session creation. Each launch SHALL target its resolved address exclusively.

#### Scenario: The native default is selected from another server

- **WHEN** an execution account inside tmux on a non-default socket launches with `user-default`
- **THEN** the launch uses the account’s native default socket and starts that server if needed

#### Scenario: Two fresh births request a private server

- **WHEN** two new instances launch with `new`
- **THEN** they start successfully on distinct owner-private sockets even if their session names are identical

#### Scenario: The specified server exits after preflight

- **WHEN** an existing-only server disappears between preflight and session creation
- **THEN** launch returns an error for the specified socket without starting a server or connecting elsewhere

### Requirement: Relaunch preserves the concrete socket and startup permission

Tmux-backed managed birth SHALL persist the resolved socket and startup permission with the runtime binding. Later tmux operations SHALL use the persisted socket. Relaunch SHALL apply the saved startup permission at that address even when the original profile or default record has changed.

#### Scenario: Relaunch reuses a private socket after profile edit

- **GIVEN** a stopped instance born with `new` whose server has exited
- **WHEN** an operator relaunches the instance after editing the profile
- **THEN** the runtime starts the session at the socket saved in the manifest

#### Scenario: Relaunch preserves the existing-only contract

- **GIVEN** an instance that originally selected `socket`
- **WHEN** an operator relaunches it while its recorded server is unavailable
- **THEN** relaunch reports the unavailable server without starting or selecting another one
