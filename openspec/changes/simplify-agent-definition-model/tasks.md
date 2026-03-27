## 1. Definition Model And Layout

- [x] 1.1 Introduce the new user-facing `agents/` source layout for `skills`, `roles/<role>/presets`, and `tools/<tool>/{adapter,setups,auth}` in the tracked fixture tree.
- [x] 1.2 Define and implement the minimal strict source preset schema (`skills`, optional `auth`, optional `launch.{prompt_mode,overrides}`, optional `mailbox`, optional `extra`) with path-derived role/tool/setup identity, unknown top-level field rejection, and migrated gateway defaults under `extra.gateway` when present.
- [x] 1.3 Introduce the canonical parsed agent-definition model and resolved launch/build data models that downstream code will consume independent of the user-facing source layout.

## 2. Build And Resolution Pipeline

- [x] 2.1 Replace recipe- and blueprint-specific loader outputs with source parsers that populate the canonical parsed catalog from presets, setups, auth bundles, adapters, and role packages.
- [x] 2.2 Update native selector resolution to map `--agents` plus provider onto the canonical parsed catalog, including bare-role -> `default` setup resolution, explicit preset file selectors, and rejection of `<role>/<setup>` shorthand.
- [x] 2.3 Update brain construction and manifest generation/parsing to consume canonical resolved inputs, record `preset_path`, `setup`, and effective `auth` in brain manifest schema version 3, update loader version checks, and regenerate the checked-in JSON schemas.

## 3. CLI And Runtime Integration

- [x] 3.1 Update `houmao-mgr agents launch` and related local build surfaces to consume canonical resolved launch/build specs, preserve `launch.prompt_mode` and `launch.overrides`, keep `--agent-name` optional and `--agent-id` optional, and support an explicit `--auth` override.
- [x] 3.2 Keep managed-agent identity launch-time only by removing preset-owned default agent names, preserving current runtime fallback identity derivation when launch-time identity is omitted, and documenting that distinct concurrent logical agents require explicit `--agent-name` values.
- [x] 3.3 Migrate any blueprint-owned non-core launch metadata that still matters into parser-managed preset `extra`, including gateway defaults under `extra.gateway`, and remove obsolete recipe/blueprint code paths.

## 4. Fixtures, Docs, And Verification

- [x] 4.1 Migrate tracked agent fixtures, demo inputs, `compatibility-profiles/` references, and README/MIGRATION guidance to the new setup/auth/preset terminology and directory layout.
- [x] 4.2 Update unit, integration, and demo tests to cover strict source-schema validation, parser output into the canonical catalog, path-derived preset identity, selector rules, canonical-spec-backed launch resolution, and manifest schema version 3 field changes.
- [x] 4.3 Add focused tests for one tool supporting multiple setup bundles and multiple auth bundles independently, including auth override behavior, optional `--agent-name` fallback behavior, and omission of preset-owned `default_agent_name`.
