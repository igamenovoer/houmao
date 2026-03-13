## MODIFIED Requirements

### Requirement: JSON Schema assets live in `src/` runtime package
The system SHALL keep JSON Schema files for runtime-generated structured artifacts inside the runtime package under `src/houmao/.../schemas/`.

#### Scenario: Session manifest schema is versioned and discoverable
- **WHEN** developers inspect the runtime package source
- **THEN** they can find versioned JSON Schema files (for example `session_manifest.v1.schema.json`) under the runtime package `schemas/` directory
- **AND THEN** generated artifacts include schema version information that selects the matching schema for validation
