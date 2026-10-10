# houmao-admin-entrypoint-skill Specification

## Purpose
TBD - created by archiving change refactor-system-skills-by-actor. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a public human-operator entrypoint
Houmao SHALL provide a public skill named `houmao-admin-entrypoint` as the executable entrypoint of the admin pack.

Its startup-visible description and opening workflow SHALL state that the assistant acts for a human operator, is not the managed agent being administered, and routes mutations only after resolving the required target and intent.

#### Scenario: Human invokes the admin entrypoint
- **WHEN** a human invokes `houmao-admin-entrypoint` for a managed-agent operation
- **THEN** the entrypoint establishes an admin actor frame before selecting a protected route
- **AND THEN** it does not use managed self identity as an implicit target

### Requirement: Admin entrypoint resolves target and operation before mutation
For target-sensitive work, the admin entrypoint SHALL resolve the requested operation and explicit project, agent, mailbox, gateway, credential, workspace, or loop target from the prompt and recent unambiguous context.

If a blocking value remains unknown, it SHALL use supported read-only discovery and the required/optional question contract. It SHALL preserve explicit user choices and SHALL NOT guess a mutating target.

#### Scenario: Multiple managed agents match an admin request
- **WHEN** read-only discovery finds more than one plausible target and the user did not identify one
- **THEN** the entrypoint asks for the required target and separates optional modifiers
- **AND THEN** it performs no target mutation before the user resolves the ambiguity

### Requirement: Admin entrypoint routes only through its protected admin composition
Operational commands SHALL route from the public admin entrypoint to the admin composition of `houmao-shared-routines` using manifest-declared route member names.

The entrypoint SHALL reject agent-only routes and SHALL NOT instruct the user to invoke a protected logical id as a public skill.

#### Scenario: Admin routes agent inspection
- **WHEN** a human asks to inspect an explicitly selected managed agent
- **THEN** the entrypoint routes through `houmao-admin-entrypoint->houmao-shared-routines->agent-inspect`
- **AND THEN** the protected routine receives the admin frame and selected target

### Requirement: Admin entrypoint delegates welcome-oriented commands
Empty invocation and the commands `help`, `show-options`, `choose-path`, `show-command-map`, `next-step`, and `start-guided-tour` SHALL delegate to the installed public `houmao-admin-welcome` skill.

The entrypoint SHALL preserve supplied context during delegation and SHALL NOT maintain a second copy of the welcome content beneath its own asset tree.

#### Scenario: Empty admin invocation opens welcome guidance
- **WHEN** a user invokes `houmao-admin-entrypoint` without an executable operation
- **THEN** the entrypoint routes to `houmao-admin-welcome`
- **AND THEN** the response stays read-only until the user requests a concrete handoff

### Requirement: Admin entrypoint owns explicit joined-session adoption handoff
The admin entrypoint SHALL route joined-session adoption only when the human explicitly asks to adopt the current session.

After successful adoption it SHALL stop admin routing, refresh skill discovery when necessary, verify managed self identity, and hand later work to `houmao-agent-entrypoint`.

#### Scenario: Adoption succeeds
- **WHEN** the explicit joined-session adoption command succeeds
- **THEN** the admin entrypoint reports the actor transition
- **AND THEN** subsequent managed self work enters through `houmao-agent-entrypoint`

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

### Requirement: Admin entrypoint routes explicit-instance workspace operations
The admin entrypoint SHALL route workspace inspection, validation, remapping, materialization, tracking, projection, and cleanup through the existing agent-instance routine.

#### Scenario: Human remaps one semantic label
- **WHEN** the human names one agent, label, and relative path
- **THEN** routing SHALL use explicit-target admin mutation

#### Scenario: Human requests cleanup
- **WHEN** the human asks to delete a private workspace
- **THEN** routing SHALL identify the destructive operation and require maintained drift checks

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

