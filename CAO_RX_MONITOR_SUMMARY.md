# CAO Rx Monitor: Quick Reference Summary

## What You Asked For

1. ✅ Complete read of `cao_rx_monitor.py` with all public classes, signatures, I/O types, scheduler injection, coupling analysis, and RxPy operators
2. ✅ Test file analysis (`test_cao_rx_monitor.py`) covering scenarios, scheduler injection patterns, and test observation patterns  
3. ✅ Server `tracking.py` analysis: observation format, output format, compatibility with cao_rx_monitor, completion triggers, baseline/turn anchoring
4. ✅ Server models and lifecycle enums in `models.py`
5. ✅ Server/service integration in `service.py`
6. ✅ Feasibility assessment of extracting a shared Rx lifecycle kernel

## One-Line Answers

| Question | Answer |
|----------|--------|
| **Is extraction feasible?** | ✅ **YES** — Confidence: HIGH (8/10). Core logic is already decoupled from RxPy and CAO specifics. |
| **Tight coupling to CAO?** | ❌ **NO** — Classification, reduction, and timing are domain-agnostic. Only surface semantics matter. |
| **Scheduler decoupling?** | ✅ **FULLY INJECTABLE** — All timers use `reactivex.timer()` with injected scheduler. Tests use `TestScheduler`. |
| **API adaptability?** | ✅ **MINIMAL CHANGES NEEDED** — Observation/result types map 1:1 to server tracker semantics. |
| **Type mismatches?** | ⚠️ **MINOR** — ProjectionDialogue (object) vs. string projection, but trivial adapter possible. |
| **Completion semantics?** | ✅ **IDENTICAL** — Both use: saw_working, saw_projection_change, stability_window, baseline comparison. |
| **Stall timeout semantics?** | ✅ **IDENTICAL** — Both use: 30s unknown→stalled, timer resets on state change. |

## Key Technical Details

### Public API (cao_rx_monitor.py)

**Input:**
- `ShadowObservation`: observation + monotonic_ts + parser_family

**Output:**
- `ReadyResult` | `CompletedResult` | `BlockedResult` | `FailedResult` | `StalledResult` | `TimedOutResult`

**Pipeline Functions:**
```python
build_readiness_pipeline(source, stall_timeout_seconds, scheduler) → Observable[PipelineResult]
build_completion_pipeline(source, stability_seconds, stall_timeout_seconds, baseline_projection, 
                          completion_observer, scheduler) → Observable[PipelineResult]
```

**Scheduler Injection:** All timing via `reactivex.timer()` — fully injectable for deterministic tests.

### ReactiveX Operators Used

| Operator | Purpose | CAO-Coupling? |
|----------|---------|----------------|
| `map()` | Transform → classify → events | ❌ None |
| `scan()` | Accumulate state (reducer) | ❌ None |
| `filter()` | Discard nulls | ❌ None |
| `switch_latest()` | Cancel timer on state change | ❌ None |
| `merge()` | Combine observations + timers | ❌ None |
| `timer()` | Emit after N seconds | ❌ None |
| `distinct_until_changed()` | Detect signature changes | ❌ None (signature-based) |

**→ Zero CAO-specific operators.**

### Server Tracking.py Integration

**Observation flow:**
```
service.py (polling loop) 
  → tracker.record_cycle(parsed_surface, ...) 
  → _SurfaceStateReducer.observe(SurfaceObservation) 
  → returns SurfaceReduction with readiness_state + completion_state
```

**Completion state transitions:**
- `in_progress` → `candidate_complete` → `completed` (if stability window satisfied)
- Stability window: `completion_stability_seconds` (default 1-2s)
- Triggers: **saw_working** (true) + **saw_projection_change** (true) + **submit_ready** (true)

**Baseline & turn anchoring:**
- Captured via `parser_adapter.capture_baseline()` on first poll
- Stored as `baseline_pos` in tracker
- Used to detect projection changes (normalized text comparison)
- Frozen on `baseline_invalidated=true`

---

## Implementation Roadmap (Estimated 1 Week)

### Phase 1: Extract Core (2-3 days)
- Create `shared_lifecycle_kernel.py` with pure reducer functions
- Copy/adapt: `_classify_readiness()`, `_reduce_readiness_event()`, evidence accumulation
- No RxPy dependency in kernel
- Unit test with plain Python (no scheduler needed)

### Phase 2: Adapt Server (1-2 days)
- Refactor `_SurfaceStateReducer` to call kernel functions
- Remove duplicated timing logic
- Property-based testing (old vs. new)

