## Context

The `_TurnMonitor` class in `cao_rest.py` (lines 332–537) is the stateful lifecycle tracker for CAO shadow-only sessions. It drives two polling loops — `_wait_for_shadow_ready_status()` (readiness) and `_wait_for_shadow_completion()` (completion) — by accumulating 8 mutable fields and making irrevocable lifecycle decisions from single-sample observations and manual timestamp arithmetic.

Three interrelated problems (documented in issue-002) stem from this design:

- **A. Single-sample completion**: One `idle` snapshot after any `working` snapshot immediately triggers completion. No debounce or stability window. Transient idle flickers (e.g., tool approval that resolves instantly) cause false completion.
- **B. Wall-clock stall timing**: `m_unknown_started_at` / `m_stalled_started_at` measure wall-clock elapsed time, not observation count. If polls slow down (slow CAO, network), the stall timer fires after fewer actual observations than intended.
- **C. Projection-based diffing**: Completion compares `dialog_projection.dialog_text != baseline`. The projector is best-effort and drops banners/spinners/separators. If projector drop rules change across presets, the diff behavior changes, flipping `m_saw_projection_change_after_submit` differently across versions.

Issue-007 recently added a 8th mutable field (`saw_post_submit_activity`) to decouple mailbox observer from generic completion, further expanding the imperative state surface.

The `reactivex` package (≥4.1.0) is already a project dependency but not yet imported in `cao_rest.py`.

## Goals / Non-Goals

**Goals:**

- Replace `_TurnMonitor` with two ReactiveX pipelines (readiness + completion) that make temporal semantics explicit via Rx operators.
- Require N seconds of stable idle before declaring completion (`ops.debounce`) instead of single-sample completion.
- Measure stall timeouts as inter-emission gaps (`ops.timeout`) instead of wall-clock timestamps, so slow polls naturally extend the wait.
- Decouple lifecycle decisions from projector drop rules by using `ops.distinct_until_changed(key=normalized_text)` instead of raw projection-text diffing.
- Express issue-007's decoupled mailbox observer as a stream operator (completion observer runs on every post-submit emission) rather than an imperative flag check.
- Enable deterministic time-based unit tests via `TestScheduler`.
- Preserve all existing external behavior: blocked-operator, unsupported-surface, disconnect, stall, and timeout error semantics remain unchanged from the caller's perspective.

**Non-Goals:**

- Changing the `ShadowOnlyTurnEngine.execute_turn()` synchronous call boundary — callers continue to block on turn results.
- Replacing the `ShadowParser` or `DialogProjection` subsystems — those remain as-is.
- Addressing issue-003 (signal classification), issue-004 (capability probe), or issue-005 (baseline invalidation) directly — though this work creates the Rx foundation they build on.
- Changing the CAO REST polling interval or adding adaptive polling.
- Modifying the two-axis surface priority order (that stays the same).

## Decisions

### D1: Two separate Rx pipelines, not one unified stream

**Choice**: Separate readiness pipeline and completion pipeline, each with its own observable chain.

**Rationale**: Readiness and completion have different terminal conditions, different state accumulation needs, and different timeout semantics. A single pipeline would require complex branching that defeats the clarity goal. The existing code already separates these into two functions — the Rx rewrite preserves that boundary.

**Alternative considered**: Single pipeline with phase-switching via `ops.group_by()`. Rejected because it adds complexity without benefit — the two phases never overlap within a turn.

### D2: `ops.debounce(stability_seconds)` for completion stability

**Choice**: After post-submit activity is observed, require `stability_seconds` of continuous idle (no state changes) before emitting a completion event. Each new change resets the timer.

**Rationale**: This directly fixes problem A. A transient idle flicker resets the debounce timer when the next `working` observation arrives. Only sustained idle survives the debounce window.

**Default**: `stability_seconds = 1.0` (configurable via shadow stall policy, same config surface as existing `unknown_to_stalled_timeout_seconds`).

### D3: `ops.timeout()` for stall detection on inter-emission gaps

**Choice**: Apply `ops.timeout(stall_seconds)` on the sub-stream of observations classified as unknown-for-stall. The timeout measures the gap between emissions, not wall-clock time from a start timestamp.

**Rationale**: This directly fixes problem B. If polls slow down, fewer emissions arrive, but the inter-emission gap stays proportional to the actual polling interval. The stall timer fires after the configured duration of *continuous unknown observations*, not after N wall-clock seconds that might contain only 2 actual polls.

### D4: `ops.distinct_until_changed(key=normalized_text)` for change detection

