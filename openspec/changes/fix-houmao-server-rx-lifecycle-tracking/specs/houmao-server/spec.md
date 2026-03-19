## ADDED Requirements

### Requirement: Tracked-state routes expose lifecycle authority for background and turn-anchored monitoring
When `houmao-server` returns server-owned tracked-state payloads for watched sessions, it SHALL expose structured lifecycle authority metadata alongside the lifecycle states so clients can distinguish unanchored background watch behavior from turn-anchored completion monitoring.

At minimum, that lifecycle authority metadata SHALL identify:

- whether completion monitoring is `unanchored_background` or `turn_anchored`,
- whether a current turn anchor is active, absent, or lost/invalidated, and
- enough state to explain why `candidate_complete` or `completed` is or is not currently authoritative.

For tracked sessions with no active server-owned turn anchor, the default emitted lifecycle authority SHALL be `unanchored_background` plus `absent`.

The same tracked-state payload revision that suppresses unanchored `candidate_complete` or `completed` SHALL expose lifecycle authority metadata that explains that suppression.

For terminal input submissions accepted through the supported `houmao-server` control surface, the server SHALL record a turn anchor for the corresponding tracked session and SHALL use that anchor when reducing later completion state. That anchor SHALL be scoped to one anchored cycle and SHALL expire when the cycle reaches a terminal outcome, after which the tracked-state payload returns to `unanchored_background` plus `absent` until the next accepted submission.

When no such anchor exists, the server SHALL still expose continuous watch state for the session, but it SHALL NOT imply that background ready-surface churn is authoritative turn completion.

#### Scenario: Background watch response exposes unanchored lifecycle authority
- **WHEN** a caller requests tracked state for a watched session that has no active server-owned turn anchor
- **THEN** `houmao-server` returns the current continuous watch state
- **AND THEN** the payload identifies completion monitoring as `unanchored_background`
- **AND THEN** the payload identifies the current anchor state as `absent`

#### Scenario: Server-owned input arms turn-anchored monitoring
- **WHEN** `houmao-server` accepts a terminal input submission for a tracked session through its supported control surface
- **THEN** the server records a turn anchor for that tracked session
- **AND THEN** later tracked-state responses may expose turn-anchored candidate-complete or completed lifecycle states for that anchored cycle

#### Scenario: Terminal outcome expires the active turn anchor
- **WHEN** a tracked session has an active server-owned turn anchor
- **AND WHEN** the anchored cycle reaches a terminal outcome such as `completed`, `blocked`, `failed`, or `stalled`
- **THEN** `houmao-server` clears that anchor for completion authority purposes
- **AND THEN** later tracked-state responses return to `unanchored_background` with anchor state `absent` until the next accepted input submission

#### Scenario: Unanchored background churn does not surface authoritative completed state
- **WHEN** a watched session has no active turn anchor
- **AND WHEN** its parsed surface changes and later returns to a submit-ready prompt
- **THEN** `houmao-server` does not surface `completed` as authoritative turn completion from that background churn alone
- **AND THEN** the response continues to expose only the continuous-watch lifecycle authority for that state
