## ADDED Requirements

### Requirement: Agent Definition routine supports bounded plural deployment
The existing Agent Definition routine SHALL collect count, shared inputs, member overrides, and explicit delegation before creating a Batch Request.

#### Scenario: Human delegates three selection categories
- **WHEN** the human asks for `N` deployments and explicitly delegates names, tools, and credential references
- **THEN** the routine SHALL propose bounded selections and SHALL preview every member before apply

### Requirement: The routine uses maintained batch commands
The routine SHALL delegate validation, planning, apply, recovery, and doctor to maintained `houmao-mgr` batch commands.

#### Scenario: Human confirms the batch plan
- **WHEN** every member is valid and the human confirms
- **THEN** the routine SHALL call one maintained batch apply command
