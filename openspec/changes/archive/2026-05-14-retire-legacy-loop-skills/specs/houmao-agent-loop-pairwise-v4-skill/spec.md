## REMOVED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise-v4` system skill
**Reason**: The pairwise-v4 package is retired from the current system-skill inventory in favor of `houmao-agent-loop-pro`.
**Migration**: Use `houmao-agent-loop-pro` execplan generation for current structured document templates, source constraints, generated role skills, and generated validation contracts.

## ADDED Requirements

### Requirement: Pairwise-v4 skill is retired
The system SHALL NOT package `houmao-agent-loop-pairwise-v4` as a current installable Houmao-owned system skill.

Current template-driven loop guidance SHALL route through pro generated execplan artifacts rather than the retired pairwise-v4 package.

#### Scenario: Pairwise-v4 name is absent from current inventory
- **WHEN** the current system-skill inventory is loaded
- **THEN** `houmao-agent-loop-pairwise-v4` is not present as a current installable skill
- **AND THEN** template-driven loop guidance points to `houmao-agent-loop-pro`
