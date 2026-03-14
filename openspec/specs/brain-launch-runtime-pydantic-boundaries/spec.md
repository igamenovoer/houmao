## Purpose
Define validation and schema-packaging expectations for runtime-persisted artifacts and their public interface boundaries.
## Requirements
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
- **THEN** they can find versioned schema files under `houmao/agents/realm_controller/schemas/` (for example `session_manifest.v1.schema.json`)

### Requirement: Public runtime interfaces remain dataclass-first
The system SHALL keep the runtime’s public execution-time interfaces dataclass-first (for example events and control results), and SHALL NOT require callers to construct Pydantic models to use the runtime.

#### Scenario: CLI emits session events without exposing Pydantic models
- **WHEN** a developer runs the `send-prompt` CLI command
- **THEN** the CLI prints JSON events derived from runtime dataclass outputs
- **AND THEN** the user does not need to import or construct Pydantic models to use the CLI/API

### Requirement: Shared-registry record schema is packaged as a standalone versioned JSON Schema
The system SHALL ship a standalone versioned JSON Schema file for the shared-registry `record.json` contract inside the runtime package.

That schema SHALL live under `houmao/agents/realm_controller/schemas/` and SHALL correspond to the current v1 shared-registry record payload written under `live_agents/<agent-key>/record.json`, including nested `identity`, `runtime`, and `terminal` groups plus optional `gateway` and `mailbox` groups when present.

#### Scenario: Registry record schema is discoverable in the runtime package
- **WHEN** a developer inspects the runtime package source or installed package contents
- **THEN** they can find a versioned shared-registry record schema file under `houmao/agents/realm_controller/schemas/`
- **AND THEN** that schema file describes the persisted v1 `record.json` contract for one live published agent, including the currently documented optional publication groups

### Requirement: Shared-registry record create and rewrite flows are validated against the packaged schema
When the runtime creates or rewrites shared-registry `record.json`, it SHALL validate the serialized payload against the packaged shared-registry record schema before atomically replacing the on-disk file.

This requirement SHALL apply to both first publication and later refresh-driven rewrites of the same record.

This packaged-schema validation supplements, and SHALL NOT replace, the existing strict `LiveAgentRegistryRecordV1` Pydantic boundary for semantic invariants that the lightweight runtime schema validator does not encode.

#### Scenario: Initial publication validates against the packaged registry schema
- **WHEN** the runtime publishes a new shared-registry `record.json` for a live session
- **THEN** it validates the serialized payload against the packaged registry-record schema before replacing the target file
- **AND THEN** the written file conforms to the standalone packaged contract for that schema version

#### Scenario: Refresh rewrite rejects a schema-invalid registry payload
- **WHEN** the runtime is about to rewrite an existing shared-registry `record.json` during a later refresh or state update
- **AND WHEN** the serialized payload does not conform to the packaged registry-record schema
- **THEN** the rewrite is rejected before the atomic replace completes
- **AND THEN** the runtime does not leave behind a partially written replacement `record.json`

### Requirement: Shared-registry packaged schema complements model-only invariants
The system SHALL continue to treat `LiveAgentRegistryRecordV1` as the authoritative typed boundary for current registry-record semantics, while using the packaged schema as the shipped structural disk contract for runtime-managed writes.

#### Scenario: Cross-field registry invariant remains model-enforced
- **WHEN** a registry payload would violate a semantic invariant such as incomplete live gateway fields, a non-canonical `agent_name`, or `lease_expires_at` not later than `published_at`
- **THEN** the runtime still rejects that record through the strict typed boundary
- **AND THEN** the packaged schema is not treated as the sole source of truth for those model-only invariants
