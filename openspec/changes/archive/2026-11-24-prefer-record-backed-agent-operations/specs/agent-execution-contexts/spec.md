# Spec Delta

## MODIFIED Requirements

### Requirement: Owner-side tmux operations use an explicit server binding

When an owner-side operation uses tmux, Houmao SHALL use the recorded tmux server/socket and exact agent handles. Context entry SHALL discard inherited TMUX and TMUX_PANE selectors. No lifecycle operation SHALL kill or restart the shared localhost tmux server or terminate an unrelated session. Test cleanup SHALL target only its explicitly isolated server and resources.

#### Scenario: Inherited operator tmux variables do not redirect delegation

- **WHEN** Houmao is invoked inside the operator's tmux session with TMUX and TMUX_PANE set
- **THEN** delegated launch and subsequent terminal operations use the explicitly selected owner-side tmux server
- **AND THEN** the operator's enclosing session remains untouched

#### Scenario: Stop preserves sibling agent and user sessions

- **WHEN** the selected owner-side server contains the addressed agent, a sibling agent, and an unrelated user session
- **THEN** stopping or cleaning the addressed agent affects only its validated resources
- **AND THEN** the tmux server and other sessions remain available

#### Scenario: Direct TUI prompt reaches a peer on another server

- **WHEN** an authorized caller selects a ready TUI peer by agent ID and no gateway is attached
- **AND WHEN** the sender and recipient run on different tmux sockets
- **THEN** the manager validates the selected generation and admits the prompt through the owner
- **AND THEN** it submits the prompt to the recipient's exact recorded pane and reports the observed handoff

#### Scenario: Cleanup resolves a socket before terminal inspection

- **WHEN** a selected cleanup target has terminal metadata and the caller's tmux server contains a session with the same name
- **THEN** Houmao uses the selected owner's recorded socket for the liveness check and any authorized terminal action
- **AND THEN** the caller's matching session is unaffected
