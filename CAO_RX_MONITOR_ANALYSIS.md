# CAO Rx Monitor Analysis: Feasibility Assessment for Shared Lifecycle Kernel

## Executive Summary

The CAO Rx monitor is **architecturally sound and highly generalizable**. It can be extracted into a shared lifecycle timing kernel with minimal API adaptation. The core logic is already decoupled from CAO-specific concepts — it operates on generic surface observations and emit standardized state results. The main work lies in wrapping the existing APIs with adapter layers for different consumer contexts (realm-controller shadow operations vs. server tui tracking).

---

## 1. CAO Rx Monitor: Core Architecture & API

### 1.1 Public Classes & Signatures

**Input Type:**
```python
@dataclass(frozen=True)
class ShadowObservation:
    """One CAO shadow observation flowing through the monitor pipelines."""
    output: CaoTerminalOutputResponse
    snapshot: ParsedShadowSnapshot
    projection: DialogProjection
    monotonic_ts: float          # ← scheduler-relative timestamps
    parser_family: str
```

**Output Types (Result Variants):**
```python
PipelineResult: TypeAlias = (
    ReadyResult | CompletedResult | BlockedResult | FailedResult | StalledResult | TimedOutResult
)

@dataclass(frozen=True)
class ReadyResult:
    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    kind: Literal["ready"] = "ready"

@dataclass(frozen=True)
class CompletedResult:
    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    completion_payload: dict[str, object] | None = None  # ← mailbox observer output
    kind: Literal["completed"] = "completed"

@dataclass(frozen=True)
class BlockedResult:
    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    kind: Literal["blocked"] = "blocked"

@dataclass(frozen=True)
class FailedResult:
    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    kind: Literal["failed"] = "failed"

@dataclass(frozen=True)
class StalledResult:
    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    elapsed_unknown_seconds: float = 0.0
    elapsed_stalled_seconds: float | None = None
    kind: Literal["stalled"] = "stalled"

@dataclass(frozen=True)
class TimedOutResult:
    observation: ShadowObservation | None
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    shadow_status: str = "unknown"
    kind: Literal["timed_out"] = "timed_out"
```

### 1.2 Public Pipeline Functions

```python
def build_readiness_pipeline(
    source: Observable[ShadowObservation],
    *,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,  # ← Injected for deterministic testing
) -> Observable[PipelineResult]:
    """Build the readiness monitoring pipeline."""

def build_completion_pipeline(
    source: Observable[ShadowObservation],
    *,
    stability_seconds: float,
    stall_timeout_seconds: float,
    baseline_projection: DialogProjection,  # ← Turn-relative baseline
    completion_observer: CompletionObserver | None,  # ← Pluggable observer
    scheduler: abc.SchedulerBase,
) -> Observable[PipelineResult]:
    """Build the completion monitoring pipeline."""
```

**CompletionObserver Type:**
```python
CompletionObserver: TypeAlias = Callable[
    [str, ParsedShadowSnapshot, DialogProjection],
    dict[str, object] | None,
]
# Parameters:
#   raw_output_text: str
#   snapshot: ParsedShadowSnapshot
#   baseline_projection: DialogProjection
# Returns: completion payload dict or None if not triggered
```

### 1.3 Scheduler Injection Pattern

**Deterministic Testing:**
- Uses `HistoricalScheduler` from reactivex
- All timing logic is scheduler-driven (not wall-clock dependent)
- Tests inject `TestScheduler` with full control over virtual time
- `time.monotonic()` is captured at observation ingestion, not at pipeline decision points
- Stall/stability timers are implemented via `reactivex.timer()` which respects the injected scheduler

**Example from cao_rest.py (line 1013):**
```python
scheduler = HistoricalScheduler()
subscription = build_readiness_pipeline(
    observation_subject,
    stall_timeout_seconds=30.0,
    scheduler=scheduler,
).subscribe(on_next=_capture_result, on_error=_capture_error)

# During polling loop:
last_scheduler_monotonic = self._advance_shadow_scheduler(
    scheduler=scheduler,
    previous_monotonic=last_scheduler_monotonic,
    current_monotonic=now_monotonic,
)
```

