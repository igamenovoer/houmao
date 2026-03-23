from __future__ import annotations

from reactivex.subject import Subject
from reactivex.testing import TestScheduler

from houmao.lifecycle.rx_lifecycle_kernel import (
    LifecycleObservation,
    build_anchored_completion_pipeline,
    build_readiness_pipeline,
)


def _observation(
    *,
    at: float,
    availability: str = "supported",
    business_state: str,
    input_mode: str,
    projection_text: str = "baseline",
    ui_context: str = "normal_prompt",
) -> LifecycleObservation:
    return LifecycleObservation(
        availability=availability,
        business_state=business_state,
        input_mode=input_mode,
        ui_context=ui_context,
        normalized_projection_text=projection_text,
        baseline_invalidated=False,
        operator_blocked_excerpt=None,
        monotonic_ts=at,
        parser_family="codex_shadow",
    )


def _emit(
    *,
    scheduler: TestScheduler,
    subject: Subject[LifecycleObservation],
    observation: LifecycleObservation,
) -> None:
    scheduler.advance_to(observation.monotonic_ts)
    subject.on_next(observation)


def test_readiness_kernel_recovers_after_stalled_unknown() -> None:
    scheduler = TestScheduler()
    subject: Subject[LifecycleObservation] = Subject()
    results: list[object] = []
    build_readiness_pipeline(
        subject,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(at=0.0, business_state="unknown", input_mode="unknown"),
    )
    scheduler.advance_to(5.0)
    assert results[-1].status == "stalled"
    assert results[-1].entered_stalled is True

    _emit(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(at=6.0, business_state="idle", input_mode="freeform"),
    )
    assert results[-1].status == "ready"
    assert results[-1].recovered_from_stalled is True
    assert results[-1].recovered_to == "submit_ready"


def test_anchored_completion_kernel_requires_post_submit_activity() -> None:
    scheduler = TestScheduler()
    subject: Subject[LifecycleObservation] = Subject()
    results: list[object] = []
    build_anchored_completion_pipeline(
        subject,
        baseline_projection_text="baseline",
        stability_seconds=1.0,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline",
        ),
    )

    assert results[-1].status == "waiting"


def test_anchored_completion_kernel_resets_debounce_on_projection_change() -> None:
    scheduler = TestScheduler()
    subject: Subject[LifecycleObservation] = Subject()
    results: list[object] = []
    build_anchored_completion_pipeline(
        subject,
        baseline_projection_text="baseline",
        stability_seconds=1.0,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=0.0,
            business_state="working",
            input_mode="freeform",
        ),
    )
    _emit(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=1.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline\nfirst answer",
        ),
    )
    assert results[-1].status == "candidate_complete"

    _emit(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=1.8,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline\nfirst answer\nmore",
        ),
    )
    assert results[-1].status == "candidate_complete"
    assert results[-1].candidate_elapsed_seconds == 0.0

    scheduler.advance_to(2.7)
    assert results[-1].status == "candidate_complete"

    scheduler.advance_to(2.8)
    assert results[-1].status == "completed"


def test_anchored_completion_kernel_recovers_from_stalled_unknown() -> None:
    scheduler = TestScheduler()
    subject: Subject[LifecycleObservation] = Subject()
    results: list[object] = []
    build_anchored_completion_pipeline(
        subject,
        baseline_projection_text="baseline",
        stability_seconds=1.0,
        stall_timeout_seconds=5.0,
        scheduler=scheduler,
    ).subscribe(results.append)

    _emit(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(at=0.0, business_state="unknown", input_mode="unknown"),
    )
    scheduler.advance_to(5.0)
    assert results[-1].status == "stalled"

    _emit(
        scheduler=scheduler,
        subject=subject,
        observation=_observation(
            at=6.0,
            business_state="idle",
            input_mode="freeform",
            projection_text="baseline",
        ),
    )
    assert results[-1].status == "waiting"
    assert results[-1].recovered_from_stalled is True
