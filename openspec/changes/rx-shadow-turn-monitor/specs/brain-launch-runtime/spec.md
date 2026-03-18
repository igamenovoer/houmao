## MODIFIED Requirements

### Requirement: CAO shadow polling supports configurable unknown-to-stalled policy
For CAO sessions in `parsing_mode=shadow_only`, the runtime SHALL support a configurable shadow stall policy with at least:
- `unknown_to_stalled_timeout_seconds`
- `stalled_is_terminal`

When unset, `unknown_to_stalled_timeout_seconds` SHALL default to 30 seconds.

The same `unknown_to_stalled_timeout_seconds` value applies to both:
- readiness wait before prompt submission, and
- completion wait during turn execution.

For the corrected two-axis shadow surface model, the unknown-to-stalled timer SHALL treat a surface as "unknown for stall purposes" only when either:

- `availability = unknown`, or
- `availability = supported` and `business_state = unknown`

`input_mode = unknown` by itself SHALL keep the surface non-ready, but SHALL NOT trigger the unknown-to-stalled timer when `business_state` remains known.

The unknown-to-stalled timeout SHALL measure inter-observation gaps rather than wall-clock elapsed time from a fixed start timestamp. When polling intervals vary (slow network, slow CAO), the effective timeout SHALL scale proportionally to the number of actual observations rather than firing after a fixed wall-clock duration that may contain fewer observations than intended.

Any known observation SHALL cancel a pending unknown-to-stalled timeout and reset unknown/stalled tracking. The runtime SHALL NOT enter `stalled` unless the current continuous unknown run reaches the configured threshold.

#### Scenario: Unknown business state reaches stalled threshold
- **WHEN** shadow polling remains on a supported surface with `business_state = unknown`
- **AND WHEN** the continuous inter-observation gap on unknown surfaces reaches `unknown_to_stalled_timeout_seconds`
- **THEN** runtime marks the shadow lifecycle state as `stalled`

#### Scenario: Unknown input mode alone does not enter stalled
- **WHEN** shadow polling remains on a supported surface with a known `business_state`
- **AND WHEN** only `input_mode = unknown`
- **THEN** runtime keeps the surface non-ready
- **AND THEN** it does not enter `stalled` solely because the input mode is unknown

#### Scenario: Slow polling extends effective stall wait
- **WHEN** shadow polling intervals are slower than normal (e.g., due to network latency or CAO load)
- **AND WHEN** the surface remains unknown across those slow polls
- **THEN** the stall timeout fires after the configured duration of continuous unknown observations
- **AND THEN** the effective wall-clock wait is longer than it would be under normal polling intervals

#### Scenario: Known observation cancels pending stall timeout
- **WHEN** shadow polling emits unknown-for-stall observations
- **AND WHEN** a later observation returns to a known surface before the stall threshold is reached
- **THEN** runtime cancels the pending unknown-to-stalled timeout
- **AND THEN** it does not emit `stalled` unless a later continuous unknown run reaches the threshold

### Requirement: Shadow TurnMonitor evaluates two-axis surfaces in deterministic priority order
For CAO sessions in `parsing_mode=shadow_only`, runtime SHALL feed each parsed observation into a stateful turn monitor that preserves post-submit progress evidence across observations.

At minimum, the readiness path SHALL evaluate each observation in this priority order:

1. `availability in {unsupported, disconnected}` -> fail
2. `business_state = awaiting_operator` -> blocked outcome
3. unknown-for-stall surface -> unknown or stalled path
4. otherwise remain in readiness waiting, and submit only when `submit_ready`

At minimum, the completion path SHALL evaluate each observation in this priority order:

1. update progress evidence from normalized shadow text change derived from `DialogProjection.normalized_text` and `business_state = working`
2. `availability in {unsupported, disconnected}` -> fail
3. `business_state = awaiting_operator` -> blocked outcome
4. unknown-for-stall surface -> unknown or stalled path
5. `business_state = working` -> keep `in_progress` regardless of `input_mode`
6. `submit_ready` plus previously-seen progress evidence plus completion stability window elapsed -> complete
7. otherwise remain in a post-submit waiting state

