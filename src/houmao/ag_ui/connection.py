"""Connection bookkeeping for Houmao AG-UI GUI attachments."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import threading
from uuid import uuid4

from houmao.ag_ui.models import AgUiConnectInput


@dataclass(frozen=True)
class AgUiConnectionRecord:
    """One GUI attachment record owned by the AG-UI connection registry."""

    connection_id: str
    thread_id: str
    run_id: str
    created_at_utc: datetime
    parent_run_id: str | None = None
    last_seen_event_id: str | None = None
    detached: bool = False
    detached_at_utc: datetime | None = None

    def as_detached(self, *, detached_at_utc: datetime) -> "AgUiConnectionRecord":
        """Return a detached copy of this connection record."""

        return replace(self, detached=True, detached_at_utc=detached_at_utc)


class AgUiConnectionRegistry:
    """Thread-safe registry for active AG-UI GUI attachment records."""

    def __init__(
        self,
        *,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Initialize an empty connection registry.

        Parameters
        ----------
        id_factory:
            Optional factory used by tests to produce stable connection ids.
        clock:
            Optional clock used by tests to produce stable timestamps.
        """

        self.m_lock: threading.Lock = threading.Lock()
        self.m_connections: dict[str, AgUiConnectionRecord] = {}
        self.m_id_factory: Callable[[], str] = id_factory or (lambda: f"agui-{uuid4().hex}")
        self.m_clock: Callable[[], datetime] = clock or (lambda: datetime.now(UTC))

    def create(
        self,
        *,
        thread_id: str,
        run_id: str,
        parent_run_id: str | None = None,
        last_seen_event_id: str | None = None,
    ) -> AgUiConnectionRecord:
        """Create and store one active connection record."""

        record = AgUiConnectionRecord(
            connection_id=self.m_id_factory(),
            thread_id=thread_id,
            run_id=run_id,
            parent_run_id=parent_run_id,
            last_seen_event_id=last_seen_event_id,
            created_at_utc=self.m_clock(),
        )
        with self.m_lock:
            self.m_connections[record.connection_id] = record
        return record

    def create_from_input(self, connect_input: AgUiConnectInput) -> AgUiConnectionRecord:
        """Create one active connection from AG-UI connect input."""

        return self.create(
            thread_id=connect_input.thread_id,
            run_id=connect_input.run_id,
            parent_run_id=connect_input.parent_run_id,
            last_seen_event_id=connect_input.last_seen_event_id,
        )

    def get(self, connection_id: str) -> AgUiConnectionRecord | None:
        """Return one active connection record by id, if present."""

        with self.m_lock:
            return self.m_connections.get(connection_id)

    def detach(self, connection_id: str) -> AgUiConnectionRecord | None:
        """Detach one active connection and return its detached record copy."""

        with self.m_lock:
            record = self.m_connections.pop(connection_id, None)
        if record is None:
            return None
        return record.as_detached(detached_at_utc=self.m_clock())

    def active_connections(self) -> tuple[AgUiConnectionRecord, ...]:
        """Return active connections in registry insertion order."""

        with self.m_lock:
            return tuple(self.m_connections.values())
