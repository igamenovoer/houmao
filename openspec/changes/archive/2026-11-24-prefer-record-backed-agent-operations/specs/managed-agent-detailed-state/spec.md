# Spec Delta

## ADDED Requirements

### Requirement: Manager state retains recorded facts during observation failure

Manager `state` and detailed inspection SHALL return authorized recorded identity and mailbox summaries separately from live evidence. Recorded lifecycle and lease freshness SHALL describe publication. Readiness and current activity SHALL require qualified observation. If observation is unavailable, the response SHALL keep its known facts and report the unavailable or unknown fields with a reason.

#### Scenario: TUI peer is known but its terminal cannot be inspected

- **WHEN** the manager can resolve the selected TUI peer's saved records but cannot inspect its live terminal
- **THEN** the state response includes the peer's known identity and recorded contact data
- **AND THEN** the live terminal posture is unavailable and prompt readiness is unconfirmed

#### Scenario: A published active record does not establish readiness

- **WHEN** the registry reports an active agent and the manager lacks a current observation for that generation
- **THEN** the response distinguishes recorded lifecycle from observed control availability
- **AND THEN** the response does not infer idle, ready, or stopped state from the missing observation

### Requirement: Manager state uses evidence appropriate to the native mode

Manager state and detailed inspection SHALL use current verified native or gateway observations for Web and service state, and runtime execution records and saved turns for headless state. For current TUI state, the manager SHALL use eligible tracker observations or perform targeted terminal observation when required. Observation SHALL preserve source and freshness.

#### Scenario: Native observation remains available across sockets

- **WHEN** an authorized caller inspects a Web or service agent with a reachable native owner and an inaccessible supervisor socket
- **THEN** the manager reports the verified native state without probing the supervisor's terminal
- **AND THEN** the response identifies the native evidence and its freshness

#### Scenario: Completed headless turn does not depend on tmux

- **WHEN** saved execution records establish the terminal outcome of the selected agent's latest headless turn
- **THEN** the manager reports that outcome even if the supervisor cannot be inspected
- **AND THEN** the response distinguishes turn completion from whether a new turn can be admitted

#### Scenario: Current TUI state requires terminal evidence

- **WHEN** the caller requests current TUI detail and no eligible current tracker observation is available through the gateway
- **THEN** the manager can obtain a fresh observation from the authorized owner's recorded terminal
- **AND THEN** it reports unavailability if that observation cannot be obtained
