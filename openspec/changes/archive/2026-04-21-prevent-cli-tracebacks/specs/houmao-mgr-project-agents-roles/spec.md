## ADDED Requirements

### Requirement: `project agents roles` fail clearly when referenced preset files are malformed

When a maintained `houmao-mgr project agents roles ...` command traverses project-local preset references and encounters malformed YAML or invalid preset content under `.houmao/agents/presets/`, the command SHALL fail as explicit CLI error output rather than leaking a Python traceback.

This SHALL apply at minimum to role flows that inspect or enforce preset references, including:

- `project agents roles list`
- `project agents roles get`
- `project agents roles remove`

The error text SHALL identify the offending preset file path so the operator can repair or remove the malformed preset file.

#### Scenario: Role inspection fails clearly when a referenced preset file is malformed

- **WHEN** an operator runs `houmao-mgr project agents roles get --name researcher`
- **AND WHEN** the role inspection path encounters malformed or invalid preset content under `.houmao/agents/presets/`
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error identifies the offending preset file path
- **AND THEN** the operator does not see a Python traceback

#### Scenario: Role listing fails clearly when the preset tree is malformed

- **WHEN** an operator runs `houmao-mgr project agents roles list`
- **AND WHEN** the role listing path encounters malformed or invalid preset content under `.houmao/agents/presets/`
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error identifies the offending preset file path
- **AND THEN** the operator does not see a Python traceback
