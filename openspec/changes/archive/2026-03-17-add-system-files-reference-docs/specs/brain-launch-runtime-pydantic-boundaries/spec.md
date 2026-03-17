## ADDED Requirements

### Requirement: Runtime schema-packaging specs describe the current v2 shared-registry contract
The runtime Pydantic-boundaries specification SHALL describe the current packaged shared-registry schema and typed boundary in terms of the `agent_id`-keyed v2 registry record contract rather than the retired v1 `agent_key` contract.

At minimum, the current-contract description SHALL align on:

- `live_agents/<agent-id>/record.json` as the current persisted registry path pattern,
- `live_agent_registry_record.v2.schema.json` as the current packaged standalone registry schema for the active record contract,
- `LiveAgentRegistryRecordV2` as the current typed boundary for live registry-record semantics.

#### Scenario: Current registry schema packaging is described through the v2 contract
- **WHEN** a reader uses the runtime schema-packaging spec to understand the current packaged registry schema
- **THEN** the spec describes the active shipped registry schema in terms of the v2 `agent_id`-keyed contract
- **AND THEN** it does not present the v1 `agent_key` schema as the current write-time contract

### Requirement: Historical packaged registry schemas are either removed or clearly marked as non-current
If the runtime package retains historical shared-registry schema files that are no longer the active supported contract, the specification SHALL distinguish those historical artifacts from the current registry schema rather than describing them as equally current.

If no live code, tests, or supported docs rely on an older packaged registry schema artifact, the repository MAY remove that artifact instead of retaining it.

#### Scenario: Retained historical registry schema is not presented as the active contract
- **WHEN** a historical packaged registry schema such as `live_agent_registry_record.v1.schema.json` remains in the repository
- **THEN** the surrounding specification describes it as historical or non-current
- **AND THEN** readers are not left to infer that the historical file is the active registry schema used by current publication flows

#### Scenario: Unused historical registry schema may be removed
- **WHEN** maintainers confirm that an older packaged registry schema is no longer exercised by live code, tests, or supported docs
- **THEN** the repository may remove that historical schema artifact
- **AND THEN** the current spec remains centered on the active shipped registry schema contract
