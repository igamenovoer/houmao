## 1. Shared Reasoning Contract

- [x] 1.1 Replace the normalized `1..10` reasoning parser with non-negative preset-index parsing in the shared model-selection helpers and request payload models.
- [x] 1.2 Redesign the reasoning mapping policy to resolve tool/model-specific preset ladders, support optional `0` off semantics, and saturate overflow to the highest maintained preset.
- [x] 1.3 Update brain-build and headless runtime override flows to record requested preset indices, native mapping summaries, and saturation/off provenance in manifests.

## 2. CLI And Authoring Surfaces

- [x] 2.1 Update `houmao-mgr agents launch`, `agents prompt`, `agents gateway prompt`, and `agents turn submit` to stop enforcing a fixed `1..10` range and to pass non-negative reasoning indices through the shared resolver.
- [x] 2.2 Update recipe, launch-profile, and easy-profile authoring surfaces to store reasoning levels as tool/model-specific preset indices and keep clear/remove behavior intact.
- [x] 2.3 Add clear resolution-time errors for unsupported `0` off requests and any other resolved tool/model reasoning cases that Houmao cannot satisfy.

## 3. Tests

- [x] 3.1 Replace the existing even-distribution mapping tests with coverage for per-tool/model ladders, overflow saturation, optional `0` off support, and Gemini multi-setting preset projection.
- [x] 3.2 Update launch, brain-builder, and headless override tests to reflect the new preset-index semantics and manifest provenance.
- [x] 3.3 Update CLI command tests to cover non-negative parsing, removal of the global upper bound, and negative-input rejection.

## 4. Documentation

- [x] 4.1 Update CLI reference and getting-started docs to describe `--reasoning-level` as a tool/model-specific preset index instead of a normalized `1..10` scale.
- [x] 4.2 Document the maintained preset ladders for Claude and Codex and add Gemini preset-table guidance that explains when Houmao maps one level to multiple native settings.
- [x] 4.3 Add operator guidance that users needing finer vendor-native control should omit Houmao reasoning levels and manage native tool config or env directly.
