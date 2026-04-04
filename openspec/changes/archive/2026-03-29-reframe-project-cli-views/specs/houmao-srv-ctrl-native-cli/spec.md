## REMOVED Requirements

### Requirement: `houmao-mgr project` exposes `agent-tools` instead of `credential`
**Reason**: The supported `project` tree now exposes three repo-local views: `agents`, `easy`, and `mailbox`. Keeping a dedicated `agent-tools` naming rule would preserve the old synthetic namespace and under-specify the new project surface.
**Migration**: Use `houmao-mgr project agents ...` for low-level project source management, `houmao-mgr project easy ...` for specialist and instance UX, and `houmao-mgr project mailbox ...` for project-scoped mailbox-root operations.

## ADDED Requirements

### Requirement: `houmao-mgr project` exposes repo-local project views
When `houmao-mgr` exposes the repo-local `project` command family, that family SHALL include:

- `init`
- `status`
- `agents`
- `easy`
- `mailbox`

The `project` help surface SHALL present those subtrees as repo-local views over project source management, high-level project authoring, and project-scoped mailbox operations.

#### Scenario: Project help shows the project views
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, `agents`, `easy`, and `mailbox`
- **AND THEN** the help output does not present `agent-tools` or `credential` as the supported public project command family
