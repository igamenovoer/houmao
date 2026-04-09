## ADDED Requirements

### Requirement: Live tracked state recovers stale active turns after stable submit-ready posture
The authoritative live tracked-state layer SHALL recover a stuck `turn.phase=active` posture when the current surface has remained submit-ready for a bounded recovery window without live active evidence.

For this recovery path, submit-ready posture SHALL require at minimum:
- `parsed_surface.business_state=idle`,
- `parsed_surface.input_mode=freeform`,
- `surface.accepting_input=yes`,
- `surface.editing_input=no`,
- `surface.ready_posture=yes`,
- no blocking interactive surface, and
- no current active-turn evidence from the live edge or recent transcript growth.

The system SHALL keep the normal success-settlement path as the primary way to produce `last_turn.result=success`.

When stale-active recovery fires, the tracker SHALL clear the stuck active phase to `ready` without manufacturing `last_turn.result=success` unless the normal success rules already established that outcome independently.

The stale-active recovery path SHALL be implemented through the repository's existing ReactiveX-based tracking and scheduler infrastructure rather than through a separate manually managed timeout path.

The default stale-active recovery window SHALL be 5 seconds.

#### Scenario: Stable submit-ready posture clears a stale active phase after the default recovery window
- **WHEN** the tracker is currently publishing `turn.phase=active`
- **AND WHEN** the live surface remains submit-ready with no live active evidence for 5 continuous seconds
- **THEN** the tracker recovers the current turn posture to `turn.phase=ready`
- **AND THEN** prompt-ready consumers are no longer blocked by the stale active phase

#### Scenario: Ongoing transcript growth prevents stale-active recovery
- **WHEN** the visible Codex running row has disappeared
- **AND WHEN** the latest-turn transcript is still growing within the recent temporal window
- **THEN** the tracker does not fire stale-active recovery
- **AND THEN** the turn remains active until the live activity evidence clears or normal completion settles

#### Scenario: Stale-active recovery does not manufacture success
- **WHEN** stale-active recovery clears a stuck `turn.phase=active` posture
- **AND WHEN** the normal success-settlement path has not independently recorded a successful completed turn
- **THEN** the tracker does not set `last_turn.result=success` only because recovery fired
- **AND THEN** the recovery behaves as a readiness correction rather than as a completion verdict

#### Scenario: Recovery uses tracker-owned ReactiveX timing rather than manual deadline bookkeeping
- **WHEN** the tracker evaluates whether the stale-active recovery window has elapsed
- **THEN** that timing is derived through the existing ReactiveX scheduler and tracker-owned observable pipeline
- **AND THEN** the implementation does not require a second imperative manual timeout mechanism for stale-active recovery
