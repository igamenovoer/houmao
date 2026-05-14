## REMOVED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise-v2` system skill
**Reason**: The pairwise-v2 package is retired from the current system-skill inventory in favor of `houmao-agent-loop-pro`.
**Migration**: Use `houmao-agent-loop-pro` for current loop authoring and generated loop execution. Treat pairwise-v2 routing-packet and recovery language as legacy context unless a current pro execplan explicitly generates equivalent contracts.

## ADDED Requirements

### Requirement: Pairwise-v2 skill is retired
The system SHALL NOT package `houmao-agent-loop-pairwise-v2` as a current installable Houmao-owned system skill.

Current docs and routing guidance SHALL NOT present pairwise-v2 as a current choice for new loop authoring.

#### Scenario: Pairwise-v2 name is absent from current inventory
- **WHEN** the current system-skill inventory is loaded
- **THEN** `houmao-agent-loop-pairwise-v2` is not present as a current installable skill
- **AND THEN** current loop authoring guidance points to `houmao-agent-loop-pro`
