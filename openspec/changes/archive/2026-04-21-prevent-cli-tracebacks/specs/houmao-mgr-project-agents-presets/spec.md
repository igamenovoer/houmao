## ADDED Requirements

### Requirement: `project agents recipes` fail clearly on malformed stored preset files

When `houmao-mgr project agents recipes ...` or the compatibility `project agents presets ...` surface parses existing stored preset files during inspection or enumeration and encounters malformed YAML or invalid preset content, the command SHALL fail as explicit CLI error output rather than leaking a Python traceback.

This SHALL apply at minimum to:

- `project agents recipes list`
- `project agents recipes get`
- `project agents presets list`
- `project agents presets get`

The error text SHALL identify the offending preset file path so the operator can repair or remove the malformed file.

#### Scenario: Canonical recipe list fails clearly on a malformed preset file

- **WHEN** an operator runs `houmao-mgr project agents recipes list`
- **AND WHEN** `.houmao/agents/presets/broken.yaml` contains malformed or invalid preset content
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error identifies `.houmao/agents/presets/broken.yaml` as the offending file
- **AND THEN** the operator does not see a Python traceback

#### Scenario: Preset compatibility get fails clearly on a malformed preset file

- **WHEN** an operator runs `houmao-mgr project agents presets get --name broken`
- **AND WHEN** `.houmao/agents/presets/broken.yaml` contains malformed or invalid preset content
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error identifies `.houmao/agents/presets/broken.yaml` as the offending file
- **AND THEN** the operator does not see a Python traceback
