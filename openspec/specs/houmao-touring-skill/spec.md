## Purpose
Define the packaged `houmao-touring` guided-tour system skill and its routing boundaries.
## Requirements
### Requirement: `houmao-touring` is retired in favor of the admin welcome
Houmao SHALL NOT package, install, or advertise `houmao-touring` as a current public or protected system skill.

The admin pack SHALL provide `houmao-admin-welcome` as the maintained first-use, reorientation, and subsystem-exploration surface. Migration guidance SHALL map saved touring invocations to the welcome without creating a compatibility directory.

#### Scenario: Current system-skill inventory is inspected
- **WHEN** a maintainer or operator inspects current public and protected system-skill records
- **THEN** `houmao-touring` is absent
- **AND THEN** `houmao-admin-welcome` is the public guided-tour owner

### Requirement: Maintained touring behavior moves to the welcome contract
The welcome SHALL retain state-aware orientation, compact steps, explanatory questions, subsystem exploration, next-step guidance, and the maintained Single Agent Full Run, Operator-Controlled Agent Team, and Pro Agent Loop paths.

It SHALL also expose Existing Project Reorientation as a curated path and SHALL hand all executable work to `houmao-admin-entrypoint` rather than delegating to former peer skills directly.

#### Scenario: Existing-project user requests the former tour
- **WHEN** a user asks for guided reorientation in an existing Houmao project
- **THEN** `houmao-admin-welcome` inspects supported read-only posture and presents the Existing Project Reorientation path
- **AND THEN** executable follow-up uses the admin entrypoint

### Requirement: Admin welcome is the semantic successor to pre-compaction touring
`houmao-admin-welcome` SHALL preserve the maintained behavior of `houmao-touring` from Git commit `8f377c468bc7f87ff40dbf40c0a68327616112bd` while changing the public name, read-only boundary, and executable handoff target.

The welcome SHALL retain bare-invocation orientation, state inspection before path selection, likely-intent inference, blank-workspace and project-ready menus, fast-path use cases, subsystem exploration, compact presentation, informative questions, concept guidance, and non-linear next steps. It SHALL NOT replace that behavior with a shallow route list.

#### Scenario: Bare welcome runs in a blank workspace
- **WHEN** a user invokes bare `$houmao-admin-welcome` and no project overlay exists
- **THEN** welcome inspects supported read-only posture and introduces Houmao in context
- **AND THEN** it shows exactly Create Houmao Project, Subsystem Exploration, and Inspect as the no-prompt choices
- **AND THEN** it does not return a generic activation acknowledgement

#### Scenario: Existing user asks for reorientation
- **WHEN** welcome finds an existing project, definitions, running agents, or loop artifacts
- **THEN** it preserves current state and recommends a matching continuation path
- **AND THEN** it does not restart from project initialization

### Requirement: Admin welcome preserves maintained guided paths and subsystem depth
The welcome SHALL retain Single Agent Full Run, Operator-Controlled Agent Team, Pro Agent Loop, and Subsystem Exploration, and SHALL expose Existing Project Reorientation as the state-aware continuation path.

Subsystem exploration SHALL retain project state, runtime control, communication, context and evidence, and multi-agent structure coverage. Detailed executable behavior SHALL remain owned by the admin entrypoint, shared routines, and loop siblings.

#### Scenario: User chooses Pro Agent Loop
- **WHEN** a user selects the pro-loop guided path
- **THEN** welcome teaches the relevant intent, topology, readiness, and validation concepts
- **AND THEN** executable follow-up hands off to the admin entrypoint's top-level pro-loop route

### Requirement: Admin welcome remains independently installable and read-only
The welcome directory SHALL contain all of its own command and reference pages and SHALL have no shared-routines or loop dependency for read-only orientation.

When the user confirms executable work, welcome SHALL preserve the selected path, targets, constraints, known posture, confirmed choices, and unresolved required inputs in a handoff to `$houmao-admin-entrypoint`.

#### Scenario: User asks welcome to create a credential
- **WHEN** a concrete credential mutation request reaches welcome
- **THEN** welcome does not mutate credential state
- **AND THEN** it hands the known context to the admin entrypoint's credential route
