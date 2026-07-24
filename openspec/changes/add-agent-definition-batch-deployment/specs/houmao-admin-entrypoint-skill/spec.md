## ADDED Requirements

### Requirement: Admin entrypoint routes plural definition deployment
The admin entrypoint SHALL route a request for multiple project deployments from one materialized definition to the Agent Definition batch route.

#### Scenario: Human requests several agents
- **WHEN** the request names a definition, target project, and positive count
- **THEN** the entrypoint SHALL preserve explicit delegation and SHALL not route to repeated live launches

### Requirement: Plural deployment does not imply launch
The admin entrypoint SHALL present member launch handoffs after apply and SHALL wait for separate launch instructions.

#### Scenario: Batch apply succeeds
- **WHEN** all members are created
- **THEN** the entrypoint SHALL not start any member
