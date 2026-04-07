## Context

Houmao's current model-selection behavior is split across tool-specific ownership seams:

- Claude model selection is effectively auth-owned through allowlisted env such as `ANTHROPIC_MODEL`.
- Codex model selection is typically setup-owned through copied `config.toml`.
- Gemini has maintained auth and setup projection, but no first-class Houmao model-selection surface.

Reasoning controls are even less uniform:

- Claude exposes effort as its own concept and also distinguishes thinking-budget controls.
- Codex exposes `model_reasoning_effort` as a first-class config field.
- Gemini uses generation settings under `thinkingConfig`, and the exact native control differs by model family.

That asymmetry leaks tool details into user workflows. A recipe or specialist cannot declare one obvious default model in a tool-agnostic way, launch profiles cannot currently carry model choice as reusable birth-time configuration, and top-level launch cannot override the model without falling back to tool-specific hacks. The build path already has a clean projection seam, though: Houmao copies setup into a fresh runtime home, projects auth, and then synthesizes launch/runtime state. This change uses that seam instead of pushing more responsibility into auth bundles or setup bundles.

The repository is also already organized around a shared birth-time configuration model:

- recipes/presets describe reusable source defaults,
- launch profiles describe reusable birth-time defaults,
- direct CLI flags provide one-off overrides,
- runtime policies patch tool-owned state inside the constructed home.

Model configuration fits that structure better than the current tool-specific storage rules.

## Goals / Non-Goals

**Goals:**
- Give users one unified way to specify a model by name across recipes, specialists, launch profiles, and direct launch.
- Give users one unified coarse reasoning control using a normalized Houmao scale from `1` through `10`.
- Let recipes and specialists persist a reusable default model as secret-free launch configuration.
- Let launch profiles persist reusable model and reasoning overrides separate from the source recipe.
- Let direct launch override the model configuration for one run without rewriting reusable stored state.
- Resolve model configuration through one explicit precedence chain and preserve that result in build/runtime provenance.
- Project the resolved model name into each tool's supported runtime-home surfaces so users do not need to hand-edit env, `config.toml`, or `settings.json`.
- Route normalized reasoning levels through one Houmao-owned mapping policy layer rather than exposing each tool's native reasoning surface directly.
- Keep detailed vendor-native tuning out of the core CLI and reserve it for agent skills and advanced workflows.

**Non-Goals:**
- Validate model names against upstream provider catalogs.
- Expose every provider-specific secondary model knob such as Claude small/fast, Gemini full generation-config tuning, or subagent model families in this change.
- Replace all existing auth/setup storage immediately; legacy tool-specific model inputs may remain as fallback sources.
- Redesign the entire project catalog or launch-override framework beyond what is required to support unified model selection.
- Cover runtime in-session `/model` mutations beyond preserving the rule that they remain runtime-owned and non-persistent.

## Decisions

### Decision: Model configuration becomes launch-owned configuration under `launch`

The canonical user-facing ownership model will be:

- auth owns secrets and endpoint credentials,
- setup owns secret-free baseline tool config,
- launch owns reusable model configuration.

Recipes and specialists will therefore persist model configuration under launch configuration rather than as a top-level field or as part of auth/setup semantics. The canonical structured form becomes:

```yaml
launch:
  model:
    name: gpt-5.4
    reasoning:
      level: 7
```

CLI surfaces expose simple launch-owned flags such as `--model <name>` and `--reasoning-level <1..10>`. Source parsing may accept a shorthand scalar form for `launch.model` when only the name is needed, but the internal model stays structured so Houmao can extend it later without redefining the field shape.

Alternatives considered:

- Top-level `model` field: rejected because model selection is a birth-time launch concern and belongs with other launch settings such as prompt mode.
- Tool-specific per-surface flags only: rejected because it keeps the asymmetric mental model the user is trying to remove.
- Store model in `launch_overrides`: rejected because `launch_overrides` is backend-arg translation, while model projection needs runtime-home mutation and env/config synthesis.

### Decision: Reasoning becomes a Houmao-defined normalized 1..10 scale

Houmao will define one coarse reasoning scale from `1` through `10`.

- `1` always means the lowest reasoning Houmao will request for the resolved tool/model.
- `10` always means the highest reasoning Houmao will request for the resolved tool/model.
- Intermediate values are Houmao-defined coarse buckets rather than promises about any vendor-native term.

This scale is intentionally opaque at the native level. The exact mapping may depend on:

- tool family,
- tool version,
- model name,
- model family,
- other runtime context required by the native tool.

Houmao therefore owns the mapping policy in Python code. The mapping policy takes normalized launch-owned input and returns native projection edits plus provenance. User docs and concise CLI help explain the mapping at a high level, but detailed vendor-native tuning remains out of scope for the core CLI and is delegated to agent skills.

Alternatives considered:

