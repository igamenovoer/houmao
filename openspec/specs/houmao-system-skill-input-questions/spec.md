## Purpose
Define common question-shape expectations for Houmao-owned system skills when they need user input for Houmao platform, setup, runtime, or lifecycle operations.
## Requirements
### Requirement: System-operation questions preserve actor scope
Houmao public entrypoints and protected routines SHALL distinguish required and optional system inputs while preserving the current actor frame.

For an admin actor, a target that cannot be recovered unambiguously SHALL be required before target mutation. For an agent actor, verified self identity SHALL satisfy a self-target input and SHALL NOT be requested again. A question SHALL NOT offer an option that changes the actor kind or unlocks an audience-ineligible routine.

#### Scenario: Admin target is missing
- **WHEN** an admin route requires a managed-agent selector that is not explicit or unambiguous
- **THEN** the question labels the selector as required and separates optional modifiers
- **AND THEN** it does not offer managed self scope as a guessed default

#### Scenario: Agent self target is already verified
- **WHEN** an agent route needs the current agent and the actor frame contains verified identity
- **THEN** the routine uses that identity
- **AND THEN** it asks only for other blocking inputs and optional modifiers

### Requirement: Direct operational questions remain concise
Executable entrypoints and protected operational routines SHALL use concise Markdown lists or compact tables for missing platform, setup, routing, launch, mailbox, credential, workspace, loop-execution, or lifecycle inputs.

The route SHALL inspect available read-only context before asking and SHALL ask only for unresolved values needed by the selected operation. Domain-intent questions MAY use a natural style when they do not choose Houmao runtime behavior.

#### Scenario: Protected workspace route needs one path
- **WHEN** read-only context resolves all workspace inputs except the required root
- **THEN** the routine asks for that root and lists only applicable optional modifiers
- **AND THEN** it preserves the public entrypoint and actor frame in the continuation

### Requirement: Admin welcome questions remain explanatory and read-only
`houmao-admin-welcome` SHALL preserve examples, concept explanations, recommended defaults, and skip paths while visibly separating required values from optional values for a selected guided path.

The welcome SHALL collect only enough information to orient or prepare a handoff. It SHALL pass confirmed answers to `houmao-admin-entrypoint` and SHALL NOT execute the resulting operation.

#### Scenario: First-time user chooses an agent-team tour
- **WHEN** the welcome needs a project choice before preparing the handoff
- **THEN** it explains the project concept with a realistic example
- **AND THEN** it separates the required project choice from optional team modifiers and skip paths
- **AND THEN** it hands confirmed values to the admin entrypoint when the user proceeds
