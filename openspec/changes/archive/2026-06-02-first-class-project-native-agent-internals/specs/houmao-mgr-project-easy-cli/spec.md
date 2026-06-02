## ADDED Requirements

### Requirement: Public project easy prefix is retired
The public `houmao-mgr project easy` command family SHALL be retired.

All maintained higher-level project workflows previously exposed under `project easy` SHALL be promoted to ordinary `project` command groups:

- `project easy specialist ...` -> `project specialist ...`
- `project easy profile ...` -> `project profile ...`
- `project easy instance ...` -> project-scoped managed-agent commands such as `project agents ...` or another project-layer instance command selected by the implementation design

The promoted commands SHALL preserve the project-layer semantics of specialists, profiles, managed-header policy, skill overlays, memo seeds, gateway defaults, model configuration, credential references, and managed-agent lifecycle behavior unless another spec explicitly changes those semantics.

#### Scenario: Project easy is not shown as the ordinary path
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output does not list `easy`
- **AND THEN** it lists the promoted specialist/profile/project-agent command groups

#### Scenario: Promoted specialist create replaces easy specialist create
- **WHEN** an operator wants to create a project specialist
- **THEN** the supported ordinary command path is `houmao-mgr project specialist create`
- **AND THEN** the command persists the same project-layer specialist semantics formerly owned by `project easy specialist create`

### Requirement: Project profile replaces easy profile terminology
The user-facing term `easy profile` SHALL be replaced by `profile` in ordinary project commands, documentation, config drafts, command-template descriptions, and packaged system skills.

Internal persisted lane names MAY remain stable during migration when changing them would create unnecessary catalog churn, but user-facing output SHALL explain the resource as a project profile.

#### Scenario: Profile get reports project profile terminology
- **WHEN** an operator runs `houmao-mgr project profile get --name reviewer-fast`
- **THEN** the command reports the resource as a project profile
- **AND THEN** it does not call the resource an easy profile in ordinary user-facing fields

## REMOVED Requirements

### Requirement: `project easy specialist create` compiles one specialist into canonical project agent artifacts
**Reason**: The specialist create workflow is promoted to `houmao-mgr project specialist create`; the `easy` prefix is no longer part of the public model.
**Migration**: Use `houmao-mgr project specialist create` with the same project-layer specialist inputs.

#### Scenario: Specialist creation uses the promoted command
- **WHEN** an operator creates a specialist
- **THEN** the maintained public path is `houmao-mgr project specialist create`
- **AND THEN** `project easy specialist create` is not presented as the ordinary workflow

### Requirement: `project easy profile create/list/get/remove` manages specialist-backed easy profiles
**Reason**: Specialist-backed reusable launch defaults are ordinary project profiles.
**Migration**: Use `houmao-mgr project profile create|list|get|remove`.

#### Scenario: Profile management uses the promoted command
- **WHEN** an operator manages a reusable specialist-backed profile
- **THEN** the maintained public path is `houmao-mgr project profile ...`
- **AND THEN** the resource is described as a project profile

### Requirement: `project easy instance launch` derives provider from one specialist and launches one runtime instance
**Reason**: Project managed-agent lifecycle belongs to the first-class project agent/instance surface, not an `easy` wrapper.
**Migration**: Use the promoted project-scoped managed-agent launch command selected by this change's implementation.

#### Scenario: Instance launch uses project-scoped lifecycle commands
- **WHEN** an operator launches a managed agent from a specialist or profile
- **THEN** the maintained public path is a promoted project-scoped managed-agent command
- **AND THEN** `project easy instance launch` is not presented as the ordinary workflow

### Requirement: `project easy instance list/get/stop` presents runtime state by specialist and wraps existing runtime stop control
**Reason**: Project-scoped managed-agent lifecycle inspection and stop belong to the promoted project agent/instance command surface.
**Migration**: Use the promoted project-scoped managed-agent list/get/stop commands.

#### Scenario: Runtime inspection uses project-scoped lifecycle commands
- **WHEN** an operator lists, inspects, or stops project-managed agents
- **THEN** the maintained public path is the promoted project-scoped managed-agent lifecycle command
- **AND THEN** the command does not require an `easy` prefix
