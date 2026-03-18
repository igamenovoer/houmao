## Why

The `_TurnMonitor` in `cao_rest.py` hand-rolls temporal logic via 8 mutable fields and manual timestamp arithmetic. This creates three interrelated reliability problems: (A) single-sample completion — a single `idle` snapshot after any `working` snapshot triggers immediate completion without debounce, causing false completions on transient idle flickers; (B) polling-interval/stall-timeout disconnect — stall timers measure wall-clock time, not observation count, so slow polls fire the stall timer after fewer observations than intended; (C) projection-based diffing — completion decisions are coupled to a best-effort projector whose drop rules vary across presets, making lifecycle behavior version-dependent. Issue-007's recent fix added yet another mutable field (`saw_post_submit_activity`), further expanding the imperative state surface. Replacing this with ReactiveX pipelines (already a project dependency) will make temporal semantics explicit, testable, and decoupled from projection internals.

## What Changes

- Replace `_TurnMonitor` class with two ReactiveX pipelines — one for readiness monitoring, one for completion monitoring.
- Replace single-sample completion with `ops.debounce(stability_seconds)` — require N seconds of stable idle before declaring completion.
- Replace wall-clock stall timing with `ops.timeout()` on inter-emission gaps — slow polls naturally extend the wait.
- Replace projection-text diffing with `ops.distinct_until_changed(key=normalized_text)` — decouple lifecycle from projector drop-rule changes.
- Replace manual mutable fields (`m_saw_working_after_submit`, `m_saw_projection_change_after_submit`, `m_unknown_started_at`, `m_stalled_started_at`, `m_baseline_projection_text`) with Rx operator internal state (`ops.scan()`, `ops.debounce()`, `ops.timeout()`).
- Preserve issue-007's decoupled mailbox observer behavior: completion observer runs on every post-submit emission independent of generic shadow lifecycle, expressed as a stream operator rather than an imperative flag check.
- Keep synchronous boundary at `ShadowOnlyTurnEngine.execute_turn()` — use `NewThreadScheduler` internally, block on `observable.run()` at the call site.
- Existing blocked-operator, unsupported-surface, disconnect, stall, and timeout error behavior remains unchanged from the caller's perspective.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `brain-launch-runtime`: Shadow completion monitoring gains debounce-based stability requirement instead of single-sample completion; stall detection becomes observation-gap-based instead of wall-clock-based; mailbox observer integration expressed as stream operator.

## Impact

- `src/houmao/agents/realm_controller/backends/cao_rest.py` — `_TurnMonitor` class removed; `_wait_for_shadow_completion()` and `_wait_for_shadow_ready_status()` rewritten to drive Rx pipelines instead of imperative monitor.
- `tests/unit/agents/realm_controller/test_cao_client_and_profile.py` — Existing shadow tests updated; new `TestScheduler`-based deterministic timing tests added.
- Dependencies: `reactivex` (already in `pyproject.toml`, not yet imported in `cao_rest.py`).
- Subsumes issue-005's baseline invalidation recovery via `ops.scan()` re-baseline.
- Prerequisite for issue-004 (capability probe reuses the Rx readiness pipeline).
