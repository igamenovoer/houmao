## Context

The shared tracked-TUI demo pack already has a real configuration surface in [demo-config.toml](/data1/huangzhe/code/houmao/scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml) and a real resolver in [config.py](/data1/huangzhe/code/houmao/src/houmao/demo/shared_tui_tracking_demo_pack/config.py). The current loader parses TOML, merges profile and scenario overrides, applies CLI overrides, and converts the merged mapping into internal dataclasses.

That is enough for happy-path operation, but the contract is still implicit in three places:

- the checked-in TOML file,
- lightweight README prose, and
- ad hoc Python parsing rules.

The repo also already has a precedent for packaged JSON Schemas and schema-consistency tests under `src/houmao/.../schemas/`, so this change should align with an existing pattern instead of inventing a demo-specific one-off approach.

One important nuance: operator-facing commands already accept `--demo-config`, but that override is only lightly documented. The change therefore needs to distinguish between:

- capabilities that do not exist yet, such as explicit schema publication and fail-fast validation, and
- behavior that already exists in code, such as alternate config-path selection, but must become an explicit supported part of the demo contract.

## Goals / Non-Goals

**Goals:**

- Add a dedicated developer-facing config reference document under `scripts/demo/shared-tui-tracking-demo-pack/`.
- Package a machine-readable JSON Schema for the demo config under `src/houmao/demo/shared_tui_tracking_demo_pack/`.
- Validate demo-config TOML payloads before they influence launch, capture, validation, or sweep behavior.
- Preserve deterministic config merge order while making config-path selection an explicit, documented operator feature.
- Keep resolved source-config provenance visible in run artifacts and error messages.

**Non-Goals:**

- Redesigning the meaning of existing demo settings, profile semantics, or sweep semantics.
- Introducing a repo-wide generic config system beyond this demo pack.
- Changing the internal `dashboard` command to resolve config independently; it remains run-root driven.
- Replacing the current `ResolvedDemoConfig` dataclasses with a fully different public runtime model unless required by validation boundaries.

## Decisions

### 1. Introduce a boundary-model plus packaged-schema contract for demo config

The demo pack should gain a config boundary layer that is separate from `ResolvedDemoConfig`.

The intended shape is:

- raw TOML mapping
- boundary validation model(s) for the supported config contract
- packaged JSON Schema checked into the demo source package
- conversion into the existing runtime-oriented `ResolvedDemoConfig`

This keeps a clean distinction between:

- the developer-facing configuration contract,
- the machine-readable schema artifact, and
- the internal resolved runtime object used by the demo workflows.

The packaged schema should live under a source-owned `schemas/` directory inside `src/houmao/demo/shared_tui_tracking_demo_pack/`, following the repository’s existing schema-packaging convention.

Alternative considered: keep the current ad hoc parser as the only contract and add documentation only. Rejected because it would leave malformed and unsupported configs discoverable only at runtime and would not give maintainers a stable machine-readable contract.

### 2. Validate both the base config shape and the effective merged config

Validation should happen in two layers:

1. Validate the loaded TOML file as a supported demo-config document, including top-level sections such as `profiles`, `scenario_overrides`, and `sweeps`.
2. After profile/scenario/CLI merge, validate the effective config again as a fully resolved config payload before converting it into `ResolvedDemoConfig`.

This matters because override blocks are partial fragments, not full configs. The schema/model layer therefore needs reusable definitions for:

- the full top-level config,
- override fragments for profile/scenario blocks, and
- nested sweep/profile structures.

Without this split, the loader would either:

- reject valid override fragments because they are intentionally partial, or
- validate only the final merged payload and miss unsupported keys or malformed fragments in dormant profile/override sections.

Alternative considered: validate only the final merged config. Rejected because invalid override blocks could remain hidden until selected, and unsupported keys in the config file would still be harder to detect and explain.

### 3. Treat `--demo-config` as the supported alternate-config selection mechanism