### Phase 3: Adapter Interfaces (1 day)
- Document protocol requirements
- Show how CAO REST wraps kernel in Observable
- Show how server wraps kernel in synchronous reducer

### Phase 4: Docs & Finalization (1-2 days)
- Update docstrings
- Integration examples for new consumers
- Benchmark before/after

---

## What CAN Be Shared (7 Functions)

1. `_classify_readiness()` — Surface state → readiness classification
2. `_classify_completion_surface()` — Surface state → base completion classification
3. `_reduce_readiness_event()` — (state, event) → new state (stall/recovery)
4. `_reduce_completion_event()` — (state, event) → new state (stall/stability/completion)
5. Evidence accumulation (`saw_working`, `saw_projection_change`)
6. Signature-change detection (for stability window resets)
7. Baseline/frozen projection handling

## What Should Remain Separate

1. **RxPy pipeline builders** — Observable merging, timer emission, subscription
2. **Server-specific logic** — Thread locking, persistent state, recent transitions
3. **Domain adapters** — Converting `HoumaoParsedSurface` → observation, etc.

---

## Semantic Mapping: CAO Rx ↔ Server Tracker

| CAO Rx | Server | Match |
|--------|--------|-------|
| `ReadyResult` | `readiness_state == "ready"` | ✅ Exact |
| `CompletedResult` | `completion_state == "completed"` | ✅ Exact |
| `BlockedResult` | `readiness_state == "blocked"` | ✅ Exact |
| `FailedResult` | `completion_state == "failed"` | ✅ Exact |
| `StalledResult` | `{readiness,completion}_state == "stalled"` | ✅ Exact |
| Stall timeout | `unknown_to_stalled_timeout_seconds` | ✅ Same |
| Stability window | `completion_stability_seconds` | ✅ Same |
| Baseline | `baseline_projection` | ✅ Same concept |
| Mailbox observer | `completion_observer` | ✅ Protocol match |

**→ 1:1 semantic alignment. No fundamental mismatches.**

---

## Why It's Feasible

1. **Decoupled from RxPy** — Core logic is pure functions with scheduler injection
2. **Decoupled from CAO** — Classification logic only cares about surface semantics (availability, business_state, input_mode)
3. **Decoupled from domain objects** — Works on generic observations (string availability, string business_state, etc.)
4. **Already proven in 2 contexts** — CAO REST uses RxPy, server uses threading. Both work.
5. **Semantically identical** — Both use same stall timeout, same stability window, same evidence flags
6. **Minimal type impedance** — Only adaptation needed: ProjectionDialogue object ↔ string

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Breaking CAO REST | High | Extract to separate module first; keep cao_rx_monitor.py unchanged initially |
| Server tracker behavior change | High | Property-based testing with old vs. new side-by-side |
| Performance regression | Low | Core algorithms unchanged; benchmark before/after |
| Type system complexity | Medium | Use TypeAlias; document protocols clearly |

---

## Files Modified (Estimated)

| File | Changes | LOC Impact |
|------|---------|-----------|
| NEW: `shared_lifecycle_kernel.py` | New module with 7 core functions | +200 |
| `cao_rx_monitor.py` | Import from kernel; keep pipeline builders | -100 (net) |
| `tracking.py` | Import from kernel; remove duplication | -80 (net) |
| `test_cao_rx_monitor.py` | No changes (uses public API) | 0 |
| `test_tracking.py` | Expand coverage for kernel functions | +50 |

**Total refactoring: ~150 LOC net reduction**

---

## Confidence Assessment

**HIGH CONFIDENCE** that extraction is feasible and low-risk.

**Why?**
- Architecture already separates concerns well
- RxPy is a thin adapter layer over pure logic
- Both consumers (CAO REST + server) already demonstrate the pattern works
- Test infrastructure is robust (TestScheduler proves it)
- No redesign needed — just reorganization

**What makes it NOT 10/10?**
- Projection type mismatch requires adapter (trivial but needs validation)
- Server tracker has stateful history tracking we haven't fully analyzed
- Performance impact of any additional indirection (likely negligible)

---

## Next Steps (If Approved)

1. **Review this analysis** — Confirm assessment aligns with your intent
2. **Spike Phase 1** — Extract 2-3 core functions; verify tests pass
3. **Design kernel API** — Define clean interface for both consumers
4. **Implement full extraction** — 1 week timeline
5. **Validate** — Property-based testing, benchmarking, stress tests

