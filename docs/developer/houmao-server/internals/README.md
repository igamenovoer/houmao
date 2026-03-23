# TUI Handling Internals

This doc set explains how `houmao-server` performs server-owned live TUI tracking after `add-houmao-server-official-tui-tracker` and the later hardening work. It is intentionally about the internal watch plane, not about the broader operator migration story in [`docs/migration/houmao/server-pair/README.md`](../../../migration/houmao/server-pair/README.md).

The key architectural boundary is:

- `houmao-server` owns the `src/houmao/server/tui/` watch-plane module: discovery, polling, parsing, host-side lifecycle, and terminal-keyed live lookup.
- `houmao.shared_tui_tracking` owns tracker semantics for raw-snapshot reduction, detector/profile resolution, and tracker-owned `surface` / `turn` / `last_turn`.
- The supervised child `cao-server` still exists for CAO-compatible control routes, but it is no longer in the parsing or live-state authority path.
- Live tracker state is memory-primary. On restart, the server rebuilds watch authority from registration records plus current tmux liveness instead of replaying old tracker snapshots from disk.
- The public tracked-state contract is now centered on `diagnostics`, foundational `surface` observables, current `turn`, and sticky `last_turn`, while lifecycle authority and settle timing remain internal tracker machinery.

## Module Map

- [`../../../../src/houmao/server/service.py`](../../../../src/houmao/server/service.py): top-level wiring, registration route handling, alias maps, and the poll cycle entrypoint
- [`../../../../src/houmao/server/tui/registry.py`](../../../../src/houmao/server/tui/registry.py): registration-backed discovery and metadata enrichment
- [`../../../../src/houmao/server/tui/transport.py`](../../../../src/houmao/server/tui/transport.py): tmux pane resolution and capture
- [`../../../../src/houmao/server/tui/process.py`](../../../../src/houmao/server/tui/process.py): live process-tree inspection for supported TUI detection
- [`../../../../src/houmao/server/tui/parser.py`](../../../../src/houmao/server/tui/parser.py): official parser adapter over the shared shadow parser stack
- [`../../../../src/houmao/server/tui/tracking.py`](../../../../src/houmao/server/tui/tracking.py): in-memory tracked state, internal settle/anchor machinery, public simplified turn mapping, stability, and recent transitions
- [`../../../../src/houmao/server/tui/supervisor.py`](../../../../src/houmao/server/tui/supervisor.py): reconcile loop and per-session watch workers
- [`tui_tracking_module.md`](tui_tracking_module.md): package-level ownership and module map for `src/houmao/server/tui/`
- [`../../../../src/houmao/server/models.py`](../../../../src/houmao/server/models.py): public route payloads for tracked state, history, and registration
- [`../../../../src/houmao/shared_tui_tracking/models.py`](../../../../src/houmao/shared_tui_tracking/models.py): canonical type definitions (`Tristate`, `TurnPhase`, `TrackedDiagnosticsAvailability`, etc.)
- [`../../../../src/houmao/shared_tui_tracking/public_state.py`](../../../../src/houmao/shared_tui_tracking/public_state.py): canonical mapping functions (`diagnostics_availability()`, `turn_phase_from_signals()`)
- [`../../../../src/houmao/shared_tui_tracking/detectors.py`](../../../../src/houmao/shared_tui_tracking/detectors.py): shared detector/profile contracts and compatibility exports
- [`../../../../src/houmao/shared_tui_tracking/apps/claude_code/`](../../../../src/houmao/shared_tui_tracking/apps/claude_code/): Claude Code detector/profile implementations
- [`../../../../src/houmao/shared_tui_tracking/apps/codex_tui/`](../../../../src/houmao/shared_tui_tracking/apps/codex_tui/): Codex interactive TUI detector/profile implementations and temporal hint logic
- [`../../../../src/houmao/shared_tui_tracking/apps/unsupported_tool/`](../../../../src/houmao/shared_tui_tracking/apps/unsupported_tool/): fallback detector/profile implementation

## Public Surface Versus Internal Authority

The public Houmao-owned routes for the tracker are still terminal-keyed:

- `POST /houmao/launches/register`
- `GET /houmao/terminals/{terminal_id}/state`
- `GET /houmao/terminals/{terminal_id}/history`

Internally, the tracker is not keyed by `terminal_id`. The authoritative identity is `HoumaoTrackedSessionIdentity`, whose primary key is `tracked_session_id` and whose compatibility alias set includes the terminal id. `terminal_id` remains the public lookup token, but route resolution goes through an alias map held by `houmao-server` instead of making terminal id the internal watch authority.

## Reading Order

1. [`tui_tracking_module.md`](tui_tracking_module.md)
2. [`registration_and_discovery.md`](registration_and_discovery.md)
3. [`probe_parse_track_pipeline.md`](probe_parse_track_pipeline.md)
4. [`live_state_model.md`](live_state_model.md)
5. [`supervisor_and_lifecycle.md`](supervisor_and_lifecycle.md)

## Primary Source References

- [`../../../../src/houmao/server/app.py`](../../../../src/houmao/server/app.py)
- [`../../../../src/houmao/server/service.py`](../../../../src/houmao/server/service.py)
- [`../../../../src/houmao/server/tui/registry.py`](../../../../src/houmao/server/tui/registry.py)
- [`../../../../src/houmao/server/tui/transport.py`](../../../../src/houmao/server/tui/transport.py)
- [`../../../../src/houmao/server/tui/process.py`](../../../../src/houmao/server/tui/process.py)
- [`../../../../src/houmao/server/tui/parser.py`](../../../../src/houmao/server/tui/parser.py)
- [`../../../../src/houmao/server/tui/tracking.py`](../../../../src/houmao/server/tui/tracking.py)
- [`../../../../src/houmao/server/tui/supervisor.py`](../../../../src/houmao/server/tui/supervisor.py)
- [`../../../../src/houmao/shared_tui_tracking/models.py`](../../../../src/houmao/shared_tui_tracking/models.py)
- [`../../../../src/houmao/shared_tui_tracking/public_state.py`](../../../../src/houmao/shared_tui_tracking/public_state.py)
- [`../../../../src/houmao/shared_tui_tracking/detectors.py`](../../../../src/houmao/shared_tui_tracking/detectors.py)
- [`../../../../src/houmao/shared_tui_tracking/apps/codex_tui/`](../../../../src/houmao/shared_tui_tracking/apps/codex_tui/)
