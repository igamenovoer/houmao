## 1. Foundation types and pipeline module

- [x] 1.1 Create `src/houmao/agents/realm_controller/backends/cao_rx_monitor.py` with `ShadowObservation` frozen dataclass bundling `(output, snapshot, projection, monotonic_ts)`
- [x] 1.2 Define `PostSubmitEvidence` frozen dataclass accumulator for `ops.scan()` (saw_working, saw_projection_change, baseline_normalized_text)
- [x] 1.3 Define `PipelineResult` union type covering completion, blocked, failed, stalled, and timed-out terminal outcomes
- [x] 1.4 Add `normalize_projection_text(text: str) -> str` function for `DialogProjection.normalized_text` keying in `distinct_until_changed`

## 2. Readiness pipeline

- [x] 2.1 Implement `build_readiness_pipeline(subject, *, stall_timeout_seconds, scheduler) -> Observable[PipelineResult]` that classifies each observation and applies the readiness priority order (unsupported/disconnected → blocked → unknown/stalled → waiting/ready) using Rx operators
- [x] 2.2 Derive unknown/stalled timing from the full classified-state stream so any known observation cancels the pending stall timeout while continuous unknown observations still trigger inter-emission-gap stall detection
- [x] 2.3 Emit `stalled_entered` / `stalled_recovered` anomaly codes via `ops.do_action()` matching existing anomaly contract

## 3. Completion pipeline

- [x] 3.1 Implement `build_completion_pipeline(subject, *, stability_seconds, stall_timeout_seconds, baseline_projection, completion_observer, scheduler) -> Observable[PipelineResult]` that classifies each observation and applies the completion priority order using Rx operators
- [x] 3.2 Wire `ops.scan()` with `PostSubmitEvidence` accumulator to track post-submit working and normalized-text-change evidence
- [x] 3.3 Wire `ops.distinct_until_changed(key=normalize_projection_text)` on `DialogProjection.normalized_text` for lifecycle change detection decoupled from projector drop rules
- [x] 3.4 Drive completion stability from the full classified-state stream so any non-idle emission or normalized-text change resets the pending debounce window
- [x] 3.5 Wire mailbox `completion_observer` as a side-stream operator that completes immediately on non-None payload, bypassing the stability window

## 4. Integration into cao_rest.py

- [x] 4.1 Replace `_TurnMonitor` class with imports from `cao_rx_monitor` — remove the 8 mutable fields and all `_TurnMonitor` methods
- [x] 4.2 Rewrite `_wait_for_shadow_ready_status()` to subscribe once to the readiness pipeline, push `ShadowObservation` from the current-thread polling loop into a `Subject`, and stop when a callback/result-holder receives a terminal result
- [x] 4.3 Rewrite `_wait_for_shadow_completion()` to subscribe once to the completion pipeline, push `ShadowObservation` from the current-thread polling loop into a `Subject`, and stop when a callback/result-holder receives a terminal result
- [x] 4.4 Extend `src/houmao/agents/realm_controller/launch_plan.py` shadow-policy extraction/storage to carry `completion_stability_seconds`
- [x] 4.5 Extend `_ShadowStallPolicy` resolution/validation in `cao_rest.py` to default and validate `completion_stability_seconds`
- [x] 4.6 Add `completion_stability_seconds` to runtime diagnostics and serialized shadow metadata payloads alongside existing policy fields
- [x] 4.7 Preserve existing `BackendExecutionError` raise sites for blocked-operator, unsupported-surface, disconnect, stall, and timeout — map `PipelineResult` variants to the same error messages

## 5. Tests

- [x] 5.1 Add `tests/unit/agents/realm_controller/test_cao_rx_monitor.py` with `TestScheduler`-based tests for the readiness pipeline: unknown→stalled transition, stalled recovery, blocked-operator, unsupported/disconnected fail, normal ready
- [x] 5.2 Add `TestScheduler`-based tests for the completion pipeline: debounce stability (transient idle flicker does not complete, sustained idle completes), projection-change resets debounce, working-after-submit evidence tracking
- [x] 5.3 Add `TestScheduler`-based test verifying mailbox observer bypasses stability window on definitive result
- [x] 5.4 Add `TestScheduler`-based test verifying slow-poll stall timeout scales with inter-emission gaps
- [x] 5.5 Add launch-plan/backend policy tests for `completion_stability_seconds` extraction, validation, and diagnostics serialization
- [x] 5.6 Update existing shadow tests in `test_cao_client_and_profile.py` that depend on `_TurnMonitor` internals to work with the new Rx-based implementation
- [x] 5.7 Migrate the behavioral scenarios from `tests/unit/agents/realm_controller/test_cao_shadow_turn_monitor.py` into the new Rx-based test suite and delete the old file
- [ ] 5.8 Run full `pixi run test-runtime` suite and verify no regressions

## 6. Cleanup

- [x] 6.1 Remove `_TurnMonitor`, `_TurnMonitorPhase`, `_TurnMonitorState` type definitions from `cao_rest.py`
- [x] 6.2 Update issue-002 status to "Fixed on `devel`" and cross-reference this change
- [ ] 6.3 Run `pixi run format && pixi run lint && pixi run typecheck` and fix any issues
