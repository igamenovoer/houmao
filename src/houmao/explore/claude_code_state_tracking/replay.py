"""ReactiveX-driven replay helpers for recorded Claude observations."""

from __future__ import annotations

from typing import Callable

from reactivex.subject import Subject
from reactivex.testing import TestScheduler

from houmao.explore.claude_code_state_tracking.models import (
    RecordedObservation,
    ReplayEvent,
    TimelineState,
)
from houmao.explore.claude_code_state_tracking.state_reducer import StreamStateReducer


class ReplayTracker(StreamStateReducer):
    """Backward-compatible replay tracker wrapper over the shared reducer."""


def replay_timeline(
    *,
    observations: list[RecordedObservation],
    observed_version: str | None,
    settle_seconds: float,
) -> tuple[list[TimelineState], list[ReplayEvent]]:
    """Replay one recorded observation list through the shared reducer."""

    scheduler = TestScheduler()
    subject: Subject[RecordedObservation] = Subject()
    tracker = ReplayTracker(
        observed_version=observed_version,
        settle_seconds=settle_seconds,
        scheduler=scheduler,
    )
    timeline: list[TimelineState] = []
    subject.subscribe(lambda observation: timeline.append(tracker.process_observation(observation)))

    for observation in observations:
        scheduler.schedule_absolute(
            observation.elapsed_seconds,
            _build_emit_action(subject=subject, observation=observation),
        )
    if observations:
        scheduler.advance_to(observations[-1].elapsed_seconds + settle_seconds + 1.0)

    return timeline, tracker.events


def _build_emit_action(
    *, subject: Subject[RecordedObservation], observation: RecordedObservation
) -> Callable[[TestScheduler, object | None], None]:
    """Return one scheduled emission action for a replay observation."""

    def _emit(_scheduler: TestScheduler, _state: object | None = None) -> None:
        """Emit one recorded observation into the replay subject."""

        subject.on_next(observation)

    return _emit
