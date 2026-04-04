## MODIFIED Requirements

### Requirement: `houmao-mgr project` exposes repo-local project administration commands
`houmao-mgr` SHALL expose a top-level `project` command family for repo-local Houmao overlay administration.

At minimum, that family SHALL include:

- `init`
- `status`
- `agents`
- `easy`
- `mailbox`

The `project` family SHALL be presented as a local operator workflow for repo-local Houmao state rather than as a pair-authority or server-backed control surface.

#### Scenario: Operator sees the project command family
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, `agents`, `easy`, and `mailbox`
- **AND THEN** the help output presents `project` as a local project-overlay workflow

## ADDED Requirements

### Requirement: `houmao-mgr project init` bootstraps project source roots but does not create optional project workflow state by default
`houmao-mgr project init` SHALL bootstrap the base project overlay and canonical `.houmao/agents/` tree without creating optional mailbox or `easy` metadata state by default.

At minimum, `project init` SHALL NOT create:

- `.houmao/mailbox/`
- `.houmao/easy/`

only because init was run.

#### Scenario: Project init leaves mailbox and easy state opt-in
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command creates the base `.houmao/` overlay and `.houmao/agents/` tree
- **AND THEN** it does not create `/repo/app/.houmao/mailbox/` only because init was run
- **AND THEN** it does not create `/repo/app/.houmao/easy/` only because init was run
