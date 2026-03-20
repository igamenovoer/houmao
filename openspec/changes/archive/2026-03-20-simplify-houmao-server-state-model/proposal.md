## Why

The current `houmao-server` tracked-state contract exposes too many overlapping layers at once: direct observation, reducer-internal lifecycle states, authority bookkeeping, and operator summary. It also still leans on two assumptions that are not reliable enough for a primary contract: that slash-command-looking input can be distinguished from normal prompting, and that visible progress signals are required to recognize an active turn.

## What Changes

- **BREAKING** simplify the primary tracked-state contract around directly observable surface facts: whether the TUI is accepting input, whether input is actively being edited, whether the visible surface is in a ready posture, and other explicit operator-facing signals
- **BREAKING** replace the current public readiness/completion/authority-heavy lifecycle surface with one unified turn model that reports current turn phase and the last observed terminal outcome
- Stop differentiating chat turns from slash commands in the public state model; all submitted input is treated as one turn lifecycle because command-looking input is not reliably distinguishable from normal prompting
- Fold ambiguous menus, selection boxes, permission prompts, and other unstable operator-interaction UI into `turn.phase=unknown` rather than publishing a dedicated ask-user state or terminal outcome
- Rename the public failure outcome to `known_failure` and reserve it for specifically recognized failure signatures; failure-like but unmatched surfaces collapse into `turn.phase=unknown`
- Treat progress bars, spinners, and similar activity signs as supporting evidence only; they are sufficient evidence for active-turn inference when seen, but not necessary evidence
- Treat unexplained TUI churn conservatively; visible change may update diagnostics, surface state, transitions, or stability without automatically implying lifecycle progress
- Keep timed behavior in state tracking ReactiveX-driven; the simplification SHALL NOT reintroduce manual timer reducers or ad hoc wall-clock bookkeeping for settle, debounce, or unknown-duration behavior
- Keep transport/process/parse failures and parsed-surface evidence available as diagnostics, but stop making reducer-internal states such as `candidate_complete`, `completed`, `stalled`, and turn-anchor authority the primary consumer-facing contract
- Update the dual shadow-watch demo and maintainer-facing docs to present the simplified server-owned model instead of the current lifecycle-heavy surface

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `official-tui-state-tracking`: simplify the server-owned tracked-state semantics around foundational observables, current turn phase, and last observed terminal outcome
- `houmao-server`: revise the tracked-state extension-route contract to publish the simplified state model and demote reducer internals to diagnostics
- `houmao-server-dual-shadow-watch-demo`: consume and display the simplified server-owned state model instead of the current readiness/completion/authority presentation

## Impact

- Public tracked-state models and JSON payloads in `src/houmao/server/models.py`
- State reduction and mapping in `src/houmao/server/tui/tracking.py` and supporting lifecycle code
- Demo monitor and operator copy under `src/houmao/demo/houmao_server_dual_shadow_watch/` and `scripts/demo/houmao-server-dual-shadow-watch/`
- Developer and reference docs describing `houmao-server` state tracking
