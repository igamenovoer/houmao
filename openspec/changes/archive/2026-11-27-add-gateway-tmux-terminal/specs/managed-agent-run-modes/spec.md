# Spec Delta

## MODIFIED Requirements

### Requirement: Run mode and operator handoff are independent

The stored mode SHALL select the native entrypoint independently of prompt policy, executor, gateway attachment, or caller terminal availability. Native terminal handoff and key control require a verified terminal surface. Native Web handoff SHALL expose a safe browser origin and bound session, with browser opening under explicit operator control. An explicit gateway tmux attachment SHALL use the verified live tmux session and retain its console role and the stored run mode.

#### Scenario: A Web host has a tmux supervisor

- **WHEN** a Web launch completes from an interactive terminal
- **THEN** the manager reports the browser surface and safe connection information and keeps its log pane out of the automatic native terminal handoff

#### Scenario: A TUI starts without an interactive caller

- **WHEN** a script launches a supported TUI with unattended policy
- **THEN** the TUI starts under the configured supervisor and the launch result identifies how an operator can attach

#### Scenario: An operator opens the gateway terminal

- **WHEN** an authorized operator opens the live tmux session for an agent through its running gateway
- **THEN** the browser shows the existing session and the agent retains its stored native mode and native surface metadata
- **AND THEN** a supervisor console does not confer a provider TUI, terminal parser, or structured key control capability
