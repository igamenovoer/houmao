## Context

All `houmao-mgr` commands currently emit output through a single `emit_json()` function in `src/houmao/srv_ctrl/commands/common.py`. This function serializes Pydantic models or plain dicts to JSON with `indent=2, sort_keys=True` and writes via `click.echo()`. There are ~106 call sites across 12 command modules, plus ~5 manual `click.echo("key=value")` patterns for launch/join completion messages.

The `rich` library (`>=14.3.3,<15`) is already declared as a project dependency but unused in the CLI path. The CLI uses Click for command routing and has no custom context object — `click.Context` is passed directly.

Current output is always JSON, which is hard to read for quick human inspection but good for scripts. The project is breaking-change-friendly, so changing the default output format is acceptable.

## Goals / Non-Goals

**Goals:**
- Provide three distinct print styles: `plain` (human-readable text), `json` (machine-readable), `fancy` (rich-formatted).
- Default to `plain` for human-first interactive use.
- Support a global `HOUMAO_CLI_PRINT_STYLE` environment variable so operators can set a persistent preference.
- Introduce generic fallback renderers so every existing command works correctly in all three modes immediately — no per-command work required for baseline functionality.
- Provide curated per-domain renderers for high-traffic commands (agent list, agent state, server status, gateway status) for improved readability.
- Keep `plain` mode free of `rich` import cost — use `click.echo()` only.

**Non-Goals:**
- Per-command `--print-*` flags — the flags live only on the root group and apply globally.
- `--concise` / `--detail` verbosity axis — all modes show the same data completeness; only the formatting style differs.
- Interactive/TUI features (progress bars, spinners, live-updating tables).
- Reformatting error output — `click.ClickException` handling stays as-is.
- Changing `houmao-server` or `houmao-cli` output — only `houmao-mgr` is in scope.

## Decisions

### Decision 1: Three mutually exclusive `--print-*` flags on the root group

The root `houmao-mgr` click group gains three flag-value options mapping to a single `print_style` parameter: `--print-plain` (flag_value `"plain"`), `--print-json` (flag_value `"json"`), `--print-fancy` (flag_value `"fancy"`). Click enforces mutual exclusion naturally via the shared parameter name.

**Alternative considered**: A single `--output-format` option with choices. Rejected because three flag-style options are faster to type and self-documenting in `--help`.

**Alternative considered**: Per-command flags. Rejected because output style is a user preference, not a per-command decision.

### Decision 2: Resolution precedence — flag > env var > default

Print style is resolved as: explicit CLI flag (highest) → `HOUMAO_CLI_PRINT_STYLE` env var → default `"plain"`. This follows the standard CLI convention where explicit flags override environment, which overrides defaults.

### Decision 3: New `output.py` module as the output engine

A new module `src/houmao/srv_ctrl/commands/output.py` owns:
- `PrintStyle` literal type (`"plain" | "json" | "fancy"`)
- `OutputContext` class holding the resolved style and a lazy `rich.Console` instance
- `resolve_print_style()` function implementing the resolution precedence
- `output_options()` click decorator factory for the three flags
- `emit()` top-level function that reads `OutputContext` from click context and dispatches

The existing `emit_json()` in `common.py` becomes a thin alias calling `emit()` with forced JSON mode during transition, then is removed.

**Alternative considered**: Putting everything in `common.py`. Rejected because `common.py` already has unrelated concerns (agent selector helpers, port options, prompt resolution); output formatting deserves its own module.

### Decision 4: Generic fallback renderers for all three modes

Every call to `emit()` works immediately in all three styles via generic renderers:
- **json**: `json.dumps(payload, indent=2, sort_keys=True)` — identical to current behavior.
- **plain**: Flat dict → aligned `key: value` lines; dict with list values → header + column-aligned rows; nested dicts → top-level keys shown, nested values summarized.
- **fancy**: Flat dict → `rich.Table(key, value)` panel; list data → `rich.Table` with auto-detected columns; nested dicts → `rich.Tree`.

Commands can optionally pass `plain_renderer` and `fancy_renderer` callables to `emit()` for curated output. When not provided, the generic fallback is used.

### Decision 5: Curated renderers live in `renderers/` subpackage

`src/houmao/srv_ctrl/commands/renderers/` contains per-domain modules (`agents.py`, `server.py`, `gateway.py`, `mailbox.py`) that define typed rendering functions. Each function accepts the payload and `OutputContext` and produces styled output for both plain and fancy modes.

This keeps `output.py` focused on the dispatch engine and generic fallbacks while domain-specific rendering logic stays near its command group.

### Decision 6: `OutputContext` flows through `click.Context.obj`

The root group stores `OutputContext` in `ctx.ensure_object(dict)["output"]`. Subcommands access it via `click.get_current_context()`. The `emit()` function reads it automatically so individual command handlers don't need to accept or pass it.

### Decision 7: `plain` mode uses click.echo() only — no rich import

The default `plain` mode must not import `rich` at all. The `rich.Console` instance inside `OutputContext` is created lazily only when `fancy` mode is active. This keeps the default path fast and dependency-light.

## Risks / Trade-offs

- **[BREAKING: default output changes from JSON to plain text]** → Scripts relying on current JSON output will break. Mitigation: document the change; operators set `HOUMAO_CLI_PRINT_STYLE=json` or add `--print-json` to scripts. The project policy explicitly allows breaking changes.
- **[Generic plain renderer may be ugly for deeply nested payloads]** → Mitigation: Generic renderer truncates nested structures; curated renderers are added for high-traffic commands in Phase 2. JSON mode always provides full fidelity.
- **[106 call-site migration]** → Mitigation: `emit()` is a drop-in replacement for `emit_json()` with the same signature for the common case. The migration is mechanical find-and-replace.
- **[Fancy mode adds terminal escape codes to piped output]** → Mitigation: `rich.Console` auto-detects non-TTY and strips markup by default. No special handling needed.
