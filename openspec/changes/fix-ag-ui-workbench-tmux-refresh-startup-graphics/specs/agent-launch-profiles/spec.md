## ADDED Requirements

### Requirement: Launch-profile system-skill validation is selected-source scoped
Launch-profile system-skill validation SHALL evaluate the selected launch profile, selected source recipe or specialist, and the dependencies required for that selected launch.

Validation SHALL NOT fail a launch solely because an unrelated unselected project preset, profile, or launch profile contains a removed or unknown system-skill selector.

When the selected launch source contains a removed or unknown system-skill selector, validation SHALL fail before launch mutation and SHALL name the selected source and offending selector.

#### Scenario: Unselected stale preset does not block selected profile
- **WHEN** project preset `unused-kimi` stores removed system-skill selector `houmao-agent-ag-ui`
- **AND WHEN** the operator launches selected profile `test-claude` that does not depend on `unused-kimi`
- **THEN** launch-profile system-skill validation ignores `unused-kimi`
- **AND THEN** the selected `test-claude` launch proceeds or fails only for issues in its own selected source path

#### Scenario: Selected stale profile fails clearly
- **WHEN** selected launch profile `unused-kimi` stores removed system-skill selector `houmao-agent-ag-ui`
- **AND WHEN** the operator launches `unused-kimi`
- **THEN** validation fails before constructing the managed agent
- **AND THEN** the error names `unused-kimi` and `houmao-agent-ag-ui`
