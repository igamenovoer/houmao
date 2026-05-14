## REMOVED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise` system skill
**Reason**: The stable pairwise package is retired from the current system-skill inventory in favor of `houmao-agent-loop-pro`.
**Migration**: Use `houmao-agent-loop-pro` with `tree-loop` topology mode for current tree-loop authoring and execution.

## ADDED Requirements

### Requirement: Stable pairwise skill is retired
The system SHALL NOT package `houmao-agent-loop-pairwise` as a current installable Houmao-owned system skill.

Current guidance SHALL route tree-loop authoring and execution through `houmao-agent-loop-pro`.

#### Scenario: Stable pairwise name is absent from current inventory
- **WHEN** the current system-skill inventory is loaded
- **THEN** `houmao-agent-loop-pairwise` is not present as a current installable skill
- **AND THEN** `houmao-agent-loop-pro` is present as the current loop skill
