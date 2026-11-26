# Spec Delta

## MODIFIED Requirements

### Requirement: Packaged `houmao-project-mgr` skill explains project-aware side effects and renamed-skill routing boundaries
The `houmao-project-mgr` skill SHALL explain what changes for other Houmao commands when a project overlay exists. At minimum, that project-aware guidance SHALL cover:

- `houmao-mgr project agents launch` (building brain homes internally)
- `houmao-mgr agents global list`
- `houmao-mgr agents single ... state`
- `houmao-mgr mailbox ...`
- `houmao-passive-server serve`
- `houmao-mgr admin cleanup runtime ...`

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That guidance SHALL explain that those command families resolve project-local defaults such as the active agent-definition tree, runtime root, jobs root, mailbox root, or selected overlay when project context is present.

The skill SHALL use the current packaged skill names when routing neighboring concerns. At minimum, it SHALL hand off:

- specialist and project profile authoring plus easy `launch|stop` to `houmao-agent-definition`
- project-local auth bundle CRUD to `houmao-credential-mgr`
- low-level roles and recipes to `houmao-agent-definition`
- generic managed-agent lifecycle after project-scoped routing to `houmao-agent-instance`
- project or global mailbox administration to `houmao-mailbox-mgr`

#### Scenario: Reader asks what other subcommands do differently inside a project
- **WHEN** a reader uses `houmao-project-mgr` to understand project context effects
- **THEN** the skill explains which other command families become project-aware
- **AND THEN** it explains which project-local roots or defaults those families now resolve from the active overlay

#### Scenario: Reader asks which renamed packaged skill owns a neighboring workflow
- **WHEN** a reader asks `houmao-project-mgr` about specialist CRUD, auth-bundle editing, low-level role or recipe editing, mailbox administration, or generic live-agent lifecycle
- **THEN** the skill routes the request to `houmao-agent-definition`, `houmao-credential-mgr`, `houmao-mailbox-mgr`, or `houmao-agent-instance` as appropriate
- **AND THEN** the skill does not keep obsolete `houmao-manage-*` or `houmao-specialist-mgr` identifiers as the current routing targets
