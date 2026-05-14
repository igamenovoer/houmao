## Why

Houmao currently pins Codex starter setups and migration state to a fixed model name, which becomes stale as Codex changes its catalog. Current Codex source shows that omitting `model` lets Codex choose its own catalog default without opening the old model-migration prompt path, so Houmao should stop manufacturing a fixed default model.

## What Changes

- Remove Houmao's fixed Codex default-model pin from repo-owned starter Codex setup bundles.
- Stop treating a missing Codex `model` as a state that must be migrated to a hard-coded target.
- Preserve explicit model selection from copied native state, source recipe/specialist launch config, launch profile, or direct launch override.
- Keep Codex reasoning projection supported without requiring Houmao to resolve or persist a model name.
- Suppress non-essential Codex startup model availability prompts/tooltips for Houmao-managed launches where needed to keep automated/managed startup non-interactive.

## Capabilities

### New Capabilities

### Modified Capabilities
- `agent-model-selection`: Codex launches without an explicit launch-owned or native model SHALL preserve provider/Codex default selection instead of projecting a fixed Houmao model name.
- `codex-openai-compatible-brain-profile`: Repo-owned Codex setup bundles SHALL remain secret-free and provider-configured while avoiding fixed model-name defaults.

## Impact

- Affected code: Codex starter setup TOML assets, Codex provider launch-policy hooks, model-selection projection and manifest expectations, and Codex model/reasoning tests.
- Affected tests/fixtures: unit fixtures that currently assert `gpt-5.4` as the default Codex setup model, migration tests for missing/legacy Codex config, and any live smoke assumptions that rely on a fixed Codex model.
- External behavior: default Codex launches use Codex/provider catalog defaults unless an operator or reusable launch configuration explicitly selects a model.
