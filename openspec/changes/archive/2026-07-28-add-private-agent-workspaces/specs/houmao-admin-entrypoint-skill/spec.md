## ADDED Requirements

### Requirement: Admin entrypoint routes explicit-instance workspace operations
The admin entrypoint SHALL route workspace inspection, validation, remapping, materialization, tracking, projection, and cleanup through the existing agent-instance routine.

#### Scenario: Human remaps one semantic label
- **WHEN** the human names one agent, label, and relative path
- **THEN** routing SHALL use explicit-target admin mutation

#### Scenario: Human requests cleanup
- **WHEN** the human asks to delete a private workspace
- **THEN** routing SHALL identify the destructive operation and require maintained drift checks
