# CAO Rx Monitor Extraction: Concrete Code Examples

## Overview
This document shows the exact code that would be shared, extracted, and adapted.

---

## Part 1: What Gets Extracted (Shared Kernel)

### File: `houmao/agents/realm_controller/backends/shared_lifecycle_kernel.py`

```python
"""Pure lifecycle monitoring kernel (no RxPy, no CAO dependencies)."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, TypeAlias

# ============================================================================
# GENERALIZED OBSERVATION TYPE (no CaoTerminalOutputResponse, no DialogProjection)
# ============================================================================

@dataclass(frozen=True)
class LifecycleObservation:
    """Generic lifecycle observation from any source.
    
    This replaces ShadowObservation for the kernel, accepting only
    the fields needed for timing/state logic.
    """
    # Core lifecycle classification
    availability: str                # "supported" | "unsupported" | "disconnected" | "unknown"
    business_state: str              # "idle" | "working" | "awaiting_operator" | "unknown"
    input_mode: str                  # "freeform" | "modal" | "unknown"
    
    # Projection comparison (normalized text)
    projection_text: str             # Normalized dialog/output
    
    # Timing
    monotonic_ts: float              # Scheduler-relative timestamp
    
    # Optional diagnostic fields
    ui_context: str | None = None
    operator_blocked_excerpt: str | None = None
    baseline_invalidated: bool = False


# ============================================================================
# PURE REDUCER STATE TYPES
# ============================================================================

@dataclass(frozen=True)
class _ReadinessPipelineState:
    """Readiness reducer state (pure)."""
    unknown_started_at: float | None = None
    stalled_started_at: float | None = None
    is_stalled: bool = False
    last_result: ReadinessResult | None = None


@dataclass(frozen=True)
class _CompletionPipelineState:
    """Completion reducer state (pure)."""
    unknown_started_at: float | None = None
    stalled_started_at: float | None = None
    is_stalled: bool = False
    
    # Evidence accumulation
    saw_working: bool = False
    saw_projection_change: bool = False
    baseline_projection_text: str = ""
    
    # Stability tracking
    last_stable_signature: tuple[object, ...] | None = None
    stable_started_at: float | None = None
    
    last_result: CompletionResult | None = None


# ============================================================================
# PURE RESULT TYPES
# ============================================================================

@dataclass(frozen=True)
class ReadinessResult:
    """Result from readiness classification."""
    kind: Literal["ready", "blocked", "failed", "unknown", "waiting", "stalled"]
    observation: LifecycleObservation
    elapsed_unknown_seconds: float | None = None
    elapsed_stalled_seconds: float | None = None


@dataclass(frozen=True)
class CompletionResult:
    """Result from completion classification."""
    kind: Literal["in_progress", "candidate_complete", "completed", 
                  "inactive", "waiting", "blocked", "failed", "unknown", "stalled"]
    observation: LifecycleObservation
    elapsed_unknown_seconds: float | None = None
    elapsed_stalled_seconds: float | None = None
    candidate_elapsed_seconds: float | None = None
    completion_payload: dict[str, object] | None = None


# ============================================================================
# PURE CLASSIFICATION FUNCTIONS (extracted from cao_rx_monitor.py)
# ============================================================================

def classify_readiness(observation: LifecycleObservation) -> str:
    """Classify one observation for readiness monitoring.
    
    Returns: "ready" | "blocked" | "failed" | "unknown" | "waiting"
    """
    if observation.availability in {"unsupported", "disconnected"}:
        return "failed"
    
    if is_operator_blocked(observation):
        return "blocked"
    
    if is_unknown_for_stall(observation):
        return "unknown"
    
    if is_submit_ready(observation):
        return "ready"
    
    return "waiting"


def classify_completion_surface(observation: LifecycleObservation) -> str:
    """Classify one observation for completion monitoring.
    
    Returns: "in_progress" | "waiting" | "blocked" | "failed" | "unknown"
    """
    if observation.availability in {"unsupported", "disconnected"}:
        return "failed"
    
    if is_operator_blocked(observation):
        return "blocked"
    
    if is_unknown_for_stall(observation):
        return "unknown"
    
    if observation.business_state == "working":
        return "in_progress"
    
    return "waiting"


# ============================================================================
# PURE HELPER FUNCTIONS
# ============================================================================

def is_submit_ready(observation: LifecycleObservation) -> bool:
    """Return whether the surface is ready for prompt submission."""
    return (
        observation.availability == "supported"
        and observation.business_state == "idle"
        and observation.input_mode == "freeform"
    )


def is_operator_blocked(observation: LifecycleObservation) -> bool:
    """Return whether the surface requires operator interaction."""
    return (
        observation.availability == "supported"
        and observation.business_state == "awaiting_operator"
    )


def is_unknown_for_stall(observation: LifecycleObservation) -> bool:
    """Return whether the surface is effectively unknown."""
    return observation.availability == "unknown" or (
        observation.availability == "supported" 
        and observation.business_state == "unknown"
    )


def normalize_projection_text(text: str) -> str:
    """Return a lifecycle-oriented normalized projection key."""
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


# ============================================================================
# PURE REDUCER FUNCTIONS (the core business logic)
# ============================================================================

def reduce_readiness(
    state: _ReadinessPipelineState,
    observation: LifecycleObservation,
    stall_timeout_seconds: float,
) -> tuple[_ReadinessPipelineState, ReadinessResult | None]:
    """Reduce one readiness observation into state.
    
    Returns: (new_state, result_to_emit_or_none)
    
    This is a PURE FUNCTION — no side effects, deterministic.
    """
    classification = classify_readiness(observation)
    
    if classification == "unknown":
        # Transition to unknown or stay in unknown
        unknown_started_at = state.unknown_started_at
        if unknown_started_at is None:
            unknown_started_at = observation.monotonic_ts
        
        # Check if timeout elapsed
        elapsed = observation.monotonic_ts - unknown_started_at
        if elapsed >= stall_timeout_seconds and not state.is_stalled:
            # Transition to stalled
            new_state = _ReadinessPipelineState(
                unknown_started_at=unknown_started_at,
                stalled_started_at=observation.monotonic_ts,
                is_stalled=True,
                last_result=ReadinessResult(
                    kind="stalled",
                    observation=observation,
                    elapsed_unknown_seconds=elapsed,
                    elapsed_stalled_seconds=0.0,
                ),
            )
            return new_state, new_state.last_result
        else:
            # Stay in unknown (or stalled)
            new_state = _ReadinessPipelineState(
                unknown_started_at=unknown_started_at,
                stalled_started_at=state.stalled_started_at,
                is_stalled=state.is_stalled,
                last_result=None,
            )
            return new_state, None
    
    # Transitioned to known state — possibly recover from stall
    new_state = _ReadinessPipelineState(
        unknown_started_at=None,
        stalled_started_at=None,
        is_stalled=False,
        last_result=ReadinessResult(
            kind=classification,
            observation=observation,
        ) if classification in {"ready", "blocked", "failed"} else None,
    )
    return new_state, new_state.last_result


def reduce_completion(
    state: _CompletionPipelineState,
    observation: LifecycleObservation,
    stall_timeout_seconds: float,
    stability_window_seconds: float,
    baseline_projection_text: str,
) -> tuple[_CompletionPipelineState, CompletionResult | None]:
    """Reduce one completion observation into state.
    
    Returns: (new_state, result_to_emit_or_none)
    
    Handles:
    - Unknown → stalled transition
    - Stability window accumulation for completion
    - Projection change reset detection
    - Evidence accumulation (saw_working, saw_projection_change)
    """
    classification = classify_completion_surface(observation)
    
    # Update evidence flags
    saw_working = state.saw_working or observation.business_state == "working"
    projection_key = normalize_projection_text(observation.projection_text)
    effective_baseline = baseline_projection_text or projection_key
    saw_projection_change = state.saw_projection_change or (
        projection_key != effective_baseline
    )
    
    # Handle unknown/stalled
    if classification == "unknown":
        unknown_started_at = state.unknown_started_at
        if unknown_started_at is None:
            unknown_started_at = observation.monotonic_ts
        
        elapsed = observation.monotonic_ts - unknown_started_at
        if elapsed >= stall_timeout_seconds and not state.is_stalled:
            new_state = _CompletionPipelineState(
                unknown_started_at=unknown_started_at,
                stalled_started_at=observation.monotonic_ts,
                is_stalled=True,
                saw_working=saw_working,
                saw_projection_change=saw_projection_change,
                baseline_projection_text=effective_baseline,
                last_result=CompletionResult(
                    kind="stalled",
                    observation=observation,
                    elapsed_unknown_seconds=elapsed,
                    elapsed_stalled_seconds=0.0,
                ),
            )
            return new_state, new_state.last_result
        else:
            new_state = _CompletionPipelineState(
                unknown_started_at=unknown_started_at,
                stalled_started_at=state.stalled_started_at,
                is_stalled=state.is_stalled,
                saw_working=saw_working,
                saw_projection_change=saw_projection_change,
                baseline_projection_text=effective_baseline,
            )
            return new_state, None
    
    # Handle in_progress (reset stability window)
    if classification == "in_progress":
        new_state = _CompletionPipelineState(
            unknown_started_at=None,
            stalled_started_at=None,
            is_stalled=False,
            saw_working=saw_working,
            saw_projection_change=saw_projection_change,
            baseline_projection_text=effective_baseline,
            last_stable_signature=None,
            stable_started_at=None,
            last_result=CompletionResult(
                kind="in_progress",
                observation=observation,
            ),
        )
        return new_state, new_state.last_result
    
    # Handle candidate_complete / completed (stability window logic)
    if classification == "waiting" and (saw_working or saw_projection_change) and is_submit_ready(observation):
        signature = (
            observation.availability,
            observation.business_state,
            observation.input_mode,
            projection_key,
            saw_working,
            saw_projection_change,
        )
        
        # Detect signature change (reset stability timer)
        if signature != state.last_stable_signature:
            new_state = _CompletionPipelineState(
                unknown_started_at=None,
                stalled_started_at=None,
                is_stalled=False,
                saw_working=saw_working,
                saw_projection_change=saw_projection_change,
                baseline_projection_text=effective_baseline,
                last_stable_signature=signature,
                stable_started_at=observation.monotonic_ts,
                last_result=CompletionResult(
                    kind="candidate_complete",
                    observation=observation,
                    candidate_elapsed_seconds=0.0,
                ),
            )
            return new_state, new_state.last_result
        
        # Accumulate time in stable state
        stable_started_at = state.stable_started_at or observation.monotonic_ts
        candidate_elapsed = observation.monotonic_ts - stable_started_at
        
        if candidate_elapsed >= stability_window_seconds:
            new_state = _CompletionPipelineState(
                unknown_started_at=None,
                stalled_started_at=None,
                is_stalled=False,
                saw_working=saw_working,
                saw_projection_change=saw_projection_change,
                baseline_projection_text=effective_baseline,
                last_stable_signature=signature,
                stable_started_at=stable_started_at,
                last_result=CompletionResult(
                    kind="completed",
                    observation=observation,
                    candidate_elapsed_seconds=candidate_elapsed,
                ),
            )
            return new_state, new_state.last_result
        else:
            new_state = _CompletionPipelineState(
                unknown_started_at=None,
                stalled_started_at=None,
                is_stalled=False,
                saw_working=saw_working,
                saw_projection_change=saw_projection_change,
                baseline_projection_text=effective_baseline,
                last_stable_signature=signature,
                stable_started_at=stable_started_at,
                last_result=CompletionResult(
                    kind="candidate_complete",
                    observation=observation,
                    candidate_elapsed_seconds=candidate_elapsed,
                ),
            )
            return new_state, new_state.last_result
    
    # Default: waiting or other terminal states
    new_state = _CompletionPipelineState(
        unknown_started_at=None,
        stalled_started_at=None,
        is_stalled=False,
        saw_working=saw_working,
        saw_projection_change=saw_projection_change,
        baseline_projection_text=effective_baseline,
        last_result=CompletionResult(
            kind=classification,
            observation=observation,
        ) if classification in {"blocked", "failed"} else None,
    )
    return new_state, new_state.last_result
```

