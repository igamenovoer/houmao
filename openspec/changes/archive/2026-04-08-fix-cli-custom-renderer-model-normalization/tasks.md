## 1. Normalize curated renderer dispatch

- [x] 1.1 Update `src/houmao/srv_ctrl/commands/output.py` so `emit()` / `OutputContext.emit()` normalize Pydantic `BaseModel` payloads before dispatching to curated plain and fancy renderers as well as the generic fallbacks.
- [x] 1.2 Audit the curated renderer helpers under `src/houmao/srv_ctrl/commands/renderers/` and keep detached dict-copy behavior anywhere a renderer mutates local payload data.

## 2. Add regression coverage

- [x] 2.1 Add output-engine regression tests that prove a curated renderer wired through `emit()` receives normalized mapping data when the command payload is a Pydantic model.
- [x] 2.2 Add or update tests for `houmao-mgr agents list` so populated managed-agent model payloads render rows in human-oriented output instead of `No managed agents.`
- [x] 2.3 Add or update tests for `houmao-mgr agents gateway status` so populated gateway-status model payloads render fields in human-oriented output instead of `(no gateway status)`.

## 3. Verify the command surface

- [x] 3.1 Run targeted Pixi-based tests for the output engine and the affected `srv_ctrl` command suites.
- [x] 3.2 Re-run the managed-agent CLI repro path and confirm `houmao-mgr agents list` plus `houmao-mgr agents gateway status` show populated plain-text output for a live easy-launched specialist session.
