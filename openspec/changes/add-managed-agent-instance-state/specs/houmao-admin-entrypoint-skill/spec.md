## ADDED Requirements

### Requirement: Admin entrypoint routes explicit-instance state operations
The admin entrypoint SHALL route runtime-variable and mindset inspection or mutation through the existing agent-instance routine and SHALL require one explicit target.

#### Scenario: Human revises a mindset by name
- **WHEN** the human names an agent and mindset
- **THEN** the entrypoint SHALL route to operator-targeted mindset revision

#### Scenario: Human omits the target
- **WHEN** a mutation request does not identify one agent
- **THEN** the entrypoint SHALL ask for the target rather than treating the operator as self

### Requirement: Launch requests collect instance values
The admin entrypoint SHALL distinguish deployment inputs from per-instance launch values.

#### Scenario: Human supplies runtime values during launch
- **WHEN** a profile declares runtime variables
- **THEN** the entrypoint SHALL route those values to managed-launch preparation and SHALL not rewrite the project deployment