---

## Part 2: What Stays in CAO Rx Monitor (RxPy Adapter)

### File: `houmao/agents/realm_controller/backends/cao_rx_monitor.py` (Modified)

```python
"""CAO REST backend with runtime-generated profile support."""

from reactivex import Observable, abc, operators as ops
from reactivex.subject import Subject
import reactivex
from typing import cast

from .shared_lifecycle_kernel import (
    LifecycleObservation,
    ReadinessResult,
    CompletionResult,
    _ReadinessPipelineState,
    _CompletionPipelineState,
    reduce_readiness,
    reduce_completion,
    normalize_projection_text,
)

# Keep the CAO-specific wrappers
from .cao_rx_monitor_types import (
    ShadowObservation,
    PipelineResult,
    ReadyResult,
    CompletedResult,
    BlockedResult,
    FailedResult,
    StalledResult,
)

# ============================================================================
# ADAPTER: Convert CAO observation → lifecycle observation
# ============================================================================

def _adapt_shadow_observation(obs: ShadowObservation) -> LifecycleObservation:
    """Convert ShadowObservation (CAO-specific) to LifecycleObservation (generic)."""
    surface = obs.snapshot.surface_assessment
    return LifecycleObservation(
        availability=surface.availability,
        business_state=surface.business_state,
        input_mode=surface.input_mode,
        projection_text=obs.projection.normalized_text,
        monotonic_ts=obs.monotonic_ts,
        ui_context=surface.ui_context,
        operator_blocked_excerpt=surface.operator_blocked_excerpt,
        baseline_invalidated=surface.parser_metadata.baseline_invalidated,
    )


def _adapt_readiness_result(
    kernel_result: ReadinessResult,
    original_observation: ShadowObservation,
) -> PipelineResult | None:
    """Convert kernel ReadinessResult → CAO PipelineResult."""
    if kernel_result.kind == "ready":
        return ReadyResult(observation=original_observation)
    elif kernel_result.kind == "blocked":
        return BlockedResult(observation=original_observation)
    elif kernel_result.kind == "failed":
        return FailedResult(observation=original_observation)
    elif kernel_result.kind == "stalled":
        return StalledResult(
            observation=original_observation,
            elapsed_unknown_seconds=kernel_result.elapsed_unknown_seconds or 0.0,
        )
    return None


def _adapt_completion_result(
    kernel_result: CompletionResult,
    original_observation: ShadowObservation,
) -> PipelineResult | None:
    """Convert kernel CompletionResult → CAO PipelineResult."""
    if kernel_result.kind == "completed":
        return CompletedResult(
            observation=original_observation,
            completion_payload=kernel_result.completion_payload,
        )
    elif kernel_result.kind == "blocked":
        return BlockedResult(observation=original_observation)
    elif kernel_result.kind == "failed":
        return FailedResult(observation=original_observation)
    elif kernel_result.kind == "stalled":
        return StalledResult(
            observation=original_observation,
            elapsed_unknown_seconds=kernel_result.elapsed_unknown_seconds or 0.0,
        )
    return None


# ============================================================================
# PIPELINE BUILDERS (use kernel + RxPy composition)
# ============================================================================

def build_readiness_pipeline(
    source: Observable[ShadowObservation],
    *,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[PipelineResult]:
    """Build the readiness monitoring pipeline using the shared kernel."""
    
    def _reduce_with_kernel(
        state: _ReadinessPipelineState,
        observation: ShadowObservation,
    ) -> _ReadinessPipelineState:
        lifecycle_obs = _adapt_shadow_observation(observation)
        new_state, result = reduce_readiness(
            state,
            lifecycle_obs,
            stall_timeout_seconds,
        )
        # Attach result to state for downstream extraction
        return new_state.model_copy(update={"_attached_result": result})
    
    return source.pipe(
        ops.scan(_reduce_with_kernel, seed=_ReadinessPipelineState()),
        ops.map(lambda state: state._attached_result),
        ops.filter(lambda result: result is not None),
    )


def build_completion_pipeline(
    source: Observable[ShadowObservation],
    *,
    stability_seconds: float,
    stall_timeout_seconds: float,
    baseline_projection: "DialogProjection",
    completion_observer: "CompletionObserver | None",
    scheduler: abc.SchedulerBase,
) -> Observable[PipelineResult]:
    """Build the completion monitoring pipeline using the shared kernel."""
    baseline_text = baseline_projection.normalized_text
    
    def _reduce_with_kernel(
        state: _CompletionPipelineState,
        observation: ShadowObservation,
    ) -> _CompletionPipelineState:
        lifecycle_obs = _adapt_shadow_observation(observation)
        new_state, result = reduce_completion(
            state,
            lifecycle_obs,
            stall_timeout_seconds,
            stability_seconds,
            baseline_text,
        )
        return new_state.model_copy(update={"_attached_result": result})
    
    return source.pipe(
        ops.scan(_reduce_with_kernel, seed=_CompletionPipelineState()),
        ops.map(lambda state: state._attached_result),
        ops.filter(lambda result: result is not None),
    )
```