- Expose vendor-native reasoning knobs directly in core CLI: rejected because the native concepts are not uniform across Claude, Codex, and Gemini.
- Pretend all tools share the same native `low|medium|high` contract: rejected because that would be materially false for Gemini and only partially true for Claude.

### Decision: One explicit precedence chain governs the effective model configuration

The effective model configuration will resolve in this order:

1. tool-native default or copied legacy setup/auth fallback,
2. source recipe or specialist launch default,
3. launch-profile default,
4. direct launch-time override,
5. runtime-only in-session mutation.

Higher-priority layers override lower ones only for the subfields they actually specify. That means `launch.model.name` and `launch.model.reasoning.level` resolve independently: a profile may override the model name while inheriting a lower-precedence reasoning level, or vice versa.

Runtime-only changes such as a live `/model` selection remain non-persistent and do not rewrite recipe, specialist, or launch-profile state.

This matches the existing launch-profile precedence model and extends it with one more launch-owned field instead of inventing a separate precedence story for models.

Alternatives considered:

- Let auth beat recipe defaults for Claude only: rejected because it preserves tool-specific ownership.
- Let direct launch write back into launch profiles or specialists: rejected because launch overrides are intentionally one-off.

### Decision: Projection happens during brain-home construction through a Houmao-owned mapping policy layer, not as backend-specific argv

The resolved model configuration will be projected after setup copy and auth projection, and before launch helper synthesis and downstream runtime policy application. That makes the runtime home the single source of truth for startup state across interactive and headless flows.

Model-name projection surfaces are direct and stable:

- Claude: export the resolved model as `ANTHROPIC_MODEL` in the built launch environment.
- Codex: patch the constructed runtime `${CODEX_HOME}/config.toml` to set `model = "<name>"`.
- Gemini: patch the constructed runtime user-settings file `${GEMINI_CLI_HOME}/.gemini/settings.json` to set `model.name = "<name>"`.

Reasoning-level projection is not a fixed one-line table because the native controls differ. Houmao will therefore use a dedicated Python policy module that accepts at minimum:

- requested normalized level,
- resolved tool,
- resolved model name,
- tool version when available,
- existing runtime-home config context when required.

That mapping policy returns native edits and provenance. Representative projection families include:

- Claude: runtime settings or env such as `effortLevel` and, when the mapping requires it, thinking-related runtime controls.
- Codex: runtime `${CODEX_HOME}/config.toml` keys such as `model_reasoning_effort`.
- Gemini: runtime `${GEMINI_CLI_HOME}/.gemini/settings.json` generation settings under `modelConfigs` and `thinkingConfig`.

Houmao will prefer runtime-home projection over backend-specific startup argv so the same resolved state applies consistently to:

- interactive and headless startup,
- relaunch and resume flows that depend on the runtime home,
- manifest inspection and provenance.

This matches the verified upstream storage layout for both tools:

- Codex resolves persistent user config from `config.toml` under `CODEX_HOME` and already treats CLI `--model` as higher precedence than profile or file defaults.
- Gemini resolves global user settings from `${GEMINI_CLI_HOME}/.gemini/settings.json` and persists preferred-model changes at nested key `model.name`, with CLI `--model` taking precedence over settings.
- Claude exposes startup `--effort`, persisted `effortLevel`, and separate thinking-budget controls, which reinforces the need for Houmao-owned normalized mapping rather than a direct 1:1 native field.

Alternatives considered:

- Pass `--model` directly on startup commands: rejected as the primary mechanism because it would split model ownership between launch-plan argv and runtime-home config and would complicate interactive/headless parity.
- Continue relying on copied setup/auth content only: rejected because it cannot support generic launch-profile and direct-launch overrides cleanly.

### Decision: Existing tool-specific model and reasoning storage becomes compatibility fallback, not the primary authoring surface

Existing authored setups and auth bundles may already contain model state:

- Claude auth env may already include `ANTHROPIC_MODEL`.
- Claude settings may already include `effortLevel`.
- Codex setup bundles may already include `config.toml` `model`.
- Codex setup bundles may already include `config.toml` `model_reasoning_effort`.
- Future Gemini setups may include `.gemini/settings.json` model defaults.
- Future Gemini setups may include `.gemini/settings.json` `modelConfigs` overrides.

This change will not require bulk migration of those stored assets. Instead:

- if no unified `launch.model` subfield is supplied by higher-precedence layers, the copied setup/auth state remains effective,
- if a unified model name or reasoning level is supplied, Houmao overwrites or augments the runtime-home surface with the resolved value,
- new unified authoring surfaces stop treating auth/setup model or reasoning state as the normative way to choose launch-owned behavior.

This keeps adoption incremental while making the new semantic layer authoritative when present.

### Decision: Launch-profile storage gets a targeted schema extension instead of a general payload refactor

