## REMOVED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise-v3` system skill
**Reason**: The pairwise-v3 package is retired from the current system-skill inventory in favor of `houmao-agent-loop-pro`.
**Migration**: Use `houmao-agent-loop-pro` plus generated workspace contracts and the `prepare-workspace` stage for current workspace-aware loop execution.

## ADDED Requirements

### Requirement: Pairwise-v3 skill is retired
The system SHALL NOT package `houmao-agent-loop-pairwise-v3` as a current installable Houmao-owned system skill.

Current workspace-aware loop guidance SHALL route through pro generated execplan contracts rather than the retired pairwise-v3 package.

#### Scenario: Pairwise-v3 name is absent from current inventory
- **WHEN** the current system-skill inventory is loaded
- **THEN** `houmao-agent-loop-pairwise-v3` is not present as a current installable skill
- **AND THEN** workspace-aware loop guidance points to `houmao-agent-loop-pro`
