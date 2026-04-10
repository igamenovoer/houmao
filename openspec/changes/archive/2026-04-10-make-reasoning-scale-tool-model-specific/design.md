## Context

Houmao recently introduced a shared launch-owned model-selection contract that treats `reasoning.level` as a normalized portable `1..10` scale. The current mapping policy then spreads that portable scale across each tool's native reasoning controls, for example by evenly bucketing levels into Claude effort levels, Codex reasoning-effort buckets, or Gemini thinking fields.

That design makes the API look tool-agnostic, but the underlying reasoning semantics are not tool-agnostic and are often not even model-agnostic. Operators who choose a Claude, Codex, or Gemini model typically already understand that tool's native reasoning ladder better than a Houmao-defined `1..10` abstraction. The current even-distribution mapping also makes it hard to predict whether a value such as `7` means "medium", "high", or "the second-highest supported preset" for the resolved runtime.

This change keeps the secret-free launch-owned field shape but redefines its meaning. `reasoning.level` becomes a tool-and-model-specific preset index that Houmao resolves only after the final `(tool, model)` pair is known. Gemini remains supported through Houmao-maintained preset tables, but those presets are explicitly documented as Houmao convenience mappings rather than portable native equivalence classes.

## Goals / Non-Goals

**Goals:**
- Make `reasoning.level` predictable for operators who already think in terms of the target tool/model.
- Replace evenly distributed `1..10` bucketing with one-step-per-preset ladder resolution.
- Allow `0` to mean explicit off only when the resolved tool/model supports an off or no-thinking preset.
- Saturate values above the maintained ladder length to the highest maintained preset instead of rejecting or redistributing them.
- Allow Gemini presets to map one Houmao level to multiple native Gemini settings together and document that mapping clearly.
- Keep advanced provider-native tuning out of the shared launch/config contract by directing fine-grained users to native config or env surfaces.

**Non-Goals:**
- Preserve backward-compatible meaning for previously stored `1..10` values.
- Introduce a new generic schema for exact vendor-native reasoning controls.
- Guarantee cross-tool portability for the same integer reasoning value.
- Automatically migrate every existing stored reasoning value to a newly preferred smaller ordinal.

## Decisions

### Decision: `reasoning.level` becomes a resolved tool/model preset index

Houmao will continue storing one integer field at `launch.model.reasoning.level` and `execution.model.reasoning.level`, but the integer will no longer mean "normalized `1..10`". Instead it means "the Nth maintained reasoning preset for the resolved tool/model ladder".

Rationale:
- This preserves the existing secret-free field shape while removing the misleading portability claim.
- The resolved `(tool, model)` pair already participates in mapping policy, so moving from normalized bucketing to model-aware preset ladders fits the current architecture.

Alternatives considered:
- Keep normalized `1..10`: rejected because it hides native semantics behind a coarse abstraction that users do not actually reason with.
- Expose only native string/numeric values: rejected for this change because the existing CLI/API field shape is already widely referenced and a preset index is a smaller interface change.

### Decision: Ladder resolution is monotonic with saturation, not even redistribution

Each resolved tool/model will publish an ordered list of maintained presets. Houmao will interpret values as follows:

- `0`: explicit off, only when that ladder declares an off preset
- `1`: first non-off preset
- `2`: second preset
- `N`: Nth preset
- `> max_supported_index`: highest maintained preset for that ladder

Houmao will not evenly redistribute values across a global range. Overflow saturates to the highest maintained preset and is recorded as such in mapping provenance.

Rationale:
- This matches the operator mental model of "one step higher" far better than bucket redistribution.
- Saturation keeps stored values stable across future ladder shortening or tools with fewer presets.

Alternatives considered:
- Reject values above the maintained maximum: rejected because the requested direction is to treat unused higher numbers as "maximum".
- Keep round-to-nearest-bucket behavior: rejected because it creates non-local jumps and hides the actual native ladder size.

