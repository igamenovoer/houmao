"""ReactiveX-based shadow turn monitoring for CAO shadow-only sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Literal, TypeAlias, TypeGuard, cast

import reactivex
from reactivex import Observable, abc, operators as ops

from houmao.cao.models import CaoTerminalOutputResponse

from .shadow_parser_core import (
    ANOMALY_STALLED_ENTERED,
    ANOMALY_STALLED_RECOVERED,
    DialogProjection,
    ParsedShadowSnapshot,
    ShadowParserAnomaly,
    SurfaceAssessment,
    is_operator_blocked,
    is_submit_ready,
    is_unknown_for_stall,
)

ReadinessStatus: TypeAlias = Literal["ready", "blocked", "failed", "unknown", "waiting"]
CompletionStatus: TypeAlias = Literal[
    "blocked",
    "candidate_complete",
    "failed",
    "in_progress",
    "unknown",
    "waiting",
]
CompletionObserver: TypeAlias = Callable[
    [str, ParsedShadowSnapshot, DialogProjection],
    dict[str, object] | None,
]


@dataclass(frozen=True)
class ShadowObservation:
    """One CAO shadow observation flowing through the monitor pipelines."""

    output: CaoTerminalOutputResponse
    snapshot: ParsedShadowSnapshot
    projection: DialogProjection
    monotonic_ts: float
    parser_family: str


@dataclass(frozen=True)
class PostSubmitEvidence:
    """Accumulated post-submit evidence used by the completion pipeline."""

    saw_working: bool
    saw_projection_change: bool
    baseline_normalized_text: str


@dataclass(frozen=True)
class ReadyResult:
    """Terminal readiness result for submit-ready shadow surfaces."""

    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    kind: Literal["ready"] = "ready"


@dataclass(frozen=True)
class CompletedResult:
    """Terminal completion result for one shadow turn."""

    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    completion_payload: dict[str, object] | None = None
    kind: Literal["completed"] = "completed"


@dataclass(frozen=True)
class BlockedResult:
    """Blocked-operator terminal result."""

    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    kind: Literal["blocked"] = "blocked"


@dataclass(frozen=True)
class FailedResult:
    """Unsupported/disconnected terminal result."""

    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    kind: Literal["failed"] = "failed"


@dataclass(frozen=True)
class StalledResult:
    """Shadow lifecycle entered stalled state."""

    observation: ShadowObservation
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    elapsed_unknown_seconds: float = 0.0
    elapsed_stalled_seconds: float | None = None
    kind: Literal["stalled"] = "stalled"


@dataclass(frozen=True)
class TimedOutResult:
    """Global shadow wait timed out before a terminal result arrived."""

    observation: ShadowObservation | None
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    shadow_status: str = "unknown"
    kind: Literal["timed_out"] = "timed_out"


PipelineResult: TypeAlias = (
    ReadyResult | CompletedResult | BlockedResult | FailedResult | StalledResult | TimedOutResult
)


@dataclass(frozen=True)
class _ReadinessClassification:
    """One readiness classification derived from a shadow observation."""

    observation: ShadowObservation
    status: ReadinessStatus
    recovered_to: str


@dataclass(frozen=True)
class _ReadinessObservationEvent:
    """One readiness observation event consumed by the reducer."""

    classification: _ReadinessClassification


@dataclass(frozen=True)
class _ReadinessStallTimerEvent:
    """One readiness stall-timer event."""

    observation: ShadowObservation
    fired_monotonic_ts: float


ReadinessEvent: TypeAlias = _ReadinessObservationEvent | _ReadinessStallTimerEvent


@dataclass(frozen=True)
class _ReadinessPipelineState:
    """Readiness pipeline reducer state."""

    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    unknown_started_at: float | None = None
    stalled_started_at: float | None = None
    is_stalled: bool = False
    result: ReadyResult | BlockedResult | FailedResult | StalledResult | None = None


@dataclass(frozen=True)
class _CompletionAccumulatorState:
    """Completion accumulator state emitted by `ops.scan()`."""

    observation: ShadowObservation | None
    evidence: PostSubmitEvidence
    projection_key: str
    frozen_projection_key: str | None = None


@dataclass(frozen=True)
class _CompletionClassification:
    """One completion classification derived from accumulated evidence."""

    observation: ShadowObservation
    evidence: PostSubmitEvidence
    projection_key: str
    status: CompletionStatus
    recovered_to: str


@dataclass(frozen=True)
class _CompletionObservationEvent:
    """One completion observation event consumed by the reducer."""

    classification: _CompletionClassification


@dataclass(frozen=True)
class _CompletionStallTimerEvent:
    """One completion stall-timer event."""

    observation: ShadowObservation
    fired_monotonic_ts: float


@dataclass(frozen=True)
class _CompletionStableTimerEvent:
    """One completion-stability timer event."""

    classification: _CompletionClassification


@dataclass(frozen=True)
class _CompletionObserverEvent:
    """One mailbox-observer bypass event."""

    classification: _CompletionClassification
    completion_payload: dict[str, object]


CompletionEvent: TypeAlias = (
    _CompletionObservationEvent
    | _CompletionStallTimerEvent
    | _CompletionStableTimerEvent
    | _CompletionObserverEvent
)


@dataclass(frozen=True)
class _CompletionPipelineState:
    """Completion pipeline reducer state."""

    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    unknown_started_at: float | None = None
    stalled_started_at: float | None = None
    is_stalled: bool = False
    result: CompletedResult | BlockedResult | FailedResult | StalledResult | None = None


def normalize_projection_text(text: str) -> str:
    """Return a lifecycle-oriented normalized projection key."""

    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def build_readiness_pipeline(
    source: Observable[ShadowObservation],
    *,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[PipelineResult]:
    """Build the readiness monitoring pipeline."""

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
    return cast(
        Observable[PipelineResult],
        events.pipe(
            ops.scan(_reduce_readiness_event, seed=_ReadinessPipelineState()),
            ops.map(_readiness_state_result),
            ops.filter(_is_pipeline_result),
        ),
    )


def build_completion_pipeline(
    source: Observable[ShadowObservation],
    *,
    stability_seconds: float,
    stall_timeout_seconds: float,
    baseline_projection: DialogProjection,
    completion_observer: CompletionObserver | None,
    scheduler: abc.SchedulerBase,
) -> Observable[PipelineResult]:
    """Build the completion monitoring pipeline."""

    def _map_stall_timer(
        classification: _CompletionClassification,
    ) -> Observable[_CompletionStallTimerEvent]:
        return _map_completion_stall_timer(
            classification=classification,
            stall_timeout_seconds=stall_timeout_seconds,
            scheduler=scheduler,
        )

    def _map_stability_timer(
        classification: _CompletionClassification,
    ) -> Observable[_CompletionStableTimerEvent]:
        return _map_completion_stability_timer(
            classification=classification,
            stability_seconds=stability_seconds,
            scheduler=scheduler,
        )

    def _map_observer_event(
        classification: _CompletionClassification,
    ) -> _CompletionObserverEvent | None:
        return _map_completion_observer_event(
            classification=classification,
            baseline_projection=baseline_projection,
            completion_observer=completion_observer,
        )

    baseline_projection_key = normalize_projection_text(baseline_projection.normalized_text)
    accumulated = source.pipe(
        ops.scan(
            _reduce_completion_accumulator,
            seed=_CompletionAccumulatorState(
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
        ops.map(_classify_completion),
        ops.share(),
    )
    classified_changes = classified.pipe(
        ops.distinct_until_changed(_completion_change_signature),
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
    observer_events = classified.pipe(
        ops.filter(_has_post_submit_activity),
        ops.map(_map_observer_event),
        ops.filter(_is_completion_observer_event),
    )
    events = reactivex.merge(
        classified.pipe(ops.map(_map_completion_observation_event)),
        stall_timer_events,
        stability_timer_events,
        observer_events,
    )
    return cast(
        Observable[PipelineResult],
        events.pipe(
            ops.scan(_reduce_completion_event, seed=_CompletionPipelineState()),
            ops.map(_completion_state_result),
            ops.filter(_is_pipeline_result),
        ),
    )


def _map_readiness_stall_timer(
    *,
    classification: _ReadinessClassification,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[_ReadinessStallTimerEvent]:
    """Map one readiness classification to its stall-timer stream."""

    if classification.status != "unknown":
        return cast(Observable[_ReadinessStallTimerEvent], reactivex.never())
    return _build_readiness_stall_timer(
        classification=classification,
        stall_timeout_seconds=stall_timeout_seconds,
        scheduler=scheduler,
    )


def _map_readiness_observation_event(
    classification: _ReadinessClassification,
) -> ReadinessEvent:
    """Wrap one readiness classification as a reducer event."""

    return _ReadinessObservationEvent(classification=classification)


def _readiness_state_result(state: _ReadinessPipelineState) -> PipelineResult | None:
    """Extract the current readiness result from reducer state."""

    return state.result


def _map_completion_stall_timer(
    *,
    classification: _CompletionClassification,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[_CompletionStallTimerEvent]:
    """Map one completion classification to its stall-timer stream."""

    if classification.status != "unknown":
        return cast(Observable[_CompletionStallTimerEvent], reactivex.never())
    return _build_completion_stall_timer(
        classification=classification,
        stall_timeout_seconds=stall_timeout_seconds,
        scheduler=scheduler,
    )


def _map_completion_stability_timer(
    *,
    classification: _CompletionClassification,
    stability_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[_CompletionStableTimerEvent]:
    """Map one completion classification to its stability-timer stream."""

    if classification.status != "candidate_complete":
        return cast(Observable[_CompletionStableTimerEvent], reactivex.never())
    return _build_completion_stability_timer(
        classification=classification,
        stability_seconds=stability_seconds,
        scheduler=scheduler,
    )


def _map_completion_observer_event(
    *,
    classification: _CompletionClassification,
    baseline_projection: DialogProjection,
    completion_observer: CompletionObserver | None,
) -> _CompletionObserverEvent | None:
    """Map one completion classification to an observer bypass event."""

    return _build_completion_observer_event(
        classification=classification,
        baseline_projection=baseline_projection,
        completion_observer=completion_observer,
    )


def _map_completion_observation_event(
    classification: _CompletionClassification,
) -> CompletionEvent:
    """Wrap one completion classification as a reducer event."""

    return _CompletionObservationEvent(classification=classification)


def _completion_state_result(state: _CompletionPipelineState) -> PipelineResult | None:
    """Extract the current completion result from reducer state."""

    return state.result


def _classify_readiness(observation: ShadowObservation) -> _ReadinessClassification:
    """Classify one observation for readiness monitoring."""

    surface_assessment = observation.snapshot.surface_assessment
    recovered_to = _surface_status_label(surface_assessment)
    if surface_assessment.availability in {"unsupported", "disconnected"}:
        return _ReadinessClassification(
            observation=observation,
            status="failed",
            recovered_to=recovered_to,
        )
    if is_operator_blocked(surface_assessment):
        return _ReadinessClassification(
            observation=observation,
            status="blocked",
            recovered_to="blocked_operator",
        )
    if is_unknown_for_stall(surface_assessment):
        return _ReadinessClassification(
            observation=observation,
            status="unknown",
            recovered_to=recovered_to,
        )
    if is_submit_ready(surface_assessment):
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


def _build_readiness_stall_timer(
    *,
    classification: _ReadinessClassification,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[_ReadinessStallTimerEvent]:
    """Return one readiness stall-timer observable."""

    return reactivex.timer(_seconds(stall_timeout_seconds), scheduler=scheduler).pipe(
        ops.map(
            lambda _: _ReadinessStallTimerEvent(
                observation=classification.observation,
                fired_monotonic_ts=classification.observation.monotonic_ts + stall_timeout_seconds,
            )
        )
    )


def _reduce_readiness_event(
    state: _ReadinessPipelineState,
    event: ReadinessEvent,
) -> _ReadinessPipelineState:
    """Reduce one readiness event into the current readiness state."""

    if isinstance(event, _ReadinessObservationEvent):
        classification = event.classification
        if classification.status == "unknown":
            unknown_started_at = state.unknown_started_at
            if unknown_started_at is None:
                unknown_started_at = classification.observation.monotonic_ts
            return _ReadinessPipelineState(
                anomalies=state.anomalies,
                unknown_started_at=unknown_started_at,
                stalled_started_at=state.stalled_started_at,
                is_stalled=state.is_stalled,
                result=None,
            )

        anomalies, is_stalled = _recover_from_stalled(
            anomalies=state.anomalies,
            is_stalled=state.is_stalled,
            stalled_started_at=state.stalled_started_at,
            observation=classification.observation,
            phase="readiness",
            recovered_to=classification.recovered_to,
        )
        return _ReadinessPipelineState(
            anomalies=anomalies,
            unknown_started_at=None,
            stalled_started_at=None,
            is_stalled=is_stalled,
            result=_readiness_result_for_classification(
                classification=classification,
                anomalies=anomalies,
            ),
        )

    if state.is_stalled or state.unknown_started_at is None:
        return state

    elapsed_unknown_seconds = max(event.fired_monotonic_ts - state.unknown_started_at, 0.0)
    anomalies = state.anomalies + (
        _stalled_entered_anomaly(
            phase="readiness",
            elapsed_unknown_seconds=elapsed_unknown_seconds,
            parser_family=event.observation.parser_family,
        ),
    )
    return _ReadinessPipelineState(
        anomalies=anomalies,
        unknown_started_at=state.unknown_started_at,
        stalled_started_at=event.fired_monotonic_ts,
        is_stalled=True,
        result=StalledResult(
            observation=event.observation,
            anomalies=anomalies,
            elapsed_unknown_seconds=elapsed_unknown_seconds,
            elapsed_stalled_seconds=0.0,
        ),
    )


def _readiness_result_for_classification(
    *,
    classification: _ReadinessClassification,
    anomalies: tuple[ShadowParserAnomaly, ...],
) -> ReadyResult | BlockedResult | FailedResult | None:
    """Return a readiness result for one classified readiness observation."""

    if classification.status == "ready":
        return ReadyResult(observation=classification.observation, anomalies=anomalies)
    if classification.status == "blocked":
        return BlockedResult(observation=classification.observation, anomalies=anomalies)
    if classification.status == "failed":
        return FailedResult(observation=classification.observation, anomalies=anomalies)
    return None


def _reduce_completion_accumulator(
    state: _CompletionAccumulatorState,
    observation: ShadowObservation,
) -> _CompletionAccumulatorState:
    """Accumulate post-submit evidence from one completion observation."""

    projection_key = normalize_projection_text(observation.projection.normalized_text)
    frozen_projection_key = state.frozen_projection_key
    if (
        frozen_projection_key is None
        and observation.snapshot.surface_assessment.parser_metadata.baseline_invalidated
    ):
        # Preserve the current unassociated projection as the completion surface
        # until issue-005 revisits baseline invalidation semantics explicitly.
        frozen_projection_key = projection_key
    effective_projection_key = frozen_projection_key or projection_key
    surface_assessment = observation.snapshot.surface_assessment
    evidence = PostSubmitEvidence(
        saw_working=state.evidence.saw_working or surface_assessment.business_state == "working",
        saw_projection_change=(
            state.evidence.saw_projection_change
            or effective_projection_key != state.evidence.baseline_normalized_text
        ),
        baseline_normalized_text=state.evidence.baseline_normalized_text,
    )
    return _CompletionAccumulatorState(
        observation=observation,
        evidence=evidence,
        projection_key=effective_projection_key,
        frozen_projection_key=frozen_projection_key,
    )


def _classify_completion(state: _CompletionAccumulatorState) -> _CompletionClassification:
    """Classify one accumulated completion observation."""

    observation = state.observation
    if observation is None:
        raise RuntimeError("Completion classification requires an observation.")

    surface_assessment = observation.snapshot.surface_assessment
    recovered_to = _surface_status_label(surface_assessment)
    if surface_assessment.availability in {"unsupported", "disconnected"}:
        return _CompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="failed",
            recovered_to=recovered_to,
        )
    if is_operator_blocked(surface_assessment):
        return _CompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="blocked",
            recovered_to="blocked_operator",
        )
    if is_unknown_for_stall(surface_assessment):
        return _CompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="unknown",
            recovered_to=recovered_to,
        )
    if surface_assessment.business_state == "working":
        return _CompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="in_progress",
            recovered_to=recovered_to,
        )
    if is_submit_ready(surface_assessment) and _has_post_submit_activity_from_evidence(
        state.evidence
    ):
        return _CompletionClassification(
            observation=observation,
            evidence=state.evidence,
            projection_key=state.projection_key,
            status="candidate_complete",
            recovered_to="completed",
        )
    return _CompletionClassification(
        observation=observation,
        evidence=state.evidence,
        projection_key=state.projection_key,
        status="waiting",
        recovered_to=recovered_to if not is_submit_ready(surface_assessment) else "submit_ready",
    )


def _completion_change_signature(classification: _CompletionClassification) -> tuple[object, ...]:
    """Return the signature used to reset completion stability timing."""

    surface_assessment = classification.observation.snapshot.surface_assessment
    return (
        classification.status,
        surface_assessment.availability,
        surface_assessment.business_state,
        surface_assessment.input_mode,
        classification.projection_key,
        classification.evidence.saw_working,
        classification.evidence.saw_projection_change,
    )


def _build_completion_stall_timer(
    *,
    classification: _CompletionClassification,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[_CompletionStallTimerEvent]:
    """Return one completion stall-timer observable."""

    return reactivex.timer(_seconds(stall_timeout_seconds), scheduler=scheduler).pipe(
        ops.map(
            lambda _: _CompletionStallTimerEvent(
                observation=classification.observation,
                fired_monotonic_ts=classification.observation.monotonic_ts + stall_timeout_seconds,
            )
        )
    )


def _build_completion_stability_timer(
    *,
    classification: _CompletionClassification,
    stability_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[_CompletionStableTimerEvent]:
    """Return one completion-stability timer observable."""

    return reactivex.timer(_seconds(stability_seconds), scheduler=scheduler).pipe(
        ops.map(lambda _: _CompletionStableTimerEvent(classification=classification))
    )


def _build_completion_observer_event(
    *,
    classification: _CompletionClassification,
    baseline_projection: DialogProjection,
    completion_observer: CompletionObserver | None,
) -> _CompletionObserverEvent | None:
    """Return one mailbox bypass event when the observer has a definitive payload."""

    if completion_observer is None:
        return None
    payload = completion_observer(
        classification.observation.output.output,
        classification.observation.snapshot,
        baseline_projection,
    )
    if payload is None:
        return None
    return _CompletionObserverEvent(
        classification=classification,
        completion_payload=payload,
    )


def _reduce_completion_event(
    state: _CompletionPipelineState,
    event: CompletionEvent,
) -> _CompletionPipelineState:
    """Reduce one completion event into the current completion state."""

    if isinstance(event, _CompletionObservationEvent):
        classification = event.classification
        if classification.status == "unknown":
            unknown_started_at = state.unknown_started_at
            if unknown_started_at is None:
                unknown_started_at = classification.observation.monotonic_ts
            return _CompletionPipelineState(
                anomalies=state.anomalies,
                unknown_started_at=unknown_started_at,
                stalled_started_at=state.stalled_started_at,
                is_stalled=state.is_stalled,
                result=None,
            )

        anomalies, is_stalled = _recover_from_stalled(
            anomalies=state.anomalies,
            is_stalled=state.is_stalled,
            stalled_started_at=state.stalled_started_at,
            observation=classification.observation,
            phase="completion",
            recovered_to=classification.recovered_to,
        )
        return _CompletionPipelineState(
            anomalies=anomalies,
            unknown_started_at=None,
            stalled_started_at=None,
            is_stalled=is_stalled,
            result=_completion_terminal_result_for_classification(
                classification=classification,
                anomalies=anomalies,
            ),
        )

    if isinstance(event, _CompletionStallTimerEvent):
        if state.is_stalled or state.unknown_started_at is None:
            return state

        elapsed_unknown_seconds = max(event.fired_monotonic_ts - state.unknown_started_at, 0.0)
        anomalies = state.anomalies + (
            _stalled_entered_anomaly(
                phase="completion",
                elapsed_unknown_seconds=elapsed_unknown_seconds,
                parser_family=event.observation.parser_family,
            ),
        )
        return _CompletionPipelineState(
            anomalies=anomalies,
            unknown_started_at=state.unknown_started_at,
            stalled_started_at=event.fired_monotonic_ts,
            is_stalled=True,
            result=StalledResult(
                observation=event.observation,
                anomalies=anomalies,
                elapsed_unknown_seconds=elapsed_unknown_seconds,
                elapsed_stalled_seconds=0.0,
            ),
        )

    if isinstance(event, _CompletionStableTimerEvent):
        anomalies, is_stalled = _recover_from_stalled(
            anomalies=state.anomalies,
            is_stalled=state.is_stalled,
            stalled_started_at=state.stalled_started_at,
            observation=event.classification.observation,
            phase="completion",
            recovered_to=event.classification.recovered_to,
        )
        return _CompletionPipelineState(
            anomalies=anomalies,
            unknown_started_at=None,
            stalled_started_at=None,
            is_stalled=is_stalled,
            result=CompletedResult(
                observation=event.classification.observation,
                anomalies=anomalies,
                completion_payload=None,
            ),
        )

    anomalies, is_stalled = _recover_from_stalled(
        anomalies=state.anomalies,
        is_stalled=state.is_stalled,
        stalled_started_at=state.stalled_started_at,
        observation=event.classification.observation,
        phase="completion",
        recovered_to=event.classification.recovered_to,
    )
    return _CompletionPipelineState(
        anomalies=anomalies,
        unknown_started_at=None,
        stalled_started_at=None,
        is_stalled=is_stalled,
        result=CompletedResult(
            observation=event.classification.observation,
            anomalies=anomalies,
            completion_payload=event.completion_payload,
        ),
    )


def _completion_terminal_result_for_classification(
    *,
    classification: _CompletionClassification,
    anomalies: tuple[ShadowParserAnomaly, ...],
) -> BlockedResult | FailedResult | None:
    """Return a completion result for one classified completion observation."""

    if classification.status == "blocked":
        return BlockedResult(observation=classification.observation, anomalies=anomalies)
    if classification.status == "failed":
        return FailedResult(observation=classification.observation, anomalies=anomalies)
    return None


def _recover_from_stalled(
    *,
    anomalies: tuple[ShadowParserAnomaly, ...],
    is_stalled: bool,
    stalled_started_at: float | None,
    observation: ShadowObservation,
    phase: Literal["readiness", "completion"],
    recovered_to: str,
) -> tuple[tuple[ShadowParserAnomaly, ...], bool]:
    """Return updated anomaly state after a stalled-to-known recovery."""

    if not is_stalled or stalled_started_at is None:
        return anomalies, False

    elapsed_stalled_seconds = max(observation.monotonic_ts - stalled_started_at, 0.0)
    recovered_anomalies = anomalies + (
        _stalled_recovered_anomaly(
            phase=phase,
            elapsed_stalled_seconds=elapsed_stalled_seconds,
            parser_family=observation.parser_family,
            recovered_to=recovered_to,
        ),
    )
    return recovered_anomalies, False


def _stalled_entered_anomaly(
    *,
    phase: Literal["readiness", "completion"],
    elapsed_unknown_seconds: float,
    parser_family: str,
) -> ShadowParserAnomaly:
    """Build one `stalled_entered` anomaly."""

    return ShadowParserAnomaly(
        code=ANOMALY_STALLED_ENTERED,
        message="Shadow status remained unknown and entered stalled lifecycle state",
        details={
            "phase": phase,
            "elapsed_unknown_seconds": _format_seconds(elapsed_unknown_seconds),
            "parser_family": parser_family,
        },
    )


def _stalled_recovered_anomaly(
    *,
    phase: Literal["readiness", "completion"],
    elapsed_stalled_seconds: float,
    parser_family: str,
    recovered_to: str,
) -> ShadowParserAnomaly:
    """Build one `stalled_recovered` anomaly."""

    return ShadowParserAnomaly(
        code=ANOMALY_STALLED_RECOVERED,
        message="Shadow status recovered from stalled to known state",
        details={
            "phase": phase,
            "elapsed_stalled_seconds": _format_seconds(elapsed_stalled_seconds),
            "parser_family": parser_family,
            "recovered_to": recovered_to,
        },
    )


def _has_post_submit_activity(classification: _CompletionClassification) -> bool:
    """Return whether the completion pipeline has seen post-submit activity."""

    return _has_post_submit_activity_from_evidence(classification.evidence)


def _has_post_submit_activity_from_evidence(evidence: PostSubmitEvidence) -> bool:
    """Return whether accumulated evidence shows post-submit progress."""

    return evidence.saw_working or evidence.saw_projection_change


def _is_completion_observer_event(
    event: _CompletionObserverEvent | None,
) -> TypeGuard[_CompletionObserverEvent]:
    """Return whether the mapped observer event is present."""

    return event is not None


def _is_pipeline_result(result: PipelineResult | None) -> TypeGuard[PipelineResult]:
    """Return whether the mapped pipeline result is present."""

    return result is not None


def _surface_status_label(surface_assessment: SurfaceAssessment) -> str:
    """Return a concise status label for diagnostics and recovery anomalies."""

    if surface_assessment.availability == "unsupported":
        return "unsupported"
    if surface_assessment.availability == "disconnected":
        return "disconnected"
    if surface_assessment.availability == "unknown":
        return "unknown"
    return f"{surface_assessment.business_state}+{surface_assessment.input_mode}"


def _seconds(value: float) -> timedelta:
    """Return one scheduler-relative duration."""

    return timedelta(seconds=value)


def _format_seconds(value: float) -> str:
    """Render one duration as a fixed-precision seconds string."""

    return f"{value:.3f}"