**Choice**: Replace raw `dialog_projection.dialog_text != baseline` comparison with `ops.distinct_until_changed()` keyed on a normalized text representation. Any emission through this operator means a change happened.

**Rationale**: This directly fixes problem C. The normalized key strips the same transient elements (banners, spinners) but does so at the stream level, decoupling the lifecycle decision from the specific projector preset's drop rules. The normalization function is owned by the pipeline, not by the projector.

**Alternative considered**: Semantic diffing (AST-level comparison of projected dialog). Rejected as over-engineered — normalized text comparison is sufficient and simpler.

### D5: `ops.scan()` for accumulating post-submit evidence

**Choice**: Use `ops.scan()` with an accumulator dataclass to track:
- whether `working` was observed after submit
- whether projection text changed after submit
- the baseline projection text (for re-baseline on recovery, addressing issue-005's direction)

**Rationale**: Replaces `m_saw_working_after_submit`, `m_saw_projection_change_after_submit`, `m_baseline_projection_text` with a single pure-function accumulator. The accumulator is a frozen dataclass — no mutable fields.

### D6: Mailbox observer as `ops.do_action()` / `ops.flat_map()` side-stream

**Choice**: The completion pipeline emits every post-submit observation to a side-stream that runs the `completion_observer` callable. If the observer returns a non-None payload, the pipeline completes immediately with that payload.

**Rationale**: Preserves issue-007's decoupled mailbox behavior but expresses it as a stream operator instead of an imperative `if monitor.saw_post_submit_activity()` check. The observer runs on every emission after activity is detected, exactly matching the current behavior.

### D7: `NewThreadScheduler` internally, synchronous boundary at call site

**Choice**: The Rx pipelines run on `NewThreadScheduler`. The call site (`_wait_for_shadow_ready_status` / `_wait_for_shadow_completion`) blocks on `observable.run()` to maintain the synchronous contract with `ShadowOnlyTurnEngine.execute_turn()`.

**Rationale**: Rx operators like `debounce` and `timeout` require a scheduler for time-based operations. `NewThreadScheduler` provides real-time scheduling. The synchronous boundary means no changes to the caller's threading model.

**Testing**: Unit tests use `TestScheduler` for deterministic virtual-time advancement, enabling precise testing of debounce windows, timeout thresholds, and race conditions without real sleeps.

### D8: Observation dataclass as pipeline input type

**Choice**: Define a `ShadowObservation` frozen dataclass that bundles `(output, snapshot, projection, timestamp)` as the element type flowing through the pipeline. The polling loop emits `ShadowObservation` instances into a `Subject`.

**Rationale**: Gives the pipeline a clean, typed input contract. The polling loop becomes a simple producer that pushes observations into the subject. All temporal logic lives in the pipeline operators, not in the polling loop.

## Risks / Trade-offs

**[Rx learning curve]** → The team needs familiarity with ReactiveX operators. Mitigated by: (a) the operator set is small and well-documented (`debounce`, `timeout`, `scan`, `distinct_until_changed`, `do_action`), (b) the pipeline topology is linear (no complex merges or forks), (c) comprehensive `TestScheduler` tests serve as executable documentation.

**[Debounce adds latency to completion]** → A 1-second debounce window means completion is detected ~1s later than the current single-sample approach. Mitigated by: (a) 1s is negligible relative to typical agent turn durations (10–120s), (b) the stability guarantee prevents false completions that currently cause harder-to-debug failures, (c) the debounce window is configurable.

**[Threading model complexity]** → `NewThreadScheduler` introduces a background thread for Rx scheduling. Mitigated by: (a) the thread is scoped to the pipeline lifetime, (b) the synchronous `run()` boundary ensures no concurrent access to shared state, (c) the existing code already uses `time.sleep()` in polling loops — the threading model is not fundamentally different.

**[Observation-gap timeout vs wall-clock timeout behavioral difference]** → Existing stall timeouts fire after N wall-clock seconds regardless of poll rate. The new inter-emission gap timeout fires after N seconds of *continuous unknown emissions*. If polls are very slow (e.g., 10s intervals), the effective wall-clock timeout is longer. This is intentionally correct behavior (more observations = more confidence) but changes the exact timing. Mitigated by: documenting the semantic change and keeping the default timeout value the same.

## Open Questions

- Should `stability_seconds` be a separate config field or derived from `unknown_to_stalled_timeout_seconds`? Leaning toward a separate field with a sensible default (1.0s).
- Should the normalized-text key function live in the pipeline module or alongside the projector? Leaning toward pipeline module since it's a lifecycle concern, not a projection concern.
