"""ReactiveX-based shadow turn monitoring for CAO shadow-only sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, TypeAlias, TypeGuard, cast

from reactivex import Observable, abc, operators as ops

from houmao.cao.models import CaoTerminalOutputResponse
from houmao.lifecycle import (
    AnchoredCompletionSnapshot,
    LifecycleObservation,
    ReadinessSnapshot,
    build_anchored_completion_pipeline as build_shared_anchored_completion_pipeline,
    build_readiness_pipeline as build_shared_readiness_pipeline,
    normalize_projection_text,
)

from .shadow_parser_core import (
    ANOMALY_STALLED_ENTERED,
    ANOMALY_STALLED_RECOVERED,
    DialogProjection,
    ParsedShadowSnapshot,
    ShadowParserAnomaly,
)

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
class _ReadinessResultState:
    """Accumulated readiness anomalies and optional terminal result."""

    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    result: ReadyResult | BlockedResult | FailedResult | StalledResult | None = None


@dataclass(frozen=True)
class _CompletionResultState:
    """Accumulated completion anomalies and optional terminal result."""

    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    result: CompletedResult | BlockedResult | FailedResult | StalledResult | None = None


def build_readiness_pipeline(
    source: Observable[ShadowObservation],
    *,
    stall_timeout_seconds: float,
    scheduler: abc.SchedulerBase,
) -> Observable[PipelineResult]:
    """Build the readiness monitoring pipeline."""

    lifecycle_source = source.pipe(
        ops.map(_to_lifecycle_observation),
        ops.share(),
    )
    snapshots = build_shared_readiness_pipeline(
        lifecycle_source,
        stall_timeout_seconds=stall_timeout_seconds,
        scheduler=scheduler,
    )
    states = snapshots.pipe(
        ops.scan(_reduce_readiness_snapshot, seed=_ReadinessResultState()),
    )
    return cast(
        Observable[PipelineResult],
        states.pipe(
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

    lifecycle_source = source.pipe(
        ops.map(_to_lifecycle_observation),
        ops.share(),
    )
    snapshots = build_shared_anchored_completion_pipeline(
        lifecycle_source,
        baseline_projection_text=baseline_projection.normalized_text,
        stability_seconds=stability_seconds,
        stall_timeout_seconds=stall_timeout_seconds,
        scheduler=scheduler,
    )

    def _reduce_snapshot(
        state: _CompletionResultState,
        snapshot: AnchoredCompletionSnapshot,
    ) -> _CompletionResultState:
        anomalies = _updated_anomalies(
            anomalies=state.anomalies,
            snapshot=snapshot,
            phase="completion",
        )
        observation = _shadow_observation(snapshot.observation)
        completion_payload: dict[str, object] | None = None
        if completion_observer is not None and (
            snapshot.saw_working or snapshot.saw_projection_change
        ):
            completion_payload = completion_observer(
                observation.output.output,
                observation.snapshot,
                baseline_projection,
            )

        if completion_payload is not None:
            result: CompletedResult | BlockedResult | FailedResult | StalledResult | None = (
                CompletedResult(
                    observation=observation,
                    anomalies=anomalies,
                    completion_payload=completion_payload,
                )
            )
        elif snapshot.status == "completed":
            result = CompletedResult(observation=observation, anomalies=anomalies)
        elif snapshot.status == "blocked":
            result = BlockedResult(observation=observation, anomalies=anomalies)
        elif snapshot.status == "failed":
            result = FailedResult(observation=observation, anomalies=anomalies)
        elif snapshot.status == "stalled":
            result = StalledResult(
                observation=observation,
                anomalies=anomalies,
                elapsed_unknown_seconds=snapshot.unknown_elapsed_seconds or 0.0,
                elapsed_stalled_seconds=snapshot.elapsed_stalled_seconds,
            )
        else:
            result = None
        return _CompletionResultState(anomalies=anomalies, result=result)

    states = snapshots.pipe(
        ops.scan(_reduce_snapshot, seed=_CompletionResultState()),
    )
    return cast(
        Observable[PipelineResult],
        states.pipe(
            ops.map(_completion_state_result),
            ops.filter(_is_pipeline_result),
        ),
    )


def _reduce_readiness_snapshot(
    state: _ReadinessResultState,
    snapshot: ReadinessSnapshot,
) -> _ReadinessResultState:
    """Reduce one readiness snapshot into anomalies and terminal output."""

    anomalies = _updated_anomalies(
        anomalies=state.anomalies,
        snapshot=snapshot,
        phase="readiness",
    )
    observation = _shadow_observation(snapshot.observation)
    if snapshot.status == "ready":
        result: ReadyResult | BlockedResult | FailedResult | StalledResult | None = ReadyResult(
            observation=observation,
            anomalies=anomalies,
        )
    elif snapshot.status == "blocked":
        result = BlockedResult(observation=observation, anomalies=anomalies)
    elif snapshot.status == "failed":
        result = FailedResult(observation=observation, anomalies=anomalies)
    elif snapshot.status == "stalled":
        result = StalledResult(
            observation=observation,
            anomalies=anomalies,
            elapsed_unknown_seconds=snapshot.unknown_elapsed_seconds or 0.0,
            elapsed_stalled_seconds=snapshot.elapsed_stalled_seconds,
        )
    else:
        result = None
    return _ReadinessResultState(anomalies=anomalies, result=result)


def _readiness_state_result(
    state: _ReadinessResultState,
) -> ReadyResult | BlockedResult | FailedResult | StalledResult | None:
    """Return the optional readiness terminal result from one reducer state."""

    return state.result


def _updated_anomalies(
    *,
    anomalies: tuple[ShadowParserAnomaly, ...],
    snapshot: ReadinessSnapshot | AnchoredCompletionSnapshot,
    phase: Literal["readiness", "completion"],
) -> tuple[ShadowParserAnomaly, ...]:
    """Return anomalies updated from one lifecycle snapshot."""

    updated = anomalies
    if snapshot.entered_stalled:
        updated = updated + (
            _stalled_entered_anomaly(
                phase=phase,
                elapsed_unknown_seconds=snapshot.unknown_elapsed_seconds or 0.0,
                parser_family=snapshot.observation.parser_family,
            ),
        )
    if snapshot.recovered_from_stalled:
        updated = updated + (
            _stalled_recovered_anomaly(
                phase=phase,
                elapsed_stalled_seconds=snapshot.elapsed_stalled_seconds or 0.0,
                parser_family=snapshot.observation.parser_family,
                recovered_to=snapshot.recovered_to or "unknown",
            ),
        )
    return updated


def _completion_state_result(
    state: _CompletionResultState,
) -> CompletedResult | BlockedResult | FailedResult | StalledResult | None:
    """Return the optional completion terminal result from one reducer state."""

    return state.result


def _to_lifecycle_observation(observation: ShadowObservation) -> LifecycleObservation:
    """Convert one shadow observation into the shared lifecycle shape."""

    surface_assessment = observation.snapshot.surface_assessment
    projection = observation.projection
    return LifecycleObservation(
        availability=surface_assessment.availability,
        business_state=surface_assessment.business_state,
        input_mode=surface_assessment.input_mode,
        ui_context=surface_assessment.ui_context,
        normalized_projection_text=normalize_projection_text(projection.normalized_text),
        baseline_invalidated=surface_assessment.parser_metadata.baseline_invalidated,
        operator_blocked_excerpt=surface_assessment.operator_blocked_excerpt,
        monotonic_ts=observation.monotonic_ts,
        parser_family=observation.parser_family,
        source_payload=observation,
    )


def _shadow_observation(observation: LifecycleObservation) -> ShadowObservation:
    """Return the original shadow observation carried by one lifecycle observation."""

    source_payload = observation.source_payload
    if not isinstance(source_payload, ShadowObservation):
        raise RuntimeError("Lifecycle observation is missing the originating shadow observation.")
    return source_payload


def _is_pipeline_result(result: PipelineResult | None) -> TypeGuard[PipelineResult]:
    """Return whether one optional pipeline result is present."""

    return result is not None


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


def _format_seconds(value: float) -> str:
    """Format one duration for anomaly metadata."""

    return f"{value:.3f}".rstrip("0").rstrip(".")
