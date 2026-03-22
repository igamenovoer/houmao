## 1. Config Contract Documentation

- [x] 1.1 Add a dedicated demo config reference document under `scripts/demo/shared-tui-tracking-demo-pack/` that explains config sections, merge order, profiles, sweeps, and the supported `--demo-config` selection workflow.
- [x] 1.2 Update the demo-pack README to link to the dedicated config reference and show alternate config-file usage as an explicit supported operator workflow.

## 2. Schema And Validation Boundary

- [x] 2.1 Introduce demo-config boundary model(s) and a packaged JSON Schema under `src/houmao/demo/shared_tui_tracking_demo_pack/` that cover the full config document plus profile/scenario override fragments and sweep structures.
- [x] 2.2 Add demo-pack schema loading and validation helpers so `resolve_demo_config()` validates the selected TOML payload before merge and validates the effective merged config before returning `ResolvedDemoConfig`.
- [x] 2.3 Tighten config validation failures so malformed or unsupported configs report the selected config path and the invalid field or section.

## 3. Operator-Facing Config Selection

- [x] 3.1 Ensure the operator-facing demo commands consistently honor the documented alternate config-file selection workflow for config-derived roots and defaults.
- [x] 3.2 Preserve and persist resolved source-config provenance in recorded, live-watch, and sweep artifacts wherever resolved demo config is written.

## 4. Verification

- [x] 4.1 Add unit tests for default config loading, profile/scenario/CLI merge behavior, and alternate config-path selection across the demo workflows.
- [x] 4.2 Add negative tests for malformed TOML, unknown keys, missing required sections, and invalid profile/sweep/override structures.
- [x] 4.3 Add schema packaging or schema-consistency tests so the packaged JSON Schema stays aligned with the demo-config validation boundary.
