## ADDED Requirements

### Requirement: Recipe authoring surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide template entries for:

- `houmao-mgr project agents recipes add`
- `houmao-mgr project agents recipes set`

The compatibility `project agents presets` surface MAY point at the same template metadata when the same command behavior is exposed through the compatibility alias.

Each recipe template SHALL map structured field names to CLI options and SHALL document role/tool/setup requirements, auth fields, skill mutations, model and reasoning fields, prompt-mode fields, clear flags, and omitted-field semantics.

Rendering a recipe template SHALL produce argv that is equivalent to invoking the underlying `project agents recipes` command directly with the same explicit options.

#### Scenario: Recipe add has a template entry
- **WHEN** an agent lists command templates
- **THEN** `project.agents.recipes.add` appears as a supported template id
- **AND THEN** it maps to `houmao-mgr project agents recipes add`

#### Scenario: Recipe set has clear-field metadata
- **WHEN** an agent shows `project.agents.recipes.set`
- **THEN** the template describes supported update and clear fields for auth, skills, model, reasoning, and prompt mode
- **AND THEN** it distinguishes omitted fields from explicit clears

#### Scenario: Recipe add omits prompt mode from argv when unspecified
- **WHEN** an agent renders `project.agents.recipes.add` with fields `name=reviewer-codex`, `role=reviewer`, and `tool=codex`
- **THEN** the rendered argv includes only the required recipe, role, and tool fields
- **AND THEN** it does not include `--prompt-mode`
