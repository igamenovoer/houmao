# docs-build-phase-reference Specification

## Purpose
Define the documentation requirements for Houmao build-phase reference content.

## Requirements

### Requirement: Launch overrides system documented

The build-phase reference SHALL include a page documenting the launch overrides system: `LaunchDefaults`, `LaunchOverrides`, and how presets can request secret-free overrides. Content SHALL be derived from `agents/launch_overrides/` module docstrings. The page SHALL use current terminology (`preset` instead of `recipe`, `setup` instead of `config_profile`) and SHALL NOT reference `BrainRecipe`, `brain-recipes/`, or `blueprints/`.

#### Scenario: Reader understands override scope

- **WHEN** a reader opens the launch overrides page
- **THEN** they understand which launch parameters can be overridden by presets vs which are backend-owned (e.g., `-p`, `--json`, `resume`)

#### Scenario: No old terminology in launch overrides page

- **WHEN** searching `docs/reference/build-phase/launch-overrides.md` for `recipe`, `blueprint`, `config_profile`, or `credential_profile`
- **THEN** zero matches are found
