## ADDED Requirements

### Requirement: Runtime session manifests are current-schema only
Runtime session manifest loading SHALL accept only the current supported session manifest schema.

When a persisted session manifest uses an older schema version, Houmao SHALL reject it explicitly and direct the operator to start a fresh runtime session. Houmao SHALL NOT upgrade older session manifest payloads into the current schema in memory or on disk.

#### Scenario: Current session manifest loads normally
- **WHEN** Houmao loads a persisted runtime session manifest with the current supported schema version
- **THEN** the manifest is validated against the current model
- **AND THEN** runtime resume, stop, gateway attach, and inspection may use that manifest as current persisted authority

#### Scenario: Older session manifest is rejected
- **WHEN** Houmao loads a persisted runtime session manifest whose schema version is older than the current supported version
- **THEN** manifest loading fails explicitly before deriving current runtime authority from the old payload
- **AND THEN** the diagnostic directs the operator to start a fresh runtime session

#### Scenario: Legacy manifest fields are not synthesized into current authority
- **WHEN** an old session manifest stores authority only in legacy backend-specific fields
- **THEN** Houmao does not synthesize current `runtime`, `tmux`, `interactive`, `agent_launch_authority`, or `gateway_authority` fields from that legacy state
- **AND THEN** the old manifest remains unsupported current runtime state
