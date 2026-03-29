## MODIFIED Requirements

### Requirement: Brain-agnostic role packages

Roles SHALL be defined independently of the CLI tool. A role SHALL include a `system-prompt.md` and MAY include supporting files referenced by the prompt.

`system-prompt.md` MAY be intentionally empty to represent a role with no system prompt.

#### Scenario: Role prompt references supporting files

- **WHEN** a role's `system-prompt.md` references a supporting file under the role directory
- **THEN** that supporting file SHALL exist within the role package

#### Scenario: Empty role prompt remains a valid canonical role package

- **WHEN** a role's `system-prompt.md` exists but contains no prompt content
- **THEN** that role package remains valid
- **AND THEN** downstream build or launch consumers treat it as a role with no system prompt rather than a missing-role error
