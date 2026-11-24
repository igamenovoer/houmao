# Spec Delta

## ADDED Requirements

### Requirement: Managed fixtures qualify communication across isolated tmux servers

Automated coverage SHALL exercise two managed fixture runs on separate owned tmux sockets with shared registry and mail authority. It SHALL verify record-backed peer discovery and mail under the fixture's socket restrictions, plus authorized direct prompt delivery with gateways detached. The tests SHALL use synthetic inputs and affect only their isolated servers and owned sessions.

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
