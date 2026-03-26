## ADDED Requirements

### Requirement: BrainBuilder workflow documented

The build-phase reference SHALL include a page documenting the `BrainBuilder` workflow: `BuildRequest` inputs (agent_def_dir, tool, skills, config/credential profiles, recipe), the projection process (configs, skills, credentials into runtime home), and `BuildResult` outputs (home_path, manifest_path, launch_helper_path). Content SHALL be derived from `brain_builder.py` docstrings and class signatures.

#### Scenario: Reader understands build inputs and outputs

- **WHEN** a reader opens the brain-builder reference page
- **THEN** they find the `BuildRequest` fields, the projection steps, and the `BuildResult` structure with descriptions of each field

### Requirement: Recipes and tool adapters documented

The build-phase reference SHALL include a page documenting `BrainRecipe` (declarative presets: tool + skills + config_profile + credential_profile + launch_overrides) and `ToolAdapter` (per-tool build contract: launch_executable, env_injection_mode, credential mappings). Content SHALL be derived from the frozen dataclass definitions in `brain_builder.py`.

#### Scenario: Reader can write a brain recipe

- **WHEN** a reader follows the recipes-and-adapters page
- **THEN** they understand the YAML/JSON structure of a `BrainRecipe` and how it references tool adapters, skills, and config profiles

### Requirement: Launch overrides system documented

The build-phase reference SHALL include a page documenting the launch overrides system: `LaunchDefaults`, `LaunchOverrides`, and how recipes can request secret-free overrides. Content SHALL be derived from `agents/launch_overrides/` module docstrings.

#### Scenario: Reader understands override scope

- **WHEN** a reader opens the launch overrides page
- **THEN** they understand which launch parameters can be overridden by recipes vs which are backend-owned (e.g., `-p`, `--json`, `resume`)
