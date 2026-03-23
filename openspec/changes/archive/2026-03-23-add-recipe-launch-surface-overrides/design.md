## Context

Houmao's current brain-build contract splits launch ownership awkwardly:

- brain recipes select `tool`, `skills`, `config_profile`, `credential_profile`, and a few extra declarative knobs such as `default_agent_name` and `launch_policy.operator_prompt_mode`,
- tool adapters declare `launch.executable` and `launch.args` as repo-owned defaults,
- direct programmatic builds have one hidden escape hatch, `BuildRequest.launch_args_override`,
- runtime launch-plan composition consumes a flattened `launch_executable` and `launch_args` snapshot from the built manifest as though that surface were backend-agnostic.

That model has two concrete failures now:

1. recipe-backed brains cannot declaratively express per-brain launch behavior, even when the desired behavior is secret-free and reviewable, and
2. the flattened `launch.args` contract is misleading across backends because some runtime paths, especially `cao_rest`, do not actually own or honor all of those arguments end to end.

The recent Claude partial-message exploration exposed the missing ownership boundary clearly. The request is not really “add one more Claude arg.” The deeper problem is that recipes cannot say “for this brain, launch this tool with these additional supported launch semantics,” while tool adapters are overloaded as both reusable defaults and the only declarative launch contract.

This change therefore needs a refactor direction, not a one-off flag patch.

## Goals / Non-Goals

**Goals:**

- Let each brain recipe declare secret-free tool-launch overrides for that recipe.
- Use the same structured launch-override contract for recipe-backed builds and direct build inputs.
- Keep tool adapters as reusable per-tool defaults rather than the only place launch shape can be declared.
- Make backend applicability explicit so unsupported launch surfaces fail closed instead of being silently persisted and ignored.
- Persist enough provenance in the built manifest and runtime launch metadata to explain which launch settings came from adapter defaults, recipe overrides, direct overrides, launch policy, and backend-reserved protocol injection.
- Support concrete tool-specific launch parameters without pretending every provider feature can be modeled as one flat universal `args` list.
- Avoid reusing the overloaded `launch_surface` name because `LaunchSurface` already means backend selection inside `launch_policy/`.

**Non-Goals:**

- Extend the CAO REST boundary in this change to accept arbitrary provider CLI args end to end.
- Solve raw provider-partial streaming for `codex_headless`; upstream `codex exec --json` currently normalizes output into lifecycle/item JSONL rather than exposing raw message deltas.
- Allow secrets or credential material to appear inline in recipes or launch overrides.
- Turn tool adapters into a large declarative translation DSL for every provider-specific launch feature.
- Let recipes override backend-reserved protocol arguments such as `--resume`, `--output-format`, or other runtime-owned continuity flags.

## Decisions

### 1. Introduce an explicit recipe-owned `launch_overrides` layer

Brain recipes gain an optional structured `launch_overrides` mapping, and direct builds gain a matching `BuildRequest.launch_overrides` input. The same model is used in both paths so recipe-backed and explicit builds do not drift.

The initial shape is:

```yaml
launch_overrides:
  args:
    mode: append | replace
    values:
      - <string>
  tool_params:
    <param-name>: <json-compatible value>
```

`args` is the low-level escape hatch for CLI argument changes. `tool_params` is the typed, tool-specific layer for settings that should not be represented as opaque raw args alone.

The recipe already fixes the tool, so `tool_params` does not need an extra per-tool nesting layer inside the recipe.

Why:

- The core missing feature is recipe-owned launch intent.
- A shared structured model avoids keeping recipe builds and direct builds on different contracts.
- `tool_params` gives us a place for supported launch semantics that are more stable and reviewable than magic arg strings.
- `launch_overrides` describes what the structure actually does and avoids colliding with the established `LaunchSurface` backend-selection enum.

Alternatives considered:

- Keep only `launch_args_override` and expose it in recipe YAML.
  Rejected because the problem is broader than flat args and keeps the public contract opaque.
- Add recipe-owned raw `launch_args` only.
  Rejected because it still treats all launch behavior as anonymous strings and does not create a place for typed tool-specific settings.

### 2. Keep `launch.executable` adapter-owned in v1

This change does not let recipes override the tool executable itself. Tool adapters remain the owner of the executable path/name and the projection contract for that tool. Recipe overrides start at the launch-overrides layer above that default.

Why:

- Executable override has larger trust, packaging, and support-boundary implications than args/tool params.
- The current pain is recipe-owned launch behavior, not alternate executable families.
- Keeping executable selection adapter-owned makes the initial refactor smaller and keeps recipes focused on brain profile selection rather than provider installation policy.

Alternatives considered:

- Allow recipes to override `launch.executable`.
  Rejected for v1 because it expands the refactor into tool installation and trust semantics at the same time.

### 3. Keep optional provider launch behavior declarative and keep backend code focused on protocol mechanics

Tool adapters remain declarative data files for defaults and home/projection rules. This change extends that declarative boundary so optional provider launch behavior also lives in tool-adapter-owned launch metadata and recipe/direct-build `launch_overrides` input rather than being hardcoded inside headless backend classes.

