## 1. Add Stability Models

- [ ] 1.1 Add `StabilityMetadata` dataclass to models.py with is_stable, stable_for_seconds, stability_window_seconds, raw_state_signature, first_seen_at_monotonic, last_transition_at_monotonic fields
- [ ] 1.2 Add `SmoothedDashboardState` dataclass to models.py with raw_state, stability, smoothed_label fields and to_payload() method
- [ ] 1.3 Add `state_stability_window_seconds: float` field to `DualShadowWatchDemoState` with default value
- [ ] 1.4 Add `DEFAULT_STATE_STABILITY_WINDOW_SECONDS = 0.0` constant to models.py
- [ ] 1.5 Update `DualShadowWatchDemoState.from_payload()` to parse state_stability_window_seconds with default fallback

## 2. Implement RxPY Stability Operator

- [ ] 2.1 Create new file src/houmao/demo/cao_dual_shadow_watch/stability_operator.py
- [ ] 2.2 Implement _state_signature_for_stability() function extracting (readiness_state, completion_state, business_state, input_mode, ui_context, projection_changed, bool(operator_blocked_excerpt))
- [ ] 2.3 Implement _format_smoothed_label() function generating "<state> (stable/unstable)" labels
- [ ] 2.4 Implement StabilityWindowState class with window_seconds, current_signature, signature_first_seen_at, last_transition_at fields
- [ ] 2.5 Implement StabilityWindowState.process() method that detects signature changes, tracks duration, and returns SmoothedDashboardState
- [ ] 2.6 Implement apply_stability_window() RxPY operator factory
- [ ] 2.7 Implement emit_on_stability_change() RxPY operator for transition filtering

## 3. Integrate RxPY into Monitor

- [ ] 3.1 Add reactivex imports to monitor.py (rx, ops, NewThreadScheduler)
- [ ] 3.2 Add stability_operator imports to monitor.py
- [ ] 3.3 Add state_stability_window_seconds parameter to ShadowWatchMonitor.__init__()
- [ ] 3.4 Refactor monitor.run() to create raw state stream using rx.interval()
- [ ] 3.5 Add per-agent smoothed streams using apply_stability_window() operator
- [ ] 3.6 Subscribe to smoothed streams with emit_on_stability_change() for stability transition logging
- [ ] 3.7 Update dashboard rendering to use smoothed states when window > 0

## 4. Update Dashboard Display

- [ ] 4.1 Update _render_summary_table() to show stability columns when window > 0
- [ ] 4.2 Update _render_detail_panel() to display stability metadata (is_stable, stable_for_seconds, smoothed_label)
- [ ] 4.3 Update _render_transition_panel() header to show state_stability_window_seconds value
- [ ] 4.4 Add stability transition logging helper _log_stability_transition()

## 5. Add CLI Support

- [ ] 5.1 Add state_stability_window_seconds parameter to driver.start_demo()
- [ ] 5.2 Add --state-stability-window-seconds CLI argument to start_parser with type=float, default=DEFAULT_STATE_STABILITY_WINDOW_SECONDS
- [ ] 5.3 Add validation helper _require_non_negative() for stability window value
- [ ] 5.4 Pass state_stability_window_seconds to DualShadowWatchDemoState constructor
- [ ] 5.5 Update monitor command construction to include --state-stability-window-seconds argument
- [ ] 5.6 Update _start_or_inspect_payload() to include state_stability_window_seconds in output

## 6. Update Monitor Entrypoint

- [ ] 6.1 Add --state-stability-window-seconds argument to monitor.main() argparse
- [ ] 6.2 Pass state_stability_window_seconds from args to ShadowWatchMonitor constructor

## 7. Add Unit Tests

- [ ] 7.1 Create tests/unit/demo/cao_dual_shadow_watch/test_stability_operator.py
- [ ] 7.2 Add test_stability_window_immediate() for window=0 case
- [ ] 7.3 Add test_stability_window_requires_duration() for window>0 case
- [ ] 7.4 Add test_stability_resets_on_signature_change() for signature change behavior
- [ ] 7.5 Add test_state_signature_extraction() for _state_signature_for_stability()
- [ ] 7.6 Add test_smoothed_label_formatting() for _format_smoothed_label()

## 8. Documentation

- [ ] 8.1 Update scripts/demo/cao-dual-shadow-watch/run_demo.sh help text to document --state-stability-window-seconds flag
- [ ] 8.2 Add usage examples to demo README showing raw mode (window=0) vs operator mode (window=10)
