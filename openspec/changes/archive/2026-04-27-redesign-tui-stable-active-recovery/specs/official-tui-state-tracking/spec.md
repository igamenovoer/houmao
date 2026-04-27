## MODIFIED Requirements

### Requirement: Live tracked state recovers stale active turns after stable submit-ready posture
The authoritative live tracked-state layer SHALL recover a stuck `turn.phase=active` posture through one of two recovery paths: a fast stale-active recovery that consults the parser-readiness evidence, and a final stable-active recovery that judges purely from rendered-surface stability so that no parser fault can disable it.

For the existing fast stale-active recovery path, submit-ready posture SHALL require at minimum:
- `parsed_surface.business_state=idle`,
- `parsed_surface.input_mode=freeform`,
- `surface.accepting_input=yes`,
- `surface.editing_input=no`,
- `surface.ready_posture=yes`,
- no blocking interactive surface, and
- no current active-turn evidence from the live edge or recent transcript growth.

The authoritative live tracked-state layer SHALL also provide a final stable-active recovery path for detector false positives where the TUI is still published as `turn.phase=active` after a longer stable unchanged window. This path is the parser-independent backstop for the recovery contract.

For the final stable-active recovery path, the recovery SHALL fire when both of the following hold:
- the published `turn.phase` is currently `active`, and
- a rendered-surface stability signature derived from the current tmux capture has remained unchanged for the configured final recovery window.

The final stable-active recovery path SHALL NOT consult `parsed_surface`, `tracker_state.active_reasons`, `tracker_state.stability_signature`, `tracker_state.notes`, `surface.ready_posture`, `surface.accepting_input`, `surface.editing_input`, blocking-interactive-surface diagnostics, or any other activity-detection-pipeline output when deciding whether to settle the recovery timer or fire recovery. The recovery exists to repair detector misclassification and SHALL NOT be vetoed by the same detector pipeline whose faults it is designed to correct.

The rendered-surface stability signature SHALL be derived deterministically from the raw tmux capture text by stripping ANSI escape sequences, right-trimming each line, and hashing the resulting normalized text. The signature SHALL be independent of the active detector profile, parser version, temporal-hint state, and any published tracked-state field.

The final stable-active recovery path SHALL NOT require `surface.ready_posture=yes`, `surface.accepting_input=yes`, `parsed_surface.business_state=idle`, or any other parser-derived precondition. The only required precondition besides `turn.phase=active` is that the rendered-surface stability signature is observable for the current cycle.

The system SHALL keep the normal success-settlement path as the primary way to produce `last_turn.result=success`.

When stale-active or final stable-active recovery fires, the tracker SHALL clear the stuck active phase to `ready` without manufacturing `last_turn.result=success` unless the normal success rules already established that outcome independently. Final stable-active recovery SHALL also lift `surface.ready_posture` to `yes` for the recovered cycle so that prompt-ready consumers are unblocked even when the parser had downgraded that posture under false active evidence.

When final stable-active recovery fires while server-owned turn-anchor authority is active, the tracker SHALL expire that stale anchor and stop its completion monitoring before publishing the recovered ready posture.

The stale-active and final stable-active recovery paths SHALL be implemented through the repository's existing ReactiveX-based tracking and scheduler infrastructure rather than through a separate manually managed timeout path.

The default stale-active recovery window SHALL be 5 seconds.

The default final stable-active recovery window SHALL be 20 seconds.

#### Scenario: Stable submit-ready posture clears a stale active phase after the default recovery window
- **WHEN** the tracker is currently publishing `turn.phase=active`
- **AND WHEN** the live surface remains submit-ready with no live active evidence for 5 continuous seconds
- **THEN** the tracker recovers the current turn posture to `turn.phase=ready`
- **AND THEN** prompt-ready consumers are no longer blocked by the stale active phase

#### Scenario: Stable rendered surface clears a false active phase after the final recovery window
- **WHEN** the tracker is currently publishing `turn.phase=active`
- **AND WHEN** the rendered-surface stability signature remains unchanged for 20 continuous seconds
- **THEN** the tracker recovers the current turn posture to `turn.phase=ready`
- **AND THEN** the tracker recovers `surface.ready_posture` to `yes` if it had been downgraded by the false active evidence

