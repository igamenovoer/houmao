## ADDED Requirements

### Requirement: Track state signature stability duration
The system SHALL track how long a visible state signature remains unchanged and provide this duration to operators.

#### Scenario: State signature remains unchanged
- **WHEN** the visible state signature (readiness, completion, business state, input mode, ui context, projection changed, blocked status) remains unchanged across multiple observations
- **THEN** the system SHALL increment the stability duration counter

#### Scenario: State signature changes
- **WHEN** any component of the visible state signature changes
- **THEN** the system SHALL reset the stability duration counter to zero

### Requirement: Mark state as stable after configured window
The system SHALL mark a state as stable when its signature has remained unchanged for at least the configured stability window duration.

#### Scenario: State becomes stable
- **WHEN** a state signature has remained unchanged for duration >= stability_window_seconds
- **THEN** the system SHALL set is_stable flag to true

#### Scenario: State is unstable during window
- **WHEN** a state signature has remained unchanged for duration < stability_window_seconds
- **THEN** the system SHALL set is_stable flag to false

#### Scenario: Zero window means immediate stability
- **WHEN** stability_window_seconds is set to 0
- **THEN** every state SHALL be marked as stable immediately

### Requirement: Expose stability metadata
The system SHALL expose stability metadata including is_stable flag, stable_for_seconds duration, and the configured stability_window_seconds.

#### Scenario: Operator queries stability metadata
- **WHEN** operator requests current state information
- **THEN** the system SHALL include is_stable, stable_for_seconds, and stability_window_seconds in the response

### Requirement: Preserve raw state evidence
The system SHALL preserve raw state observations alongside stability metadata for debugging purposes.

#### Scenario: Raw state logged with stability
- **WHEN** a state observation is processed
- **THEN** the system SHALL log both the raw state and the computed stability metadata
