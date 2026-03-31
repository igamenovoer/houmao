## 1. Output Engine Foundation

- [ ] 1.1 Create `src/houmao/srv_ctrl/commands/output.py` with `PrintStyle` literal type, `OutputContext` class (holding resolved style and lazy `rich.Console`), `resolve_print_style()` (flag → env var → default `plain`), and `output_options()` click decorator factory
- [ ] 1.2 Implement generic JSON fallback renderer in `output.py`: serialize payload via `json.dumps(indent=2, sort_keys=True)`, normalizing Pydantic `BaseModel` via `.model_dump(mode="json")`
- [ ] 1.3 Implement generic plain fallback renderer in `output.py`: flat dicts as aligned `key: value` lines, list-bearing dicts as header + column-aligned rows, nested values summarized inline — using `click.echo()` only, no `rich` import
- [ ] 1.4 Implement generic fancy fallback renderer in `output.py`: flat dicts as `rich.Table(key, value)`, list-bearing dicts as `rich.Table` with auto-detected columns, nested dicts as `rich.Tree` — lazy `rich` import only when fancy is active
- [ ] 1.5 Implement the top-level `emit()` function in `output.py` that reads `OutputContext` from `click.get_current_context().obj["output"]`, dispatches to the active style's renderer, and accepts optional `plain_renderer`/`fancy_renderer` callables for curated overrides

## 2. Root Group Wiring

- [ ] 2.1 Wire `output_options()` decorator and `print_style` parameter to the root `cli()` group in `src/houmao/srv_ctrl/commands/main.py`; store resolved `OutputContext` in `ctx.obj["output"]`
- [ ] 2.2 Enable Click context propagation (`ctx.ensure_object(dict)`) so all subcommands inherit the output context via `click.Context.obj`

## 3. Call-Site Migration

- [ ] 3.1 Update `src/houmao/srv_ctrl/commands/common.py`: import `emit` from `output.py`, deprecate `emit_json()` as a thin alias that forces JSON mode
- [ ] 3.2 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/server.py` (~10 sites)
- [ ] 3.3 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/agents/core.py` (~8 sites) and convert `emit_local_launch_completion()` / `emit_local_join_completion()` to use `emit()` with a structured payload
- [ ] 3.4 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/agents/gateway.py` (~14 sites)
- [ ] 3.5 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/agents/mail.py` (~7 sites)
- [ ] 3.6 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/agents/turn.py` (~4 sites)
- [ ] 3.7 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/agents/cleanup.py` (~2 sites)
- [ ] 3.8 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/agents/mailbox.py` (~4 sites)
- [ ] 3.9 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/admin.py` (~4 sites)
- [ ] 3.10 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/brains.py` (~2 sites)
- [ ] 3.11 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/mailbox.py` (~11 sites)
- [ ] 3.12 Replace `emit_json()` calls with `emit()` in `src/houmao/srv_ctrl/commands/project.py` (~40 sites)

## 4. Curated Renderers

- [ ] 4.1 Create `src/houmao/srv_ctrl/commands/renderers/__init__.py` subpackage
- [ ] 4.2 Create `renderers/agents.py` with curated plain and fancy renderers for agent list (table), agent state (panel), and launch/join completion messages
- [ ] 4.3 Create `renderers/server.py` with curated plain and fancy renderers for server status (panel with optional session table)
- [ ] 4.4 Create `renderers/gateway.py` with curated plain and fancy renderers for gateway status and prompt result
- [ ] 4.5 Wire curated renderers into their respective command handlers via `emit(payload, plain_renderer=..., fancy_renderer=...)`

## 5. Tests

- [ ] 5.1 Add unit tests for `resolve_print_style()`: flag wins over env var, env var wins over default, invalid env var falls back to plain
- [ ] 5.2 Add unit tests for generic plain renderer: flat dict, list-bearing dict, nested dict, Pydantic model payloads
- [ ] 5.3 Add unit tests for generic JSON renderer: output matches `json.dumps(indent=2, sort_keys=True)` for various payload shapes
- [ ] 5.4 Add unit tests for generic fancy renderer: verify `rich.Console` output for flat dict, list, and nested payloads
- [ ] 5.5 Add unit tests for `emit()` dispatch: verify curated renderer is called when provided, generic fallback otherwise
- [ ] 5.6 Add integration test: invoke `houmao-mgr agents list --print-json` via Click test runner and verify JSON output structure
- [ ] 5.7 Update any existing `houmao-mgr` CLI tests that assert JSON output to use `--print-json` or set `HOUMAO_CLI_PRINT_STYLE=json`

## 6. Validation and Cleanup

- [ ] 6.1 Run `pixi run lint && pixi run typecheck` and fix any issues
- [ ] 6.2 Run `pixi run test` and verify all existing tests pass (with env var or flag adjustment)
- [ ] 6.3 Remove the deprecated `emit_json()` alias from `common.py` once all call sites are confirmed migrated