---

## 2. Operator Usage: RxPy Components

**All ReactiveX operators used in cao_rx_monitor:**

| Operator | Purpose | Coupling |
|----------|---------|----------|
| `ops.map()` | Transform observations → classifications/events | None — generic transformation |
| `ops.share()` | Multicast to prevent re-execution | None — generic optimization |
| `ops.scan()` | Accumulate state (reducer pattern) | None — generic fold operation |
| `ops.filter()` | Discard null results | None — generic filtering |
| `ops.distinct_until_changed()` | Detect signature changes for stability reset | None — signature-based, not CAO-specific |
| `ops.switch_latest()` | Cancel previous timer when state changes | None — generic flow control |
| `reactivex.merge()` | Combine event streams (observations + timers) | None — generic merge |
| `reactivex.timer()` | Emit after N seconds on scheduler | None — pure timing, works on any scheduler |

**No CAO-specific operators used.** All timing/lifecycle logic is pure RxPy.

---

## 3. Test Coverage Analysis

**From `test_cao_rx_monitor.py`:**

### Readiness Pipeline Tests
1. **Modal vs operator-blocked distinction** (line 124)
   - Modal states don't emit → only blocked/ready emit
   
2. **Unknown → Stalled transition** (line 160)
   - 5.0s unknown timeout triggers `StalledResult`
   - Anomaly code: `ANOMALY_STALLED_ENTERED`
   
3. **Stalled recovery** (line 190)
   - Stalled → known state emits recovery anomaly
   - Anomaly code: `ANOMALY_STALLED_RECOVERED`
   
4. **Unsupported/disconnected surfaces** (line 228)
   - Emits `FailedResult` immediately
   
5. **Submit-ready classification** (line 252)
   - `idle` + `freeform` → `ReadyResult`
   
6. **Known state prevents stall** (line 275)
   - Known `business_state` with unknown `input_mode` ≠ stall
   
7. **Inter-emission gap scaling** (line 311)
   - Timeout restarts from last observation, not absolute

### Completion Pipeline Tests
1. **Transient idle flicker rejection** (line 349)
   - Brief return to idle doesn't trigger completion
   - Requires **2.0s stability** after post-submit activity
   
2. **Projection change resets stability** (line 412)
   - Changing output resets the stability timer
   
3. **Modal interim state waits for freeform** (line 465)
   - After working → modal → must return to freeform before completion
   
4. **Mailbox observer bypass** (line 519)
   - `completion_observer` callback can force completion immediately
   - Example: MAIL_RESULT marker in output

### Test Infrastructure
- **Scheduler injection:** `TestScheduler()` for deterministic time
- **Observation factory:** `_observation()` builder with sensible defaults
- **Emission pattern:** `scheduler.advance_to()` + `subject.on_next()`
- **Result verification:** Type-checking with `isinstance(result, ...)`

---

## 4. Server Tracking.py: Current State Model

### 4.1 Input Format (Server → Tracker)

**Via `LiveSessionTracker.record_cycle()`:**
```python
def record_cycle(
    self,
    *,
    identity: HoumaoTrackedSessionIdentity,
    observed_at_utc: str,
    monotonic_ts: float,
    transport_state: TransportState,       # "tmux_up" | "tmux_missing" | "probe_error"
    process_state: ProcessState,           # "tui_up" | "tui_down" | "unsupported_tool" | ...
    parse_status: ParseStatus,             # "parsed" | "parse_error" | "transport_unavailable" | ...
    probe_snapshot: HoumaoProbeSnapshot | None,
    probe_error: HoumaoErrorDetail | None,
    parse_error: HoumaoErrorDetail | None,
    parsed_surface: HoumaoParsedSurface | None,
) -> HoumaoTerminalStateResponse:
```

