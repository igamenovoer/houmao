# CAO Rx Monitor Analysis — Complete Documentation

## Overview

This analysis answers whether the CAO Rx monitor's timing logic can be extracted into a **shared lifecycle kernel** that works for both the CAO REST backend and the server's TUI tracking system.

**Answer: ✅ YES, with HIGH confidence (8/10).** No fundamental architectural barriers exist. The core logic is already decoupled from RxPy and CAO-specific concepts.

---

## Documents in This Analysis

### 1. **CAO_RX_MONITOR_SUMMARY.md** — Start Here (12 KB, 202 lines)
**Quick reference with one-line answers to all key questions.**

- ✅ Is extraction feasible? YES (8/10 confidence)
- ❌ Is it tightly coupled to CAO? NO
- ✅ Scheduler injection level? FULLY INJECTABLE
- ✅ API adaptability? MINIMAL CHANGES NEEDED
- Semantic mapping table (CAO Rx ↔ Server Tracker)
- Implementation roadmap (1 week estimate)
- What CAN/SHOULD be shared (7 functions)

**Read this if:** You want answers fast and overview before diving deep.

---

### 2. **CAO_RX_MONITOR_ANALYSIS.md** — Complete Technical Analysis (24 KB, 671 lines)

Comprehensive breakdown of:

**Section 1: Core Architecture & API**
- `ShadowObservation` input type (with all fields)
- `PipelineResult` output types (6 variants: ReadyResult, CompletedResult, BlockedResult, FailedResult, StalledResult, TimedOutResult)
- `build_readiness_pipeline()` and `build_completion_pipeline()` signatures
- Scheduler injection pattern with code examples

**Section 2: Operator Usage**
- All 8 ReactiveX operators used in cao_rx_monitor
- Coupling analysis for each (NONE found — all generic)

**Section 3: Test Coverage**
- Readiness pipeline tests (7 scenarios covered)
- Completion pipeline tests (4 scenarios covered)
- Test infrastructure patterns (TestScheduler, observation factories)

**Section 4: Server Tracking.py**
- Input format (SurfaceObservation with 9 fields)
- Output format (SurfaceReduction with readiness/completion state + timing)
- Completion state transitions (in_progress → candidate_complete → completed)
- Baseline capture and turn anchoring

**Section 5: Compatibility Analysis**
- Semantic mapping (ReadyResult ↔ readiness_state=="ready", etc.)
- Type mismatches (ProjectionDialogue vs string — trivial adapter)
- Key differences in usage patterns (RxPy vs threading)

**Section 6: Feasibility Assessment**
- What CAN be shared (timing logic, reducers, classifiers)
- What CANNOT be shared (RxPy specifics, threading primitives)
- Proposed 3-layer architecture
- Minimum viable extraction

**Section 7-10: Detailed Findings**
- Coupling analysis
- Risks & mitigations
- Code snippets for reference

**Read this if:** You need comprehensive technical documentation and detailed rationale.

---

### 3. **CAO_RX_EXTRACTION_EXAMPLES.md** — Concrete Implementation Guide (29 KB, 815 lines)

**Working code examples showing exactly what would be extracted/adapted.**

**Part 1: Shared Kernel** (~300 LOC)
```python
# houmao/agents/realm_controller/backends/shared_lifecycle_kernel.py

@dataclass(frozen=True)
class LifecycleObservation:
    """Generic lifecycle observation (no CAO dependencies)."""
    availability: str
    business_state: str
    input_mode: str
    projection_text: str
    monotonic_ts: float

def reduce_readiness(...) -> tuple[_ReadinessPipelineState, ReadinessResult | None]:
    """Pure reducer — no side effects, fully testable."""

def reduce_completion(...) -> tuple[_CompletionPipelineState, CompletionResult | None]:
    """Pure reducer — handles all timing logic."""
```

**Part 2: RxPy Adapter** (~100 LOC)
```python
# cao_rx_monitor.py imports from shared_lifecycle_kernel
# Wraps pure logic in Observable pipeline
```

**Part 3: Server Adapter** (~50 LOC)
```python
# tracking.py imports from shared_lifecycle_kernel
# Calls pure reducer directly in polling loop
```

**Part 4: Unit Tests** (~50 LOC)
```python
# Pure function tests (no scheduler mocking needed)
def test_reduce_readiness_unknown_to_stalled():
    """Test deterministically without RxPy."""
```

**Read this if:** You're ready to implement and need working code templates.

---

## Key Findings Summary

### Architecture Quality
| Aspect | Status | Evidence |
|--------|--------|----------|
| **Scheduler decoupling** | ✅ Perfect | All timers use `reactivex.timer()` with injected scheduler |
| **CAO decoupling** | ✅ Perfect | Classification/reduction only depend on generic surface semantics |
| **RxPy decoupling** | ✅ Perfect | No RxPy imports in core logic (only `Observable[T]` type hints) |
| **Deterministic testing** | ✅ Proven | Tests use `TestScheduler` with deterministic results |
| **Code organization** | ⚠️ Good | Some duplication between cao_rx_monitor.py and tracking.py (fixable) |

### Semantic Alignment
- ✅ **Stall timeouts**: Both use 30s unknown→stalled (server: 30s, CAO: configurable)
- ✅ **Stability windows**: Both use completion_stability_seconds (server: 1-2s, CAO: 1s)
- ✅ **Evidence flags**: Both track saw_working + saw_projection_change
- ✅ **State transitions**: Identical logic in both
- ✅ **Baseline handling**: Identical turn-relative baseline concept

