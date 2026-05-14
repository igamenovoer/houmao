## REMOVED Requirements

### Requirement: Houmao provides a packaged manual `houmao-agent-loop-pairwise-v5` system skill
**Reason**: The pairwise-v5 package is retired from the current system-skill inventory after its generated-execplan workflow is consolidated into `houmao-agent-loop-pro`.
**Migration**: Use `houmao-agent-loop-pro` for `init`, `clarify-intent`, `clarify-execplan`, `execplan-*`, `prepare-*`, `validate-loop`, `launch-agents`, and run-control workflows.

## ADDED Requirements

### Requirement: Pairwise-v5 skill is retired in favor of pro
The system SHALL NOT package `houmao-agent-loop-pairwise-v5` as a current installable Houmao-owned system skill.

The current generated-execplan loop workflow SHALL live under `houmao-agent-loop-pro`.

#### Scenario: Pairwise-v5 name is absent from current inventory
- **WHEN** the current system-skill inventory is loaded
- **THEN** `houmao-agent-loop-pairwise-v5` is not present as a current installable skill
- **AND THEN** generated-execplan loop workflow guidance points to `houmao-agent-loop-pro`
