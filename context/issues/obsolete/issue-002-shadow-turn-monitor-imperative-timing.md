# Issue 002: _TurnMonitor Imperative Timing — Single-Sample Completion, Stall Fragility, Projection-Based Diffing

> Obsolete as of 2026-04-08.
> Moved from `context/issues/known/` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Priority
P1 — False completion on transient idle; stall false positives; projector changes break lifecycle decisions.

## Status
Fixed on `devel` via `openspec/changes/rx-shadow-turn-monitor`.

**Note (2026-03-19):** The same Rx timing model now also backs `houmao-server` tracked-state reduction via `openspec/changes/fix-houmao-server-rx-lifecycle-tracking`, which adds explicit lifecycle authority so background watch no longer claims submit-anchored completion without a server-owned turn anchor.

**Note (2026-03-18):** Issue-007's fix adds `saw_post_submit_activity()` to `_TurnMonitor` — one more mutable field in the hand-rolled state machine. The future Rx rewrite needs to incorporate "run mailbox observer on every post-submit emission" as a stream operator. This slightly expands the migration scope but further justifies the Rx approach.

## Review Reference
Code review sections: 2.2, 3.2, 3.3, 4.1, 4.3, 4.3.1

## Summary

The `_TurnMonitor` in `cao_rest.py` hand-rolls temporal logic via 7 mutable fields and manual timestamp arithmetic. This creates three interrelated problems:

### A. Single-sample completion (2.2)

A single snapshot showing `idle` after any `working` snapshot is immediately treated as completion. No debounce, no stability requirement. Transient idle flickers (e.g., during a tool approval that resolves instantly) trigger false completion.

### B. Polling interval / stall timeout disconnect (3.3)

The stall timer measures wall-clock time (`m_unknown_started_at`), not observation count. If polls slow down (slow CAO, network), the stall timer fires after fewer actual observations than intended.

### C. Projection-based diffing (3.2)

The completion check compares `dialog_projection.dialog_text != baseline`. This text is produced by a best-effort projector that drops banners, spinners, separators. If projector drop rules change across presets, the diff behavior changes, which can flip `m_saw_projection_change_after_submit` differently across versions.

## Root Cause

The state machine is memoryless about state *duration* and *stability*. It makes irrevocable decisions (completion) from single-sample observations, tracks timing via manual timestamps, and couples lifecycle decisions to a best-effort projection surface.

## Affected Code

- `src/houmao/agents/realm_controller/backends/cao_rest.py` — `_TurnMonitor` class (all 7 mutable fields, `observe_completion()`, `observe_readiness()`, `_observe_unknown()`, `_recover_if_stalled()`), `_wait_for_shadow_completion()`, `_wait_for_shadow_ready_status()`

## Fix Direction

Replace `_TurnMonitor` with two ReactiveX (`reactivex`) pipelines — one for readiness, one for completion. The `reactivex` package is already in the pixi environment.

**Key operator mappings:**

| Mutable field | Rx replacement |
|---|---|
| `m_state` | Pipeline terminal event type (completed / failed / stalled / blocked) |
| `m_unknown_started_at` | `ops.timeout()` on unknown-filtered sub-stream |
| `m_stalled_started_at` | `ops.debounce()` on unknown-filtered sub-stream |
| `m_saw_working_after_submit` | `ops.scan()` accumulator flag |
| `m_saw_projection_change_after_submit` | `ops.distinct_until_changed()` — any emission = change happened |
| `m_baseline_projection_text` | `ops.scan()` accumulator baseline, or pipeline seed |
| `m_anomalies` | `ops.do_action()` appending to a diagnostic list (side effect, not decision) |

**Core semantic:** `ops.debounce(stability_seconds)` implements "TUI changed → wait for N seconds of quiet, reset timer on each new change, only emit after the full quiet period." This replaces single-sample completion with a stability requirement.

**Additional benefits:**
- No sliding window or ring buffer needed — Rx operators carry temporal state internally
- `ops.distinct_until_changed(key=normalized_text)` replaces projection-based diffing with normalized-text diffing (4.5), decoupling lifecycle from projector behavior
- `ops.timeout()` measures inter-emission gaps, not wall clock, so slow polls naturally extend the wait
- `TestScheduler` enables deterministic time-based unit tests

**Threading model:** Keep synchronous boundary at `ShadowOnlyTurnEngine.execute_turn()`. Use `NewThreadScheduler` internally, block on `observable.run()` at the call site.

## Connections

- Prerequisite for issue-004 (capability probe uses the same Rx readiness pipeline)
- Subsumes issue-005's baseline invalidation recovery via `ops.scan()` re-baseline
- Enables the Rx stall watchdog that replaces `_observe_unknown()` + `_recover_if_stalled()`
