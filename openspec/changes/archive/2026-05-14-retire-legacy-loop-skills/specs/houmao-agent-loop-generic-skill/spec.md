## REMOVED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-generic` system skill
**Reason**: The generic loop package is retired from the current system-skill inventory because `houmao-agent-loop-pro` owns generic-loop topology mode.
**Migration**: Use `houmao-agent-loop-pro` with `generic-loop` topology mode for current non-tree or cycle-capable loop authoring and execution.

## ADDED Requirements

### Requirement: Generic loop skill is retired
The system SHALL NOT package `houmao-agent-loop-generic` as a current installable Houmao-owned system skill.

Current generic-loop guidance SHALL route through pro topology modes and generated execplan contracts.

#### Scenario: Generic loop name is absent from current inventory
- **WHEN** the current system-skill inventory is loaded
- **THEN** `houmao-agent-loop-generic` is not present as a current installable skill
- **AND THEN** generic-loop guidance points to `houmao-agent-loop-pro`
