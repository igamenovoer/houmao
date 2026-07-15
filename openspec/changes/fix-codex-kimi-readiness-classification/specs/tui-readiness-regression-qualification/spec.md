## ADDED Requirements

### Requirement: Prompt-submission capture gates observe a turn lifecycle before ready return
The long-horizon capture harness SHALL require a post-submit active or progress edge before a prompt-submitting operation can satisfy its after-operation ready gate.

Provider-specific busy evidence SHALL include maintained current-turn activity and retained-input surfaces. For Kimi this includes moon and labeled braille spinners plus all maintained queue hints. For Codex this includes current interruptible status rows and all maintained pending-input sections.

#### Scenario: Kimi spinner prevents immediate false-ready gate
- **WHEN** a Kimi prompt has been submitted and an empty editor remains visible while a moon spinner is active
- **THEN** the capture gate does not accept the surface as the operation's ready return
- **AND THEN** it waits for a later ready surface after the observed busy edge

#### Scenario: Missing start edge times out safely
- **WHEN** a prompt-submitting qualification operation never exposes an observable active or progress edge
- **THEN** the harness reports a short-stimulus or surface-timeout failure
- **AND THEN** it does not send the next operation merely because the editor marker stayed visible

### Requirement: Readiness replay distinguishes direct labels from legacy generated references
The readiness regression comparator SHALL map tracker output independently from reference labels. A direct UC-03 label SHALL contain its readiness label, source sample interval, visible evidence, rubric identity or digest, and review metadata.

Diagnostic unavailability SHALL map to `indeterminate` before activity, draft, overlay, or ready classification. `busy_overlay` SHALL require explicit overlay evidence rather than being inferred from every unknown or non-accepting surface.

Legacy generated tracker-shaped labels MAY be used for trend comparison, but reports SHALL identify them as legacy references and SHALL NOT describe them as independent human ground truth without auditable review evidence.

#### Scenario: TUI-down sample is indeterminate
- **WHEN** a replay sample reports diagnostics availability `tui_down`, `unavailable`, or `error`
- **THEN** tracker-label mapping returns `indeterminate` before considering stale prompt or draft fields

#### Scenario: Unknown posture is not automatically an overlay
- **WHEN** tracker output has an unknown ready posture without explicit blocking-overlay evidence
- **THEN** replay mapping does not manufacture `busy_overlay`

#### Scenario: Legacy reference is reported honestly
- **WHEN** a replay comparison consumes generated UC-02 public-state labels without auditable UC-03 review metadata
- **THEN** its report identifies the comparison as exploratory legacy-reference evidence
- **AND THEN** it does not claim behavioral `ready_immediate` qualification from that corpus

### Requirement: Recorded replay rejects sustained false-ready classification
The implementation SHALL replay the frozen Codex and Kimi readiness recordings at canonical cadence and at derived 10 Hz, 5 Hz, and 2 Hz cadences.

The replay verdict SHALL reject any sustained interval in which the tracker reports ready while source-backed current busy evidence remains represented. Residual mismatches MAY remain at short sampled transition boundaries only when the report identifies their sample range and explains why they are cadence or label noise rather than sustained state inversion.

#### Scenario: Kimi queue interval remains busy across replay cadences
- **WHEN** a derived replay schedule retains samples from a current Kimi queued-message interval
- **THEN** the tracker does not report those represented samples as ready solely because the editor is empty

#### Scenario: Codex pending-steer interval remains busy across replay cadences
- **WHEN** a derived replay schedule retains samples from a current Codex pending-steer interval
- **THEN** the tracker preserves busy-before-ready ordering until the pending surface is released