A new Python package, tentatively `src/houmao/agents/launch_overrides/`, still owns the shared typed resolver and validator, but it consumes declarative launch metadata instead of hardcoding every optional provider flag in backend `.py` code.

That split is:

- declarative tool-adapter defaults and supported optional launch settings
- declarative recipe/direct-build launch-override requests
- Python merge, validation, provenance, and backend-applicability logic
- backend `.py` code for protocol-required headless controls only

In practice, that means backend code may still own args required by the headless protocol itself, such as:

- Claude or Gemini headless print mode / resume controls
- Codex `exec --json` / `resume`
- runtime-owned native role-injection protocol args

But backend code should not be the place where optional provider behavior such as `include_partial_messages` is invented or silently defaulted.

The shared Python launch-overrides package owns:

- the typed launch-override models,
- merge logic,
- loading and validating declarative per-tool supported `tool_params`,
- backend applicability rules,
- translation of typed tool params into effective CLI args and/or runtime-owned launch-affecting state.

This shared resolver is the authoritative place for questions such as:

- which `tool_params` keys exist for Claude vs Codex,
- which tools intentionally expose no typed params in v1, such as Gemini,
- which backends support a given param,
- whether a param turns into CLI args or runtime-owned state,
- which settings are recipe-overridable vs backend-reserved.

Why:

- Tool adapters are already the repo-owned declarative place for tool defaults. Optional provider launch behavior belongs closer to that layer than to backend classes.
- The launch-policy work already showed that provider/version-sensitive behavior still benefits from typed Python logic for validation and provenance.
- This keeps backend code small and honest: protocol args in code, optional behavior in declarative launch metadata plus shared resolution.

Alternatives considered:

- Put all launch behavior entirely into backend classes.
  Rejected because it keeps optional provider behavior hidden in `.py` instead of reviewable in recipes and adapter-owned metadata.
- Put every detail into tool-adapter YAML with no shared Python resolver.
  Rejected because validation, precedence, backend applicability, and provenance still need one typed shared implementation.
- Hardcode everything in backend classes without a shared registry.
  Rejected because recipe parsing, build-time validation, runtime resolution, and docs/tests would drift quickly.

### 4. Persist build-time defaults and requested overrides separately; use schema version 2 for the new contract

The built manifest will no longer treat a flat `launch_executable` + `launch_args` snapshot as the whole launch contract. Instead, it will persist:

- the adapter-owned launch defaults snapshot needed for reproducibility,
- the requested recipe/direct launch overrides,
- construction-time launch-override provenance metadata,
- `schema_version = 2` for manifests written by the new builder.

Build time still does **not** resolve backend applicability or write backend-resolved effective args. Those remain runtime responsibilities because the selected backend may differ per launch even when the built brain is the same.

This is especially important for cases like:

- a Claude recipe that requests a headless-only param,
- the same recipe later being launched through `cao_rest` or `houmao_server_rest`,
- a Codex headless backend that cannot expose raw provider partial deltas even if a user wants them.

Why:

- Builder-time code does not own the final backend choice.
- Persisting a defaults snapshot avoids adapter drift after build.
- Launch-time resolution is the only place that knows the actual backend contract that will be used.
- A schema bump keeps the manifest contract explicit instead of trying to smuggle new semantics through the v1 layout.

Alternatives considered:

- Fully resolve launch overrides during build.
  Rejected because backend support is not always known at build time.
- Re-read the live tool adapter at launch and ignore the manifest snapshot.
  Rejected because it weakens reproducibility and makes later repo changes silently alter old built brains.

### 5. Define partial-merge behavior explicitly

When adapter defaults, recipe overrides, and direct-build overrides are merged, the merge happens by top-level section, not by one undifferentiated structure.

The merge rules are:

- unmentioned top-level sections survive from lower-priority layers,
- `tool_params` merges per key,
- `args` is an atomic section,
- if a higher-priority layer provides `args`, that section replaces lower-priority `args`,
- `args.mode` always evaluates against adapter defaults after section precedence is decided; modes do not compose across layers.

This means a direct-build override that only sets `args` does not wipe out recipe `tool_params`, but a direct-build `args` section does fully replace the recipe `args` section.

Why:

- This is the narrowest rule that keeps direct-build overrides targeted without introducing recursive merge ambiguity.
- It resolves the open question about partial-field survival explicitly before implementation.

### 6. Backend support must fail closed, and backend code only owns protocol-required args

If a requested launch override cannot be honored by the selected backend, runtime launch-plan construction fails explicitly before the backend starts.

This is the explicit direction for the current `cao_rest` mismatch and the same rule applies to `houmao_server_rest`: this change does not extend those REST backends to pass arbitrary provider launch args through. Instead, runtime resolution must reject launch-override requests that those backends cannot honor.

It is also the rule that keeps headless backends clean:

- backend code appends protocol-required args and continuity controls,
- declarative launch metadata plus `launch_overrides` owns optional provider behavior,
- runtime resolution rejects attempts to treat protocol-owned args as recipe-overridable.

