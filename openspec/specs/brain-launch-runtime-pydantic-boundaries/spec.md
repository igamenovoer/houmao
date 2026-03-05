## ADDED Requirements

### Requirement: Persisted runtime artifacts are Pydantic-validated on write
The system SHALL validate runtime-persisted artifacts (at minimum session manifests and launch-plan payloads) using Pydantic models before writing them to disk.

#### Scenario: Reject invalid session manifest on write
- **WHEN** the runtime is about to persist a session manifest payload that is missing required fields or has invalid types
- **THEN** the write is rejected
- **AND THEN** the runtime surfaces an error that identifies the failing field path and reason

#### Scenario: Persisted session manifest includes schema version
- **WHEN** the runtime writes a session manifest
- **THEN** the payload includes `schema_version=1`

### Requirement: Persisted runtime artifacts are Pydantic-validated on load/resume
The system SHALL validate persisted runtime artifacts using the same Pydantic models when loading them for resume/control operations.

#### Scenario: Reject invalid session manifest on load
- **WHEN** a caller attempts to resume a session from a persisted manifest that does not conform to the v1 model
- **THEN** the runtime rejects the operation with an explicit validation error (field path + reason)
- **AND THEN** the runtime does not silently start a new unrelated session

### Requirement: Versioned JSON Schemas remain packaged for persisted artifacts
The system SHALL ship versioned JSON Schema files for persisted runtime artifacts inside the runtime Python package.

#### Scenario: Schemas are discoverable in the runtime package
- **WHEN** a developer inspects the runtime package source
- **THEN** they can find versioned schema files under `gig_agents/agents/brain_launch_runtime/schemas/` (for example `session_manifest.v1.schema.json`)

### Requirement: Public runtime interfaces remain dataclass-first
The system SHALL keep the runtime’s public execution-time interfaces dataclass-first (for example events and control results), and SHALL NOT require callers to construct Pydantic models to use the runtime.

#### Scenario: CLI emits session events without exposing Pydantic models
- **WHEN** a developer runs the `send-prompt` CLI command
- **THEN** the CLI prints JSON events derived from runtime dataclass outputs
- **AND THEN** the user does not need to import or construct Pydantic models to use the CLI/API