---

## Part 3: Server Tracker Adaptation

### File: `houmao/server/tui/tracking.py` (Modified Section)

```python
"""In-memory live tracking and reduction for server-owned TUI state."""

from houmao.agents.realm_controller.backends.shared_lifecycle_kernel import (
    LifecycleObservation,
    reduce_readiness,
    reduce_completion,
    normalize_projection_text,
    _ReadinessPipelineState,
    _CompletionPipelineState,
)

class _SurfaceStateReducer:
    """Continuous readiness/completion reducer adapted for live tracking."""
    
    def __init__(
        self,
        *,
        completion_stability_seconds: float,
        unknown_to_stalled_timeout_seconds: float,
    ) -> None:
        """Initialize the reducer."""
        self.m_completion_stability_seconds = completion_stability_seconds
        self.m_unknown_to_stalled_timeout_seconds = unknown_to_stalled_timeout_seconds
        
        # Use kernel state directly
        self.m_readiness_state = _ReadinessPipelineState()
        self.m_completion_state = _CompletionPipelineState()
        
        self.m_baseline_projection_text: str | None = None
    
    def observe(self, observation: SurfaceObservation) -> SurfaceReduction:
        """Consume one parsed-surface observation."""
        
        # Convert server observation to lifecycle observation
        lifecycle_obs = LifecycleObservation(
            availability=observation.availability,
            business_state=observation.business_state,
            input_mode=observation.input_mode,
            projection_text=observation.normalized_projection_text,
            monotonic_ts=observation.monotonic_ts,
            ui_context=observation.ui_context,
            operator_blocked_excerpt=observation.operator_blocked_excerpt,
            baseline_invalidated=observation.baseline_invalidated,
        )
        
        # Use kernel reducer for readiness
        self.m_readiness_state, readiness_result = reduce_readiness(
            self.m_readiness_state,
            lifecycle_obs,
            self.m_unknown_to_stalled_timeout_seconds,
        )
        readiness_state = readiness_result.kind if readiness_result else "unknown"
        readiness_unknown_elapsed = (
            readiness_result.elapsed_unknown_seconds
            if readiness_result and readiness_result.kind == "unknown"
            else None
        )
        
        # Initialize baseline on first non-idle state
        if self.m_baseline_projection_text is None:
            self.m_baseline_projection_text = lifecycle_obs.projection_text
        
        # Use kernel reducer for completion
        self.m_completion_state, completion_result = reduce_completion(
            self.m_completion_state,
            lifecycle_obs,
            self.m_unknown_to_stalled_timeout_seconds,
            self.m_completion_stability_seconds,
            self.m_baseline_projection_text,
        )
        completion_state = completion_result.kind if completion_result else "unknown"
        completion_unknown_elapsed = (
            completion_result.elapsed_unknown_seconds
            if completion_result and completion_result.kind == "unknown"
            else None
        )
        completion_candidate_elapsed = (
            completion_result.candidate_elapsed_seconds
            if completion_result and completion_result.kind in {"candidate_complete", "completed"}
            else None
        )
        
        # Detect projection change (for diagnostics)
        projection_changed = (
            normalize_projection_text(lifecycle_obs.projection_text) 
            != normalize_projection_text(self.m_baseline_projection_text)
        )
        
        return SurfaceReduction(
            readiness_state=readiness_state,
            completion_state=completion_state,
            projection_changed=projection_changed,
            readiness_unknown_elapsed_seconds=readiness_unknown_elapsed,
            completion_unknown_elapsed_seconds=completion_unknown_elapsed,
            completion_candidate_elapsed_seconds=completion_candidate_elapsed,
        )
```