**Internal observation type (line 51-62):**
```python
@dataclass(frozen=True)
class SurfaceObservation:
    """Input observation for continuous parsed-surface reduction."""
    availability: str                    # "supported" | "unsupported" | "disconnected" | "unknown"
    business_state: str                  # "idle" | "working" | "awaiting_operator" | "unknown"
    input_mode: str                      # "freeform" | "modal" | "unknown"
    ui_context: str                      # "normal_prompt" | "slash_command" | "trust_prompt" | ...
    normalized_projection_text: str      # Normalized dialog/output
    operator_blocked_excerpt: str | None
    baseline_invalidated: bool
    monotonic_ts: float
    error_detail: str | None = None
```

### 4.2 Output Format (Tracker Emits)

```python
@dataclass(frozen=True)
class SurfaceReduction:
    """Derived readiness/completion state for one parsed surface cycle."""
    readiness_state: ReadinessState      # "ready" | "waiting" | "blocked" | "failed" | "unknown" | "stalled"
    completion_state: CompletionState    # "inactive" | "in_progress" | "candidate_complete" | "completed" | "waiting" | "blocked" | "failed" | "unknown" | "stalled"
    projection_changed: bool
    readiness_unknown_elapsed_seconds: float | None
    completion_unknown_elapsed_seconds: float | None
    completion_candidate_elapsed_seconds: float | None
```

**Public response:**
```python
class HoumaoTerminalStateResponse(_HoumaoModel):
    operator_state: HoumaoOperatorState  # status, readiness_state, completion_state, detail, projection_changed
    lifecycle_timing: HoumaoLifecycleTimingMetadata  # elapsed times
    stability: HoumaoStabilityMetadata   # signature, stable, stable_for_seconds
    recent_transitions: list[HoumaoRecentTransition]
```

### 4.3 Completion State Transitions (Server)

**Entry conditions for "completed" (tracking.py line 401):**
```python
if candidate_elapsed_seconds >= self.m_completion_stability_seconds:
    return "completed", None, candidate_elapsed_seconds, self.m_cycle_saw_projection_change
```

**Entry conditions for "candidate_complete" (line 410):**
```python
if was_submit_ready and (self.m_cycle_saw_working or self.m_cycle_saw_projection_change):
    # ... if stability window not reached yet
    return "candidate_complete", None, candidate_elapsed_seconds, ...
```

**Fields that trigger completed:**
- `saw_working`: Any observation with `business_state == "working"`
- `saw_projection_change`: Current projection differs from baseline
- `was_submit_ready`: `idle` + `freeform`
- **Stability window**: `completion_stability_seconds` (configurable, default ~1-2s)

### 4.4 Baseline & Turn Anchoring (Server)

**Baseline capture:**
```python
# service.py line 657-678
baseline_pos = self.m_parser_adapter.capture_baseline(
    tool=identity.tool,
    output_text=output_text,
)
tracker.set_baseline_pos(baseline_pos)
```

**Projection normalization:**
```python
# tracking.py line 339-340
effective_projection_key = (
    self.m_last_ready_projection_key or observation.normalized_projection_text
)
```

**Cycle baseline (line 343-350):**
```python
if observation.business_state == "working" and self.m_last_business_state != "working":
    self.m_cycle_baseline_projection_key = (
        self.m_last_ready_projection_key or observation.normalized_projection_text
    )
    self.m_cycle_frozen_projection_key = None
    self.m_cycle_saw_working = False
    self.m_cycle_saw_projection_change = False
```

---

## 5. Compatibility Analysis: CAO Rx Monitor vs. Server Tracker

### 5.1 Semantic Mapping

