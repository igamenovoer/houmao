## REMOVED Requirements

### Requirement: Managed-agent state reports workspace lanes
**Reason**: Managed-agent state no longer reports workspace lanes.

**Migration**: Report memory root, memo file, and pages directory.

## ADDED Requirements

### Requirement: Managed-agent state reports memo-pages memory
Managed-agent state and detailed-state payloads SHALL report memory root, memo file, and pages directory when available.

Managed-agent state SHALL NOT report scratch directory, persist binding, or persist directory as current managed memory fields.

Managed-agent state SHALL NOT report `memory_dir` as a current external persist binding.

#### Scenario: State reports memory pages
- **WHEN** managed agent `researcher` has memory root `/repo/.houmao/memory/agents/researcher-id`
- **AND WHEN** the agent has memo file `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND WHEN** the agent has pages directory `/repo/.houmao/memory/agents/researcher-id/pages`
- **THEN** managed-agent state reports the memory root
- **AND THEN** it reports the memo file
- **AND THEN** it reports the pages directory
- **AND THEN** it does not report `persist_dir`

#### Scenario: Old workspace fields are absent from current state
- **WHEN** a managed agent exposes current memo-pages memory metadata
- **THEN** managed-agent state does not report `scratch_dir`
- **AND THEN** managed-agent state does not report `persist_binding`
