## ADDED Requirements

### Requirement: Recorded validation SHALL support Kimi high-rate and low-rate labeled timelines
Recorded validation SHALL support Kimi fixture or run roots that contain a high-rate snapshot stream, a derived low-rate stream, and labels that apply to one or both streams.

The validation harness SHALL be able to run the same Kimi scenario against both sampling cadences and report whether tracker behavior remains correct when fewer frames are available.

#### Scenario: Kimi recorded validation runs both cadences
- **WHEN** a Kimi recorded-validation fixture contains both 10 fps and derived 2 fps streams
- **THEN** the validation command replays the high-rate stream and compares it with labels
- **AND THEN** it replays the low-rate stream and compares it with labels

#### Scenario: Low-rate validation exposes cadence-sensitive bugs
- **WHEN** the Kimi tracker only works at high sample frequency
- **THEN** the low-rate validation result reports the failed field and sample range
- **AND THEN** the failure is visible before the Kimi tracker is treated as maintained

### Requirement: Kimi recorded validation SHALL use manual labels as the oracle
For Kimi recorded validation, human-authored labels SHALL define the expected public tracked-state timeline.

The validation harness SHALL NOT use raw text snippets, detector notes, or exact matched fragments as the primary correctness oracle.

The validation harness SHALL distinguish development-set runs from held-out test-set runs. Held-out test-set validation SHALL be run after detector implementation and SHALL be reported separately from development-set validation.

#### Scenario: Kimi validation ignores detector-internal notes as pass criteria
- **WHEN** a Kimi detector emits diagnostic notes during replay
- **THEN** validation may include those notes in debug output
- **AND THEN** pass or fail status is determined by labeled parser and public tracked-state expectations

#### Scenario: Held-out Kimi test set is reported separately
- **WHEN** Kimi recorded validation runs for the maintained Kimi profile
- **THEN** the validation report separates development-set results from held-out test-set results
- **AND THEN** the held-out test-set result is visible as an acceptance gate for maintained tracking behavior
