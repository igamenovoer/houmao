## Why

The current `agents/` definition model exposes several overlapping concepts called "config", carries multiple duplicated `name` fields with unclear scope, and keeps some schema entries that are not required for current behavior. That makes the fixture model harder to understand, harder to author correctly, and harder to evolve without accumulating more compatibility ballast.

## What Changes

- **BREAKING** Replace the current brain-recipe plus optional-blueprint layering with a single path-derived preset model for reusable agent definitions.
- Introduce an explicit parser boundary: the `agents/` tree becomes the user-facing source format, while downstream build and launch code consume a stable canonical parsed representation instead of source-shaped files directly.
- **BREAKING** Rename the checked-in secret-free tool-runtime input bundle from "config profile" to `setup`, while reserving `home` for the generated runtime home only.
- **BREAKING** Remove build-time `name` fields and recipe-owned `default_agent_name` from agent definition files; preset identity SHALL come from directory structure and file path instead of duplicated inline names.
- Preserve launch-time managed-agent identity as an operator concern: `--agent-name` and `--agent-id` remain optional launch inputs, bare role selectors resolve the `default` setup, and non-default setup variants use explicit preset file paths.
- Preserve the existing separation between secret-free checked-in tool setup and local-only tool authentication so one tool can support multiple setups and multiple auth bundles independently.
- **BREAKING** Bump the resolved brain-manifest contract to schema version 3 and make preset files strict at the top level; non-core extension data moves under `extra`, with migrated gateway defaults kept under `extra.gateway` when needed.
- Update agent fixture docs, native selector resolution, and migration guidance to reflect the simplified definition model and naming rules.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `component-agent-construction`: simplify the reusable agent-definition layout, naming model, and checked-in schema around path-derived presets plus separate setup and auth inputs, while introducing a stable canonical parsed model between user-facing sources and downstream consumers.
- `houmao-mgr-agents-launch`: resolve local launch selectors against the parsed canonical model instead of letting launch/build code depend directly on recipe-, blueprint-, or preset-source details, while keeping launch-time managed-agent identity inputs separate from build-time definition metadata.

## Impact

- Affected code: `src/houmao/agents/brain_builder.py`, `src/houmao/agents/native_launch_resolver.py`, `src/houmao/agents/realm_controller/loaders.py`, related launch/build CLI code, internal parsed-model interfaces, and fixture-oriented tests.
- Affected fixtures and docs: `tests/fixtures/agents/**`, fixture READMEs, migration notes, and operator guidance that currently references recipes, blueprints, config profiles, or recipe-owned default names.
- Breaking areas: agent-definition file layout, checked-in field names, strict preset validation, the internal build/launch contract boundary, manifest schema versioning, selector resolution for reusable local launch presets, and any tests or demos that depend on recipe/blueprint `name` or `default_agent_name`.
