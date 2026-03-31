## Why

All `houmao-mgr` commands currently emit raw JSON via `emit_json()`. This is hard to scan visually during interactive use and provides no way for operators to choose between machine-readable and human-readable output. Operators need a quick-glance view by default and the option to switch to JSON for scripting or rich formatting for detailed inspection.

## What Changes

- Add three mutually exclusive global flags to the `houmao-mgr` root group: `--print-plain` (default), `--print-json`, and `--print-fancy`.
- Add the `HOUMAO_CLI_PRINT_STYLE` environment variable (`plain` | `json` | `fancy`) as a persistent preference that flags override.
- Introduce an output engine module (`src/houmao/srv_ctrl/commands/output.py`) that dispatches to the selected style with generic fallback renderers so every command works immediately.
- Introduce a `renderers/` subpackage for per-domain curated renderers that improve high-traffic commands (agent list, agent state, server status, gateway status).
- Replace all `emit_json()` call sites (~106 across 12 command modules) with the new `emit()` dispatcher.
- `--print-plain` produces clean aligned text via `click.echo()` only — no external dependency on the default path.
- `--print-json` preserves current behavior (indent=2, sorted keys).
- `--print-fancy` uses the `rich` library (already a dependency) for tables, panels, and colored status indicators.

## Capabilities

### New Capabilities
- `houmao-mgr-print-style`: Global print-style control for `houmao-mgr` output — flags, env var, output engine, generic fallbacks, and curated per-domain renderers.

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: The root group gains `--print-plain`, `--print-json`, `--print-fancy` flags and passes an `OutputContext` through click context to all subcommands.

## Impact

- **Code**: `src/houmao/srv_ctrl/commands/` — new `output.py` module, new `renderers/` subpackage, flag wiring in `main.py`, and replacement of `emit_json()` calls across `common.py`, `server.py`, `admin.py`, `brains.py`, `mailbox.py`, `project.py`, and `agents/` submodules.
- **Dependencies**: No new external dependencies; `rich` is already declared (`rich>=14.3.3,<15`).
- **CLI contract**: Default output format changes from JSON to plain text. Scripts relying on JSON must add `--print-json` or set `HOUMAO_CLI_PRINT_STYLE=json`. This is an intentional **BREAKING** change consistent with the project's breaking-change-friendly policy.
- **Tests**: Existing unit tests that assert JSON output will need `--print-json` or env var to pass.
