## Why

The current `houmao-server` tracked-state contract exposes too many overlapping layers at once: direct observation, reducer-internal lifecycle states, authority bookkeeping, and operator summary. That makes the API harder to understand, makes dashboards reason about reducer internals, and drifts away from a simpler foundational model: first observe whether the TUI is processing, whether it is accepting input, whether input is actively being edited, and whether the visible input posture is chat or exact slash-command; then express current work phase and last observed outcome on top of those facts.

## What Changes

- **BREAKING** simplify the primary tracked-state contract around foundational observables: whether the TUI is processing, whether it is accepting input, whether input is actively being edited, and whether the visible input mode is chat or command oriented
- **BREAKING** replace the current public readiness/completion/authority-heavy lifecycle surface with a smaller work-cycle model that reports current work phase and the last observed outcome
- Keep timed behavior in state tracking ReactiveX-driven; the simplification SHALL NOT reintroduce manual timer reducers or ad hoc wall-clock bookkeeping for settle, debounce, or unknown-duration behavior
- Keep transport/process/parse failures and parsed-surface evidence available as diagnostics, but stop making reducer-internal states such as `candidate_complete`, `completed`, `stalled`, and turn-anchor authority the primary consumer-facing contract
- Update the dual shadow-watch demo and maintainer-facing docs to present the simplified server-owned model instead of the current lifecycle-heavy surface

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `official-tui-state-tracking`: simplify the server-owned tracked-state semantics around foundational observables, current work phase, and last observed outcome
- `houmao-server`: revise the tracked-state extension-route contract to publish the simplified state model and demote reducer internals to diagnostics
- `houmao-server-dual-shadow-watch-demo`: consume and display the simplified server-owned state model instead of the current readiness/completion/authority presentation

## Impact

- Public tracked-state models and JSON payloads in `src/houmao/server/models.py`
- State reduction and mapping in `src/houmao/server/tui/tracking.py` and supporting lifecycle code
- Demo monitor and operator copy under `src/houmao/demo/houmao_server_dual_shadow_watch/` and `scripts/demo/houmao-server-dual-shadow-watch/`
- Developer and reference docs describing `houmao-server` state tracking