| CAO Rx Monitor | Server Tracker | Compatibility |
|---|---|---|
| `ShadowObservation` | `SurfaceObservation` | ✅ 1:1 conceptual mapping |
| `ReadyResult` | `readiness_state == "ready"` | ✅ Exact match |
| `CompletedResult` | `completion_state == "completed"` | ✅ Exact match |
| `BlockedResult` | `readiness_state == "blocked"` | ✅ Exact match |
| `FailedResult` | `completion_state == "failed"` | ✅ Exact match |
| `StalledResult` | `{readiness,completion}_state == "stalled"` | ✅ Exact match |
| Stall timeout | `unknown_to_stalled_timeout_seconds` | ✅ Same parameter |
| Stability window | `completion_stability_seconds` | ✅ Same parameter |
| Baseline projection | `baseline_projection` kwarg | ✅ Same concept |
| Mailbox observer | `completion_observer` callback | ✅ Protocol match |

### 5.2 Type Mismatches

**Input transformation required:**
```python
# CAO Rx Monitor expects:
ShadowObservation(
    output: CaoTerminalOutputResponse,      ← Server has string output text
    snapshot: ParsedShadowSnapshot,         ← Server has HoumaoParsedSurface
    projection: DialogProjection,           ← Server has normalized_projection_text (string)
    monotonic_ts: float,
    parser_family: str,
)

# Server has:
SurfaceObservation(
    availability: str,
    business_state: str,
    input_mode: str,
    ui_context: str,
    normalized_projection_text: str,      ← Not DialogProjection object
    operator_blocked_excerpt: str | None,
    baseline_invalidated: bool,
    monotonic_ts: float,
)
```

**Output transformation required:**
```python
# CAO Rx Monitor emits: PipelineResult (rich with anomalies, payloads)
# Server needs: CompletionState | ReadinessState (just Literal string)

# Adapter needed:
result.kind → readiness_state  # For readiness pipeline
result.kind → completion_state # For completion pipeline
```

### 5.3 Key Differences in Usage Patterns

| Aspect | CAO Rx Monitor | Server Tracker |
|---|---|---|
| **Scheduler** | Injected for all tests | Thread-based polling (no scheduler) |
| **Consumption** | RxPy subscription callback | Synchronous reducer calls |
| **Result cardinality** | Multiple emissions per observation | Single state per observation |
| **Baseline lifecycle** | Per-turn at pipeline start | Persistent across observations |
| **Projection format** | `DialogProjection` object (rich) | String only |
| **Anomalies** | Captured & returned | Not currently tracked |
| **Mailbox observer** | Optional completion bypass | N/A (mailbox not in server) |

---

## 6. Feasibility Assessment: Extracting a Shared Kernel

### 6.1 What CAN Be Shared

**A pure timing-logic kernel could handle:**
1. ✅ Unknown → stalled state transitions
2. ✅ Stability-window accumulation logic
3. ✅ Signature-change detection (for resets)
4. ✅ Evidence tracking (saw_working, saw_projection_change)
5. ✅ Post-submit activity classification
6. ✅ Projection baseline comparison
7. ✅ Frozen projection handling (baseline_invalidated)

**These are all deterministic functions of:**
- Current classification (ready/working/idle/unknown/etc.)
- Accumulated evidence flags
- Elapsed time in current state
- Signature changes

### 6.2 What CANNOT/SHOULD NOT Be Shared

**RxPy-specific logic** (realm-controller only):
- Timer creation via `reactivex.timer()`
- Observable merging and switching
- Subscription management
- Event stream filtering

**Server-specific logic** (tracking.py only):
- Thread-safe locking (`threading.RLock`)
- Persistent state across turns (streak counting, projection history)
- Recent transition recording
- Stability metadata hashing

### 6.3 Proposed Extraction Strategy

**3-Layer Architecture:**

```
Layer 1 (Shared Kernel)
└─ Pure reducer functions: (state, observation) → (state, result)
   - _classify_readiness()
   - _classify_completion()
   - _reduce_readiness_event()
   - _reduce_completion_event()
   - Projection normalization
   - Evidence accumulation
   - Stall/stability timing logic
   - Result classification
   ✅ Zero dependencies on RxPy or domain specifics
   ✅ Fully testable with plain Python

Layer 2 (RxPy Adapter - CAO REST)
└─ Observable pipeline builders
   - build_readiness_pipeline()
   - build_completion_pipeline()
   - Timer/event composition
   - Result emission
   ✅ Imports shared kernel functions
   ✅ Handles RxPy event flows

Layer 3 (Server Adapter - TUI Tracking)
└─ Synchronous wrapper
   - _SurfaceStateReducer (existing)
   - Calls shared kernel reducers directly
   - Thread-safe state management
   ✅ No RxPy dependency
   ✅ Plugs into polling loop
```

