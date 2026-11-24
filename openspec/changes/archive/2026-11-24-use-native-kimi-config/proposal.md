# Proposal

## Why

Houmao currently validates Kimi reasoning against the setup bundle and can launch with a different `config.toml` from the credential bundle. Kimi already supports native file settings for model catalogs and many preferences that Houmao accepts as environment variables. [Issue #94](https://github.com/igamenovoer/houmao/issues/94)

## What Changes

- Resolve one effective Kimi `config.toml` from the selected setup and credential inputs. Use it for preflight and for the private runtime home so a model declared in the credential bundle needs no duplicate definition.
- Use native TOML for supported Kimi model, provider, and runtime settings. Remove their environment bindings from managed Kimi processes and tmux sessions, including inherited bindings. Deliver explicitly referenced API keys through private credential inputs and retain process inputs Kimi needs at startup.
- Define each multi-effort model's ordered `support_efforts` in native TOML. Map Houmao's numeric levels to the selected alias's exact native labels, including Kimi model overrides. Keep the existing numeric saturation and off semantics.
- **BREAKING** Retire the managed Kimi env-model path and its environment-writing provider, model, and telemetry flags. Existing env-model bundles must supply native TOML before launch. Update credential authoring guidance, fixtures, and maintained demo callers to use that format.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime` resolves and materializes effective Kimi config, delivers private credentials, and excludes config-owned bindings from startup and tmux.
- `agent-model-selection` selects native Kimi aliases and maps numeric levels using each alias's ordered effort catalog.
- `houmao-mgr-project-agent-tools` defines the starter Kimi adapter's native config and remaining environment inputs.
- `houmao-mgr-credentials-cli` defines the Kimi config import and private API-key inputs for maintained authoring commands.
- `houmao-manage-credentials-skill` directs Kimi credential authoring to config-backed API and OAuth workflows.
- `test-agent-launch-fixtures` uses the same native model and provider configuration for raw and managed Kimi fixtures.

## Impact

The change affects Kimi brain construction, launch and relaunch planning, native model projection, credential authoring, starter assets, and managed tmux environment publication. It covers Kimi headless, TUI, ACP, and Web through their existing startup paths. It also updates Kimi fixture and demo preparation, operator reference examples, and packaged guidance.
