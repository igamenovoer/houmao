## REMOVED Requirements

### Requirement: `houmao-mgr project agents presets` mirrors the project-local preset tree
**Reason**: Presets/recipes are native-agent material and are no longer ordinary project resources.
**Migration**: Use `houmao-mgr internals native-agent recipes ... --native-agent-root <path>`. `presets` may exist only as an internal compatibility alias if retained.

#### Scenario: Recipe tree management moves to native-agent internals
- **WHEN** an operator needs direct recipe management
- **THEN** the supported internal path is `houmao-mgr internals native-agent recipes ...`
- **AND THEN** ordinary project help does not present `project agents presets`

### Requirement: `project agents presets` manages named preset resources
**Reason**: Named preset resources are renamed native-agent recipes and moved to the internal native-agent surface.
**Migration**: Use `internals native-agent recipes add|set|get|list|remove`.

#### Scenario: Recipe mutation uses native-agent command paths
- **WHEN** an operator edits a native recipe
- **THEN** the command path is `houmao-mgr internals native-agent recipes set`
- **AND THEN** the edited resource is described as a native-agent recipe

### Requirement: `project agents recipes` fail clearly on malformed stored preset files
**Reason**: Malformed native recipe diagnostics belong to native-agent internals.
**Migration**: Use `internals native-agent recipes list|get` for direct native recipe validation.

#### Scenario: Malformed recipes are reported by native internals
- **WHEN** native recipe storage contains malformed files
- **THEN** `internals native-agent recipes ...` reports those malformed resources
- **AND THEN** ordinary project specialist/profile commands do not expose the old project-agent preset tree

### Requirement: Recipe authoring surfaces provide command-template entries
**Reason**: Recipe command templates must use the native-agent command path and terminology.
**Migration**: Use native-agent command-template ids for recipe authoring.

#### Scenario: Recipe command templates use native ids
- **WHEN** an agent lists command templates
- **THEN** direct recipe authoring templates use native-agent ids
- **AND THEN** they do not use `project.agents.recipes.*` ids as the maintained public names
