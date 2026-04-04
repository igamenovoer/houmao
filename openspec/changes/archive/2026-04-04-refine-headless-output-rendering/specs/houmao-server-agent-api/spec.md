## ADDED Requirements

### Requirement: Managed headless turn events use canonical semantic event records
For accepted managed headless turns, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` SHALL return canonical Houmao semantic event records rather than thin provider passthrough records.

Those event records SHALL expose normalized execution semantics such as assistant output, tool lifecycle, completion state, provider provenance, and canonical session identity when available.

The route SHALL not require callers to understand provider-specific event names in order to interpret normal turn progress.

#### Scenario: Caller inspects canonical semantic events
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` for an accepted managed headless turn
- **THEN** `houmao-server` returns canonical Houmao semantic event records for that turn
- **AND THEN** the caller can distinguish assistant progress and tool lifecycle without parsing provider-specific event names directly

#### Scenario: Unknown provider event remains inspectable
- **WHEN** the underlying headless turn includes a provider event that Houmao cannot classify into a more specific semantic category
- **THEN** `houmao-server` still returns a canonical passthrough or diagnostic event for that record
- **AND THEN** the route does not fail solely because one provider event shape is newly introduced upstream

### Requirement: Managed headless raw artifact routes remain provider-owned debug surfaces
For accepted managed headless turns, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout` and `.../stderr` SHALL continue exposing the raw durable artifacts for that turn.

The stdout artifact route SHALL return raw provider stdout rather than live rendered pane text or canonical Houmao semantic JSON.

#### Scenario: Stdout artifact remains raw provider output
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout` for a managed headless turn
- **THEN** `houmao-server` returns the raw provider stdout artifact for that turn
- **AND THEN** the response does not substitute rendered human text or canonical semantic event output for that raw artifact
