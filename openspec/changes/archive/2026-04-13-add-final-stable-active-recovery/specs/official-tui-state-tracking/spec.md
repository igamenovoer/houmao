## MODIFIED Requirements

### Requirement: Live tracked state recovers stale active turns after stable submit-ready posture
The authoritative live tracked-state layer SHALL recover a stuck `turn.phase=active` posture when the current surface has remained submit-ready for a bounded recovery window without live active evidence.

For the existing fast stale-active recovery path, submit-ready posture SHALL require at minimum:
- `parsed_surface.business_state=idle`,
- `parsed_surface.input_mode=freeform`,
- `surface.accepting_input=yes`,
- `surface.editing_input=no`,
- `surface.ready_posture=yes`,
- no blocking interactive surface, and
- no current active-turn evidence from the live edge or recent transcript growth.

The authoritative live tracked-state layer SHALL also provide a final stable-active recovery path for detector false positives where the TUI is still published as `turn.phase=active` after a longer stable unchanged window.

For the final stable-active recovery path, readiness evidence SHALL require at minimum:
- parsed surface diagnostics are available,
- `parsed_surface.business_state=idle`,
- `parsed_surface.input_mode=freeform`,
- `surface.accepting_input=yes`,
- `surface.editing_input=no`,
- no unsupported, disconnected, blocked, or ambiguous interactive surface, and
- stable unchanged evidence for the configured final recovery window.

The final stable-active recovery path SHALL NOT require `surface.ready_posture=yes`, because the condition it corrects includes detector false positives that may have downgraded `surface.ready_posture` to `no` while independent parser and input-mode evidence still indicate prompt readiness.

Stable unchanged evidence for final stable-active recovery SHALL include the selected profile's current raw surface signature when that signature is available, plus the relevant published tracked-state and parser-readiness evidence used by the recovery candidate.

The system SHALL keep the normal success-settlement path as the primary way to produce `last_turn.result=success`.

When stale-active or final stable-active recovery fires, the tracker SHALL clear the stuck active phase to `ready` without manufacturing `last_turn.result=success` unless the normal success rules already established that outcome independently.

When final stable-active recovery fires while server-owned turn-anchor authority is active, the tracker SHALL expire that stale anchor and stop its completion monitoring before publishing the recovered ready posture.

The stale-active and final stable-active recovery paths SHALL be implemented through the repository's existing ReactiveX-based tracking and scheduler infrastructure rather than through a separate manually managed timeout path.

The default stale-active recovery window SHALL be 5 seconds.

The default final stable-active recovery window SHALL be 20 seconds.

#### Scenario: Stable submit-ready posture clears a stale active phase after the default recovery window
- **WHEN** the tracker is currently publishing `turn.phase=active`
- **AND WHEN** the live surface remains submit-ready with no live active evidence for 5 continuous seconds
- **THEN** the tracker recovers the current turn posture to `turn.phase=ready`
- **AND THEN** prompt-ready consumers are no longer blocked by the stale active phase

#### Scenario: Stable idle/freeform prompt clears a false active phase after the final recovery window
- **WHEN** the tracker is currently publishing `turn.phase=active`
- **AND WHEN** the selected profile raw surface signature and relevant published state remain unchanged for 20 continuous seconds
- **AND WHEN** the parsed surface reports `business_state=idle` and `input_mode=freeform`
- **AND WHEN** the surface reports `accepting_input=yes` and `editing_input=no`
- **THEN** the tracker recovers the current turn posture to `turn.phase=ready`
- **AND THEN** the tracker recovers `surface.ready_posture` to `yes` if it had been downgraded by the false active evidence

#### Scenario: Final recovery does not fire while the raw surface keeps changing
- **WHEN** the tracker is currently publishing `turn.phase=active`
- **AND WHEN** the detector continues to produce different raw surface signatures before the final recovery window elapses
- **THEN** the tracker does not fire final stable-active recovery
- **AND THEN** the final recovery timer restarts from the latest stable candidate

#### Scenario: Final recovery does not fire without independent prompt-ready evidence
- **WHEN** the tracker is currently publishing `turn.phase=active`
- **AND WHEN** the published active state is stable for the final recovery window
- **AND WHEN** the parsed surface is working, unknown, awaiting operator, not freeform, or unavailable
- **THEN** the tracker does not fire final stable-active recovery
- **AND THEN** prompt-ready consumers remain blocked until stronger readiness evidence appears

#### Scenario: Final recovery expires stale turn anchors without manufacturing success
- **WHEN** final stable-active recovery clears a stuck `turn.phase=active` posture while server-owned turn-anchor authority is active
- **THEN** the tracker expires the stale turn anchor and stops anchored completion monitoring
- **AND THEN** the tracker does not set `last_turn.result=success` only because recovery fired
- **AND THEN** the recovery behaves as a readiness correction rather than as a completion verdict

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
- **WHEN** the tracker evaluates whether a recovery window has elapsed
- **THEN** that timing is derived through the existing ReactiveX scheduler and tracker-owned observable pipeline
- **AND THEN** the implementation does not require a second imperative manual timeout mechanism for stale-active or final stable-active recovery
