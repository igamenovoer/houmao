## MODIFIED Requirements

### Requirement: `houmao-mgr project` exposes repo-local project administration commands
`houmao-mgr` SHALL expose a top-level `project` command family for repo-local Houmao overlay administration.

At minimum, that family SHALL include:

- `init`
- `status`
- `agents`
- `easy`
- `migrate`
- `skills`
- `credentials`
- `mailbox`

The `project` family SHALL be presented as a local operator workflow for repo-local Houmao state rather than as a pair-authority or server-backed control surface.

#### Scenario: Operator sees the project command family
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, `agents`, `easy`, `migrate`, `skills`, `credentials`, and `mailbox`
- **AND THEN** the help output presents `project` as a local project-overlay workflow

## ADDED Requirements

### Requirement: Ordinary project-aware commands do not silently migrate legacy project structure
Maintained `houmao-mgr project ...` commands and project-aware catalog-backed flows SHALL NOT silently rewrite known legacy project structure as a side effect of ordinary inspection, bootstrap, authoring, or launch preparation commands.

When one of those flows detects a known legacy project structure that requires conversion into the current supported project model, the command SHALL fail clearly and direct the operator to `houmao-mgr project migrate`.

This requirement applies to ordinary project administration and authoring flows such as `project init`, `project easy ...`, project-backed credential commands, and project-aware compatibility materialization.

#### Scenario: Project command fails with migration guidance instead of upgrading implicitly
- **WHEN** the selected project overlay contains one known legacy project structure that requires explicit migration
- **AND WHEN** an operator runs one ordinary stateful `houmao-mgr project ...` command other than `project migrate`
- **THEN** the command fails clearly
- **AND THEN** the diagnostic directs the operator to `houmao-mgr project migrate`
