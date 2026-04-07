# docs-build-phase-reference Specification

## Purpose
Define the documentation requirements for Houmao build-phase reference content.

## Requirements

### Requirement: Launch overrides system documented

The build-phase reference SHALL include a page documenting the launch overrides system: `LaunchDefaults`, `LaunchOverrides`, and how recipes and reusable launch profiles can request secret-free overrides. Content SHALL be derived from `agents/launch_overrides/` module docstrings.

The page SHALL describe the effective-launch precedence pipeline as:

1. tool-adapter `LaunchDefaults`
2. recipe `LaunchOverrides`
3. launch-profile defaults
4. direct `LaunchOverrides`
5. live runtime mutations such as late mailbox registration

The page SHALL state that fields omitted by a higher-priority layer survive from the next lower-priority layer, and that direct overrides do not rewrite the stored recipe or launch profile.

The page SHALL render the precedence pipeline as a mermaid diagram, not as ASCII art.

The page SHALL describe `merge_launch_intent` as merging launch overrides from multiple layers (recipe overrides, launch-profile defaults, and direct overrides) into a single resolved intent, with later layers taking precedence.

The page SHALL use the canonical user-facing source noun `recipe` when describing source-layer overrides. The page MAY mention that `project agents presets ...` remains a compatibility alias for the same recipe resources but SHALL NOT describe the source layer as "preset overrides" only. The page SHALL NOT reference `BrainRecipe`, `brain-recipes/`, or `blueprints/`.

The page SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model that ties launch profiles to the build-phase override pipeline.

#### Scenario: Reader understands override scope

- **WHEN** a reader opens the launch overrides page
- **THEN** they understand which launch parameters can be overridden by recipes and launch profiles versus which are backend-owned (e.g., `-p`, `--json`, `resume`)

#### Scenario: Reader sees the launch-profile layer in the precedence pipeline

- **WHEN** a reader scans the precedence section of the launch overrides page
- **THEN** the documented precedence order is tool-adapter defaults, then recipe overrides, then launch-profile defaults, then direct overrides, then live runtime mutations
- **AND THEN** the page states that direct overrides do not rewrite the stored recipe or launch profile

#### Scenario: Precedence pipeline is rendered as a mermaid diagram

- **WHEN** a reader scrolls to the precedence pipeline section of the launch overrides page
- **THEN** the precedence chain is rendered as a mermaid fenced code block
- **AND THEN** the page does not represent the precedence chain as plain-text ASCII art

#### Scenario: No legacy intermediate-source terminology in the launch overrides page

- **WHEN** searching `docs/reference/build-phase/launch-overrides.md` for `BrainRecipe`, `blueprint`, `config_profile`, or `credential_profile`
- **THEN** zero matches are found
