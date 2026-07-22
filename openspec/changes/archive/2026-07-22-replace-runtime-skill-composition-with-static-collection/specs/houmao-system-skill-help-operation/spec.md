## ADDED Requirements

### Requirement: Current system skills expose a read-only help operation
Every current standalone Houmao system skill declared in the v4 manifest SHALL expose a `help` meta operation from its `SKILL.md`. Every parent-scoped child owned by `houmao-shared-routines` SHALL expose equivalent help from its `SKILL-MAIN.md` or from an explicitly declared parent help route that preserves the child's scope.

Help SHALL be read-only and SHALL be handled before normal operation routing, child loading, missing-input collection, command execution, filesystem mutation, mailbox mutation, gateway mutation, or managed-agent lifecycle mutation.

Explicit help intent SHALL include `<skill-name> help`, `help for <skill-name>`, `usage for <skill-name>`, `available functionality for <skill-name>`, and `what can <skill-name> do`. Help SHALL NOT capture a concrete ordinary task merely because the request contains the word `help`.

Retired assets under `legacy/` SHALL NOT be required to expose this help operation.

#### Scenario: Explicit standalone help stays read-only
- **WHEN** a user invokes one of the six standalone skills with explicit help intent
- **THEN** the skill returns usage and routing guidance
- **AND THEN** it does not run commands, mutate state, verify operational targets, or load an executable child

#### Scenario: Shared child help stays scoped
- **WHEN** a user asks shared routines for help on one selected child
- **THEN** the response describes that child's preserved operations and boundaries
- **AND THEN** it does not execute the child's default operation

#### Scenario: Ordinary task still routes normally
- **WHEN** a user asks a current system skill to perform a concrete supported task
- **THEN** the skill follows its normal actor, route, and operation workflow
- **AND THEN** it does not stop at generic help solely because the request contains `help`

#### Scenario: Explicit help request stays read-only
- **WHEN** a user invokes a current system skill with explicit help intent
- **THEN** the agent responds with usage guidance for that skill
- **AND THEN** the agent does not run Houmao commands, mutate files, send mail, change gateway state, change agent lifecycle state, or collect missing operational inputs for the underlying workflow


### Requirement: Future current skills include the help operation
Any new standalone skill or parent-scoped shared child added to the current v4 manifest SHALL include the standard read-only help contract before it becomes current.

Content validation SHALL fail when a standalone `SKILL.md` or child `SKILL-MAIN.md` lacks the declared help route, when help can trigger a mutating default, or when loop help asks for `<loop-dir>`.

#### Scenario: Manifest validation catches missing child help
- **WHEN** a maintainer adds a shared child record whose `SKILL-MAIN.md` lacks the standard help contract
- **THEN** system-skill content validation fails
- **AND THEN** the child cannot be installed as part of a healthy shared-routines source

#### Scenario: Catalog test catches missing help
- **WHEN** a maintainer adds a new current skill to `catalog.toml`
- **AND WHEN** that skill's top-level `SKILL.md` does not expose the standard help operation
- **THEN** the system-skill content tests fail
- **AND THEN** the maintainer must add help guidance before the skill can pass verification

### Requirement: Mega-router help describes sibling dependencies
Admin and agent entrypoint help SHALL list their eligible route subcommands and identify `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite` as sibling delegation targets where applicable.

Shared-routines help SHALL describe direct advanced invocation, default admin posture, explicit managed-self posture, and its sixteen children. It SHALL NOT describe itself as a protected mount.

#### Scenario: Operator asks admin entrypoint for help
- **WHEN** an operator invokes `$houmao-admin-entrypoint help`
- **THEN** the response identifies the admin actor and target rule
- **AND THEN** it lists static sibling routes without loading or executing them
