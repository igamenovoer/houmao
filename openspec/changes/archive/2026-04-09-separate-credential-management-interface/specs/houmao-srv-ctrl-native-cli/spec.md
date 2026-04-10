## ADDED Requirements

### Requirement: `houmao-mgr` exposes `credentials` as a top-level native command family
`houmao-mgr` SHALL expose `credentials` as a top-level native command family in the supported root command tree.

The root help surface SHALL present `credentials` as the first-class Houmao-owned credential-management family rather than as a nested projection-maintenance detail.

#### Scenario: Native help surface shows the credentials command family
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `credentials` among the supported top-level command families
- **AND THEN** the help output presents `credentials` as the supported credential-management surface

## MODIFIED Requirements

### Requirement: `houmao-mgr project` exposes repo-local project views
When `houmao-mgr` exposes the repo-local `project` command family, that family SHALL include:

- `init`
- `status`
- `agents`
- `easy`
- `credentials`
- `mailbox`

The `project` help surface SHALL present those subtrees as repo-local views over project source management, high-level project authoring, project-scoped credential management, and project-scoped mailbox operations.

#### Scenario: Project help shows the project views
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, `agents`, `easy`, `credentials`, and `mailbox`
- **AND THEN** the help output does not present `agent-tools` as the supported public project command family
