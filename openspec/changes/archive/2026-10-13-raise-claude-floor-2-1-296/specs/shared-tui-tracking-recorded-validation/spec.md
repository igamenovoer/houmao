# Spec Delta

## ADDED Requirements

### Requirement: Claude recorded validation uses blind-labeled captures and a boolean qualification gate
Claude detector qualification SHALL use recorded live sessions captured at about 5 fps with ground truth authored as blind labels from raw snapshots and drive events, frozen with a provenance manifest before any replay. The frozen recordings SHALL be promoted into the fixture corpus, and a qualification replay test SHALL gate the maintained Claude profile on `surface_accepting_input` and `surface_ready_posture` against the frozen labels at recorded thresholds.

#### Scenario: Frozen Claude labels gate the maintained profile
- **WHEN** the Claude qualification replay test runs against the promoted fixture recordings
- **THEN** it replays the recordings through the maintained `analyze_terminal_record` production path
- **AND THEN** it asserts per-session agreement on the two booleans at or above the recorded thresholds

#### Scenario: Blind-label boundary precedes replay
- **WHEN** a new Claude validation recording is captured for qualification
- **THEN** labels are authored blind from raw snapshots and drive events and frozen with a provenance manifest before any detector replay scores them
- **AND THEN** later label corrections are recorded with objective surface evidence
