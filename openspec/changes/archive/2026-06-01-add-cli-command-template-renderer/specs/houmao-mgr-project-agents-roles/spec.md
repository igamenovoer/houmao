## ADDED Requirements

### Requirement: Role authoring surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide template entries for:

- `houmao-mgr project agents roles init`
- `houmao-mgr project agents roles set`

Each role template SHALL map structured field names to CLI options and SHALL document prompt text/file conflicts, clear prompt behavior, required role target fields, and omitted-field semantics.

Rendering a role template SHALL produce argv that is equivalent to invoking the underlying `project agents roles` command directly with the same explicit options.

#### Scenario: Role init has a template entry
- **WHEN** an agent lists command templates
- **THEN** `project.agents.roles.init` appears as a supported template id
- **AND THEN** it maps to `houmao-mgr project agents roles init`

#### Scenario: Role set clears prompt only when explicit
- **WHEN** an agent renders `project.agents.roles.set` with fields `name=reviewer` and `clear_system_prompt=true`
- **THEN** the rendered argv includes the role target and the clear prompt option
- **AND THEN** prompt text and prompt file options remain absent
