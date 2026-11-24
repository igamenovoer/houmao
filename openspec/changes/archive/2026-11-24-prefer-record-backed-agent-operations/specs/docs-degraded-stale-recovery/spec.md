# Spec Delta

## MODIFIED Requirements

### Requirement: Probe classification documented

The recovery page SHALL document the confirmed classifications used in recovery.

- `healthy` means the selected tmux session and its required primary surface are present.
- `degraded_missing_primary` means the selected session is present and inspection has confirmed primary-surface degradation. A gateway remnant may survive.
- `stale_missing_session` means inspection established that the recorded session is absent on its owning socket.

#### Scenario: Reader understands probe outcomes

- **WHEN** a reader examines the probe-classification section
- **THEN** they see the distinguishing evidence for each confirmed classification and how it maps to a recovery path

#### Scenario: Reader distinguishes an unavailable probe from a missing session

- **WHEN** a reader looks up a permission error, socket refusal, or inconclusive inspection
- **THEN** the page explains that the probe could not establish the selected session's condition
- **AND THEN** it identifies the recorded owner as the place to verify the runtime before taking a recovery action
