# Spec Delta

## ADDED Requirements

### Requirement: Unavailable terminal inspection does not authorize recovery

When a required probe cannot inspect the selected terminal, `houmao-mgr` SHALL report inspection unavailable with the selected agent and a safe reason. Stale or degraded recovery SHALL require evidence of the corresponding condition on the recorded owner socket. An inconclusive probe SHALL preserve the agent, its runtime artifacts, and its registry record.

#### Scenario: Fixture shim refuses the peer socket

- **WHEN** a terminal-dependent operation selects a registered peer and the socket probe is rejected
- **THEN** the command reports that it could not inspect the peer's terminal
- **AND THEN** the response contains neither a stale-session claim nor stale-recovery guidance
- **AND THEN** the command makes no lifecycle change and does not retry on the ambient tmux server

#### Scenario: Pane observation fails after the session is found

- **WHEN** the owner socket confirms the session exists but the primary surface check cannot complete
- **THEN** the result reports unavailable inspection unless another qualified observation establishes the actual condition

#### Scenario: Terminal check cannot justify registry removal

- **WHEN** session cleanup or registry cleanup sees a fresh active record and the selected terminal cannot be inspected
- **THEN** it preserves the registry record and reports the unavailable check
- **AND THEN** session cleanup preserves the runtime artifacts

#### Scenario: Recorded owner confirms a missing session

- **WHEN** the owner-side probe confirms absence of the recorded session and recovery verifies the selected generation
- **THEN** an authorized lifecycle command can take the existing stale recovery path
