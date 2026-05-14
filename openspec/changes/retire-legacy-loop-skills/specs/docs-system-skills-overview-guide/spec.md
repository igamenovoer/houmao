## ADDED Requirements

### Requirement: System-skills overview presents pro-only loop control
The system-skills overview guide SHALL describe `houmao-agent-loop-pro` as the current loop authoring, execplan generation, and generated-loop execution skill.

The overview SHALL describe tree-loop and generic-loop as pro topology modes rather than separate packaged loop skills.

#### Scenario: Reader uses overview to select loop skill
- **WHEN** a reader uses the system-skills overview to identify the loop skill
- **THEN** the overview points to `houmao-agent-loop-pro`
- **AND THEN** it does not present retired pairwise or generic packages as current alternatives
