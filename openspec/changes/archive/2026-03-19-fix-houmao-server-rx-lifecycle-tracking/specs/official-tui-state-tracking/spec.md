## ADDED Requirements

### Requirement: Timer-driven live lifecycle semantics use ReactiveX observation streams
For supported parsed tmux-backed sessions, timer-driven lifecycle semantics in this capability SHALL be implemented over ordered observation streams using ReactiveX operators rather than hand-rolled mutable timestamp reducers and manual wall-clock bookkeeping.

That ReactiveX timing layer SHALL be authoritative for:

- unknown-to-stalled timing,
- candidate-complete debounce timing,
- recovery from stalled when known observations return, and
- deterministic scheduler-driven tests for those timing rules.

#### Scenario: Known observation cancels pending unknown timeout
- **WHEN** the live observation stream enters an unknown-for-stall classification
- **AND WHEN** the stalled timeout has not yet elapsed
- **AND WHEN** a later known observation arrives before that timeout
- **THEN** the pending stalled transition is canceled
- **AND THEN** the tracked state continues from the returned known observation instead of entering `stalled`

#### Scenario: Candidate-complete debounce resets on later observation change
- **WHEN** turn-anchored completion monitoring has already reached `candidate_complete`
- **AND WHEN** a later classified observation changes the completion signature before `completion_stability_seconds` elapses
- **THEN** the pending completion debounce resets
- **AND THEN** the tracked state does not emit `completed` until the candidate surface remains stable for the full configured window

#### Scenario: Lifecycle timing is testable without real sleeps
- **WHEN** unit tests exercise unknown-to-stalled timing, stalled recovery, or completion debounce for this capability
- **THEN** the implementation can drive those cases with deterministic scheduler control
- **AND THEN** the tests do not require real wall-clock sleeps to verify the lifecycle semantics

## MODIFIED Requirements

### Requirement: Live tracked state exposes lifecycle timing and stalled classification for consumer dashboards
For supported parsed tmux-backed sessions, the system SHALL keep server-owned lifecycle reduction that is rich enough for consumer dashboards to preserve manual-validation semantics without re-implementing parser timing logic outside `houmao-server`.

At minimum, that server-owned lifecycle view SHALL include:

- readiness states that distinguish `ready`, `waiting`, `blocked`, `failed`, `unknown`, and `stalled`
- completion states that distinguish `inactive`, `in_progress`, `candidate_complete`, `completed`, `blocked`, `failed`, `unknown`, and `stalled`
- lifecycle timing metadata that includes:
  - `readiness_unknown_elapsed_seconds`
  - `completion_unknown_elapsed_seconds`
  - `completion_candidate_elapsed_seconds`
  - `unknown_to_stalled_timeout_seconds`
  - `completion_stability_seconds`
- lifecycle authority metadata that includes:
  - whether completion monitoring is `turn_anchored` or `unanchored_background`
  - whether a current turn anchor is active, absent, or lost/invalidated

The system SHALL treat readiness, blocked, failed, unknown, stalled, and visible-state stability as authoritative continuous-watch outputs.

The same tracked-state payload revision that suppresses unanchored `candidate_complete` and `completed` SHALL expose lifecycle authority metadata explaining whether completion is `turn_anchored` or `unanchored_background`.

The system SHALL emit `candidate_complete` and `completed` only when completion monitoring is armed from a server-owned turn anchor. When no turn anchor exists, continuous background watch SHALL NOT infer authoritative completion from ready-surface churn alone.

Completion evidence and completion debounce timing SHALL be scoped to one anchored cycle at a time. When turn-anchored monitoring reaches a terminal outcome for that cycle, the system SHALL expire the anchor for completion authority purposes and return later observations to `unanchored_background` semantics until a new server-owned anchor is armed.

The system SHALL treat those lifecycle states, timings, and authority signals as part of the authoritative server-owned tracked state rather than as a demo-local interpretation layer.

#### Scenario: Continuous unknown readiness enters stalled in server-owned state
- **WHEN** the tracked readiness surface remains unknown for stall purposes continuously for `unknown_to_stalled_timeout_seconds`
- **THEN** the server-owned tracked state reports readiness as `stalled`
- **AND THEN** the corresponding tracked-state payload exposes the unknown elapsed timing that led to that transition

#### Scenario: Unanchored background watch does not infer completion from ready-surface churn
- **WHEN** a tracked session has no active server-owned turn anchor
- **AND WHEN** the parsed surface remains or returns to submit-ready after background prompt-surface churn
- **THEN** the server-owned tracked state does not report `candidate_complete` or `completed` from that churn alone
- **AND THEN** the tracked-state payload exposes that completion is currently `unanchored_background`

#### Scenario: Candidate-complete timing is exposed before completion for turn-anchored monitoring
- **WHEN** a tracked session has armed completion monitoring from an active server-owned turn anchor
- **AND WHEN** the parsed surface returns to submit-ready after post-submit activity
- **AND WHEN** the parsed surface remains a completion candidate but has not yet satisfied `completion_stability_seconds`
- **THEN** the server-owned tracked state reports completion as `candidate_complete`
- **AND THEN** the tracked-state payload exposes the elapsed candidate-complete timing for that anchored cycle

#### Scenario: Terminal anchored outcome expires completion authority for the next cycle
- **WHEN** a tracked session has armed completion monitoring from an active server-owned turn anchor
- **AND WHEN** that anchored cycle reaches a terminal outcome such as `completed`, `blocked`, `failed`, or `stalled`
- **THEN** the server-owned tracked state expires the current turn anchor for completion authority purposes
- **AND THEN** later tracked-state payloads return to `unanchored_background` semantics until a new server-owned anchor is armed

#### Scenario: State queries can consume lifecycle timing and authority without local recomputation
- **WHEN** a caller queries the authoritative tracked state for a live supported session
- **THEN** the response includes the current lifecycle states, lifecycle timing metadata, and lifecycle authority metadata needed to interpret unknown, candidate-complete, completed, and stalled transitions
- **AND THEN** the caller does not need to replay terminal text or re-run parser timing logic locally to obtain those values
