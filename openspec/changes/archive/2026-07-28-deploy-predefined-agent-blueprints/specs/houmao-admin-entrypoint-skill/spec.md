## ADDED Requirements

### Requirement: Admin entrypoint distinguishes authoring from deployment
The admin entrypoint SHALL route human requirements for a reusable agent to Agent Definition authoring and SHALL route an existing materialized revision plus a target project to deployment.

#### Scenario: Requirements have no materialized revision
- **WHEN** the human describes what a reusable agent should be
- **THEN** the entrypoint SHALL route to `houmao-agent-definition init-intent` or derivation rather than project deployment

#### Scenario: Materialized revision is supplied
- **WHEN** the human asks to deploy a specific revision
- **THEN** the entrypoint SHALL route to deployment input collection and planning

### Requirement: Admin entrypoint keeps deployment separate from launch
The entrypoint SHALL not interpret “deploy this definition” as authority to start a managed agent.

#### Scenario: Deployment succeeds
- **WHEN** apply returns a launch handoff
- **THEN** the entrypoint SHALL present the command and wait for a separate launch instruction
