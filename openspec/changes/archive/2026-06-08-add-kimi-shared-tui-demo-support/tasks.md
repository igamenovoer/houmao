## 1. Tool Catalog and Configuration

- [x] 1.1 Add `kimi` to the shared TUI demo `ToolName` catalog, CLI `--tool` choices, fixture/run manifest parsing, scenario parsing, and sweep path inference.
- [x] 1.2 Extend demo boundary models, config parsing, and generated JSON Schema so `tools.kimi` is valid in full configs and override fragments.
- [x] 1.3 Add `[tools.kimi]` defaults to `scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml`.
- [x] 1.4 Update config reference documentation to describe Kimi tool defaults, Kimi overrides, and Kimi fixture roots.

## 2. Kimi Launch Assets and Auth Projection

- [x] 2.1 Add demo-local Kimi agent assets under `inputs/agents/tools/kimi/`, including adapter and default setup files.
- [x] 2.2 Add `interactive-watch-kimi-default.yaml` using the demo-local `default` auth alias and Kimi interactive TUI launch posture.
- [x] 2.3 Extend demo auth materialization to project `tools/kimi/auth/default` from a host-local Kimi auth bundle.
- [x] 2.4 Add secret-free placeholder or documentation for the expected Kimi auth-bundle shape under `tests/fixtures/auth-bundles/kimi/`.
- [x] 2.5 Ensure missing Kimi auth bundle preflight errors report the concrete missing source path before tmux launch.

## 3. Kimi Runtime Observation and Scenario Control

- [x] 3.1 Add Kimi version detection command candidates for the demo pack.
- [x] 3.2 Add Kimi process matching for both `kimi-code` and `kimi` in demo runtime observations and process-kill helpers.
- [x] 3.3 Add Kimi interrupt and close behavior to recorded scenario control, using Escape as the Kimi interrupt path.
- [x] 3.4 Confirm scenario execution resolves Kimi through `app_id_from_tool(tool="kimi")` and the shared `kimi_code` profile registry path.

## 4. Kimi Live Watch and Recorded Scenarios

- [x] 4.1 Add `run_demo.sh start --tool kimi` support and ensure start/inspect output reports Kimi tool and dashboard attach commands.
- [x] 4.2 Add first-wave Kimi scenario JSON files for explicit success, interrupted after active, approval rejection, footer-thinking-ready, and TUI-down diagnostics.
- [x] 4.3 Add Kimi entries to capture-frequency sweep contracts where first-wave scenarios have stable transition expectations.
- [x] 4.4 Update the demo README with Kimi live-watch, recorder-enabled live-watch, recorded-capture, and manual auth setup examples.

## 5. Recorded Validation and Future Corpus Support

- [x] 5.1 Ensure `recorded-validate --tool kimi` works when a fixture root lacks `fixture_manifest.json`.
- [x] 5.2 Ensure Kimi fixture manifests drive replay as `tool = kimi` and preserve observed Kimi version metadata.
- [x] 5.3 Ensure `recorded-sweep` and `recorded-validate-corpus` include Kimi fixtures when manifests or fixture paths identify Kimi.
- [x] 5.4 Keep missing or empty Kimi fixture corpus behavior as a clear preflight error instead of requiring committed Kimi fixtures in this change.

## 6. Tests and Validation

- [x] 6.1 Add unit tests for Kimi agent-tree materialization, default auth alias projection, and missing-auth preflight errors.
- [x] 6.2 Add unit tests for Kimi config parsing, schema acceptance, CLI choices, and sweep path inference.
- [x] 6.3 Add workflow tests proving live-watch and recorded-capture build requests use demo-local Kimi assets.
- [x] 6.4 Add replay-entry tests for Kimi fixture manifests and explicit `--tool kimi` recorded validation.
- [x] 6.5 Run `openspec validate add-kimi-shared-tui-demo-support --type change --strict`.
- [x] 6.6 Run focused demo-pack tests with `pixi run pytest tests/unit/demo/shared_tui_tracking_demo_pack -q`.
- [x] 6.7 Local Kimi auth bundle was unavailable at `tests/fixtures/auth-bundles/kimi/personal-a-default`, so the conditional manual `start --tool kimi --with-recorder` smoke was skipped.
