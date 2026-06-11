"""Volatile destination fallback state for Houmao AG-UI publishing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import threading
from typing import Literal

AgUiActiveThreadSource = Literal["gui_button", "gui_connect", "manual"]
AgUiLastSentSource = Literal["explicit", "event", "connection", "active_thread"]
AgUiDestinationSource = AgUiLastSentSource | Literal["default_sink"]


@dataclass(frozen=True)
class AgUiThreadDestination:
    """One optional AG-UI thread destination slot."""

    status: Literal["empty", "active", "sent"]
    thread_id: str | None
    updated_at_utc: datetime | None = None
    source: str | None = None


class AgUiDestinationState:
    """Thread-safe process-local destination fallback state."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        """Initialize empty destination fallback state."""

        self.m_lock: threading.Lock = threading.Lock()
        self.m_clock: Callable[[], datetime] = clock or (lambda: datetime.now(UTC))
        self.m_active_thread: AgUiThreadDestination = AgUiThreadDestination(
            status="empty",
            thread_id=None,
        )
        self.m_last_sent_thread: AgUiThreadDestination = AgUiThreadDestination(
            status="empty",
            thread_id=None,
        )

    @property
    def active_thread(self) -> AgUiThreadDestination:
        """Return the current GUI-selected active thread state."""

        with self.m_lock:
            return self.m_active_thread

    @property
    def last_sent_thread(self) -> AgUiThreadDestination:
        """Return the current gateway-published thread state."""

        with self.m_lock:
            return self.m_last_sent_thread

    def set_active_thread(
        self,
        thread_id: str,
        *,
        source: AgUiActiveThreadSource = "manual",
    ) -> AgUiThreadDestination:
        """Set the current GUI-selected active thread."""

        normalized = _normalize_thread_id(thread_id)
        if normalized is None:
            raise ValueError("active AG-UI thread id must be non-empty.")
        state = AgUiThreadDestination(
            status="active",
            thread_id=normalized,
            updated_at_utc=self.m_clock(),
            source=source,
        )
        with self.m_lock:
            self.m_active_thread = state
        return state

    def clear_active_thread(self, *, expected_thread_id: str | None = None) -> AgUiThreadDestination:
        """Clear the active thread without mutating last-sent-thread.

        If `expected_thread_id` is provided, clear only when the current active
        thread still matches it. This prevents a stale pane close from clearing a
        newer active selection made by another pane.
        """

        state = AgUiThreadDestination(status="empty", thread_id=None)
        with self.m_lock:
            expected = _normalize_optional_thread_id(expected_thread_id)
            if expected is not None and self.m_active_thread.thread_id != expected:
                return self.m_active_thread
            self.m_active_thread = state
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
        """Return active-thread and last-sent-thread atomically."""

        with self.m_lock:
            return self.m_active_thread, self.m_last_sent_thread


def _normalize_thread_id(value: str) -> str | None:
    """Return a non-empty normalized thread id."""

    normalized = value.strip()
    return normalized or None


def _normalize_optional_thread_id(value: str | None) -> str | None:
    """Return a normalized optional thread id."""

    if value is None:
        return None
    return _normalize_thread_id(value)


__all__ = [
    "AgUiDestinationSource",
    "AgUiDestinationState",
    "AgUiActiveThreadSource",
    "AgUiLastSentSource",
    "AgUiThreadDestination",
]
