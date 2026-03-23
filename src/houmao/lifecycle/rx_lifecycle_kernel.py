"""Shared ReactiveX lifecycle timing kernel.

This module provides the reusable readiness and anchored-completion timing
pipelines shared by the CAO runtime and `houmao-server`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal, TypeAlias, cast

import reactivex
from reactivex import Observable, abc, operators as ops

ReadinessLifecycleStatus: TypeAlias = Literal[
    "ready",
    "waiting",
    "blocked",
    "failed",
    "unknown",
    "stalled",
]
AnchoredCompletionStatus: TypeAlias = Literal[
    "waiting",
    "in_progress",
    "candidate_complete",
    "completed",
    "blocked",
    "failed",
    "unknown",
    "stalled",
]
CompletionAuthorityMode: TypeAlias = Literal["turn_anchored", "unanchored_background"]
TurnAnchorState: TypeAlias = Literal["active", "absent", "lost"]


@dataclass(frozen=True)
class LifecycleObservation:
    """One normalized parsed-TUI observation flowing through lifecycle pipelines.

    Parameters
    ----------
    availability:
        Parsed availability classification for the surface.
    business_state:
        Parsed business-state classification for the surface.
    input_mode:
        Parsed input-mode classification for the surface.
    ui_context:
        Parsed UI-context classification for the surface.
    normalized_projection_text:
        Lifecycle-oriented normalized projection text for comparison.
    baseline_invalidated:
        Whether the parser invalidated the baseline for this observation.
    operator_blocked_excerpt:
        Optional operator-blocked excerpt from the parser.
    monotonic_ts:
        Observation timestamp in monotonic seconds.
    parser_family:
        Parser-family label for diagnostics.
    source_payload:
        Optional caller-owned payload reference carried through the pipeline.
    """

    availability: str
    business_state: str
    input_mode: str
    ui_context: str
    normalized_projection_text: str
    baseline_invalidated: bool
    operator_blocked_excerpt: str | None
    monotonic_ts: float
    parser_family: str
    source_payload: object | None = None


@dataclass(frozen=True)
class TurnAnchor:
    """One explicit turn anchor owned by the caller."""

    anchor_id: int
    source: Literal["terminal_input", "surface_inference"]
    baseline_projection_text: str
    armed_at_utc: str
    armed_monotonic_ts: float
    message_excerpt: str | None = None


@dataclass(frozen=True)
class PostSubmitEvidence:
    """Accumulated post-submit evidence for one anchored completion cycle."""

    saw_working: bool
    saw_projection_change: bool
    baseline_normalized_text: str


@dataclass(frozen=True)
class ReadinessSnapshot:
    """Current readiness timing snapshot for one observation or timer event."""

    observation: LifecycleObservation
    status: ReadinessLifecycleStatus
    unknown_elapsed_seconds: float | None = None
    elapsed_stalled_seconds: float | None = None
    entered_stalled: bool = False
    recovered_from_stalled: bool = False
    recovered_to: str | None = None


@dataclass(frozen=True)
class AnchoredCompletionSnapshot:
    """Current anchored completion timing snapshot."""

    observation: LifecycleObservation
    status: AnchoredCompletionStatus
    unknown_elapsed_seconds: float | None = None
    candidate_elapsed_seconds: float | None = None
    elapsed_stalled_seconds: float | None = None
    projection_changed: bool = False
    saw_working: bool = False
    saw_projection_change: bool = False
    entered_stalled: bool = False
    recovered_from_stalled: bool = False
    recovered_to: str | None = None


@dataclass(frozen=True)
class _ReadinessClassification:
    """One readiness classification derived from one lifecycle observation."""

    observation: LifecycleObservation
    status: Literal["ready", "waiting", "blocked", "failed", "unknown"]
    recovered_to: str


@dataclass(frozen=True)
class _ReadinessObservationEvent:
    """One readiness observation event."""

    classification: _ReadinessClassification


@dataclass(frozen=True)
class _ReadinessStallTimerEvent:
    """One readiness stall-timer event."""

    observation: LifecycleObservation
    fired_monotonic_ts: float


ReadinessEvent: TypeAlias = _ReadinessObservationEvent | _ReadinessStallTimerEvent


@dataclass(frozen=True)
class _ReadinessReducerState:
    """Reducer state for the readiness timing pipeline."""

    unknown_started_at: float | None = None
    stalled_started_at: float | None = None
    is_stalled: bool = False
    snapshot: ReadinessSnapshot | None = None


@dataclass(frozen=True)
class _AnchoredCompletionAccumulatorState:
    """Accumulator state for post-submit evidence."""

    observation: LifecycleObservation | None
    evidence: PostSubmitEvidence
    projection_key: str
    frozen_projection_key: str | None = None


@dataclass(frozen=True)
class _AnchoredCompletionClassification:
    """One anchored completion classification."""

    observation: LifecycleObservation
    evidence: PostSubmitEvidence
    projection_key: str
    status: Literal["blocked", "candidate_complete", "failed", "in_progress", "unknown", "waiting"]
    recovered_to: str


@dataclass(frozen=True)
class _AnchoredCompletionObservationEvent:
    """One anchored completion observation event."""

    classification: _AnchoredCompletionClassification


@dataclass(frozen=True)
class _AnchoredCompletionStallTimerEvent:
    """One anchored completion stall-timer event."""

    observation: LifecycleObservation
    fired_monotonic_ts: float


@dataclass(frozen=True)
class _AnchoredCompletionStableTimerEvent:
    """One anchored completion stability-timer event."""

    classification: _AnchoredCompletionClassification
    signature: tuple[object, ...]
    fired_monotonic_ts: float


AnchoredCompletionEvent: TypeAlias = (
    _AnchoredCompletionObservationEvent
    | _AnchoredCompletionStallTimerEvent
    | _AnchoredCompletionStableTimerEvent
)


@dataclass(frozen=True)
class _AnchoredCompletionReducerState:
    """Reducer state for anchored completion timing."""

    unknown_started_at: float | None = None
    stalled_started_at: float | None = None
    is_stalled: bool = False
    candidate_started_at: float | None = None
    candidate_signature: tuple[object, ...] | None = None
    completed_signature: tuple[object, ...] | None = None
    snapshot: AnchoredCompletionSnapshot | None = None


def normalize_projection_text(text: str) -> str:
    """Return one lifecycle-oriented normalized projection key."""

    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def build_readiness_pipeline(
    source: Observable[LifecycleObservation],
    *,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[ReadinessSnapshot]:
    """Build the shared readiness timing pipeline."""

    def _map_stall_timer(
        classification: _ReadinessClassification,
    ) -> Observable[_ReadinessStallTimerEvent]:
        return _map_readiness_stall_timer(
            classification=classification,
            stall_timeout_seconds=stall_timeout_seconds,
            scheduler=scheduler,
        )

    classified = source.pipe(
        ops.map(_classify_readiness),
        ops.share(),
    )
    stall_timer_events = classified.pipe(
        ops.map(_map_stall_timer),
        ops.switch_latest(),
    )
    events = reactivex.merge(
        classified.pipe(ops.map(_map_readiness_observation_event)),
        stall_timer_events,
    )
    states = events.pipe(ops.scan(_reduce_readiness_event, seed=_ReadinessReducerState()))
    return cast(
        Observable[ReadinessSnapshot],
        states.pipe(
            ops.map(_readiness_reducer_snapshot),
            ops.filter(_is_readiness_snapshot),
        ),
    )


def build_anchored_completion_pipeline(
    source: Observable[LifecycleObservation],
    *,
    baseline_projection_text: str,
    stability_seconds: float,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[AnchoredCompletionSnapshot]:
    """Build the shared anchored completion timing pipeline."""

    def _map_stall_timer(
        classification: _AnchoredCompletionClassification,
    ) -> Observable[_AnchoredCompletionStallTimerEvent]:
        return _map_anchored_completion_stall_timer(
            classification=classification,
            stall_timeout_seconds=stall_timeout_seconds,
            scheduler=scheduler,
        )

    def _map_stability_timer(
        classification: _AnchoredCompletionClassification,
    ) -> Observable[_AnchoredCompletionStableTimerEvent]:
        return _map_anchored_completion_stability_timer(
            classification=classification,
            stability_seconds=stability_seconds,
            scheduler=scheduler,
        )

    baseline_projection_key = normalize_projection_text(baseline_projection_text)
    accumulated = source.pipe(
        ops.scan(
            _reduce_anchored_completion_accumulator,
            seed=_AnchoredCompletionAccumulatorState(
                observation=None,
                evidence=PostSubmitEvidence(
                    saw_working=False,
                    saw_projection_change=False,
                    baseline_normalized_text=baseline_projection_key,
                ),
                projection_key=baseline_projection_key,
                frozen_projection_key=None,
            ),
        ),
        ops.share(),
    )
    classified = accumulated.pipe(
        ops.map(_classify_anchored_completion),
        ops.share(),
    )
    classified_changes = classified.pipe(
        ops.distinct_until_changed(_anchored_completion_change_signature),
        ops.share(),
    )
    stall_timer_events = classified.pipe(
        ops.map(_map_stall_timer),
        ops.switch_latest(),
    )
    stability_timer_events = classified_changes.pipe(
        ops.map(_map_stability_timer),
        ops.switch_latest(),
    )
    events = reactivex.merge(
        classified.pipe(ops.map(_map_anchored_completion_observation_event)),
        stall_timer_events,
        stability_timer_events,
    )
    states = events.pipe(
        ops.scan(_reduce_anchored_completion_event, seed=_AnchoredCompletionReducerState())
    )
    return cast(
        Observable[AnchoredCompletionSnapshot],
        states.pipe(
            ops.map(_anchored_completion_reducer_snapshot),
            ops.filter(_is_anchored_completion_snapshot),
        ),
    )


def _classify_readiness(observation: LifecycleObservation) -> _ReadinessClassification:
    """Classify one observation for readiness timing."""

    recovered_to = _surface_status_label(observation)
    if observation.availability in {"unsupported", "disconnected"}:
        return _ReadinessClassification(
            observation=observation,
            status="failed",
            recovered_to=recovered_to,
        )
    if _is_operator_blocked(observation):
        return _ReadinessClassification(
            observation=observation,
            status="blocked",
            recovered_to="blocked_operator",
        )
    if _is_unknown_for_stall(observation):
        return _ReadinessClassification(
            observation=observation,
            status="unknown",
            recovered_to=recovered_to,
        )
    if _is_submit_ready(observation):
        return _ReadinessClassification(
            observation=observation,
            status="ready",
            recovered_to=recovered_to,
        )
    return _ReadinessClassification(
        observation=observation,
        status="waiting",
        recovered_to=recovered_to,
    )


def _map_readiness_stall_timer(
    *,
    classification: _ReadinessClassification,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[_ReadinessStallTimerEvent]:
    """Map one readiness classification to its stall timer."""

    if classification.status != "unknown":
        return cast(Observable[_ReadinessStallTimerEvent], reactivex.never())
    return reactivex.timer(_seconds(stall_timeout_seconds), scheduler=scheduler).pipe(
        ops.map(
            lambda _: _ReadinessStallTimerEvent(
                observation=classification.observation,
                fired_monotonic_ts=classification.observation.monotonic_ts + stall_timeout_seconds,
            )
        )
    )


def _map_readiness_observation_event(
    classification: _ReadinessClassification,
) -> _ReadinessObservationEvent:
    """Wrap one readiness classification as a reducer event."""

    return _ReadinessObservationEvent(classification=classification)


def _reduce_readiness_event(
    state: _ReadinessReducerState,
    event: ReadinessEvent,
) -> _ReadinessReducerState:
    """Reduce one readiness event into the current pipeline state."""

    if isinstance(event, _ReadinessObservationEvent):
        classification = event.classification
        observation = classification.observation
        if classification.status == "unknown":
            unknown_started_at = state.unknown_started_at
            if unknown_started_at is None:
                unknown_started_at = observation.monotonic_ts
            unknown_elapsed_seconds = max(observation.monotonic_ts - unknown_started_at, 0.0)
            if state.is_stalled and state.stalled_started_at is not None:
                return _ReadinessReducerState(
                    unknown_started_at=unknown_started_at,
                    stalled_started_at=state.stalled_started_at,
                    is_stalled=True,
                    snapshot=ReadinessSnapshot(
                        observation=observation,
                        status="stalled",
                        unknown_elapsed_seconds=unknown_elapsed_seconds,
                        elapsed_stalled_seconds=max(
                            observation.monotonic_ts - state.stalled_started_at,
                            0.0,
                        ),
                    ),
                )
            return _ReadinessReducerState(
                unknown_started_at=unknown_started_at,
                stalled_started_at=None,
                is_stalled=False,
                snapshot=ReadinessSnapshot(
                    observation=observation,
                    status="unknown",
                    unknown_elapsed_seconds=unknown_elapsed_seconds,
                ),
            )

        recovered_from_stalled = state.is_stalled and state.stalled_started_at is not None
        return _ReadinessReducerState(
            unknown_started_at=None,
            stalled_started_at=None,
            is_stalled=False,
            snapshot=ReadinessSnapshot(
                observation=observation,
                status=classification.status,
                recovered_from_stalled=recovered_from_stalled,
                recovered_to=classification.recovered_to if recovered_from_stalled else None,
            ),
        )

    if state.is_stalled or state.unknown_started_at is None:
        return state

    elapsed_unknown_seconds = max(event.fired_monotonic_ts - state.unknown_started_at, 0.0)
    return _ReadinessReducerState(
        unknown_started_at=state.unknown_started_at,
        stalled_started_at=event.fired_monotonic_ts,
        is_stalled=True,
        snapshot=ReadinessSnapshot(
            observation=event.observation,
            status="stalled",
            unknown_elapsed_seconds=elapsed_unknown_seconds,
            elapsed_stalled_seconds=0.0,
            entered_stalled=True,
        ),
    )


def _reduce_anchored_completion_accumulator(
    state: _AnchoredCompletionAccumulatorState,
    observation: LifecycleObservation,
) -> _AnchoredCompletionAccumulatorState:
    """Accumulate anchored post-submit evidence from one observation."""

    projection_key = normalize_projection_text(observation.normalized_projection_text)
    frozen_projection_key = state.frozen_projection_key
    if frozen_projection_key is None and observation.baseline_invalidated:
        frozen_projection_key = projection_key
    effective_projection_key = frozen_projection_key or projection_key
    evidence = PostSubmitEvidence(
        saw_working=state.evidence.saw_working or observation.business_state == "working",
        saw_projection_change=(
            state.evidence.saw_projection_change
            or effective_projection_key != state.evidence.baseline_normalized_text
        ),
        baseline_normalized_text=state.evidence.baseline_normalized_text,
    )
    return _AnchoredCompletionAccumulatorState(
        observation=observation,
        evidence=evidence,
        projection_key=effective_projection_key,
        frozen_projection_key=frozen_projection_key,
    )


def _classify_anchored_completion(
    state: _AnchoredCompletionAccumulatorState,
) -> _AnchoredCompletionClassification:
    """Classify one accumulated anchored-completion observation."""

    observation = state.observation
    if observation is None:
        raise RuntimeError("Anchored completion classification requires an observation.")

    recovered_to = _surface_status_label(observation)
    if observation.availability in {"unsupported", "disconnected"}:
        return _AnchoredCompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="failed",
            recovered_to=recovered_to,
        )
    if _is_operator_blocked(observation):
        return _AnchoredCompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="blocked",
            recovered_to="blocked_operator",
        )
    if _is_unknown_for_stall(observation):
        return _AnchoredCompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="unknown",
            recovered_to=recovered_to,
        )
    if observation.business_state == "working":
        return _AnchoredCompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="in_progress",
            recovered_to=recovered_to,
        )
    if _is_submit_ready(observation) and _has_post_submit_activity(state.evidence):
        return _AnchoredCompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="candidate_complete",
            recovered_to="completed",
        )
    return _AnchoredCompletionClassification(
        observation=observation,
        evidence=state.evidence,
        projection_key=state.projection_key,
        status="waiting",
        recovered_to=recovered_to if not _is_submit_ready(observation) else "submit_ready",
    )


def _anchored_completion_change_signature(
    classification: _AnchoredCompletionClassification,
) -> tuple[object, ...]:
    """Return the signature used to reset the completion stability timer."""

    return (
        classification.status,
        classification.observation.availability,
        classification.observation.business_state,
        classification.observation.input_mode,
        classification.projection_key,
        classification.evidence.saw_working,
        classification.evidence.saw_projection_change,
    )


def _map_anchored_completion_stall_timer(
    *,
    classification: _AnchoredCompletionClassification,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[_AnchoredCompletionStallTimerEvent]:
    """Map one anchored completion classification to its stall timer."""

    if classification.status != "unknown":
        return cast(Observable[_AnchoredCompletionStallTimerEvent], reactivex.never())
    return reactivex.timer(_seconds(stall_timeout_seconds), scheduler=scheduler).pipe(
        ops.map(
            lambda _: _AnchoredCompletionStallTimerEvent(
                observation=classification.observation,
                fired_monotonic_ts=classification.observation.monotonic_ts + stall_timeout_seconds,
            )
        )
    )


def _map_anchored_completion_stability_timer(
    *,
    classification: _AnchoredCompletionClassification,
    stability_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[_AnchoredCompletionStableTimerEvent]:
    """Map one anchored completion classification to its stability timer."""

    if classification.status != "candidate_complete":
        return cast(Observable[_AnchoredCompletionStableTimerEvent], reactivex.never())
    signature = _anchored_completion_change_signature(classification)
    return reactivex.timer(_seconds(stability_seconds), scheduler=scheduler).pipe(
        ops.map(
            lambda _: _AnchoredCompletionStableTimerEvent(
                classification=classification,
                signature=signature,
                fired_monotonic_ts=classification.observation.monotonic_ts + stability_seconds,
            )
        )
    )


def _map_anchored_completion_observation_event(
    classification: _AnchoredCompletionClassification,
) -> _AnchoredCompletionObservationEvent:
    """Wrap one anchored completion classification as a reducer event."""

    return _AnchoredCompletionObservationEvent(classification=classification)


def _reduce_anchored_completion_event(
    state: _AnchoredCompletionReducerState,
    event: AnchoredCompletionEvent,
) -> _AnchoredCompletionReducerState:
    """Reduce one anchored completion event into the current pipeline state."""

    if isinstance(event, _AnchoredCompletionObservationEvent):
        classification = event.classification
        observation = classification.observation
        projection_changed = classification.evidence.saw_projection_change
        saw_working = classification.evidence.saw_working
        saw_projection_change = classification.evidence.saw_projection_change
        recovered_from_stalled = state.is_stalled and state.stalled_started_at is not None

        if classification.status == "unknown":
            unknown_started_at = state.unknown_started_at
            if unknown_started_at is None:
                unknown_started_at = observation.monotonic_ts
            unknown_elapsed_seconds = max(observation.monotonic_ts - unknown_started_at, 0.0)
            if state.is_stalled and state.stalled_started_at is not None:
                return _AnchoredCompletionReducerState(
                    unknown_started_at=unknown_started_at,
                    stalled_started_at=state.stalled_started_at,
                    is_stalled=True,
                    candidate_started_at=None,
                    candidate_signature=None,
                    completed_signature=None,
                    snapshot=AnchoredCompletionSnapshot(
                        observation=observation,
                        status="stalled",
                        unknown_elapsed_seconds=unknown_elapsed_seconds,
                        elapsed_stalled_seconds=max(
                            observation.monotonic_ts - state.stalled_started_at,
                            0.0,
                        ),
                        projection_changed=projection_changed,
                        saw_working=saw_working,
                        saw_projection_change=saw_projection_change,
                    ),
                )
            return _AnchoredCompletionReducerState(
                unknown_started_at=unknown_started_at,
                stalled_started_at=None,
                is_stalled=False,
                candidate_started_at=None,
                candidate_signature=None,
                completed_signature=None,
                snapshot=AnchoredCompletionSnapshot(
                    observation=observation,
                    status="unknown",
                    unknown_elapsed_seconds=unknown_elapsed_seconds,
                    projection_changed=projection_changed,
                    saw_working=saw_working,
                    saw_projection_change=saw_projection_change,
                ),
            )

        if classification.status == "candidate_complete":
            signature = _anchored_completion_change_signature(classification)
            candidate_started_at = state.candidate_started_at
            completed_signature = state.completed_signature
            if signature != state.candidate_signature or candidate_started_at is None:
                candidate_started_at = observation.monotonic_ts
                completed_signature = None
            assert candidate_started_at is not None
            candidate_elapsed_seconds = max(observation.monotonic_ts - candidate_started_at, 0.0)
            status: AnchoredCompletionStatus = (
                "completed" if completed_signature == signature else "candidate_complete"
            )
            return _AnchoredCompletionReducerState(
                unknown_started_at=None,
                stalled_started_at=None,
                is_stalled=False,
                candidate_started_at=candidate_started_at,
                candidate_signature=signature,
                completed_signature=completed_signature,
                snapshot=AnchoredCompletionSnapshot(
                    observation=observation,
                    status=status,
                    candidate_elapsed_seconds=candidate_elapsed_seconds,
                    projection_changed=projection_changed,
                    saw_working=saw_working,
                    saw_projection_change=saw_projection_change,
                    recovered_from_stalled=recovered_from_stalled,
                    recovered_to=classification.recovered_to if recovered_from_stalled else None,
                ),
            )

        return _AnchoredCompletionReducerState(
            unknown_started_at=None,
            stalled_started_at=None,
            is_stalled=False,
            candidate_started_at=None,
            candidate_signature=None,
            completed_signature=None,
            snapshot=AnchoredCompletionSnapshot(
                observation=observation,
                status=classification.status,
                projection_changed=projection_changed,
                saw_working=saw_working,
                saw_projection_change=saw_projection_change,
                recovered_from_stalled=recovered_from_stalled,
                recovered_to=classification.recovered_to if recovered_from_stalled else None,
            ),
        )

    if isinstance(event, _AnchoredCompletionStallTimerEvent):
        if state.is_stalled or state.unknown_started_at is None:
            return state
        elapsed_unknown_seconds = max(event.fired_monotonic_ts - state.unknown_started_at, 0.0)
        return _AnchoredCompletionReducerState(
            unknown_started_at=state.unknown_started_at,
            stalled_started_at=event.fired_monotonic_ts,
            is_stalled=True,
            candidate_started_at=None,
            candidate_signature=None,
            completed_signature=None,
            snapshot=AnchoredCompletionSnapshot(
                observation=event.observation,
                status="stalled",
                unknown_elapsed_seconds=elapsed_unknown_seconds,
                elapsed_stalled_seconds=0.0,
                entered_stalled=True,
            ),
        )

    if state.candidate_started_at is None or state.candidate_signature != event.signature:
        return state
    return _AnchoredCompletionReducerState(
        unknown_started_at=None,
        stalled_started_at=None,
        is_stalled=False,
        candidate_started_at=state.candidate_started_at,
        candidate_signature=state.candidate_signature,
        completed_signature=event.signature,
        snapshot=AnchoredCompletionSnapshot(
            observation=event.classification.observation,
            status="completed",
            candidate_elapsed_seconds=max(
                event.fired_monotonic_ts - state.candidate_started_at,
                0.0,
            ),
            projection_changed=event.classification.evidence.saw_projection_change,
            saw_working=event.classification.evidence.saw_working,
            saw_projection_change=event.classification.evidence.saw_projection_change,
        ),
    )


def _is_submit_ready(observation: LifecycleObservation) -> bool:
    """Return whether the parsed surface is submit-ready."""

    return (
        observation.availability == "supported"
        and observation.business_state == "idle"
        and observation.input_mode == "freeform"
    )


def _is_operator_blocked(observation: LifecycleObservation) -> bool:
    """Return whether the parsed surface requires operator attention."""

    return (
        observation.availability == "supported"
        and observation.business_state == "awaiting_operator"
    )


def _is_unknown_for_stall(observation: LifecycleObservation) -> bool:
    """Return whether the parsed surface should count as unknown for stall timing."""

    return observation.availability == "unknown" or (
        observation.availability == "supported" and observation.business_state == "unknown"
    )


def _surface_status_label(observation: LifecycleObservation) -> str:
    """Return a concise surface-status label for recovery metadata."""

    if observation.availability == "unsupported":
        return "unsupported"
    if observation.availability == "disconnected":
        return "disconnected"
    if observation.availability == "unknown":
        return "unknown"
    if _is_operator_blocked(observation):
        return "blocked_operator"
    if observation.business_state == "working":
        return "working"
    if _is_submit_ready(observation):
        return "submit_ready"
    return f"{observation.business_state}/{observation.input_mode}/{observation.ui_context}"


def _has_post_submit_activity(evidence: PostSubmitEvidence) -> bool:
    """Return whether anchored evidence shows post-submit activity."""

    return evidence.saw_working or evidence.saw_projection_change


def _seconds(value: float) -> timedelta:
    """Return one duration as a scheduler-friendly timedelta."""

    return timedelta(seconds=value)


def _is_readiness_snapshot(snapshot: ReadinessSnapshot | None) -> bool:
    """Return whether one optional readiness snapshot is present."""

    return snapshot is not None


def _readiness_reducer_snapshot(
    state: _ReadinessReducerState,
) -> ReadinessSnapshot | None:
    """Return the optional readiness snapshot from one reducer state."""

    return state.snapshot


def _is_anchored_completion_snapshot(
    snapshot: AnchoredCompletionSnapshot | None,
) -> bool:
    """Return whether one optional anchored-completion snapshot is present."""

    return snapshot is not None


def _anchored_completion_reducer_snapshot(
    state: _AnchoredCompletionReducerState,
) -> AnchoredCompletionSnapshot | None:
    """Return the optional anchored-completion snapshot from one reducer state."""

    return state.snapshot
