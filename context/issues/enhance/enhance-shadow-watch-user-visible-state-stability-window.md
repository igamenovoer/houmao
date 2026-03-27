# Enhancement Proposal: Shadow Watch Should Expose A User-Visible State Stability Window

## Status
Proposed

## Summary
The dual shadow-watch demo currently shows the raw classified state stream from finite TUI snapshots. That is useful for parser debugging, but it is not enough for an operator who wants a practical answer to a different question:

```text
Has this state stayed unchanged long enough that I should treat it as stable?
```

Today the monitor already has a narrow internal debounce for one specific concept:

- `completion_stability_seconds` delays the transition from `candidate_complete` to `completed`

But there is no general user-visible stability concept for the full observed state stream. When the parser or the sampled TUI flickers between neighboring states, the operator has to manually watch the dashboard and infer whether the stream has "settled enough."

The monitor should expose an explicit stability window so an operator can choose a policy like:

- "If the observed state has not changed for 10 seconds, treat it as stable."

This proposal does not assume every flicker is a bug. Some flicker is expected because the system only sees periodic snapshots of a live interactive TUI and may sample at awkward boundaries between tool sub-states.

## Why

The current dashboard mixes two use cases:

1. parser-debugging view
   - every raw state transition matters
   - even sub-second oscillation is useful evidence

2. operator view
   - the user wants a calmer answer such as:
     - "still working"
     - "ready and stable"
     - "blocked and stable"
     - "completed and stable"

Those are not the same need.

With live CAO-backed tools, especially Claude Code and Codex, it is normal to observe fast transitions such as:

- `processing -> idle -> processing`
- `working -> idle -> working`
- `candidate_complete -> in_progress -> candidate_complete`

Some of these transitions may reflect real tool behavior. Some may be artifacts of tail-window classification or poll timing. Either way, the operator still needs a smoothing layer above the raw stream.

Without that layer:

- the dashboard can feel noisy even when the overall tool behavior is understandable,
- users may overreact to flicker that should be treated as transient,
- there is no first-class answer to "how long has this state been unchanged?",
- "stable enough to trust" remains a manual judgment instead of a surfaced runtime hint.

## Requested Direction

### 1. Add a general state-stability window distinct from completion debounce

Introduce one monitor-level policy for user-visible stability, for example:

- `state_stability_window_seconds`

This is separate from:

- `completion_stability_seconds`
- `unknown_to_stalled_timeout_seconds`

Its purpose is not to redefine parser semantics. Its purpose is to tell the operator whether the currently displayed state signature has remained unchanged for long enough to be treated as stable.

### 2. Track stability over the full visible state signature

The stability timer should be based on the same state signature the operator sees, or on a clearly documented derived signature, for example:

- readiness state
- completion state
- business state
- input mode
- ui context
- blocked excerpt presence
- projection-changed flag, if relevant

When that signature changes, the stability timer resets.

When it stays unchanged for the configured window, the monitor can mark the state as stable.

### 3. Surface both raw and smoothed interpretations

Do not hide the raw stream. Keep raw evidence available for debugging.

The monitor should present both:

- raw current state
- stability metadata, such as:
  - `stable_for_seconds`
  - `is_stable`
  - `stability_window_seconds`

Optionally, it may also present a smoothed label such as:

- `working (stable)`
- `ready (stable)`
- `blocked (stable)`
- `completed (stable)`
- `waiting (unstable)`

### 4. Let operators choose the window

The stability window should be configurable for interactive use, not hard-coded.

Examples:

- default `0` or a small value for raw parser debugging
- `10s` for a calmer operator-facing dashboard

Possible surfaces:

- demo CLI flag
- persisted demo-state field
- runtime config policy

The exact config path can be decided later, but the policy should be explicit and user-controlled.

### 5. Preserve the meaning of existing completion logic

This proposal should not silently replace the current completion policy. Completion debounce still has a separate meaning:

- "candidate complete remained quiet long enough to call it completed"

The new stability window is a broader UX layer:

- "whatever the current visible state is, it has stopped changing for N seconds"

These two concepts should remain distinguishable in code, UI, and docs.

## Acceptance Criteria

1. The monitor exposes a documented user-visible state stability policy separate from `completion_stability_seconds`.
2. Operators can configure a stability window value for interactive monitoring.
3. The dashboard or emitted state includes whether the current state is stable and how long it has remained unchanged.
4. Raw transition evidence remains available and is not replaced by the smoothed view.
5. Docs explain the difference between:
   - raw observed state,
   - completion debounce,
   - general state stability window,
   - unknown-to-stalled timeout.
6. A user can adopt an operational rule like:
   - "if the state has not changed for 10 seconds, treat it as stable"
   and the system provides the data needed to support that rule directly.

## Likely Touch Points

- `src/houmao/demo/houmao_server_dual_shadow_watch/driver.py`
- `src/houmao/demo/houmao_server_dual_shadow_watch/models.py`
- `scripts/demo/houmao-server-dual-shadow-watch/scripts/watch_dashboard.py`
- `scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh`
- docs for shadow monitoring and troubleshooting

## Non-Goals

- No claim that every observed flicker is a parser bug.
- No requirement to eliminate raw oscillation from the underlying parser stream.
- No requirement to change provider-specific parser semantics in the same change.
- No requirement to replace `completion_stability_seconds` with one unified timer.

## Suggested Follow-Up

1. Decide whether this belongs only to the dual shadow-watch demo or should become a reusable monitor-layer concept.
2. Define the exact state signature whose unchanged duration counts as "stable."
3. Decide how to present the result in UI and NDJSON:
   - metadata only,
   - additional smoothed labels,
   - or both.
4. Create an OpenSpec change if we want to implement the stability window rather than just track the need.
