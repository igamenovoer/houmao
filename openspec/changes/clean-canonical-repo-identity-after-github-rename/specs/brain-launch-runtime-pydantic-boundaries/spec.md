## MODIFIED Requirements

### Requirement: Versioned JSON Schemas remain packaged for persisted artifacts
The system SHALL ship versioned JSON Schema files for persisted runtime artifacts inside the runtime Python package.

#### Scenario: Schemas are discoverable in the runtime package
- **WHEN** a developer inspects the runtime package source
- **THEN** they can find versioned schema files under `houmao/agents/realm_controller/schemas/` (for example `session_manifest.v1.schema.json`)