### 6.4 Minimum Viable Extraction

**Without major refactoring, could extract:**
1. All reducer functions (currently prefixed with `_reduce_*`)
2. All classification functions (currently prefixed with `_classify_*`)
3. Evidence accumulation logic
4. Anomaly building helpers

**Remaining in cao_rx_monitor.py:**
- Observable pipeline builders
- Timer emission functions
- Event type definitions

**Could move to new module `shared_lifecycle_kernel.py`:**
```python
# Shared types (no RxPy dependency)
@dataclass(frozen=True)
class LifecycleObservation:  # Generalized ShadowObservation
    classification: str  # readiness/completion state
    monotonic_ts: float
    availability: str
    business_state: str
    # ... other fields

@dataclass(frozen=True)
class LifecycleResult:  # Generalized PipelineResult
    kind: str  # "ready" | "completed" | etc.
    state: str
    elapsed_seconds: float | None
    anomalies: tuple[...] = ()

# Shared reducers (pure functions)
def reduce_readiness_event(
    state: LifecycleState,
    event: LifecycleEvent,
) -> LifecycleState:
    """Pure reducer, works in any context (RxPy, threading, async)."""

def classify_readiness(observation: LifecycleObservation) -> str:
    """Pure classifier, no side effects."""
```

---

## 7. Implementation Roadmap

### Phase 1: Extract Core Timing Logic (Low Risk)
1. Create `shared_lifecycle_kernel.py`
2. Copy reducer functions from cao_rx_monitor.py
3. Create generalized observation/result types
4. Remove dependency on `DialogProjection`, `CaoTerminalOutputResponse`, etc.
5. Write unit tests for pure functions (no scheduler needed)
6. Update cao_rx_monitor.py to import and use kernel functions

### Phase 2: Adapt Server Tracker (Parallel Work)
1. Refactor `_SurfaceStateReducer` to use kernel functions
2. Remove duplicated logic in tracking.py
3. Add comprehensive tests for determinism
4. Verify all existing server tests still pass

### Phase 3: Create Adapter Interfaces
1. Define abstract `LifecycleObserver` protocol
2. Implement CAO Rx adapter (wraps Observable emitters)
3. Implement server synchronous adapter
4. Document how to add new consumers (e.g., async frameworks)

### Phase 4: Documentation & Finalization
1. Update docstrings
2. Add integration examples
3. Create migration guide for future consumers
4. Benchmark: verify no performance regression

---

## 8. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Breaking CAO REST pipeline changes | High | Extract to shadow_kernel module first, keep cao_rx_monitor unchanged until Phase 1 complete |
| Server tracker behavior changes | High | Extensive property-based testing with old vs. new implementation |
| Scheduler abstraction issues | Medium | Keep TestScheduler for tests; only use HistoricalScheduler in production |
| Type system complexity | Medium | Use TypeAlias extensively; document protocol requirements clearly |
| Performance regression | Low | Benchmark before/after; shared kernel uses same algorithms |

---

## 9. Detailed Findings: Tight Coupling Analysis

### 9.1 NOT Tightly Coupled (Good News)

✅ **Classification logic is domain-agnostic:**
```python
# cao_rx_monitor.py line 464-497
def _classify_readiness(observation: ShadowObservation) -> _ReadinessClassification:
    surface_assessment = observation.snapshot.surface_assessment
    if surface_assessment.availability in {"unsupported", "disconnected"}:
        return _ReadinessClassification(..., status="failed", ...)
    if is_operator_blocked(surface_assessment):
        return _ReadinessClassification(..., status="blocked", ...)
    if is_unknown_for_stall(surface_assessment):
        return _ReadinessClassification(..., status="unknown", ...)
    # ...
```
→ Only references the surface semantics, not CAO specifics

