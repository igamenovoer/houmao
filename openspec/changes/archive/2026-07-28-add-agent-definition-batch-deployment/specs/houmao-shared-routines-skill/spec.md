## ADDED Requirements

### Requirement: Shared routines exposes plural deployment under admin posture
The public shared-routines skill SHALL expose batch deployment as a subcommand of `houmao-agent-definition` and SHALL reject it under `as-agent`.

#### Scenario: Advanced admin invokes batch deployment
- **WHEN** actor posture is admin
- **THEN** the route SHALL expose Batch Request, plan, and apply guidance

#### Scenario: Managed agent invokes batch deployment
- **WHEN** actor posture is managed agent
- **THEN** the route SHALL reject the operation
