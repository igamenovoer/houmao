## 1. Definition Model And Layout

- [ ] 1.1 Introduce the new canonical `agents/` layout for `skills`, `roles/<role>/presets`, and `tools/<tool>/{adapter,setups,auth}` in the tracked fixture tree.
- [ ] 1.2 Define and implement the minimal preset schema (`skills`, optional `auth`, optional `launch`, optional `mailbox`, optional `extra`) with path-derived role/tool/setup identity.
- [ ] 1.3 Replace recipe- and blueprint-specific loader models with preset/setup/auth loader models and remove build-time `name` / `default_agent_name` requirements from reusable definitions.

## 2. Build And Resolution Pipeline

- [ ] 2.1 Update brain construction to resolve tool setup bundles and auth bundles from the new per-tool layout and project them into generated runtime homes.
- [ ] 2.2 Update manifest generation and parsing to record `preset_path`, `setup`, and effective `auth` instead of legacy config-profile / credential-profile fields.
- [ ] 2.3 Update native selector resolution to map `--agents` plus provider onto path-derived presets, including default-setup resolution and explicit path-like preset selectors.

## 3. CLI And Runtime Integration

- [ ] 3.1 Update `houmao-mgr agents launch` and related local build surfaces to consume presets, preserve preset launch settings, and support an explicit `--auth` override.
- [ ] 3.2 Keep managed-agent identity launch-time only by removing preset-owned default agent names while preserving existing runtime fallback behavior when launch-time identity is omitted.
- [ ] 3.3 Migrate any blueprint-owned non-core launch metadata that still matters into the new preset model or `extra`, and remove obsolete recipe/blueprint code paths.

## 4. Fixtures, Docs, And Verification

- [ ] 4.1 Migrate tracked agent fixtures, demo inputs, and README/MIGRATION guidance to the new setup/auth/preset terminology and directory layout.
- [ ] 4.2 Update unit, integration, and demo tests to cover path-derived preset identity, preset-backed launch resolution, and manifest field changes.
- [ ] 4.3 Add focused tests for one tool supporting multiple setup bundles and multiple auth bundles independently, including auth override behavior and omission of preset-owned `default_agent_name`.
