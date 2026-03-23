"""Harness-owned compatibility wrapper over the shared replay reducer."""

from __future__ import annotations

from typing import Any, Callable

from reactivex import abc

from houmao.shared_tui_tracking.reducer import StreamStateReducer as _SharedStreamStateReducer


TraceWriter = Callable[[str, dict[str, Any]], None]


class StreamStateReducer(_SharedStreamStateReducer):
    """Compatibility wrapper that binds the shared replay reducer to Claude."""

    def __init__(
        self,
        *,
        observed_version: str | None,
        settle_seconds: float,
        scheduler: abc.SchedulerBase,
        trace_writer: TraceWriter | None = None,
    ) -> None:
        """Initialize one Claude-bound replay reducer."""

        super().__init__(
            tool="claude",
            observed_version=observed_version,
            settle_seconds=settle_seconds,
            scheduler=scheduler,
            trace_writer=trace_writer,
        )
