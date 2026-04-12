## ADDED Requirements

### Requirement: Gateway attach applies configurable TUI tracking timings
The gateway companion SHALL accept optional gateway-owned TUI tracking timing configuration when attaching to a gateway-capable TUI-backed managed session.

The timing configuration SHALL include:

- watch poll interval seconds
- readiness stability threshold seconds
- completion stability seconds
- unknown-to-stalled timeout seconds
- stale-active recovery seconds

When a timing value is omitted, the gateway attach flow SHALL preserve the existing default or previously persisted desired value for that field.

When a timing value is supplied, the gateway attach flow SHALL validate that it is greater than zero before starting the gateway companion.

The gateway companion SHALL apply the resolved timing values to its gateway-owned `SingleSessionTrackingRuntime` and underlying live TUI tracker.

The gateway attach flow SHALL persist the resolved timing configuration in gateway desired configuration so later attach or restart flows for the same gateway root reuse the selected values unless a stronger explicit override is supplied.

The gateway reset-context wait and poll constants SHALL remain unaffected by this timing configuration.

#### Scenario: Explicit attach timings configure gateway-owned TUI tracking
- **WHEN** an operator attaches a gateway to a TUI-backed managed session with explicit gateway TUI timing overrides
- **THEN** the gateway service starts its TUI tracking runtime with those resolved timing values
- **AND THEN** the gateway-owned TUI state lifecycle metadata reflects the configured completion stability, unknown-to-stalled, and stale-active recovery values

#### Scenario: Later attach reuses persisted gateway TUI timings
- **WHEN** a gateway attach succeeds with explicit gateway TUI timing overrides
- **AND WHEN** the same gateway root is attached again without explicit timing overrides
- **THEN** the later attach reuses the persisted desired timing values for gateway-owned TUI tracking

#### Scenario: Invalid gateway TUI timing value is rejected before attach
- **WHEN** a gateway attach request supplies a gateway TUI timing value less than or equal to zero
- **THEN** the attach request fails before starting or reusing the gateway service process
- **AND THEN** the failure identifies the invalid timing field

#### Scenario: Gateway reset-context timing remains separate
- **WHEN** a gateway is attached with gateway TUI tracking timing overrides
- **THEN** those overrides affect continuous TUI tracking and stale-active recovery
- **AND THEN** they do not change the gateway reset-context wait or reset-context polling constants