### Type Compatibility
| Type | CAO Rx | Server | Adaptation |
|------|--------|--------|-----------|
| Observation | `ShadowObservation` | `SurfaceObservation` | Wrapping 1:1 |
| Projection | `DialogProjection` (object) | `str` (text) | Extract `normalized_text` |
| Output | `CaoTerminalOutputResponse` | Already aggregated | Not needed for kernel |
| Results | 6 typed variants | String literals | Map via `kind` field |

---

## Implementation Roadmap

### Phase 1: Extract Core (2-3 days)
1. Create `shared_lifecycle_kernel.py`
2. Move 7 core functions + 2 state types
3. Remove RxPy/CAO imports
4. Write pure function tests

### Phase 2: Adapt Server (1-2 days)
1. Refactor `_SurfaceStateReducer.observe()` to call kernel
2. Remove duplicated timing logic
3. Property-based testing (old vs new)

### Phase 3: Adapt CAO REST (1 day)
1. Update `build_readiness_pipeline()` to use kernel
2. Update `build_completion_pipeline()` to use kernel
3. Verify all existing tests pass

### Phase 4: Docs & Polish (1-2 days)
1. Update docstrings
2. Document adapter protocols
3. Benchmark before/after
4. Create migration guide for future consumers

**Total: ~1 week**

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Breaking CAO REST | High | Extract to separate module first; keep cao_rx_monitor.py unchanged during Phase 1 |
| Server tracker regression | High | Property-based testing with old vs new implementation side-by-side |
| Performance regression | Low | Core algorithms unchanged; benchmark to verify |
| Type system complexity | Medium | Use TypeAlias extensively; document protocols |

---

## What Should Be Done Next

1. **Review this analysis** (or summarize with your team)
2. **Agree on kernel API** (e.g., what LifecycleObservation fields are required)
3. **Spike Phase 1** (2 days: extract 2-3 core functions, verify tests pass)
4. **Full implementation** (remaining phases)
5. **Comprehensive testing** (property-based, benchmarking, stress)

---

## File References

**Core Files Analyzed:**
- `/data1/huangzhe/code/houmao/src/houmao/agents/realm_controller/backends/cao_rx_monitor.py` (993 LOC)
- `/data1/huangzhe/code/houmao/tests/unit/agents/realm_controller/test_cao_rx_monitor.py` (571 LOC)
- `/data1/huangzhe/code/houmao/src/houmao/server/tui/tracking.py` (745 LOC)
- `/data1/huangzhe/code/houmao/src/houmao/server/service.py` (863 LOC)
- `/data1/huangzhe/code/houmao/src/houmao/server/models.py` (340 LOC, excerpt)

**Analysis Documents:**
- `CAO_RX_MONITOR_SUMMARY.md` — Start here for quick answers
- `CAO_RX_MONITOR_ANALYSIS.md` — Comprehensive technical analysis
- `CAO_RX_EXTRACTION_EXAMPLES.md` — Working code templates

---

## Questions This Analysis Answers

1. ✅ **What is the CAO Rx monitor's public API?**
   → 2 pipeline functions, 6 result types, 1 observation type, configurable parameters for scheduler/timeouts

2. ✅ **How are observations ingested?**
   → `Observable[ShadowObservation]` → continuous stream with monotonic_ts

3. ✅ **What does it emit?**
   → `Observable[PipelineResult]` → ReadyResult, CompletedResult, etc. with anomalies

4. ✅ **How is the scheduler injectable?**
   → All timers use `reactivex.timer(duration, scheduler=scheduler)`

5. ✅ **Is it tightly coupled to CAO-specific concepts?**
   → NO — classification/reduction logic is domain-agnostic

6. ✅ **What ReactiveX operators are used?**
   → 8 operators; all generic (map, scan, filter, switch_latest, merge, timer, distinct_until_changed, share)

7. ✅ **Are the server tracker and cao_rx_monitor semantically compatible?**
   → YES — 1:1 mapping for all key concepts (stall timeout, stability window, baseline, evidence)

8. ✅ **What would a shared kernel look like?**
   → Pure reducer functions: reduce_readiness(), reduce_completion(), classify_readiness(), etc.

9. ✅ **What would need to be adapted?**
   → Observation type (ProjectionDialogue → string), result type (domain-specific → generic)

10. ✅ **Is extraction feasible?**
    → ✅ YES — HIGH confidence (8/10). No fundamental barriers. Estimated 1 week work.

---

## Quick Decision Matrix

| Decision | If Approved | Next Step |
|----------|------------|-----------|
| Extract shared kernel? | ✅ Proceed to Phase 1 spike | Create `shared_lifecycle_kernel.py` module |
| Keep RxPy in cao_rx_monitor? | ✅ Yes, it's the right abstraction | No changes needed |
| Break up cao_rx_monitor.py? | ✅ Yes, split into adapter + kernel import | Refactor imports |
| Update server tracker? | ✅ Yes, remove duplication | Phase 2 of roadmap |
| Create new tests? | ✅ Yes, pure function unit tests | Add to test suite |
| Benchmark impact? | ✅ Yes, before/after performance | Use existing load tests |

---

## Additional Context

This analysis was performed through:
1. Complete read of cao_rx_monitor.py (993 LOC) + test file (571 LOC)
2. Analysis of server tracking.py (745 LOC) + service.py (863 LOC)
3. Cross-reference of observation types and completion triggers
4. Semantic mapping of state transitions
5. Scheduler injection patterns examination
6. RxPy operator inventory and coupling analysis

All findings are based on direct code inspection with no assumptions.

