## ADDED Requirements

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

The system SHALL treat those lifecycle states and timings as part of the authoritative server-owned tracked state rather than as a demo-local interpretation layer.

#### Scenario: Continuous unknown readiness enters stalled in server-owned state
- **WHEN** the tracked readiness surface remains unknown for stall purposes continuously for `unknown_to_stalled_timeout_seconds`
- **THEN** the server-owned tracked state reports readiness as `stalled`
- **AND THEN** the corresponding tracked-state payload exposes the unknown elapsed timing that led to that transition

#### Scenario: Candidate-complete timing is exposed before completion
- **WHEN** a tracked session has armed completion monitoring from a previously ready baseline
- **AND WHEN** the parsed surface returns to submit-ready after post-submit activity
- **AND WHEN** the parsed surface remains a completion candidate but has not yet satisfied `completion_stability_seconds`
- **THEN** the server-owned tracked state reports completion as `candidate_complete`
- **AND THEN** the tracked-state payload exposes the elapsed candidate-complete timing for that cycle

#### Scenario: State queries can consume lifecycle timing without local recomputation
- **WHEN** a caller queries the authoritative tracked state for a live supported session
- **THEN** the response includes the current lifecycle states and lifecycle timing metadata needed to interpret unknown, candidate-complete, completed, and stalled transitions
- **AND THEN** the caller does not need to replay terminal text or re-run parser timing logic locally to obtain those values