For concrete v1 scope:

- `claude_headless` supports the first typed launch param, `include_partial_messages`,
- `gemini_headless` starts with an empty supported typed-tool-param set,
- `codex_headless` does not claim an equivalent raw provider-partial streaming param while it remains `codex exec --json`.

Why:

- Silent ignore is exactly the bug pattern we are trying to remove.
- An explicit error is better than persisting misleading launch metadata.
- Keeping optional args out of backend classes avoids baking per-provider behavior into the wrong layer.

Alternatives considered:

- Best-effort ignore unsupported settings on unsupported backends.
  Rejected because it preserves the current debugging trap.
- Extend CAO right now to support arbitrary recipe launch overrides.
  Rejected as too large for this refactor and not required to fix the contract boundary.

### 7. Normalize precedence and ordering across build, launch-override resolution, launch policy, and backend protocol args

The effective launch flow becomes:

1. adapter defaults snapshot
2. recipe `launch_overrides`
3. direct `BuildRequest.launch_overrides` for explicit builds
4. shared launch-override validation/translation for the selected tool/backend using declarative tool-launch metadata
5. versioned launch-policy application
6. backend-reserved protocol arg injection

Direct build overrides win over recipe values when both are present. Backend-reserved protocol args remain runtime-owned and are never recipe-overridable.

Why:

- There needs to be one consistent layering model.
- Launch policy and backend protocol args solve different problems and should not be conflated with recipe-owned overrides.

Alternatives considered:

- Apply launch policy before launch-overrides resolution.
  Rejected because launch policy needs to validate against the effective pre-protocol launch overrides, not an incomplete one.
- Let recipe overrides compete with backend-reserved args.
  Rejected because it would break continuity and machine-readable control guarantees.

### 8. Replace `launch_args_override` directly with the structured override contract

The ad hoc `BuildRequest.launch_args_override` path is replaced directly by the structured launch-overrides model. The build CLI should expose one structured input, such as `--launch-overrides <file-or-json>`, instead of accumulating more one-off flags.

Why:

- The current override path exists only in code and is not part of the normal recipe-first operator contract.
- One structured input keeps direct-build parity with recipe-backed builds.
- This repository does not need a soft deprecation window for generated brain-home plumbing.

### 9. Normalize headless arg ownership around “protocol vs optional behavior”

For headless backends, the source of truth becomes:

- tool-adapter defaults and `launch_overrides` for optional provider launch behavior
- backend `.py` code for only the args required by the headless protocol itself

This implies a cleanup direction in the implementation phase:

- optional headless behavior currently baked into backend code should move to declarative launch metadata where possible
- protocol-required args that define the backend contract may stay in backend code
- existing inconsistencies, such as one tool keeping a headless-mode arg in adapter defaults while another injects it in backend code, should be normalized to one rule

Why:

- This is the narrowest rule that keeps the architecture understandable.
- It lets recipes and adapters describe provider behavior without turning backends into hidden policy stores.
- It preserves the runtime’s ability to own continuity, machine-readable mode, and other protocol requirements.

## Risks / Trade-offs

- [The launch contract becomes more layered and harder to explain] → Mitigation: persist explicit provenance, keep adapters as defaults only, and update the recipe/tool-adapter docs with one clear precedence model.
- [The new typed launch-overrides resolver may lag provider feature growth] → Mitigation: keep `args` as a low-level escape hatch for supported backends while adding stable `tool_params` keys incrementally for important features.
- [Manifest/schema churn touches many tests and docs] → Mitigation: treat the change as one repo-wide contract refactor and update fixtures, docs, and runtime JSON/schema snapshots together.
- [Some users may expect executable override once recipe overrides exist] → Mitigation: call executable override out as an explicit non-goal in v1 and revisit only after the smaller launch-overrides refactor lands cleanly.
- [`cao_rest` or `houmao_server_rest` users may view fail-closed behavior as a regression] → Mitigation: document that it is an intentional correction of a previously misleading contract and link the runtime error to the known REST-boundary limitation.

## Migration Plan

1. Add the new launch-overrides models, recipe parsing, direct-build override input, declarative tool-launch metadata, and manifest schema version 2.
2. Update `build_brain_home()` to write the new structured launch-overrides data and construction-time provenance without writing backend-resolved effective args.
3. Update launch-plan composition to consume the new structure, apply the explicit merge rules, perform backend-aware validation, and emit effective launch-overrides provenance.
4. Refactor backends to consume the resolved launch overrides rather than assuming a flat adapter-owned args list is universally meaningful.
5. Reject legacy schema-version-1 brain manifests for this contract and require rebuilding affected homes.
6. Update recipes, tests, fixture adapters, and docs to use the new contract.

Rollback strategy:

- This change affects repo-owned generated artifacts rather than durable external data. Reverting the code and rebuilding the affected brain homes is sufficient rollback.

## Open Questions

None for the proposal-level refactor direction. The main architectural choices for ownership, precedence, backend applicability, and CAO behavior are resolved in this design.
