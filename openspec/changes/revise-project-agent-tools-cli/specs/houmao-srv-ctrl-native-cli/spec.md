## ADDED Requirements

### Requirement: `houmao-mgr project` exposes `agent-tools` instead of `credential`
When `houmao-mgr` exposes the repo-local `project` command family, that family SHALL include:

- `init`
- `status`
- `agent-tools`

The `project` help surface SHALL NOT advertise `credential` as the supported project-local auth-management subtree.

#### Scenario: Project help shows the renamed tool-oriented subtree
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, and `agent-tools`
- **AND THEN** the help output does not present `credential` as the supported project auth-management command family
