## ADDED Requirements

### Requirement: Apply stability window operator to state stream
The system SHALL provide an RxPY operator that transforms raw state observations into smoothed states with stability metadata.

#### Scenario: Operator transforms state stream
- **WHEN** raw state stream is piped through apply_stability_window operator
- **THEN** the system SHALL emit SmoothedDashboardState objects containing raw state and stability metadata

### Requirement: Compute state signature for stability
The system SHALL define a state signature function that extracts stability-relevant fields from dashboard state.

#### Scenario: State signature extracted
- **WHEN** computing stability for a dashboard state
- **THEN** the system SHALL use readiness_state, completion_state, business_state, input_mode, ui_context, projection_changed, and operator_blocked_excerpt presence as the signature

### Requirement: Generate smoothed labels
The system SHALL generate human-readable smoothed labels combining primary state with stability status.

#### Scenario: Stable state labeled
- **WHEN** a state is marked stable
- **THEN** the system SHALL generate label format "<primary_state> (stable)"

#### Scenario: Unstable state labeled
- **WHEN** a state is not yet stable
- **THEN** the system SHALL generate label format "<primary_state> (unstable)"

### Requirement: Support stability transition filtering
The system SHALL provide an operator to emit only when stability status changes.

#### Scenario: Stability transition detected
- **WHEN** state transitions from unstable to stable or vice versa
- **THEN** the system SHALL emit the state change

#### Scenario: Stability unchanged
- **WHEN** state remains stable or remains unstable
- **THEN** the system SHALL NOT emit duplicate stability events
