## MODIFIED Requirements

### Requirement: `houmao-mgr project` exposes repo-local project administration commands
`houmao-mgr` SHALL expose a top-level `project` command family for first-class Houmao project administration and ordinary project-based managed-agent workflows.

At minimum, that family SHALL include:

- `init`
- `status`
- `specialist`
- `profile`
- `agents`
- `migrate`
- `skills`
- `credentials`
- `mailbox`

The `project` family SHALL be presented as the ordinary local Houmao workflow. It SHALL NOT present `easy` as a public nesting level, and it SHALL NOT present provider-aligned native-agent material as ordinary project resources.

#### Scenario: Operator sees the first-class project command family
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, `specialist`, `profile`, `agents`, `migrate`, `skills`, `credentials`, and `mailbox`
- **AND THEN** the help output does not list `easy` as a public command group
- **AND THEN** the help output presents `project` as the ordinary local Houmao workflow

## ADDED Requirements

### Requirement: Project commands use specialist/profile/managed-agent language
Ordinary `houmao-mgr project` commands SHALL use project-layer terms:

- `specialist` for reusable project-local persona/tool/credential definitions,
- `profile` for reusable launch defaults for a specialist,
- `managed agent` or `agent instance` for live or stopped Houmao-managed runtime identities.

Project help text, structured output keys intended for ordinary users, config drafts, and packaged project-management skill guidance SHALL NOT call those project-layer resources native agents, raw agent definitions, raw profiles, or launch dossiers.

#### Scenario: Project specialist help avoids native-agent terms
- **WHEN** an operator runs `houmao-mgr project specialist --help`
- **THEN** the help output describes project-local specialists
- **AND THEN** it does not describe the command as native-agent role or recipe management

### Requirement: Project initialization is the explicit project creation entrypoint
`houmao-mgr project init` SHALL remain the explicit command for creating or validating a project overlay.

Ordinary stateful project-backed commands SHALL require an active project overlay and SHALL fail clearly when no active project exists. They SHALL NOT implicitly bootstrap `<cwd>/.houmao` merely because the command requires local Houmao-owned state.

#### Scenario: Specialist create requires an initialized project
- **WHEN** no active Houmao project exists from the invocation directory
- **AND WHEN** an operator runs `houmao-mgr project specialist create --name reviewer --tool codex --credential reviewer-creds`
- **THEN** the command fails clearly
- **AND THEN** the error tells the operator to run `houmao-mgr project init` or select an existing project overlay
- **AND THEN** the command does not create `<cwd>/.houmao` as a side effect

## REMOVED Requirements

### Requirement: Project-aware agent-definition defaults discover the nearest project config
**Reason**: The agent-definition model is being renamed and moved to internal native-agent commands, while ordinary project commands now require an active project instead of bootstrapping project-local native material on demand.
**Migration**: Use `houmao-mgr project init` before ordinary project workflows. Use `houmao-mgr internals native-agent ... --native-agent-root <path>` for direct provider-aligned native-agent material.

#### Scenario: Old project-aware agent-definition defaulting is no longer the ordinary contract
- **WHEN** no active project exists
- **AND WHEN** an operator needs direct native-agent material
- **THEN** the operator uses `houmao-mgr internals native-agent` with an explicit native-agent root
- **AND THEN** ordinary project commands do not silently fall back to `<cwd>/.houmao/agents`

### Requirement: Maintained project-local source creation flows bootstrap the active overlay on demand
**Reason**: First-class project semantics make implicit project creation surprising and unsafe, especially with ancestor discovery.
**Migration**: Run `houmao-mgr project init` before creating project specialists, profiles, credentials, skills, or other project-local state.

#### Scenario: Source creation no longer creates the overlay implicitly
- **WHEN** no active project exists
- **AND WHEN** an operator runs a project-local source creation command
- **THEN** the command fails with project initialization guidance
- **AND THEN** it does not bootstrap a new overlay

### Requirement: Maintained local project-aware commands no longer require prior manual project init
**Reason**: This requirement is inverted by the first-class project model; ordinary maintained local commands now require an active project unless they are explicit initialization or status/discovery flows.
**Migration**: Initialize or select a project before running ordinary stateful Houmao commands.

#### Scenario: Manual project init becomes required for ordinary workflows
- **WHEN** no active project exists
- **AND WHEN** an operator runs an ordinary stateful Houmao command
- **THEN** the command reports that a project is required
- **AND THEN** it does not proceed by creating an implicit project
