## Why

The shared tracked-TUI demo pack now has a meaningful configuration surface, but the contract is still split across README prose, Python assumptions, and the checked-in TOML file itself. That makes it harder to understand which settings are supported, to safely switch between alternate config files, and to fail early when a config is malformed or semantically invalid.

## What Changes

- Add a dedicated developer-facing configuration reference document inside the shared tracked-TUI demo pack that explains the TOML structure, setting groups, profile behavior, sweep behavior, and config selection workflow.
- Introduce a checked-in JSON Schema under the demo source package that describes the supported demo-config structure, required sections, value shapes, and allowed enums.
- Validate demo config payloads against that schema when the demo resolves configuration, so malformed or unsupported config files fail fast with actionable errors.
- Make alternate config-file selection an explicit supported launch behavior for the demo workflow, so operators can point the demo at another TOML file instead of relying only on the companion checked-in file.
- Persist the resolved source config path and validated resolved config in run artifacts as part of the supported operator/debugging workflow.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shared-tui-tracking-demo-configuration`: Expand the configuration contract to require a dedicated config reference document, a formal machine-readable schema, fail-fast validation of demo configs on load, and an explicitly supported alternate config-path selection workflow for demo commands.

## Impact

- Affected code: `src/houmao/demo/shared_tui_tracking_demo_pack/config.py`, the demo driver/entrypoint flow, and any helper modules that surface config resolution or launch behavior.
- Affected docs: the demo-pack README plus a new dedicated config reference document under `scripts/demo/shared-tui-tracking-demo-pack/`.
- Affected assets: a new JSON Schema file under `src/houmao/demo/shared_tui_tracking_demo_pack/` and tests covering valid/invalid config resolution and alternate config-file selection.
