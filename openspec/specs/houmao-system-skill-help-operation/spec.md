# houmao-system-skill-help-operation Specification

## Purpose
Let users inspect available system-skill operations and eligible routes through read-only help before operational checks. Cover both public invocation examples and help supplied by protected routers.
## Requirements
### Requirement: Public system skills handle help before operational routing
Each current public Houmao system skill SHALL expose read-only help from its top-level `SKILL.md` and SHALL answer explicit help intent before identity verification, target collection, protected routing, command execution, or mutation.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

`houmao-admin-welcome` SHALL own the full first-use tour and route comparison. `houmao-admin-entrypoint` SHALL handle help, empty invocation, and welcome-oriented requests locally. It can recommend the explicit manual welcome invocation. `houmao-agent-entrypoint` SHALL provide concise help for its eligible managed-agent routes.

#### Scenario: Admin entrypoint receives explicit help
- **WHEN** a user invokes `houmao-admin-entrypoint help`
- **THEN** the entrypoint explains available admin routes and the target rule locally
- **AND THEN** it leaves skill loading, target lookup, and protected operations for substantive requests

#### Scenario: Agent entrypoint receives explicit help
- **WHEN** a user invokes `houmao-agent-entrypoint help`
- **THEN** it lists the managed-agent routes and identity prerequisite concisely
- **AND THEN** it does not perform a substantive self-identity or state operation solely to answer help

### Requirement: Help distinguishes public invocations from protected routes
Public help SHALL list copyable prompts that begin with `$houmao-admin-welcome`, `$houmao-admin-entrypoint`, or `$houmao-agent-entrypoint`.

It MAY show entrypoint-qualified protected designators to explain routing, but SHALL identify them as internal route traces and SHALL NOT present protected logical ids as independently invokable top-level skills.

#### Scenario: Help describes agent inspection
- **WHEN** public help explains the protected inspect capability
- **THEN** it provides a public entrypoint invocation the user can copy
- **AND THEN** any protected designator is labeled as a nested route rather than an install or public trigger

### Requirement: Protected routers expose read-only route summaries
Each parent-scoped `SKILL-MAIN.md` SHALL provide enough read-only help for its parent to summarize purpose, commands, eligible actors, boundaries, and direct child routes. The parent SHALL preserve the selected route's audience and handle help before it selects a default operation.

#### Scenario: Protected loop help lacks required loop directory
- **WHEN** a valid entrypoint route requests help for a top-level loop skill without a loop directory
- **THEN** the skill returns its command summary
- **AND THEN** it leaves initialization and target collection for substantive requests

### Requirement: Current system skills expose a read-only help operation
Every current standalone Houmao system skill declared in the manifest SHALL expose a `help` meta operation from its `SKILL.md`. Every parent-scoped child owned by `houmao-shared-routines` SHALL expose equivalent help from its `SKILL-MAIN.md` or from an explicitly declared parent help route that preserves the child's scope.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

### Requirement: Mega-router help describes sibling dependencies
Admin and agent entrypoint help SHALL list eligible route subcommands and identify the shared routines and two loop skills as sibling delegation targets. Shared-routines help SHALL describe direct invocation, default admin posture, explicit managed-self posture, and all declared shared child routes.

#### Scenario: Operator asks admin entrypoint for help
- **WHEN** an operator invokes `$houmao-admin-entrypoint help`
- **THEN** the response identifies the admin actor and target rule
- **AND THEN** it lists static sibling routes without loading or executing them

### Requirement: Editorial review verifies the declared help surface
Maintainers SHALL review public help and parent route summaries against the declared command and actor inventory. Review SHALL cover eligible actors, the “When to Route Here” guidance, and copyable invocation forms. Unit tests of skill assets SHALL check declared paths and entrypoint layout only.

#### Scenario: New protected subskill lacks a parent summary
- **WHEN** a maintainer adds a protected subskill without a matching parent route summary
- **THEN** editorial review identifies the missing summary for correction
- **AND THEN** automated asset tests verify the declared child and its entrypoint exist at the expected path

### Requirement: New catalog members include read-only help
Any new standalone skill or parent-scoped shared child added to the current manifest SHALL provide standard read-only help. Editorial review SHALL verify that help describes the declared operations and stops before defaults, target collection, or mutations.

#### Scenario: Maintainer reviews a new shared child's help
- **WHEN** a maintainer adds a shared child record whose `SKILL-MAIN.md` lacks the standard help contract
- **THEN** editorial review identifies the missing help for correction

#### Scenario: New catalog member is verified
- **WHEN** a maintainer adds a newly declared current skill
- **THEN** the structural check verifies the corresponding role-canonical entrypoint exists
- **AND THEN** editorial review verifies read-only help, including that loop help requires no `<loop-dir>`
