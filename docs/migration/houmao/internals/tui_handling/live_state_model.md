# Live State Model

The public live-state payload is `HoumaoTerminalStateResponse` in [`../../../../../src/houmao/server/models.py`](../../../../../src/houmao/server/models.py). The response is returned by `GET /houmao/terminals/{terminal_id}/state`, but the authoritative state is held in memory by `LiveSessionTracker`.

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

`diagnostics` is the public low-level sample health view.

Current `diagnostics.availability` mapping is:

- `error` when probe or parse failed for the current sample
- `unavailable` when the tracked tmux target is gone
- `tui_down` when tmux is reachable but the supported TUI process is not running
- `available` when the parser produced a supported parsed surface
- `unknown` when the server is still watching but the current sample is not classifiable confidently enough for normal interpretation

The full `diagnostics` object also carries:

- `transport_state`
- `process_state`
- `parse_status`
- optional `probe_error`
- optional `parse_error`

## Foundational Surface Observables

`surface` is now the public “what is directly observable right now?” layer.

Its fields are:

- `accepting_input`
- `editing_input`
- `ready_posture`

These are produced by tool/version-specific signal detection in [`../../../../../src/houmao/server/tui/turn_signals.py`](../../../../../src/houmao/server/tui/turn_signals.py), using:

- current raw `output_text`
- optional `parsed_surface`
- tool-specific matchers for active work, interruption, failure, and ready/success cues

Important consequences of the current implementation:

- visible progress rows are supporting evidence only, not a required condition for activity
- a submit-ready parsed surface can still yield `ready_posture=yes` even if the raw tool prompt chrome is partially missing
- ambiguous interactive UI such as menus, selection boxes, and permission prompts degrades `ready_posture` toward `unknown`

## Turn And Last-Turn Mapping

The public turn model is intentionally smaller than the internal reducer graph.

### `turn.phase`

The current implementation uses:

- `ready` when no active anchor remains and the surface looks ready for another turn
- `active` when an explicit or inferred anchor is armed, or when the detector has strong current active evidence
- `unknown` when diagnostics are degraded or the current posture is ambiguous

Ambiguous interactive UI does not create a dedicated ask-user public phase. It contributes to `turn.phase="unknown"` unless stronger active or terminal evidence exists.

### `last_turn`

`last_turn` is sticky and updates only when a tracked turn reaches a terminal outcome:

- `success`
- `interrupted`
- `known_failure`
- `none`

The source is:

- `explicit_input` for the supported server-owned input route
- `surface_inference` for inferred direct tmux prompting
- `none` before any terminal turn is recorded

The current success path is important:

- success still depends on the shared ReactiveX settle window
- success does not require a `Worked for <duration>`-style marker on every turn
- the tracker may retract a premature success if a later observation proves the same turn surface was still evolving

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

- [`../../../../../src/houmao/server/models.py`](../../../../../src/houmao/server/models.py)
- [`../../../../../src/houmao/server/tui/turn_signals.py`](../../../../../src/houmao/server/tui/turn_signals.py)
- [`../../../../../src/houmao/server/tui/tracking.py`](../../../../../src/houmao/server/tui/tracking.py)
- [`../../../../../src/houmao/server/service.py`](../../../../../src/houmao/server/service.py)
