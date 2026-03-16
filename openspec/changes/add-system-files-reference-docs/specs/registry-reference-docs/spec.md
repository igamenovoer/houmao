## ADDED Requirements

### Requirement: Registry reference pages link to the centralized system-files reference for the broader Houmao filesystem map
The shared-registry reference documentation SHALL keep registry-specific contract, ownership, and lifecycle semantics in the registry subtree while pointing readers to the centralized system-files reference for the broader Houmao filesystem map.

Registry pages SHALL continue to document registry-specific paths such as `live_agents/<agent-id>/record.json`, but they SHALL defer the broader relationship between the registry root, runtime root, launcher state, and workspace-local scratch to the centralized system-files reference.

Registry reference pages SHALL use current `agent_id`-keyed terminology for live-agent directories and SHALL NOT describe the current registry layout through legacy `agent key` language from the older canonical-name-keyed design.

Registry reference pages SHALL describe the current shipped standalone registry schema and typed publication model in terms of the v2 registry record contract and SHALL NOT describe `LiveAgentRegistryRecordV1` or “packaged schema is still a follow-up” as current implementation status.

At minimum, the registry reference SHALL link to the centralized system-files reference when discussing:

- the place of the registry root within the larger Houmao-owned storage model,
- filesystem-preparation guidance that extends beyond registry-only concerns,
- comparisons between registry files and other Houmao-owned artifact families.

#### Scenario: Registry docs keep locator semantics local and broader storage guidance central
- **WHEN** a reader opens the registry reference to understand `record.json` layout, freshness, or cleanup behavior
- **THEN** the registry docs explain those registry-specific contracts directly
- **AND THEN** they point to the centralized system-files reference for the broader Houmao root-and-layout map

#### Scenario: Registry docs do not become the only filesystem-preparation guide
- **WHEN** a reader needs to understand how the shared-registry root relates to other Houmao-managed storage or how to plan filesystem preparation more broadly
- **THEN** the registry docs link to the centralized system-files reference
- **AND THEN** the reader is not forced to infer non-registry filesystem guidance from registry pages alone

#### Scenario: Registry landing docs use current live-agent directory terminology
- **WHEN** a reader opens registry reference pages to understand how live-agent directories are named
- **THEN** the docs describe the current layout in terms of authoritative `agent_id` directories
- **AND THEN** they do not present legacy `agent key` wording as the current filesystem contract

#### Scenario: Registry docs use the current typed model and packaged-schema status
- **WHEN** a reader opens registry reference pages that explain publication flow or shipped registry schema status
- **THEN** those pages describe the current live registry model in terms of `LiveAgentRegistryRecordV2` and the shipped v2 schema
- **AND THEN** they do not describe the packaged schema as a future follow-up or `LiveAgentRegistryRecordV1` as the current publication model
