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
- Require N seconds of stable idle before declaring completion via the full classified-state stream instead of single-sample completion.
- Measure stall timeouts as inter-emission gaps on the full classified-state stream instead of wall-clock timestamps, so known observations cancel pending unknown timeouts and slow polls naturally extend the wait.
- Decouple lifecycle decisions from projector drop rules by keying change detection on `DialogProjection.normalized_text` with a pipeline-owned normalization helper instead of raw projection-text diffing.
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

### D2: Completion stability is driven from the full classified-state stream

**Choice**: After post-submit activity is observed, classify every completion observation first, then arm the stability window only for candidate-completion states. Any later non-idle observation or other state change on the full classified-state stream resets the pending completion timer.

**Rationale**: This directly fixes problem A without hiding recovery events behind a filtered submit-ready branch. A transient idle flicker is canceled when the next `working` or otherwise non-idle observation arrives. Only sustained idle survives the stability window.

**Default**: `completion_stability_seconds = 1.0` as a separate field on the existing `runtime.cao.shadow` policy surface.

### D3: Stall detection is driven from the full classified-state stream

**Choice**: Classify each readiness/completion observation first, then derive unknown/stalled timing from the full classified-state stream so any known observation cancels the pending unknown timeout. Rx time-based operators still implement the timeout behavior, but not on a filtered unknown-only branch.

**Rationale**: This directly fixes problem B while preserving the current recovery semantics. If polls slow down, fewer emissions arrive, but the inter-emission gap still tracks the actual polling interval. The stall timer fires only after a continuous unknown run and is reset as soon as the surface returns to a known state.

### D4: `ops.distinct_until_changed(key=normalized_text)` for change detection

**Choice**: Replace raw `dialog_projection.dialog_text != baseline` comparison with `ops.distinct_until_changed()` keyed on `DialogProjection.normalized_text` after a pipeline-owned `normalize_projection_text()` helper. Projector-derived `dialog_text` is not used as lifecycle evidence.

**Rationale**: This directly fixes problem C. `normalized_text` is the closer-to-source snapshot surface already documented by the parser contract, so using it keeps lifecycle behavior stable across projector preset changes. Any extra stripping rules remain explicit and testable inside the pipeline module instead of being inherited from projector drop rules.

**Alternative considered**: Semantic diffing (AST-level comparison of projected dialog). Rejected as over-engineered — normalized text comparison is sufficient and simpler.

### D5: `ops.scan()` for accumulating post-submit evidence

**Choice**: Use `ops.scan()` with an accumulator dataclass to track:
- whether `working` was observed after submit
- whether normalized shadow text changed after submit
- the baseline normalized shadow text (for future re-baseline/recovery follow-up)

**Rationale**: Replaces `m_saw_working_after_submit`, `m_saw_projection_change_after_submit`, `m_baseline_projection_text` with a single pure-function accumulator keyed to the chosen lifecycle evidence surface. The accumulator is a frozen dataclass — no mutable fields.

### D6: Mailbox observer as `ops.do_action()` / `ops.flat_map()` side-stream

**Choice**: The completion pipeline emits every post-submit observation to a side-stream that runs the `completion_observer` callable. If the observer returns a non-None payload, the pipeline completes immediately with that payload.

**Rationale**: Preserves issue-007's decoupled mailbox behavior but expresses it as a stream operator instead of an imperative `if monitor.saw_post_submit_activity()` check. The observer runs on every emission after activity is detected, exactly matching the current behavior.

### D7: Current-thread polling with callback-based result capture

**Choice**: `_wait_for_shadow_ready_status()` and `_wait_for_shadow_completion()` remain current-thread polling loops. Each wait function creates a `Subject`, subscribes once to the pipeline, pushes `ShadowObservation` values on every poll, and stops when a callback/result-holder captures a terminal `PipelineResult`. Time-based operators receive an injected scheduler; tests use `TestScheduler`.

**Rationale**: This preserves the synchronous contract without deadlocking the producer. The existing wait functions already own polling and error translation, so keeping them as the producer is the smallest architectural change. Rx still handles temporal logic, but the backend avoids adding a separate producer thread or blocking on `observable.run()`.

**Testing**: Unit tests use `TestScheduler` for deterministic virtual-time advancement, enabling precise testing of debounce windows, timeout thresholds, and race conditions without real sleeps. Runtime wiring passes a real-time scheduler without changing the current-thread polling ownership.

### D8: Observation dataclass as pipeline input type

**Choice**: Define a `ShadowObservation` frozen dataclass that bundles `(output, snapshot, projection, timestamp)` as the element type flowing through the pipeline. The current-thread polling loop emits `ShadowObservation` instances into a `Subject`.

**Rationale**: Gives the pipeline a clean, typed input contract. The polling loop becomes a simple producer that pushes observations into the subject. All temporal logic lives in the pipeline operators, not in the polling loop.

## Risks / Trade-offs

**[Rx learning curve]** → The team needs familiarity with ReactiveX operators. Mitigated by: (a) the operator set is small and well-documented (`debounce`, `timeout`, `scan`, `distinct_until_changed`, `do_action`), (b) the pipeline topology is linear (no complex merges or forks), (c) comprehensive `TestScheduler` tests serve as executable documentation.

**[Debounce adds latency to completion]** → A 1-second debounce window means completion is detected ~1s later than the current single-sample approach. Mitigated by: (a) 1s is negligible relative to typical agent turn durations (10–120s), (b) the stability guarantee prevents false completions that currently cause harder-to-debug failures, (c) the debounce window is configurable.

**[Subscription coordination complexity]** → The wait functions now need a small result-holder/callback bridge between the current-thread polling loop and the subscribed Rx pipeline. Mitigated by: (a) polling ownership stays where it already lives, (b) no dedicated producer thread is introduced, (c) error mapping remains in the existing wait functions.

**[Observation-gap timeout vs wall-clock timeout behavioral difference]** → Existing stall timeouts fire after N wall-clock seconds regardless of poll rate. The new inter-emission gap timeout fires after N seconds of *continuous unknown emissions*. If polls are very slow (e.g., 10s intervals), the effective wall-clock timeout is longer. This is intentionally correct behavior (more observations = more confidence) but changes the exact timing. Mitigated by: documenting the semantic change and keeping the default timeout value the same.