#### Scenario: Final recovery fires even while the parser keeps re-emitting active evidence
- **WHEN** the tracker is currently publishing `turn.phase=active` because the activity-detection pipeline keeps producing non-empty `active_reasons` on every snapshot
- **AND WHEN** the rendered-surface stability signature remains unchanged for 20 continuous seconds
- **THEN** the tracker fires final stable-active recovery and recovers the public state to `turn.phase=ready`
- **AND THEN** the recovery decision does not consult `tracker_state.active_reasons`, `parsed_surface`, or any other activity-detection output

#### Scenario: Final recovery is not vetoed by parser-reported readiness gaps
- **WHEN** the tracker is currently publishing `turn.phase=active`
- **AND WHEN** the rendered-surface stability signature has remained unchanged for the final recovery window
- **AND WHEN** the parser reports `parsed_surface.business_state` as `working`, `unknown`, or unavailable
- **THEN** the tracker still fires final stable-active recovery
- **AND THEN** prompt-ready consumers are unblocked because the rendered surface alone established stability

#### Scenario: Final recovery does not fire while the rendered surface keeps changing
- **WHEN** the tracker is currently publishing `turn.phase=active`
- **AND WHEN** the rendered-surface stability signature changes at least once before the final recovery window elapses
- **THEN** the tracker does not fire final stable-active recovery
- **AND THEN** the final recovery timer restarts from the latest stable candidate

#### Scenario: Final recovery is robust to ANSI styling and trailing-whitespace jitter
- **WHEN** the rendered text content of the tmux capture is identical across cycles
- **AND WHEN** ANSI escape sequences, cursor styling codes, or trailing-whitespace padding differ between cycles
- **THEN** the rendered-surface stability signature remains unchanged across those cycles
- **AND THEN** the final stable-active recovery timer accumulates uninterrupted

#### Scenario: Final recovery expires stale turn anchors without manufacturing success
- **WHEN** final stable-active recovery clears a stuck `turn.phase=active` posture while server-owned turn-anchor authority is active
- **THEN** the tracker expires the stale turn anchor and stops anchored completion monitoring
- **AND THEN** the tracker does not set `last_turn.result=success` only because recovery fired
- **AND THEN** the recovery behaves as a readiness correction rather than as a completion verdict

#### Scenario: Ongoing transcript growth prevents stale-active recovery
- **WHEN** the visible Codex running row has disappeared
- **AND WHEN** the latest-turn transcript is still growing within the recent temporal window
- **THEN** the tracker does not fire stale-active recovery
- **AND THEN** the turn remains active until the live activity evidence clears, the rendered surface stabilizes long enough for final stable-active recovery, or normal completion settles

#### Scenario: Stale-active recovery does not manufacture success
- **WHEN** stale-active recovery clears a stuck `turn.phase=active` posture
- **AND WHEN** the normal success-settlement path has not independently recorded a successful completed turn
- **THEN** the tracker does not set `last_turn.result=success` only because recovery fired
- **AND THEN** the recovery behaves as a readiness correction rather than as a completion verdict

#### Scenario: Recovery uses tracker-owned ReactiveX timing rather than manual deadline bookkeeping
- **WHEN** the tracker evaluates whether a recovery window has elapsed
- **THEN** that timing is derived through the existing ReactiveX scheduler and tracker-owned observable pipeline
- **AND THEN** the implementation does not require a second imperative manual timeout mechanism for stale-active or final stable-active recovery

## REMOVED Requirements

### Requirement: Stable promptable error surfaces recover from false active state
**Reason**: This requirement narrowed the final stable-active recovery contract to a specific "stable promptable compact-error surface" shape with parser-readiness preconditions (`parsed_surface` submit-ready, `surface.accepting_input=yes`, `surface.editing_input=no`, no blocking overlay). Under the redesigned final stable-active recovery contract, recovery is parser-independent and fires whenever `turn.phase=active` and the rendered-surface stability signature has been unchanged for the configured window, regardless of error-vs-non-error or parser-readiness state. The behavior the original requirement guaranteed — recovering from a stable promptable error surface without settling `last_turn.result=success` and without emitting `known_failure` — is now strictly covered by the redesigned `Live tracked state recovers stale active turns after stable submit-ready posture` requirement (recovery never manufactures `success`, and the recovery side effects do not touch chat-context-diagnostic or known-failure projections).

**Migration**: No caller-visible migration is required. Consumers that previously relied on the narrow precondition shape will see recovery fire under the same conditions they did before, and additionally under broader conditions where the parser had been blocking recovery. Test fixtures that asserted "recovery does not apply while prompt readiness is ambiguous" must be updated to expect recovery to fire under the new contract once the rendered surface is stable for the configured window.
