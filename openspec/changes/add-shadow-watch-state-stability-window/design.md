## Context

The dual shadow-watch monitor polls CAO terminals at ~500ms intervals, parses TUI snapshots, and classifies them into dashboard states. The current system has `completion_stability_seconds` for delaying `candidate_complete → completed` transitions, but no general stability concept for the full state stream. When TUI sampling catches state transitions mid-flight, operators see flicker like `processing → idle → processing` that may or may not be meaningful.

Current architecture:
- `AgentSessionMonitor.sample()` fetches + parses + reduces one observation
- `AgentStateTracker.observe()` applies state machine logic
- `ShadowWatchMonitor.run()` polls all agents in a loop and renders Rich dashboard
- State transitions logged to NDJSON when `transition_signature()` changes

Constraint: `reactivex>=4.1.0` already in dependencies.

## Goals / Non-Goals

**Goals:**
- Add user-configurable stability window separate from completion debounce
- Track stability over full visible state signature (readiness, completion, business, input, ui_context, projection_changed, blocked)
- Expose both raw and smoothed states for debugging vs operational views
- Use RxPY for composable, testable smoothing logic
- Zero overhead when disabled (window=0)

**Non-Goals:**
- Not changing parser semantics or `completion_stability_seconds` behavior
- Not eliminating raw flicker (some is expected from periodic sampling)
- Not replacing existing state machine logic in `AgentStateTracker`
- Not adding stability to non-shadow parsing modes

## Decisions

### Decision 1: RxPY operator pattern over imperative smoothing

**Choice:** Implement stability as an RxPY operator that transforms `Observable[AgentDashboardState] → Observable[SmoothedDashboardState]`.

**Rationale:**
- Composable: can add debounce, throttle, or other operators without touching monitor
- Testable: pure function `StabilityWindowState.process()` with no I/O
- Observable: both raw and smoothed streams available for logging
- Familiar: RxPY already in deps, team knows reactive patterns

**Alternatives considered:**
- Imperative tracking in `AgentStateTracker`: couples stability to state machine, harder to test
- Post-processing NDJSON logs: too late for live dashboard

### Decision 2: State signature for stability = visible operator fields

**Choice:** Stability signature = `(readiness_state, completion_state, business_state, input_mode, ui_context, projection_changed, bool(operator_blocked_excerpt))`.

**Rationale:**
- These are the fields operators see and care about
- Excludes parser metadata (preset_id, anomaly_codes) that change without affecting operator view
- Excludes dialog_tail (too noisy, changes every keystroke)
- Matches `transition_signature()` concept but focused on operator-visible state

**Alternatives considered:**
- Use full `transition_signature()`: includes anomaly_codes which flicker on transient parser warnings
- Use only readiness+completion: too coarse, misses business_state transitions

### Decision 3: Separate stability window from completion debounce

**Choice:** Add `state_stability_window_seconds` as distinct from `completion_stability_seconds`.

**Rationale:**
- Completion debounce has specific semantics: "candidate_complete stayed quiet long enough"
- Stability window is broader: "whatever the current state is, it stopped changing"
- Operators may want different policies (e.g., 1s completion, 10s stability)
- Keeps existing completion logic unchanged (non-breaking)

**Alternatives considered:**
- Unify into one timer: breaks existing completion semantics, confuses two concerns

### Decision 4: Minimal integration into monitor loop

**Choice:** Keep imperative polling loop, wrap state stream in RxPY only for smoothing.

**Rationale:**
- Existing loop is simple and works
- Full reactive rewrite is high risk for marginal benefit
- Hybrid approach: imperative fetch, reactive transform, imperative render

**Implementation:**
```python
raw_stream = rx.interval(poll_interval).pipe(ops.map(fetch_states))
smoothed = raw_stream.pipe(apply_stability_window(window_seconds))
smoothed.subscribe(render_dashboard)
```

## Risks / Trade-offs

**Risk:** RxPY adds complexity for simple use case
→ Mitigation: Stability operator is <100 LOC, well-tested, optional (window=0 disables)

**Risk:** Time-based stability may not match operator intuition
→ Mitigation: Configurable window lets operators tune; default=0 preserves current behavior

**Risk:** Smoothed state lags raw state by up to window duration
→ Mitigation: Dashboard shows both raw and smoothed when window>0; operators choose view

**Trade-off:** Stability metadata increases NDJSON log size
→ Acceptable: logs are for debugging, disk is cheap, can filter in post-processing

## Migration Plan

1. Add models (`StabilityMetadata`, `SmoothedDashboardState`) to `models.py`
2. Implement `stability_operator.py` with unit tests
3. Add `state_stability_window_seconds` to `DualShadowWatchDemoState` with default=0
4. Integrate RxPY stream into `monitor.py` (conditional on window>0)
5. Add CLI flag to `driver.py`
6. Update dashboard rendering to show stability when enabled

Rollback: Remove CLI flag, revert to imperative loop. No data migration needed (new field has default).

## Open Questions

None. Design is ready for implementation.