### Decision: Validation becomes model-aware and removes the global upper bound

The CLI and API will stop enforcing `1..10` as a universal bound. Validation becomes:

- negative values are invalid,
- `0` is valid only when the resolved tool/model ladder supports explicit off,
- positive integers are accepted and resolved against the ladder with overflow saturation.

This requires moving validation away from fixed `IntRange(1, 10)` style checks and into the shared model-mapping policy or a shared helper that can see the resolved tool/model.

Rationale:
- A fixed upper bound conflicts with the new saturation rule.
- Tool/model-relative ladders cannot be validated correctly without resolution context.

Alternatives considered:
- Keep `1..10` as a hard cap: rejected because it reintroduces an arbitrary portable scale that the new design is explicitly removing.

### Decision: Gemini levels are Houmao-maintained preset tables

For Gemini, Houmao will define documented preset ladders per maintained model family. A single Houmao level may project to a combination of native Gemini settings such as `thinkingLevel`, `thinkingBudget`, or both. The documentation will make clear that these are Houmao presets for convenience, not raw Gemini-native scalar levels.

If an operator needs finer control than the documented presets, the supported workflow is to omit Houmao `reasoning.level` and manage Gemini-native config or environment directly.

Rationale:
- Gemini reasoning behavior is not always expressible as one ordinal native field.
- Preset tables let Houmao provide a simple launch-owned interface without pretending that the field is universal or exact.

Alternatives considered:
- Force Gemini into one scalar only: rejected because it loses useful combined preset definitions.
- Add generic first-class CLI flags for Gemini-native thinking controls: rejected because that would expand the shared contract in a provider-specific way.

### Decision: Existing stored values are reinterpreted under the new ladder semantics

This repository allows breaking changes, so existing stored reasoning integers will be interpreted under the new ladder semantics without a compatibility shim. Larger historical values may therefore saturate to a model's maximum preset after this change. The migration path is explicit documentation plus operator review of stored launch defaults when needed.

Rationale:
- The old and new meanings are fundamentally different, so a faithful automatic translation is not reliable.
- Avoiding compatibility shims keeps the shared contract and mapping policy simpler.

Alternatives considered:
- Add legacy-versioned reasoning semantics: rejected because it would complicate every authoring and runtime surface for a transitional behavior that is not intended to persist.

## Risks / Trade-offs

- [Risk] Existing stored reasoning values may become more aggressive than before because high historical values now saturate to the model maximum. → Mitigation: document the breaking semantic change clearly and update operator-facing docs/examples to use small ladder indices.
- [Risk] Validation becomes dependent on the resolved model, which is later than some current CLI checks. → Mitigation: centralize validation in shared resolution logic and keep only coarse non-negative integer parsing at the edge.
- [Risk] Different models under the same tool may support different ladder lengths or off semantics, which can surprise users who switch models without changing stored values. → Mitigation: require mapping provenance to record the resolved native preset and saturation state, and document that reasoning levels are model-relative.
- [Risk] Gemini preset tables can drift from upstream provider behavior. → Mitigation: keep the preset definitions explicit in one maintained mapping module and document that users needing exact native control should bypass Houmao presets.

## Migration Plan

1. Replace the shared reasoning contract language in the model-selection spec and the launch/runtime specs.
2. Update CLI capability specs and docs specs to remove normalized `1..10` wording and fixed upper-bound examples.
3. Implement shared model-aware reasoning validation and preset resolution in the mapping layer, then update edge CLI parsing to accept non-negative integers.
4. Update docs and examples to show small preset indices and Gemini preset-table guidance.
5. Accept that existing stored reasoning values are reinterpreted under the new semantics; do not add automatic back-compat translation.

## Open Questions

- Should manifests record both the requested preset index and the effective saturated preset index when overflow occurs, or is the native mapping summary sufficient?
- Do we want any optional warning surface when a stored value saturates to maximum, or should the behavior remain silent and only observable through manifest/native projection output?