✅ **Reducer is pure (no I/O, no side effects):**
```python
def _reduce_readiness_event(state: _ReadinessPipelineState, event: ReadinessEvent) -> _ReadinessPipelineState:
    """Reduce one readiness event into the current readiness state."""
```
→ Can be called from any thread/scheduler/context

✅ **Timer logic is scheduler-agnostic:**
```python
return reactivex.timer(_seconds(stall_timeout_seconds), scheduler=scheduler).pipe(...)
```
→ Works on TestScheduler, HistoricalScheduler, or wall-clock scheduler

### 9.2 LOOSELY Coupled (Expected)

⚠️ **Depends on surface-state semantics:**
- Must provide `availability` ∈ {supported, unsupported, disconnected, unknown}
- Must provide `business_state` (idle, working, awaiting_operator, unknown)
- Must provide `input_mode` (freeform, modal, unknown)
- These are intentionally generic and already used in server

⚠️ **Projection representation:**
- CAO Rx expects `DialogProjection` object
- Server has string projection text
- **Trivial adapter:** Convert string → DialogProjection with minimal fields

---

## 10. Final Recommendation

### ✅ **YES, Extraction is Highly Feasible**

**Confidence Level: HIGH (8/10)**

**Why:**
1. Core logic is already decoupled from RxPy and CAO specifics
2. Scheduler injection pattern is already proven in tests
3. Type system is well-structured with clear separation of concerns
4. Server tracker and CAO Rx monitor use identical timing semantics
5. No fundamental redesign required — just organizational refactoring

**Expected effort:**
- Phase 1 (extract kernel): 2-3 days
- Phase 2 (adapt server): 1-2 days
- Phase 3 (interfaces): 1 day
- Phase 4 (docs/tests): 1-2 days
- **Total: ~1 week for full extraction + testing**

**Risk level: LOW**
- Extraction can be done incrementally
- Old implementation can coexist during transition
- All logic changes can be validated with property-based tests

---

## Appendix: Code Snippets for Reference

### Test Scheduler Pattern
```python
# From test_cao_rx_monitor.py
scheduler = TestScheduler()
subject: Subject[ShadowObservation] = Subject()
results: list[object] = []
build_readiness_pipeline(
    subject,
    stall_timeout_seconds=5.0,
    scheduler=scheduler,
).subscribe(results.append)

# Advance time and emit
scheduler.advance_to(0.0)
subject.on_next(observation)
scheduler.advance_to(5.0)  # Timeout fires here
assert isinstance(results[-1], StalledResult)
```

### CAO REST Usage Pattern
```python
# From cao_rest.py line 1013
scheduler = HistoricalScheduler()
subscription = build_readiness_pipeline(
    observation_subject,
    stall_timeout_seconds=30.0,
    scheduler=scheduler,
).subscribe(on_next=_capture_result, on_error=_capture_error)

# In polling loop:
observation_subject.on_next(ShadowObservation(...))
self._advance_shadow_scheduler(scheduler, last_ts, current_ts)
for result in pipeline_results:
    if isinstance(result, ReadyResult): return ...
```

### Server Tracker Pattern
```python
# From tracking.py line 273
def observe(self, observation: SurfaceObservation) -> SurfaceReduction:
    readiness_state, readiness_unknown_elapsed = self._reduce_readiness(observation)
    completion_state, completion_unknown_elapsed, completion_candidate_elapsed, \
        projection_changed = self._reduce_completion(observation)
    return SurfaceReduction(
        readiness_state=readiness_state,
        completion_state=completion_state,
        projection_changed=projection_changed,
        readiness_unknown_elapsed_seconds=readiness_unknown_elapsed,
        completion_unknown_elapsed_seconds=completion_unknown_elapsed,
        completion_candidate_elapsed_seconds=completion_candidate_elapsed,
    )
```

