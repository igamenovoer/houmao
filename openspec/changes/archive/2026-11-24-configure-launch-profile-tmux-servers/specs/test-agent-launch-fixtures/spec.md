# Spec Delta

## ADDED Requirements

### Requirement: Local tmux-backed fixtures default to the Houmao server

Managed fixture launches and fixture-owned raw TUI or Web launches SHALL select `houmao-default` unless preparation explicitly selects `--tmux-server new`. Managed fixtures SHALL express the choice in their launch profile. Raw headless launches SHALL remain process-only. Passive launches SHALL use the addressed server’s own socket policy.

#### Scenario: Managed fixtures share the default server

- **WHEN** two local managed fixtures with separate initially empty registries launch without a tmux override in the same owner scope
- **THEN** each uses a profile selecting `houmao-default`
- **AND THEN** their run metadata records distinct owned sessions on the same concrete socket

#### Scenario: A raw tmux-backed fixture uses the default server

- **WHEN** a raw terminal or Web fixture launches without a tmux override
- **THEN** its owned session starts on the owner’s Houmao default socket
- **AND THEN** the fixture keeps selected provider credentials out of shared tmux state

#### Scenario: An isolated fixture explicitly requests a new server

- **WHEN** an operator prepares and launches two local tmux-backed fixtures using `--tmux-server new`
- **THEN** each run uses its own socket and retains that socket for follow-up actions

### Requirement: Fixture lifecycle uses captured ownership on either server

Fixture follow-up and cleanup SHALL use the captured agent or verify the run’s ownership at its captured terminal coordinates. Tmux-backed fixture tests SHALL use isolated test-owned socket resources, including tests of the shared default.

#### Scenario: One shared fixture stops without affecting another

- **WHEN** two fixture runs have active sessions on the same test-owned Houmao default server
- **AND WHEN** the operator stops the first run
- **THEN** only that run’s session stops and the second run can still be controlled

#### Scenario: A fixture follow-up runs from another tmux server

- **WHEN** the caller’s enclosing tmux socket differs from the run’s saved socket
- **THEN** fixture checks and terminal operations use the saved binding for that run

## MODIFIED Requirements

### Requirement: Managed fixtures qualify communication across isolated tmux servers

Automated coverage SHALL use `--tmux-server new` to exercise two managed fixture runs on separate owned tmux sockets with shared registry and mail authority. It SHALL verify record-backed peer discovery and mail under the fixture’s socket restrictions, plus authorized direct prompt delivery with gateways detached. The tests SHALL use synthetic inputs and affect only their isolated servers and owned sessions.

#### Scenario: Peer lookup and mail work while peer tmux access is blocked

- **WHEN** two prepared managed agents share a registry and offline mail authority and neither has an attached gateway
- **AND WHEN** the sender's command environment refuses access to the recipient's socket
- **THEN** the sender resolves the registered recipient's mailbox through the normal CLI without a peer tmux invocation
- **AND THEN** sending through the sender's own mailbox commits a message that the recipient can retrieve

#### Scenario: A reachable gateway is reported through its own evidence

- **WHEN** the recipient publishes a verified live gateway and its terminal is inaccessible to the sender
- **THEN** record-backed discovery can return the recipient's live gateway binding without probing the recipient's tmux server

#### Scenario: Authorized direct prompt uses the recorded recipient

- **WHEN** both gateways are detached and the test provides an authorized route to the selected TUI peer's socket
- **THEN** a normal managed prompt hands off input to the peer's recorded pane
- **AND THEN** the sender's session and unrelated terminal sessions receive no input
