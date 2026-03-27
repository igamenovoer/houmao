## Why

The passive server can currently discover agents and proxy gateway requests, but it cannot observe what agents are doing. Step 4 of the greenfield migration adds TUI observation — the ability to poll each discovered agent's tmux pane, parse the tool-specific TUI surface, track state transitions, and serve the observation state through HTTP endpoints. This is the passive server's most complex feature and is required before headless turn management (step 5) can be built.

## What Changes

- Add a `TuiObservationService` to the passive server that:
  - Watches the discovery index for agent arrivals/departures.
  - Creates per-agent observers that poll tmux panes, inspect process liveness, parse TUI snapshots, and feed through the shared tracking session.
  - Maintains per-agent in-memory state: current TUI snapshot, recent transitions, stability metadata, diagnostics.
  - Runs a shared background polling loop that iterates over all active observers each cycle.
- Add agent state response models to `passive_server/models.py` that reuse existing sub-models (`HoumaoTrackedDiagnostics`, `HoumaoParsedSurface`, `HoumaoProbeSnapshot`, `HoumaoTrackedSurface`, `HoumaoTrackedTurn`, etc.) from `server/models.py`.
- Add three HTTP endpoints:
  - `GET /houmao/agents/{agent_ref}/state` — compact observation state (surface, turn, stability, diagnostics summary).
  - `GET /houmao/agents/{agent_ref}/state/detail` — full observation state including probe snapshot and parsed surface.
  - `GET /houmao/agents/{agent_ref}/history` — recent state transitions.
- Reuse existing infrastructure directly (not copy):
  - `TuiTrackerSession` from `shared_tui_tracking` for core tracking logic.
  - `TmuxTransportResolver` from `server/tui/transport.py` for tmux pane capture.
  - `PaneProcessInspector` from `server/tui/process.py` for process liveness.
  - `OfficialTuiParserAdapter` from `server/tui/parser.py` for TUI parsing.
  - Detector profiles from `shared_tui_tracking` for tool-specific signal detection.

## Capabilities

### New Capabilities
- `passive-server-tui-observation`: Defines the TUI observation lifecycle (per-agent observer creation/removal, polling pipeline, state tracking) and the three HTTP state/detail/history endpoints served by the passive server.

### Modified Capabilities
- `passive-server-agent-discovery`: The discovery index now drives observation lifecycle — newly discovered agents trigger observer creation, removed agents trigger observer teardown. No requirement-level changes to discovery itself.

## Impact

- **New file**: `src/houmao/passive_server/observation.py` — TUI observation service and per-agent observer.
- **Modified**: `src/houmao/passive_server/models.py` — new response models for agent state/detail/history.
- **Modified**: `src/houmao/passive_server/service.py` — new observation-backed service methods.
- **Modified**: `src/houmao/passive_server/app.py` — three new HTTP routes.
- **Modified**: `src/houmao/passive_server/config.py` — observation poll interval config.
- **Dependencies on existing code** (import, not copy): `server.tui.transport`, `server.tui.process`, `server.tui.parser`, `server.models`, `shared_tui_tracking`.
- **New tests**: `tests/unit/passive_server/test_observation.py`, updates to `test_service.py` and `test_app_contracts.py`.
