## Why

The dual shadow-watch demo currently shows raw classified state streams from TUI snapshots, which is useful for parser debugging but creates noise for operators. When the parser or sampled TUI flickers between neighboring states (e.g., `processing -> idle -> processing`), operators must manually infer whether the stream has "settled enough" to be actionable. A user-visible stability window would let operators configure a policy like "treat state as stable if unchanged for 10 seconds," providing a calmer operational view while preserving raw evidence for debugging.

## What Changes

- Add `state_stability_window_seconds` configuration parameter to demo state and CLI
- Implement RxPY-based reactive smoothing layer that tracks state signature stability duration
- Extend dashboard state models with stability metadata (`is_stable`, `stable_for_seconds`, `smoothed_label`)
- Add stability indicators to Rich dashboard display (optional, based on window > 0)
- Emit both raw and smoothed state streams to NDJSON logs for debugging
- Keep existing `completion_stability_seconds` unchanged (separate concern)

## Capabilities

### New Capabilities
- `state-stability-tracking`: Track how long a visible state signature remains unchanged and mark it stable after a configurable window
- `rxpy-state-smoothing`: Apply reactive operators to raw state streams to produce smoothed output with stability metadata

### Modified Capabilities
<!-- No existing spec requirements are changing; this is purely additive -->

## Impact

- `src/houmao/demo/cao_dual_shadow_watch/models.py`: Add stability metadata models and demo state field
- `src/houmao/demo/cao_dual_shadow_watch/monitor.py`: Integrate RxPY smoothing into polling loop
- `src/houmao/demo/cao_dual_shadow_watch/driver.py`: Add CLI argument and pass to monitor
- New file: `src/houmao/demo/cao_dual_shadow_watch/stability_operator.py`: RxPY operators for stability windowing
- `scripts/demo/cao-dual-shadow-watch/run_demo.sh`: Support new CLI flag
- Tests: Unit tests for stability operator logic
