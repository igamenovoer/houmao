# Live State Model

The public live-state payload is `HoumaoTerminalStateResponse` in [`../../../../src/houmao/server/models.py`](../../../../src/houmao/server/models.py). The response is returned by `GET /houmao/terminals/{terminal_id}/state`, but the authoritative state is held in memory by `LiveSessionTracker`.

This migration note focuses on the current implementation shape: a simplified public state model built over existing internal anchor/settle machinery.

## Identity And Aliases

Every tracker owns one `HoumaoTrackedSessionIdentity`.

Important identity fields are:

- `tracked_session_id`: the internal watch-plane key
- `session_name`: the original registration session name
- `tool`
- `tmux_session_name`
- `tmux_window_name`
- `terminal_aliases`
- optional `agent_name`, `agent_id`, `manifest_path`, and `session_root`

The public terminal route resolves through `m_terminal_aliases`, then returns the tracker state for the bound `tracked_session_id`. This is why terminal id remains the route key while tracked session identity remains the in-memory authority.

## Public State Shape

`HoumaoTerminalStateResponse` is now organized around four primary consumer-facing groups plus supporting diagnostics:

- low-level diagnostics: `diagnostics`
- raw evidence: `probe_snapshot`, `parsed_surface`
- foundational observables: `surface`
- current turn posture: `turn`
- sticky terminal outcome: `last_turn`
- generic stability: `stability`
- bounded recent history: `recent_transitions`

Low-level `transport_state`, `process_state`, `parse_status`, `probe_error`, and `parse_error` are still carried on the model for service/debug use, but the public API contract is the simplified `diagnostics / surface / turn / last_turn` surface.

The compatible history route, `GET /houmao/terminals/{terminal_id}/history`, returns the same recent transition entries without the rest of the current-state payload.

## Initial State

When a tracker is first created, `LiveSessionTracker` builds an explicit unknown state instead of leaving the state absent.

The initial values are:

- `diagnostics.availability="unknown"`
- `transport_state="tmux_missing"`
- `process_state="unknown"`
- `parse_status="transport_unavailable"`
- `surface.accepting_input="unknown"`
- `surface.editing_input="unknown"`
- `surface.ready_posture="unknown"`
- `turn.phase="unknown"`
- `last_turn.result="none"`
- `last_turn.source="none"`
- empty `recent_transitions`

That state means “the tracker exists, but no successful live observation has been recorded yet.”

## Diagnostics Mapping

For the full definition of each `diagnostics.availability` value (intuitive meaning, technical derivation, operational implications), see the [State Reference Guide](../state-reference.md#diagnosticsavailability).

In brief, `diagnostics.availability` maps low-level observation outcomes (`transport_state`, `process_state`, `parse_status`, errors) into one of five values: `available`, `unavailable`, `tui_down`, `error`, `unknown`. The full `diagnostics` object also carries those low-level fields for service/debug use.

## Foundational Surface Observables

For the full definition of each surface observable (`accepting_input`, `editing_input`, `ready_posture`) and their tristate values, see the [State Reference Guide](../state-reference.md#surface-observables).

In brief, surface observables are produced by tool/version-specific signal detectors in [`src/houmao/shared_tui_tracking/detectors.py`](../../../../src/houmao/shared_tui_tracking/detectors.py) from raw snapshot text alone. The live server feeds that raw text into the standalone tracker session and keeps parsed-surface metadata on the server side.

## Turn And Last-Turn Mapping

For the full definition of `turn.phase`, `last_turn.result`, and `last_turn.source` values, see the [State Reference Guide](../state-reference.md#turnphase). For transition diagrams and operation acceptability, see the [State Transitions Guide](../state-transitions.md).

In brief: `turn.phase` is narrower than the internal reducer graph, collapsing ambiguous states into `unknown`. `last_turn` is sticky and only changes on terminal outcomes. Success depends on the settle window, does not require a completion marker, and may be retracted if the surface proves to still be evolving.

## Internal Timing And Authority Still Exist

The simplified public contract did not remove the underlying timing machinery.

Internally, the tracker still keeps:

- shared readiness snapshots
- anchored completion snapshots
- active/lost/expired turn anchors
- settle timing driven by the ReactiveX kernel
- internal operator/lifecycle metadata used for service/debug paths

Those fields remain valuable for debugging and coarse service projection, but they are no longer the primary consumer-facing contract.

## Recent Transitions

`recent_transitions` is a bounded in-memory list of `HoumaoRecentTransition`.

A new transition entry is created when visible public state changes. The current diff includes:

- `diagnostics_availability`
- `transport_state`
- `process_state`
- `parse_status`
- `surface_accepting_input`
- `surface_editing_input`
- `surface_ready_posture`
- `turn_phase`
- `last_turn_result`
- `last_turn_source`
- parsed surface `business_state`
- parsed surface `input_mode`
- parsed surface `ui_context`
- probe and parse error messages

Each entry records:

- `recorded_at_utc`
- a human-readable `summary`
- the tuple of `changed_fields`
- the resulting diagnostics/turn/last-turn fields plus low-level transport/process/parse fields

The buffer remains bounded by `recent_transition_limit`, so it is useful for recent diagnosis without becoming a persistent event log.

## Related Sources

- [`../../../../src/houmao/server/models.py`](../../../../src/houmao/server/models.py)
- [`../../../../src/houmao/server/tui/turn_signals.py`](../../../../src/houmao/server/tui/turn_signals.py)
- [`../../../../src/houmao/server/tui/tracking.py`](../../../../src/houmao/server/tui/tracking.py)
- [`../../../../src/houmao/server/service.py`](../../../../src/houmao/server/service.py)
