## REMOVED Requirements

### Requirement: BrainBuilder workflow documented

**Reason**: The build-phase reference page for the `BrainBuilder` workflow (`docs/reference/build-phase/brain-builder.md`) is deleted. The getting-started `overview.md` now covers the two-phase lifecycle with current terminology (`BuildRequest`, `AgentPreset`, `setup`/`auth`), and the old page described the obsolete `config_profile`/`credential_profile` projection paths.

**Migration**: Readers seeking build-phase details SHALL use `docs/getting-started/overview.md` for the two-phase lifecycle and `docs/getting-started/agent-definitions.md` for the agent definition directory layout.

#### Scenario: brain-builder.md no longer exists

- **WHEN** listing files under `docs/reference/build-phase/`
- **THEN** `brain-builder.md` does not exist

### Requirement: Recipes and tool adapters documented

**Reason**: The recipes-and-adapters reference page (`docs/reference/build-phase/recipes-and-adapters.md`) is deleted. The `BrainRecipe` and `ToolAdapter` composition model it described was replaced by path-derived `AgentPreset` resolution. The getting-started `agent-definitions.md` documents the new preset model.

**Migration**: Readers seeking preset/adapter documentation SHALL use `docs/getting-started/agent-definitions.md` for the preset layout and `docs/getting-started/quickstart.md` for end-to-end usage.

#### Scenario: recipes-and-adapters.md no longer exists

- **WHEN** listing files under `docs/reference/build-phase/`
- **THEN** `recipes-and-adapters.md` does not exist

## MODIFIED Requirements

### Requirement: Launch overrides system documented

The build-phase reference SHALL include a page documenting the launch overrides system: `LaunchDefaults`, `LaunchOverrides`, and how presets can request secret-free overrides. Content SHALL be derived from `agents/launch_overrides/` module docstrings. The page SHALL use current terminology (`preset` instead of `recipe`, `setup` instead of `config_profile`) and SHALL NOT reference `BrainRecipe`, `brain-recipes/`, or `blueprints/`.

#### Scenario: Reader understands override scope

- **WHEN** a reader opens the launch overrides page
- **THEN** they understand which launch parameters can be overridden by presets vs which are backend-owned (e.g., `-p`, `--json`, `resume`)

#### Scenario: No old terminology in launch overrides page

- **WHEN** searching `docs/reference/build-phase/launch-overrides.md` for `recipe`, `blueprint`, `config_profile`, or `credential_profile`
- **THEN** zero matches are found