Recipes and specialists already have generic `launch_payload` storage, so adding model selection there is straightforward. Launch profiles currently store several launch defaults as dedicated columns plus JSON blobs for env/mailbox/posture.

For this change, launch-profile persistence will add an explicit model field rather than replacing the whole table with a new generic launch payload. That keeps migration narrow and lets the rest of the feature land without a broader catalog redesign.

Alternatives considered:

- Replace launch-profile defaults with one generic JSON payload: rejected as a larger architectural refactor than this feature needs.
- Hide model inside `env_payload`: rejected because model selection is not generic env and must not be authored through unrestricted env records.

### Decision: Unified `--model` and `--reasoning-level` become the supported CLI concepts across authoring and launch

The supported CLI concepts become `--model` and `--reasoning-level` on the relevant low-level and easy surfaces:

- recipe add/set,
- explicit launch-profile add/set,
- easy specialist create,
- easy profile create/set,
- `agents launch`,
- `project easy instance launch`.

Stored sources that support editing the field should also support `--clear-reasoning-level` to remove a persisted launch-owned override.

Tool-specific authoring flags that currently imply model choice, such as easy `--claude-model`, should become compatibility aliases or be deprecated in favor of `--model`. Persistent `--env-set` remains blocked from setting reserved model env names because model selection must stay in the semantic launch layer.

### Decision: Advanced native tuning is delegated to skills, not the core CLI

The core CLI will expose only:

- model name,
- normalized reasoning level.

Detailed vendor-native tuning such as explicit Claude thinking-token budgets, Gemini generation-parameter recipes, or provider-specific secondary model-routing knobs will not be added to the main launch/config CLI in this change. Those advanced workflows remain available through skills, higher-level agent workflows, or future narrowly scoped capabilities when justified.

This keeps the shared launch surface understandable and prevents the generic CLI from turning into a thin wrapper over three incompatible vendor config systems.

### Decision: The built manifest records resolved model-configuration provenance

The brain manifest and runtime launch metadata will record:

- the requested unified model-configuration sources where relevant,
- the resolved effective model,
- the requested normalized reasoning level when present,
- the resolved native reasoning mapping summary,
- whether a launch profile contributed the model,
- tool-specific projection target metadata only as secret-free provenance.

This keeps inspection, debugging, and replay coherent and avoids re-deriving effective model choice from copied config files alone.

## Risks / Trade-offs

- [Tool-native reasoning semantics do not match across tools] → Mitigation: define reasoning as a Houmao-owned normalized 1..10 scale and keep the native mapping in one policy module with explicit provenance.
- [Legacy setup/auth model state may disagree with the new launch-owned field] → Mitigation: make the precedence chain explicit and preserve both requested and resolved model provenance in the manifest.
- [The mapping policy is intentionally less transparent than vendor-native settings] → Mitigation: document representative mappings, surface concise CLI help, and preserve the exact resolved native mapping in manifests and diagnostics.
- [Runtime-home mutation may interact with unattended launch-policy hooks] → Mitigation: apply model projection before policy hooks and treat model selection as distinct from policy-owned approval/sandbox/trust state.
- [Adding one more dedicated launch-profile column increases catalog surface area] → Mitigation: keep the change intentionally narrow and defer broader launch-profile payload normalization to a separate refactor.
- [Users may continue reaching for `--claude-model`, direct env edits, or vendor-native reasoning settings] → Mitigation: add unified `--model` and `--reasoning-level`, keep reserved env validation, document legacy tool-specific inputs as compatibility behavior, and reserve advanced native tuning for skills.

## Migration Plan

1. Extend recipe parsing and project-easy specialist metadata so launch-owned model configuration can be stored and projected without changing existing recipes.
2. Add launch-profile persistence and reporting for the shared model-configuration field with a targeted catalog migration.
3. Add unified `--model`, `--reasoning-level`, and stored-field clearing flows to low-level recipe/launch-profile paths and to easy specialist/profile/instance and direct `agents launch`.
4. Add the Houmao-owned Python mapping policy module for normalized reasoning-level projection.
5. Extend brain-build and runtime manifest construction to resolve, project, and record effective model configuration together with native mapping provenance.
6. Keep existing tool-specific model and reasoning state as fallback input for existing repos; no bulk rewrite of auth bundles or setup bundles is required.
7. Optionally keep `--claude-model` as a compatibility alias for one deprecation window before removing it in a follow-up change.

Rollback is low-risk because the change adds a new semantic layer on top of existing copied setup/auth behavior. If the unified layer must be disabled, existing authored setup/auth model state remains available as fallback.

## Open Questions

- Should `--claude-model` remain as a compatibility alias for one release window, or should the easy surface switch directly to `--model`?
- Should CLI help display only the normalized 1..10 scale, or also print representative native examples per tool family?
- Should low-level auth mutation commands continue to accept tool-specific model flags during the compatibility window, or should they stop advertising model ownership immediately once launch-owned model configuration exists?