The turn monitor SHALL be implemented as ReactiveX pipelines using `reactivex` operators for temporal logic rather than hand-rolled mutable fields and manual timestamp arithmetic.
The turn monitor's temporal operators SHALL consume the full classified-state stream so non-target observations can cancel pending stall and completion timers instead of being hidden behind filtered sub-streams.

#### Scenario: Working modal surface remains in progress during completion
- **WHEN** a post-submit `shadow_only` observation shows `availability = supported`, `business_state = working`, and `input_mode = modal`
- **THEN** the runtime keeps the turn in an in-progress lifecycle path
- **AND THEN** it does not complete the turn or treat the modal input mode as a blocked outcome by itself

#### Scenario: Awaiting-operator surface is evaluated before ready or complete
- **WHEN** a `shadow_only` observation shows `business_state = awaiting_operator`
- **THEN** the runtime routes the observation to a blocked-surface outcome before considering ready or completion gating
- **AND THEN** it does not treat that observation as submit-ready or completed

## ADDED Requirements

### Requirement: Shadow completion requires stability window before declaring turn complete
For CAO sessions in `parsing_mode=shadow_only`, the runtime SHALL accept a configurable stability window (`completion_stability_seconds`) from the CAO shadow policy config surface and SHALL NOT declare a turn complete on a single idle observation after post-submit activity. Instead, the runtime SHALL require `completion_stability_seconds` of continuous idle observations with no state changes before emitting a completion event.

When unset, `completion_stability_seconds` SHALL default to 1.0 second.

Each new state change (`DialogProjection.normalized_text` change after pipeline normalization, `business_state` transition) observed during the stability window SHALL reset the stability timer.

The stability window applies only to generic shadow completion. Caller-owned completion observers (e.g., mailbox sentinel detection) that find a definitive result MAY bypass the stability window and complete immediately.

#### Scenario: Transient idle flicker does not trigger false completion
- **WHEN** a post-submit `shadow_only` observation shows `submit_ready` after previously observing `working`
- **AND WHEN** a subsequent observation within `completion_stability_seconds` shows `business_state = working` again
- **THEN** the runtime resets the stability timer and does not declare the turn complete
- **AND THEN** the runtime continues monitoring for sustained idle

#### Scenario: Sustained idle after activity triggers completion
- **WHEN** a post-submit `shadow_only` observation shows `submit_ready` after previously observing `working`
- **AND WHEN** no further state changes occur for `completion_stability_seconds`
- **THEN** the runtime declares the turn complete

#### Scenario: Normalized shadow text change resets stability window
- **WHEN** a post-submit `shadow_only` observation shows `submit_ready` after previously observing `working`
- **AND WHEN** the normalized shadow text changes again before `completion_stability_seconds` elapses
- **THEN** the runtime resets the stability timer
- **AND THEN** it continues monitoring for a fresh sustained-idle window

#### Scenario: Mailbox observer bypasses stability window on definitive result
- **WHEN** a `shadow_only` mailbox turn's completion observer detects a valid sentinel-delimited result in post-submit shadow text
- **THEN** the runtime completes the turn immediately with that result
- **AND THEN** the generic stability window does not delay the mailbox result

### Requirement: Shadow turn monitor supports deterministic time-based testing
The shadow turn monitor's temporal logic SHALL be testable with deterministic virtual-time scheduling. Unit tests SHALL be able to advance time precisely, verify debounce windows, timeout thresholds, and observation sequences without real sleeps or wall-clock timing dependencies.

#### Scenario: Unit test verifies debounce window with virtual time
- **WHEN** a test creates a shadow completion pipeline with a `TestScheduler`
- **AND WHEN** the test advances virtual time past the stability window after emitting an idle observation
- **THEN** the pipeline emits a completion event at the expected virtual timestamp

#### Scenario: Unit test verifies stall timeout with virtual time
- **WHEN** a test creates a shadow readiness pipeline with a `TestScheduler`
- **AND WHEN** the test emits unknown observations and advances virtual time past the stall threshold
- **THEN** the pipeline emits a stalled event at the expected virtual timestamp
