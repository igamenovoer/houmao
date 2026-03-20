"""ReactiveX-driven replay helpers for recorded Claude observations."""

from __future__ import annotations

from houmao.explore.claude_code_state_tracking.models import (
    RecordedInputEvent,
    RecordedObservation,
    ReplayEvent,
    TimelineState,
)
from houmao.shared_tui_tracking.reducer import replay_timeline as _shared_replay_timeline


def replay_timeline(
    *,
    observations: list[RecordedObservation],
    observed_version: str | None,
    settle_seconds: float,
    input_events: list[RecordedInputEvent] | None = None,
) -> tuple[list[TimelineState], list[ReplayEvent]]:
    """Replay one recorded observation list through the shared reducer."""

    return _shared_replay_timeline(
        observations=observations,
        tool="claude",
        observed_version=observed_version,
        settle_seconds=settle_seconds,
        input_events=input_events,
    )
