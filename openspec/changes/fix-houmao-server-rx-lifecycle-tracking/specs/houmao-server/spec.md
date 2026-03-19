## ADDED Requirements

### Requirement: Tracked-state routes expose lifecycle authority for background and turn-anchored monitoring
When `houmao-server` returns server-owned tracked-state payloads for watched sessions, it SHALL expose structured lifecycle authority metadata alongside the lifecycle states so clients can distinguish unanchored background watch behavior from turn-anchored completion monitoring.

At minimum, that lifecycle authority metadata SHALL identify:

- whether completion monitoring is `unanchored_background` or `turn_anchored`,
- whether a current turn anchor is active, absent, or lost/invalidated, and
- enough state to explain why `candidate_complete` or `completed` is or is not currently authoritative.

For terminal input submissions accepted through the supported `houmao-server` control surface, the server SHALL record a turn anchor for the corresponding tracked session and SHALL use that anchor when reducing later completion state.

When no such anchor exists, the server SHALL still expose continuous watch state for the session, but it SHALL NOT imply that background ready-surface churn is authoritative turn completion.

#### Scenario: Background watch response exposes unanchored lifecycle authority
- **WHEN** a caller requests tracked state for a watched session that has no active server-owned turn anchor
- **THEN** `houmao-server` returns the current continuous watch state
- **AND THEN** the payload identifies completion monitoring as `unanchored_background`

#### Scenario: Server-owned input arms turn-anchored monitoring
- **WHEN** `houmao-server` accepts a terminal input submission for a tracked session through its supported control surface
- **THEN** the server records a turn anchor for that tracked session
- **AND THEN** later tracked-state responses may expose turn-anchored candidate-complete or completed lifecycle states for that anchored cycle

#### Scenario: Unanchored background churn does not surface authoritative completed state
- **WHEN** a watched session has no active turn anchor
- **AND WHEN** its parsed surface changes and later returns to a submit-ready prompt
- **THEN** `houmao-server` does not surface `completed` as authoritative turn completion from that background churn alone
- **AND THEN** the response continues to expose only the continuous-watch lifecycle authority for that state
