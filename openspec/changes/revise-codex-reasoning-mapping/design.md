## Context

Houmao's unified model-selection layer currently resolves a non-negative `reasoning.level` into tool-native settings through `src/houmao/agents/model_mapping_policy.py`. The Codex branch currently uses one broad ladder derived from Codex's generic `ReasoningEffort` enum:

```text
0=none, 1=minimal, 2=low, 3=medium, 4=high, 5=xhigh
```

That enum is valid as a schema-level set of possible Codex/OpenAI reasoning effort values, but it is not the same thing as the supported reasoning effort ladder for every Codex model. The local Codex source under `extern/orphan/codex/` shows that current Codex model metadata is model-specific. For example, `gpt-5.4`, `gpt-5.3-codex`, and `gpt-5.2-codex` list `low`, `medium`, `high`, and `xhigh` as supported reasoning levels. The Codex TUI model picker also filters choices by the selected model's `supported_reasoning_efforts`, which explains why `Minimal` does not appear for those models.

The current Houmao mapping therefore projects unsupported or non-picker-visible values for common Codex models. The fix should revise the mapping policy without changing the surrounding launch-owned model-selection contract.

## Goals / Non-Goals

**Goals:**

- Make Codex reasoning-level mapping model-aware.
- Align current maintained Codex coding-model ladders with Codex model metadata and TUI behavior.
- Preserve existing projection surfaces after mapping resolution: runtime `config.toml` plus final Codex CLI `--config` override.
- Keep the Houmao user-facing input shape unchanged: `reasoning.level` remains a non-negative tool/model-relative preset index.
- Update tests and docs so the maintained ladder no longer documents `minimal` as the first positive preset for all Codex models.

**Non-Goals:**

- Introduce a live dependency on Codex's runtime model catalog or network model metadata.
- Redesign model-selection precedence, launch-profile storage, or request-scoped override semantics.
- Add a new vendor-native reasoning-control CLI surface.
- Remove support for `minimal` as a possible Codex value when a future or custom Codex model ladder explicitly supports it.

## Decisions

### Decision: Treat Codex enum values as possible native values, not a universal ladder

Houmao should not use Codex's generic `ReasoningEffort` enum as the ordered ladder for every Codex model. Instead, Codex mapping should resolve a maintained model-aware ladder first, then project the selected native value into the existing Codex config surfaces.

For current maintained Codex coding models such as `gpt-5.4`, `gpt-5.3-codex`, and `gpt-5.2-codex`, the positive ladder should be:

```text
1=low, 2=medium, 3=high, 4=xhigh
```

Higher positive values saturate to `xhigh` and mark the mapping as saturated.

Alternative considered: keep `1=minimal` because the Codex schema accepts `minimal`. Rejected because the TUI and model catalog expose model-specific supported levels, and current common Codex coding models do not list `minimal`.

### Decision: Resolve `0` from the model-aware ladder

`0` should continue to mean an explicit off/no-reasoning preset only when the resolved Codex model ladder supports that preset. For models whose maintained ladder does not include an off preset, Houmao should reject `0` clearly instead of projecting `none`.

This preserves the existing cross-tool semantic rule while making it accurate for Codex model families.

Alternative considered: always keep `0=none` for Codex because `none` is a valid enum value. Rejected for the same reason as `minimal`: enum membership is not enough to prove support for a specific model.

### Decision: Keep the table maintained locally

The implementation should start with a local maintained Codex ladder table in Houmao's mapping policy. It can use model-family matching for known current models and a conservative fallback for unknown Codex models.

The fallback should prefer supported current coding-model behavior over the stale broad enum ladder. A reasonable fallback is `low`, `medium`, `high`, `xhigh` with no explicit off preset unless the code has a specific model-family reason to include `none`.

Alternative considered: shell out to Codex or parse Codex's installed `models.json` dynamically. Rejected because launch-time model mapping should stay deterministic, fast, and independent of Codex source checkout layout or network/model-cache availability.

### Decision: Projection and provenance stay unchanged after resolution

Once the native Codex effort is resolved, the existing projection behavior remains correct:

- write `model_reasoning_effort = "<effort>"` to the constructed `${CODEX_HOME}/config.toml`,
- attach `--config=model_reasoning_effort="<effort>"` as a final Codex CLI override,
- preserve requested level, effective level, saturation, off-requested state, and native settings in manifest provenance.

This keeps the change focused on ladder resolution instead of launch helper construction.

## Risks / Trade-offs

- [Risk] Codex model support can change faster than Houmao's maintained table. -> Mitigation: keep the table small, document that it is maintained policy, and add tests that make changes intentional.
- [Risk] Users relying on `reasoning.level: 1` producing `minimal` for Codex will see behavior change to `low` on current Codex coding models. -> Mitigation: document the behavior as an intentional correction to match Codex metadata and TUI choices.
- [Risk] Unknown custom Codex model names may support `minimal` or `none` but the conservative fallback may not expose them. -> Mitigation: allow future explicit model-family table entries and keep advanced native tuning available by omitting Houmao `reasoning.level` and managing native Codex config directly.

## Migration Plan

Implementation should update the mapping policy, tests, and docs in one change. No stored catalog, auth, setup, recipe, specialist, or launch-profile migration is required because stored `reasoning.level` values remain non-negative preset indices; only their native Codex projection changes for affected model families.

Rollback is a code/docs revert of the revised Codex ladder behavior.

## Open Questions

None.
