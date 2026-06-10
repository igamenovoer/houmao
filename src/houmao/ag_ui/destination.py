"""Volatile destination fallback state for Houmao AG-UI publishing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import threading
from typing import Literal

AgUiLastBoundSource = Literal["gui_connect", "gui_view_change", "manual"]
AgUiLastSentSource = Literal["explicit", "event", "connection", "last_sent", "last_bound"]
AgUiDestinationSource = AgUiLastSentSource | Literal["default_sink"]


@dataclass(frozen=True)
class AgUiThreadDestination:
    """One optional AG-UI thread destination slot."""

    status: Literal["empty", "bound", "sent"]
    thread_id: str | None
    updated_at_utc: datetime | None = None
    source: str | None = None


class AgUiDestinationState:
    """Thread-safe process-local destination fallback state."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        """Initialize empty destination fallback state."""

        self.m_lock: threading.Lock = threading.Lock()
        self.m_clock: Callable[[], datetime] = clock or (lambda: datetime.now(UTC))
        self.m_last_bound_thread: AgUiThreadDestination = AgUiThreadDestination(
            status="empty",
            thread_id=None,
        )
        self.m_last_sent_thread: AgUiThreadDestination = AgUiThreadDestination(
            status="empty",
            thread_id=None,
        )

    @property
    def last_bound_thread(self) -> AgUiThreadDestination:
        """Return the current GUI-bound thread state."""

        with self.m_lock:
            return self.m_last_bound_thread

    @property
    def last_sent_thread(self) -> AgUiThreadDestination:
        """Return the current gateway-published thread state."""

        with self.m_lock:
            return self.m_last_sent_thread

    def set_last_bound_thread(
        self,
        thread_id: str,
        *,
        source: AgUiLastBoundSource = "manual",
    ) -> AgUiThreadDestination:
        """Set the current GUI-bound thread."""

        normalized = _normalize_thread_id(thread_id)
        if normalized is None:
            raise ValueError("last-bound AG-UI thread id must be non-empty.")
        state = AgUiThreadDestination(
            status="bound",
            thread_id=normalized,
            updated_at_utc=self.m_clock(),
            source=source,
        )
        with self.m_lock:
            self.m_last_bound_thread = state
        return state

    def clear_last_bound_thread(self) -> AgUiThreadDestination:
        """Clear the current GUI-bound thread without mutating last-sent-thread."""

        state = AgUiThreadDestination(status="empty", thread_id=None)
        with self.m_lock:
            self.m_last_bound_thread = state
        return state

    def set_last_sent_thread(
        self,
        thread_id: str,
        *,
        source: AgUiLastSentSource,
    ) -> AgUiThreadDestination:
        """Set the last concrete non-sink AG-UI publish destination."""

        normalized = _normalize_thread_id(thread_id)
        if normalized is None:
            raise ValueError("last-sent AG-UI thread id must be non-empty.")
        state = AgUiThreadDestination(
            status="sent",
            thread_id=normalized,
            updated_at_utc=self.m_clock(),
            source=source,
        )
        with self.m_lock:
            self.m_last_sent_thread = state
        return state

    def snapshot(self) -> tuple[AgUiThreadDestination, AgUiThreadDestination]:
        """Return last-bound-thread and last-sent-thread atomically."""

        with self.m_lock:
            return self.m_last_bound_thread, self.m_last_sent_thread


def _normalize_thread_id(value: str) -> str | None:
    """Return a non-empty normalized thread id."""

    normalized = value.strip()
    return normalized or None


__all__ = [
    "AgUiDestinationSource",
    "AgUiDestinationState",
    "AgUiLastBoundSource",
    "AgUiLastSentSource",
    "AgUiThreadDestination",
]
