## ADDED Requirements

### Requirement: Passive server headless turn events prefer canonical semantic artifacts with legacy fallback
For managed headless turns, the passive server SHALL read canonical normalized event artifacts when they are present and expose those canonical semantic event records through `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`.

For legacy turns that do not yet have the canonical event artifact, the passive server SHALL fall back to the existing raw-stdout compatibility parsing path rather than failing inspection.

#### Scenario: Passive server returns canonical events for new turn artifacts
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` for a turn whose canonical normalized event artifact exists
- **THEN** the passive server returns canonical Houmao semantic event records from that artifact
- **AND THEN** the caller does not need direct provider-specific parsing logic for that turn

#### Scenario: Passive server preserves inspection for legacy turns
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` for an older turn that only has raw provider stdout artifacts
- **THEN** the passive server falls back to compatibility parsing of the raw stdout artifact
- **AND THEN** the route remains usable instead of failing only because the canonical event artifact is absent

### Requirement: Passive server raw artifact routes remain raw provider debug surfaces
For managed headless turns, the passive server artifact routes SHALL continue returning the raw durable provider artifacts rather than rendered pane output or canonical semantic JSON.

#### Scenario: Passive server stdout artifact remains raw provider output
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout` for a managed headless turn
- **THEN** the passive server returns the raw provider stdout artifact for that turn
- **AND THEN** the response does not replace that artifact with rendered human text or canonical semantic event output
