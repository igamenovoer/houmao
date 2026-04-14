## ADDED Requirements

### Requirement: Managed-agent state reports workspace lanes
Managed-agent state and detailed-state payloads SHALL report workspace root, memo file, scratch directory, persist binding, and persist directory when available.

When persistence is disabled, managed-agent state SHALL report the disabled persist binding and `persist_dir: null`.

Managed-agent state SHALL NOT report `memory_dir` as the current workspace contract.

#### Scenario: State reports enabled workspace lanes
- **WHEN** managed agent `researcher` has workspace root `/repo/.houmao/memory/agents/researcher-id`
- **AND WHEN** persistence is enabled
- **THEN** managed-agent state reports the workspace root
- **AND THEN** it reports the memo file
- **AND THEN** it reports the scratch directory
- **AND THEN** it reports the persist directory

#### Scenario: State reports disabled persist lane
- **WHEN** managed agent `researcher` has persistence disabled
- **THEN** managed-agent state reports the workspace root, memo file, and scratch directory
- **AND THEN** it reports `persist_dir: null`
- **AND THEN** it does not report `memory_dir`