The operator-facing CLI already accepts `--demo-config` on the user-facing commands. This change should preserve that mechanism and make it part of the supported contract rather than replacing it with a different override style.

The implementation/doc behavior should be:

- the companion checked-in TOML remains the default when no override is provided,
- operator-facing commands accept `--demo-config <path>` to select another config file,
- README and the new config reference document explain that this is the supported way to switch configs, and
- tests cover that alternate config selection influences path roots and persisted `source_config_path`.

This is intentionally narrower than adding new environment-variable or global-wrapper override mechanisms. The current flag-based shape is already present and consistent with the Python driver.

Alternative considered: add an environment variable or a wrapper-global `--demo-config` before the subcommand. Rejected for this change because it expands surface area without solving the core problems of discoverability, formal contract, and validation.

### 4. Add a dedicated config reference doc and keep README as the operator index

The README should remain the short operator guide, while the new dedicated config reference becomes the place for:

- section-by-section setting explanations,
- merge-order explanation,
- profile and sweep semantics,
- alternate config-path usage,
- validation expectations and common failure modes.

This avoids overloading the main README with a line-by-line config schema while still keeping the demo self-explanatory from its own directory.

Alternative considered: expand the README to document every field directly. Rejected because the README is already mixing workflow, fixture-authoring, and operator usage; a full config reference would make it harder to scan and maintain.

### 5. Make validation strict on unsupported fields and actionable on failure

The validation layer should reject:

- missing required sections,
- wrong value types,
- unsupported enum values,
- structurally invalid sweep/profile/override blocks, and
- unknown fields where the demo contract intends a closed schema.

Error reporting should include:

- the selected config path, and
- enough field-path context to explain what is invalid.

This is important because the demo is meant to support deliberate config experimentation. Loose acceptance of unknown keys would make typos and stale local configs silently fall back to unexpected defaults.

Alternative considered: keep unknown fields lenient for local convenience. Rejected because it weakens the value of the new schema and makes “easy switch” behavior less trustworthy.

## Risks / Trade-offs

- [Boundary model, packaged schema, and docs can drift] -> Mitigation: generate or verify the packaged schema against the boundary model in tests, and keep the dedicated config doc focused on behavior and merge semantics rather than duplicating every literal schema node.
- [Stricter validation can break ad hoc local configs that previously happened to work] -> Mitigation: produce actionable errors, document the contract clearly, and keep current supported settings/defaults stable.
- [Override-fragment validation is more complex than validating one flat config] -> Mitigation: define explicit reusable fragment models/schema defs for profile and scenario overrides instead of trying to coerce partial payloads into the full-config model.
- [Users may still miss that `inspect` and `stop` should use the same alternate config when non-default path roots are involved] -> Mitigation: document this in the new config reference and README examples, and add tests covering alternate-root lookup.

## Migration Plan

1. Introduce boundary models and a packaged JSON Schema for the demo-config contract under the demo source package.
2. Add schema-loading and validation helpers for the demo pack, reusing repository patterns where practical.
3. Update `resolve_demo_config()` to validate the loaded TOML and the effective merged config before returning `ResolvedDemoConfig`.
4. Add a dedicated config reference doc under the demo directory and update the README to link to it and show alternate config-path usage explicitly.
5. Add tests for valid default loading, alternate config-path selection, invalid config failures, and schema/model consistency.

Rollback strategy: remove the new validation gate and schema/doc additions while preserving the existing TOML loader and runtime dataclasses. The change is isolated to demo config handling and documentation, so rollback does not require broader runtime migration.

## Open Questions

- Should the packaged JSON Schema be generated from a Pydantic boundary model during development and checked in as an artifact, or should it be hand-maintained with consistency tests against the model?
- Do we want the first version of strict validation to reject all unknown keys immediately, or allow narrowly scoped passthrough only inside explicitly open-ended metadata-like areas if such areas are added later?
