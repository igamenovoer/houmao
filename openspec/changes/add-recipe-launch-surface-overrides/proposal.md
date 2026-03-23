## Why

Brain recipes currently choose the tool, skills, config profile, and credential profile, but they do not own the actual CLI launch surface for that brain. The real launch shape still comes from the selected tool adapter plus one hidden programmatic escape hatch, `BuildRequest.launch_args_override`, which means recipe-backed launches cannot declaratively express per-brain CLI behavior and operators end up debugging the wrong layer when backend behavior diverges from adapter defaults.

This has now become a structural problem rather than a one-off flag gap. We need recipes to describe tool-specific launch intent in a first-class, reviewable way, while keeping tool adapters as reusable defaults and making backend support or rejection explicit instead of silently persisting launch settings that some backends do not actually honor.

## What Changes

- Add a first-class recipe-owned launch-surface override contract for tool-specific CLI launch settings, not just a flat args list.
- Introduce structured merge and precedence rules so tool adapters provide reusable defaults while recipes can override selected launch-surface fields for a specific brain profile.
- Tighten headless launch ownership so backend `.py` code owns only protocol-required headless args and controls, while optional provider launch behavior remains declarative in tool-adapter defaults plus recipe or direct-build launch-surface overrides.
- Persist both the requested recipe launch overrides and the resolved effective launch surface into brain manifests and runtime launch metadata with explicit provenance.
- Refactor launch-plan composition so backend code applies only supported launch-surface settings and rejects unsupported or silently ignored overrides with explicit errors.
- **BREAKING**: stop treating tool-adapter `launch.args` as the only declarative source of per-brain launch behavior; recipes become an explicit override layer in the build contract.
- **BREAKING**: deprecate or replace the ad hoc `launch_args_override`-style path with the same structured launch-surface model used by recipe-backed builds so direct builds and recipe builds share one contract.
- Update recipe docs, tool-adapter docs, runtime docs, and demo launch guidance to describe the new default-plus-override ownership model.

## Capabilities

### New Capabilities
- `recipe-launch-surface-overrides`: Declarative recipe-owned tool-launch override fields, merge semantics against tool-adapter defaults, and validation/provenance rules.

### Modified Capabilities
- `component-agent-construction`: Brain recipes, direct build inputs, and resolved brain manifests gain a first-class structured launch-surface contract instead of relying on adapter-only launch defaults plus hidden ad hoc overrides.
- `brain-launch-runtime`: Launch-plan composition and backend startup resolve recipe/tool-adapter launch surfaces explicitly, keep backend code limited to protocol-required headless controls, persist effective provenance, and fail fast when a backend cannot honor a requested launch override.

## Impact

- Affected code: `src/houmao/agents/brain_builder.py`, recipe/loading code, direct build CLI inputs, tool-adapter launch metadata, launch-plan composition, runtime manifest/session schema models, and backend-specific command builders.
- Affected artifacts: `tests/fixtures/agents/brains/brain-recipes/`, `tests/fixtures/agents/brains/tool-adapters/`, resolved brain manifests, launch helpers, and runtime session metadata.
- Affected docs/tests: `docs/reference/agents_brains.md`, `docs/reference/realm_controller.md`, recipe/tool-adapter schema docs, builder/runtime unit coverage, and backend contract tests for supported vs unsupported override surfaces.
- Related system boundary: this change should also reconcile the misleading backend-generic `launch.args` story already documented in [context/issues/known/issue-cao-rest-ignores-tool-adapter-launch-args.md](/data1/huangzhe/code/houmao/context/issues/known/issue-cao-rest-ignores-tool-adapter-launch-args.md).
