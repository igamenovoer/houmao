## 1. Recipe Coverage, Resolution, And State

- [x] 1.1 Extend the shared `BrainRecipe` model and loader plus the tracked demo recipe fixtures to carry `default_agent_name`, update the existing Codex recipes with tool-specific defaults, and add the missing Claude recipe under the fixed recipe tree
- [x] 1.2 Refactor interactive demo startup to resolve every launch through a brain recipe, including selector normalization, shared recipe loading for `tool` and `default_agent_name`, delegation to `build-brain --recipe`, optional `.yaml` normalization, fixed-root recipe resolution, basename ambiguity handling, subdirectory disambiguation, recipe-owned `skills`/`config_profile`/`credential_profile`, and `--agent-name` override handling
- [x] 1.3 Persist resolved `tool`, normalized `variant_id`, and canonical `brain_recipe` metadata in the interactive demo state and verification/report models for both implicit and explicit recipe-backed launches, and treat incompatible stale local state as replaceable during startup reset
- [x] 1.4 Update startup and wrapper entrypoints to launch the selected recipe through the shared interactive demo engine while preserving the single current-run workspace flow and keeping wrapper-provided names as thin overrides rather than engine defaults
- [x] 1.5 Remove now-unneeded compatibility branches and demo-owned build defaults for superseded interactive-demo call shapes, then update any in-repo call sites to the supported recipe-first contract

## 2. Tool-Aware Inspect And Verification

- [x] 2.1 Generalize inspect JSON and human-readable rendering to report tool-aware metadata, a generic live `tool_state` field, and a stable top-level JSON field contract instead of Claude-only naming
- [x] 2.2 Route `inspect --with-output-text` through the runtime-owned tool-aware parser selection path so Claude and Codex use the correct shadow parser
- [x] 2.3 Update verify/report generation, expected-report fixtures, and verifier helpers to record and validate the selected tool and stable variant identifier

## 3. Documentation And Tests

- [x] 3.1 Expand unit tests for recipe resolution, normalized `variant_id`, stale-state replacement, persisted state, generic inspect output, and tool-aware clean output-tail behavior
- [x] 3.2 Expand integration and wrapper tests for the default Claude path, the explicit Claude recipe path, the supported Codex startup variants, tool-specific recipe default names, and ambiguous-basename failure cases
- [x] 3.3 Update the interactive demo README and related docs references to document the default Claude walkthrough as a recipe-backed launch, explain that `--agent-name` overrides the recipe-defined default name, document the supported explicit Claude and Codex recipe selectors from the same demo pack, and include an ambiguity-error example for subdirectory disambiguation
- [x] 3.4 Search the repo for broken interactive-demo invocations after the contract change and fix all affected tests, wrappers, scripts, and docs rather than adding backward-compatibility support
