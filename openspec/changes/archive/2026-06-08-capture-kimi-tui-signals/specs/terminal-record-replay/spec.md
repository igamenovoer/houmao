## ADDED Requirements

### Requirement: Recorder replay supports Kimi parser and tracker analysis
The terminal-record replay and analyze flow SHALL support recorded Kimi runs whose manifest tool is `kimi`.

For Kimi runs, replay SHALL derive parser-facing observations when a Kimi parser is available and SHALL derive shared tracked-state observations through the Kimi shared TUI profile when that profile is available.

Replay SHALL operate from persisted pane snapshots and labels without requiring a live Kimi process.

#### Scenario: Analyze accepts recorded Kimi run
- **WHEN** a maintainer runs terminal-record analysis against a recorded run whose manifest tool is `kimi`
- **THEN** the analyze command accepts the run
- **AND THEN** it emits Kimi parser or tracker observations keyed to recorded sample ids

#### Scenario: Kimi replay does not require live credentials
- **WHEN** the recorded Kimi pane snapshots and labels already exist
- **THEN** replay validation can run without launching Kimi or using live Kimi credentials

### Requirement: Replay validation compares Kimi labels against public tracked-state output
The Kimi replay validation flow SHALL compare labeled expectations against replayed public tracked-state fields.

At minimum, strict comparison SHALL cover:

- `diagnostics_availability`
- `surface_accepting_input`
- `surface_editing_input`
- `surface_ready_posture`
- `turn_phase`
- `last_turn_result`
- `last_turn_source`

Parser-facing Kimi expectations such as `business_state`, `input_mode`, and `ui_context` MAY be compared when labels include them.

#### Scenario: Kimi validation reports label mismatches by sample
- **WHEN** replayed Kimi tracked-state output differs from a label expectation
- **THEN** validation reports the sample id or sample range that failed
- **AND THEN** the report includes the expected and actual public tracked-state fields

#### Scenario: Kimi approval labels validate parser and public state
- **WHEN** a Kimi approval dialog range has both parser-facing and public tracked-state labels
- **THEN** validation compares parser state for the modal approval context
- **AND THEN** validation compares public tracked-state readiness and turn posture for the same range

