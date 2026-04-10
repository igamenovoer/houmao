## MODIFIED Requirements

### Requirement: `houmao-mgr project` exposes repo-local project administration commands
`houmao-mgr` SHALL expose a top-level `project` command family for repo-local Houmao overlay administration.

At minimum, that family SHALL include:

- `init`
- `status`
- `agents`
- `easy`
- `credentials`
- `mailbox`

The `project` family SHALL be presented as a local operator workflow for repo-local Houmao state rather than as a pair-authority or server-backed control surface.

#### Scenario: Operator sees the project command family
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, `agents`, `easy`, `credentials`, and `mailbox`
- **AND THEN** the help output presents `project` as a local project-overlay workflow

## ADDED Requirements

### Requirement: `houmao-mgr project credentials` provides explicit project-scoped credential management
`houmao-mgr project credentials <tool>` SHALL expose:

- `list`
- `get`
- `add`
- `set`
- `rename`
- `remove`

`project credentials` SHALL always resolve the active project overlay and SHALL use the project-backed credential behavior defined for project-local catalog-backed auth profiles.

`project credentials` SHALL NOT require `--agent-def-dir` because its target is the active project overlay by definition.

#### Scenario: Operator sees the project-scoped credential verbs for one tool
- **WHEN** an operator runs `houmao-mgr project credentials claude --help`
- **THEN** the help output presents `list`, `get`, `add`, `set`, `rename`, and `remove`
- **AND THEN** those commands are described as project-scoped credential management for the active overlay

#### Scenario: Project credential add uses the active overlay
- **WHEN** an operator runs `houmao-mgr project credentials codex add --name work --api-key sk-test`
- **THEN** the command resolves the active project overlay
- **AND THEN** it creates a project-local catalog-backed Codex credential in that overlay
