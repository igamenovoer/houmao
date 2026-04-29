## Context

Houmao's Codex starter setup files currently set `model = "gpt-5.4"`, and the Codex launch-policy hook also writes `model = "gpt-5.4"` when runtime config has no model. That was originally a defensive workaround for Codex TUI startup prompts around model upgrades.

Current Codex source no longer requires a fixed model to avoid that path. When `config.model` is absent, Codex resolves the default from its model catalog, currently the first visible catalog model by priority. The model-migration prompt is only shown when the selected current model has an `upgrade` entry. A stale Houmao pin is therefore more likely to reintroduce an upgrade prompt than an omitted model.

## Goals / Non-Goals

**Goals:**
- Let Codex/provider own default model selection when Houmao has no explicit model input.
- Preserve explicit model selection from copied native config, source launch config, launch profiles, and direct launch overrides.
- Avoid startup UI interruptions for Houmao-managed Codex launches without pinning a stale model name.
- Keep reasoning-effort projection available even when model selection is provider-default.

**Non-Goals:**
- Dynamically scrape OpenAI documentation or infer a global "latest" model in Houmao.
- Remove user-authored Codex model pins from arbitrary copied native homes.
- Change non-Codex model selection semantics except where shared tests or helpers need to represent the Codex default-owned case.

## Decisions

1. **Omit model from repo-owned Codex starter setups by default.**

   Repo-owned Codex setup bundles should keep provider routing, reasoning defaults, and non-interactive UI config, but should not set `model`. This makes new Codex homes follow Codex's current catalog default.

   Alternative considered: update the hardcoded model to the current latest. That repeats the original maintenance problem and can become stale as soon as Codex publishes another upgrade.

2. **Do not repair a missing Codex model into a fixed migration target.**

   The Codex launch-policy hook should stop treating `model` absence as migration-needed. If a runtime config has no model, Houmao leaves it absent. Explicit higher-precedence model inputs still project through the existing model-selection path.

   Alternative considered: query `/v1/models` and choose a model at launch time. That endpoint identifies available model IDs but does not encode Codex's recommended TUI default or migration prompt policy, and OpenAI-compatible providers may expose different catalogs.

3. **Handle stale Houmao-owned legacy model pins separately from missing model state.**

   Existing repo-owned starter fixtures or generated runtime configs that carry Houmao's old fixed default can be updated to omit the key. User-authored copied native Codex config that explicitly sets a model should remain respected as baseline native state.

   Alternative considered: automatically delete any old model key during launch. That risks overriding a user's intentional native Codex config.

4. **Suppress startup distractions through TUI config, not model selection.**

   Houmao-managed Codex launches may set non-model Codex config such as `tui.show_tooltips = false` when needed to avoid availability NUX/tooltips. This is independent from migration prompts and does not force model selection.

   Alternative considered: keep using a fixed model to suppress prompts. Current Codex behavior makes that workaround counterproductive for stale models.

5. **Keep reasoning projection model-aware but tolerant of provider-default model names.**

   When only reasoning is configured, Houmao may project `model_reasoning_effort` without projecting `model`. The reasoning mapping should use the maintained Codex fallback ladder when the model name is absent, and provenance should show that no model name was selected by Houmao.

## Risks / Trade-offs

- [Risk] Codex/provider default changes over time and launch behavior may vary across Codex versions. -> Mitigation: this is intentional for unspecified defaults; explicit Houmao launch config remains the supported pinning mechanism for reproducibility.
- [Risk] OpenAI-compatible providers may not support Codex's current default model. -> Mitigation: provider-specific setup bundles can still set `model_provider` and operators can explicitly configure a model where the provider requires it.
- [Risk] Removing the missing-model migration path changes existing tests that assumed `gpt-5.4`. -> Mitigation: update tests to assert absence/provider-default behavior for repo-owned defaults and keep explicit model override coverage.
- [Risk] Codex may introduce future startup prompts unrelated to model migration. -> Mitigation: use targeted non-model TUI config where Codex exposes it, rather than coupling prompt avoidance to model selection.

## Migration Plan

1. Remove fixed `model` keys from repo-owned Codex starter setup assets and aligned fixtures.
2. Change Codex launch-policy migration so missing model is preserved; only explicit legacy-model handling remains if it is still needed and can avoid overriding user intent.
3. Add or update unit tests for no-model Codex setup builds, explicit model overrides, reasoning-only projection, and startup tooltip suppression.
4. Update docs or fixture comments that describe the maintained Codex default model.
