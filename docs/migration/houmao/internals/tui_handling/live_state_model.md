# Live State Model

The public live-state payload is `HoumaoTerminalStateResponse` in [`../../../../../src/houmao/server/models.py`](../../../../../src/houmao/server/models.py). The response is returned by `GET /houmao/terminals/{terminal_id}/state`, but the actual state is held in memory by `LiveSessionTracker`.

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

## Top-Level State Fields

`HoumaoTerminalStateResponse` is intentionally split into layers instead of exposing only one summarized status.

The top-level groups are:

- probe transport: `transport_state`
- process liveliness: `process_state`
- parse outcome: `parse_status`
- raw evidence: `probe_snapshot`, `probe_error`, `parse_error`
- parsed TUI surface: `parsed_surface`
- operator-facing reduction: `operator_state`
- stability metadata: `stability`
- bounded recent history: `recent_transitions`

The compatible history route, `GET /houmao/terminals/{terminal_id}/history`, returns the same recent transition entries without the rest of the current-state payload.

## Initial State

When a tracker is first created, `LiveSessionTracker` builds an explicit unknown state instead of leaving the state absent.

The initial values are:

- `transport_state="tmux_missing"`
- `process_state="unknown"`
- `parse_status="transport_unavailable"`
- `operator_state.status="unknown"`
- `operator_state.completion_state="inactive"`
- empty `recent_transitions`

That state means “the tracker exists, but no successful live observation has been recorded yet.”

## Derived Operator State

`operator_state` is computed in `_build_operator_state()` inside [`../../../../../src/houmao/server/tui/tracking.py`](../../../../../src/houmao/server/tui/tracking.py).

The high-level mapping is:

- probe failures become `status="error"`
- missing tmux becomes `status="unavailable"`
- `tui_down` becomes `status="tui_down"`
- unsupported tools become `status="unknown"`
- parse failures become `status="error"`
- parsed `awaiting_operator` surfaces become `status="waiting_user_answer"`
- parsed `working` surfaces become `status="processing"`
- stable completed parsed surfaces become `status="completed"`
- parsed submit-ready surfaces become `status="ready"`

The operator-facing state also carries:

- `readiness_state`
- `completion_state`
- `detail`
- `projection_changed`
- `updated_at_utc`

## Readiness And Completion Reduction

The reducer is `_SurfaceStateReducer`, which consumes parsed observations over time instead of deciding readiness or completion from one snapshot in isolation.

Current readiness rules are:

- `failed` when the parser reports unsupported or disconnected availability
- `blocked` when the parsed surface shows `awaiting_operator`
- `unknown` when the parser output is effectively unknown
- `ready` when the surface is `supported + idle + freeform`
- `waiting` otherwise

Current completion rules are:

- `failed`, `blocked`, or `unknown` when the parsed surface is already in one of those conditions
- `in_progress` while the surface reports `business_state="working"`
- `waiting` when the cycle has not yet satisfied completion conditions
- `candidate_complete` when the surface looks submit-ready after real work or projection change, but has not stayed stable long enough yet
- `completed` once that candidate state remains stable for at least `stability_threshold_seconds`
- `inactive` when no parsed activity baseline has been established yet

`projection_changed` tracks whether the normalized dialog projection changed relative to the working-cycle baseline. This keeps “the model actually advanced” separate from “the surface is merely idle again.”

## Stability Metadata

`stability` is different from completion timing.

For every recorded cycle, the tracker builds a visible-state signature from:

- transport state
- process state
- parse status
- probe and parse errors
- parsed surface payload
- reduced operator-facing state

That payload is JSON-serialized, hashed with SHA-1, and stored in `HoumaoStabilityMetadata`.

The tracker resets `stable_since_utc` whenever the visible signature changes. `stable=True` means the current visible state has remained unchanged for at least the configured stability threshold.

This is a generic “how long has the current visible state remained identical?” signal, not only a parser-completion signal.

## Recent Transitions

`recent_transitions` is a bounded in-memory list of `HoumaoRecentTransition`.

A new transition entry is created only when one of the operator-visible fields changes. The current diff includes:

- `transport_state`
- `process_state`
- `parse_status`
- operator status
- readiness state
- completion state
- `projection_changed`
- probe error message
- parse error message
- parsed surface `business_state`
- parsed surface `input_mode`
- parsed surface `ui_context`

Each entry records:

- `recorded_at_utc`
- a human-readable `summary`
- the tuple of `changed_fields`
- the resulting `transport_state`, `process_state`, `parse_status`, and `operator_status`

The buffer is bounded by `recent_transition_limit`, so it is useful for recent diagnosis without becoming a persistent event log.

## Related Sources

- [`../../../../../src/houmao/server/models.py`](../../../../../src/houmao/server/models.py)
- [`../../../../../src/houmao/server/tui/tracking.py`](../../../../../src/houmao/server/tui/tracking.py)
- [`../../../../../src/houmao/server/service.py`](../../../../../src/houmao/server/service.py)
