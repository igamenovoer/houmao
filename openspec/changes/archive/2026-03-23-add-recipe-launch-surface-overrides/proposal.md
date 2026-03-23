## Why

Brain recipes currently choose the tool, skills, config profile, and credential profile, but they do not own the actual CLI launch behavior for that brain. The real launch shape still comes from the selected tool adapter plus one hidden programmatic escape hatch, `BuildRequest.launch_args_override`, which means recipe-backed launches cannot declaratively express per-brain CLI behavior and operators end up debugging the wrong layer when backend behavior diverges from adapter defaults.

This has become a structural problem rather than a one-off flag gap. We need recipes to describe tool-specific launch intent in a first-class, reviewable way, while keeping tool adapters as reusable defaults and making backend support or rejection explicit instead of silently persisting settings that some backends do not actually honor.

## What Changes

- Add a first-class recipe-owned `launch_overrides` contract for tool-specific CLI launch settings, not just a flat args list.
- Rename the new concept away from `launch_surface` so it does not collide with the existing `LaunchSurface` backend-selection type in `launch_policy/`.
- Introduce structured merge and precedence rules so tool adapters provide reusable defaults while recipes and direct builds can override selected launch sections predictably.
- Tighten headless launch ownership so backend `.py` code owns only protocol-required headless args and controls, while optional provider launch behavior remains declarative in tool-adapter defaults plus recipe or direct-build launch overrides.
- Persist adapter defaults, requested launch overrides, and provenance into resolved brain manifests without pre-resolving backend applicability at build time.
- Refactor launch-plan composition so backend code applies only supported launch-override settings and rejects unsupported or silently ignored overrides with explicit errors, including `houmao_server_rest` alongside `cao_rest`.
- **BREAKING**: replace the ad hoc `launch_args_override` path with the shared structured launch-overrides contract used by recipe-backed and direct builds.
- **BREAKING**: bump resolved brain manifests to schema version `2` for this contract and require rebuilding generated brain homes instead of carrying a temporary compatibility reader.
- Update recipe docs, tool-adapter docs, runtime docs, and demo launch guidance to describe the new default-plus-override ownership model, the headless protocol/optional-behavior split, and the clean-break manifest migration.

## Capabilities

### New Capabilities
- `recipe-launch-overrides`: Declarative recipe-owned tool-launch override fields, merge semantics against tool-adapter defaults, and validation/provenance rules.

### Modified Capabilities
- `component-agent-construction`: Brain recipes, direct build inputs, and resolved brain manifests gain a first-class structured `launch_overrides` contract instead of relying on adapter-only launch defaults plus hidden ad hoc overrides.
- `brain-launch-runtime`: Launch-plan composition and backend startup resolve recipe/tool-adapter launch overrides explicitly, keep backend code limited to protocol-required headless controls, require schema-version-2 manifests for this contract, persist effective provenance, and fail fast when a backend cannot honor a requested launch override.

## Impact

- Affected code: `src/houmao/agents/brain_builder.py`, recipe/loading code, direct build CLI inputs, tool-adapter launch metadata, launch-plan composition, runtime manifest/session schema models, and backend-specific command builders.
- Affected artifacts: `tests/fixtures/agents/brains/brain-recipes/`, `tests/fixtures/agents/brains/tool-adapters/`, resolved brain manifests, launch helpers, and runtime session metadata.
- Affected docs/tests: `docs/reference/agents_brains.md`, `docs/reference/realm_controller.md`, recipe/tool-adapter schema docs, builder/runtime unit coverage, fixture adapters, and backend contract tests for supported vs unsupported override surfaces.
- Related system boundary: this change should also reconcile the misleading backend-generic `launch.args` story already documented in [context/issues/known/issue-cao-rest-ignores-tool-adapter-launch-args.md](/data1/huangzhe/code/houmao/context/issues/known/issue-cao-rest-ignores-tool-adapter-launch-args.md).
