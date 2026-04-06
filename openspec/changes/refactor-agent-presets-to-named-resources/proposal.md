## Why

The current low-level project agent model exposes presets as `roles/<role>/presets/<tool>/<setup>.yaml`, which makes the CLI read as if presets are owned by roles rather than as first-class launch bindings. That shape leaks path-derived identity into parsing, launch resolution, docs, and fixtures, making `project agents roles` misleading and making future low-level definition management harder to explain.

## What Changes

- Introduce a first-class `houmao-mgr project agents presets ...` command family for named preset resources.
- **BREAKING** Replace role-scoped preset identity with named preset identity stored under `.houmao/agents/presets/<preset>.yaml`.
- **BREAKING** Move preset semantic fields `role`, `tool`, and `setup` into preset file content instead of deriving them from directory nesting.
- **BREAKING** Remove `houmao-mgr project agents roles scaffold`.
- **BREAKING** Narrow `houmao-mgr project agents roles ...` to prompt-only role management and remove nested `roles presets ...`.
- Update launch/build resolution so bare role selectors continue to work by resolving the named preset whose `role` matches the selector, whose `tool` matches the requested provider lane, and whose `setup` is `default`.
- Update project catalog projection, parser expectations, tracked fixtures, and documentation to use the new named preset resource model consistently.

## Capabilities

### New Capabilities
- `houmao-mgr-project-agents-presets`: define the first-class project-local named preset CLI for listing, getting, adding, setting, and removing named presets.

### Modified Capabilities
- `houmao-mgr-project-agents-roles`: redefine `project agents roles` as prompt-only role management and remove `scaffold` plus nested preset verbs.
- `houmao-mgr-agents-launch`: change native preset resolution to support named presets while preserving bare-role launch semantics.
- `component-agent-construction`: redefine the canonical agent-definition preset model around named preset files with inline `role`, `tool`, and `setup` fields.
- `houmao-mgr-project-cli`: update project-aware create/update/read command coverage for the new `project agents presets ...` family.
- `docs-getting-started`: update the documented `.houmao/agents/` layout and low-level authoring examples to use top-level named presets.
- `docs-cli-reference`: update CLI reference coverage for `project agents presets ...`, prompt-only roles, and the removal of `roles scaffold`.
- `minimal-agent-launch-demo`: update the maintained minimal demo to use named preset files and selectors.
- `runtime-agent-dummy-project-fixtures`: update tracked fixture layouts and references that currently assume role-scoped preset paths.

## Impact

- Affected code: `src/houmao/agents/definition_parser.py`, `src/houmao/agents/brain_builder.py`, `src/houmao/project/catalog.py`, `src/houmao/srv_ctrl/commands/project.py`, launch/build selector logic, and fixture/demo loaders.
- Affected APIs: `houmao-mgr project agents roles ...`, new `houmao-mgr project agents presets ...`, and any flow that resolves preset selectors or default role launches.
- Affected content: docs under `docs/getting-started/` and `docs/reference/cli/`, tracked fixtures under `tests/fixtures/agents/`, and demo inputs that currently encode presets under `roles/<role>/presets/`.
