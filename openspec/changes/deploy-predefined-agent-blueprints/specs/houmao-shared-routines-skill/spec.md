## ADDED Requirements

### Requirement: Shared routines exposes one Agent Definition route
The public shared-routines skill SHALL list authoring and deployment as subcommands of the existing `houmao-agent-definition` child.

#### Scenario: Advanced admin invokes authoring directly
- **WHEN** an admin explicitly invokes `houmao-shared-routines->houmao-agent-definition`
- **THEN** the skill SHALL expose the maintained authoring and deployment command family

### Requirement: Agent posture cannot administer definitions
The `as-agent` qualifier SHALL reject Agent Definition authoring, materialization, deployment, update, and removal after identity verification.

#### Scenario: Managed agent requests deployment
- **WHEN** the shared routine resolves managed-agent actor posture
- **THEN** it SHALL reject the definition administration route