---

## Part 4: Unit Tests for Shared Kernel

### File: `tests/unit/shared_lifecycle_kernel_test.py`

```python
"""Unit tests for the shared lifecycle kernel (pure functions)."""

import pytest
from houmao.agents.realm_controller.backends.shared_lifecycle_kernel import (
    LifecycleObservation,
    reduce_readiness,
    reduce_completion,
    classify_readiness,
    _ReadinessPipelineState,
    _CompletionPipelineState,
)


def test_reduce_readiness_unknown_to_stalled():
    """Test unknown → stalled transition."""
    state = _ReadinessPipelineState()
    
    # Emit observation at t=0
    obs1 = LifecycleObservation(
        availability="unknown",
        business_state="unknown",
        input_mode="unknown",
        projection_text="unknown",
        monotonic_ts=0.0,
    )
    new_state, result = reduce_readiness(state, obs1, stall_timeout_seconds=5.0)
    assert result is None
    assert new_state.unknown_started_at == 0.0
    
    # Still unknown at t=4.9
    obs2 = LifecycleObservation(
        availability="unknown",
        business_state="unknown",
        input_mode="unknown",
        projection_text="unknown",
        monotonic_ts=4.9,
    )
    new_state, result = reduce_readiness(new_state, obs2, stall_timeout_seconds=5.0)
    assert result is None
    
    # Stall at t=5.0
    obs3 = LifecycleObservation(
        availability="unknown",
        business_state="unknown",
        input_mode="unknown",
        projection_text="unknown",
        monotonic_ts=5.0,
    )
    new_state, result = reduce_readiness(new_state, obs3, stall_timeout_seconds=5.0)
    assert result is not None
    assert result.kind == "stalled"
    assert result.elapsed_unknown_seconds == 5.0


def test_reduce_completion_with_evidence_accumulation():
    """Test completion with saw_working + projection_change."""
    state = _CompletionPipelineState()
    
    # Start at working (resets baseline)
    obs1 = LifecycleObservation(
        availability="supported",
        business_state="working",
        input_mode="modal",
        projection_text="processing",
        monotonic_ts=0.0,
    )
    new_state, result = reduce_completion(
        state, obs1, stall_timeout_seconds=30.0, stability_window_seconds=1.0,
        baseline_projection_text="initial",
    )
    assert new_state.saw_working is True
    assert result.kind == "in_progress"
    
    # Transition to candidate_complete (idle + submit_ready + evidence)
    obs2 = LifecycleObservation(
        availability="supported",
        business_state="idle",
        input_mode="freeform",
        projection_text="done",  # Changed
        monotonic_ts=0.5,
    )
    new_state, result = reduce_completion(
        new_state, obs2, stall_timeout_seconds=30.0, stability_window_seconds=1.0,
        baseline_projection_text="initial",
    )
    assert new_state.saw_projection_change is True
    assert result.kind == "candidate_complete"
    assert result.candidate_elapsed_seconds == pytest.approx(0.0)
    
    # Still candidate at t=0.9
    obs3 = LifecycleObservation(
        availability="supported",
        business_state="idle",
        input_mode="freeform",
        projection_text="done",
        monotonic_ts=0.9,
    )
    new_state, result = reduce_completion(
        new_state, obs3, stall_timeout_seconds=30.0, stability_window_seconds=1.0,
        baseline_projection_text="initial",
    )
    assert result.kind == "candidate_complete"
    assert result.candidate_elapsed_seconds == pytest.approx(0.4)
    
    # Complete at t=1.0
    obs4 = LifecycleObservation(
        availability="supported",
        business_state="idle",
        input_mode="freeform",
        projection_text="done",
        monotonic_ts=1.0,
    )
    new_state, result = reduce_completion(
        new_state, obs4, stall_timeout_seconds=30.0, stability_window_seconds=1.0,
        baseline_projection_text="initial",
    )
    assert result.kind == "completed"
    assert result.candidate_elapsed_seconds == pytest.approx(0.5)
```

---

## Summary

**Extraction Pattern:**
1. **Shared kernel**: Pure reducer functions, no RxPy, no CAO dependencies
2. **RxPy adapter**: Wraps kernel in Observable, handles subscription/timer logic
3. **Server adapter**: Wraps kernel in synchronous reducer, thread-safe
4. **Both benefit**: Single source of truth for stall/stability logic

**Total shared code: ~300 LOC** (7 functions + 2 state types)
**Total adapter code: ~100 LOC** (CAO) + ~50 LOC (server) 
**Net reduction: ~150 LOC** from removing duplication

