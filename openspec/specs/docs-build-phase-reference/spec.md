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

### Requirement: Build-phase Kimi references document current system-prompt caveat

Build-phase reference pages that describe Kimi launch policy SHALL name Kimi Code 0.11.0 when discussing current Kimi launch behavior.

The build-phase launch-policy reference SHALL warn that Kimi Code 0.11.0 does not expose a native system-prompt flag. The warning SHALL distinguish this from Kimi skill support: Houmao may project `houmao-auto-system-prompt`, but Kimi users may need to invoke that skill manually before substantive chat begins when automatic skill startup does not run first.

The warning SHALL NOT claim that Kimi Code is unsupported, and SHALL NOT remove accurate Kimi `--skills-dir`, `extra_skill_dirs`, prompt-mode, or TUI unattended launch-policy details.

#### Scenario: Reader sees current Kimi launch-policy version

- **WHEN** a reader opens `docs/reference/build-phase/launch-policy.md`
- **THEN** Kimi launch-policy guidance names Kimi Code 0.11.0 for current behavior
- **AND THEN** older 0.10-family wording is not used for current Kimi launch behavior unless it is explicitly historical

#### Scenario: Reader sees Kimi system-prompt caveat without losing skill guidance

- **WHEN** a reader reviews Kimi launch-policy caveats
- **THEN** the docs state that Kimi Code 0.11.0 lacks a native system-prompt flag
- **AND THEN** the docs state that `houmao-auto-system-prompt` may need manual invocation before substantive Kimi chat begins
- **AND THEN** the docs continue to document supported Kimi skill projection and launch-policy behavior
