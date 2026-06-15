"""Live fanout for agent-published AG-UI events."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Literal
from uuid import uuid4

from ag_ui.core import BaseEvent
from houmao.ag_ui.connection import AgUiConnectionRecord


@dataclass(frozen=True)
class AgUiQueuedEvent:
    """One AG-UI event queued for SSE delivery."""

    event: BaseEvent
    event_id: str | None = None


@dataclass(frozen=True)
class AgUiEventSubscription:
    """One active AG-UI event subscription."""

    subscription_id: str
    queue: asyncio.Queue[AgUiQueuedEvent]
    thread_id: str | None
    run_id: str | None
    connection_id: str | None


@dataclass(frozen=True)
class AgUiEventPublishResult:
    """Counts produced by one publish operation."""

    accepted_count: int
    stored_count: int
    delivered_count: int
    replay: Literal["none"]


@dataclass(frozen=True)
class AgUiReplayResult:
    """Replay lookup result for compatibility with older connect code."""

    status: Literal["not_replayable"]
    events: tuple[AgUiQueuedEvent, ...]


class AgUiEventHub:
    """Live fanout for AG-UI events published to one gateway."""

    def __init__(
        self,
        *,
        agent_identity: str = "gateway",
        event_log_path: Path | None = None,
        id_factory: Callable[[], str] | None = None,
        max_queue_size: int = 100,
        max_events_per_thread: int = 500,
    ) -> None:
        """Initialize an event hub.

        Parameters
        ----------
        agent_identity:
            Compatibility argument retained for existing route wiring. Live-only
            publish does not encode gateway replay cursors.
        event_log_path:
            Compatibility argument retained for existing route wiring. Live-only
            publish ignores gateway replay logs.
        id_factory:
            Subscription id factory used by tests.
        max_queue_size:
            Maximum pending live frames for one subscription.
        max_events_per_thread:
            Compatibility argument retained for existing tests and callers.
        """

        del agent_identity, event_log_path, max_events_per_thread
        self.m_lock: threading.Lock = threading.Lock()
        self.m_subscriptions: dict[str, AgUiEventSubscription] = {}
        self.m_id_factory: Callable[[], str] = id_factory or (lambda: f"agui-sub-{uuid4().hex}")
        self.m_max_queue_size: int = max_queue_size

    @property
    def replay_enabled(self) -> bool:
        """Return whether this hub can retain and replay thread-scoped events."""

        return False

    def subscribe(
        self,
        *,
        thread_id: str | None,
        run_id: str | None,
        connection_id: str | None = None,
    ) -> AgUiEventSubscription:
        """Create one subscription for matching published events."""

        subscription = AgUiEventSubscription(
            subscription_id=self.m_id_factory(),
            queue=asyncio.Queue(maxsize=self.m_max_queue_size),
            thread_id=thread_id,
            run_id=run_id,
            connection_id=connection_id,
        )
        with self.m_lock:
            self.m_subscriptions[subscription.subscription_id] = subscription
        return subscription

    def subscribe_connection(self, record: AgUiConnectionRecord) -> AgUiEventSubscription:
        """Create one subscription for a connect-stream record."""

        return self.subscribe(
            thread_id=record.thread_id,
            run_id=record.run_id,
            connection_id=record.connection_id,
        )

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove one subscription."""

        with self.m_lock:
            self.m_subscriptions.pop(subscription_id, None)

    def publish(
        self,
        events: Sequence[BaseEvent],
        *,
        thread_id: str | None,
        run_id: str | None,
        connection_id: str | None,
    ) -> AgUiEventPublishResult:
        """Publish live events and return counts for one event batch."""

        queued_events = tuple(AgUiQueuedEvent(event=event) for event in events)
        delivered_count = self._fanout(
            queued_events,
            thread_id=thread_id,
            run_id=run_id,
            connection_id=connection_id,
        )
        return AgUiEventPublishResult(
            accepted_count=len(events),
            stored_count=0,
            delivered_count=delivered_count,
            replay="none",
        )

    def replay_after(
        self,
        *,
        thread_id: str | None,
        last_seen_event_id: str | None,
    ) -> AgUiReplayResult:
        """Return no retained events because gateway publish is live-only."""

        del thread_id, last_seen_event_id
        return AgUiReplayResult(status="not_replayable", events=())

    def _fanout(
        self,
        events: Sequence[AgUiQueuedEvent],
        *,
        thread_id: str | None,
        run_id: str | None,
        connection_id: str | None,
    ) -> int:
        """Publish queued events to matching active subscriptions."""

        if not events:
            return 0
        with self.m_lock:
            subscriptions = tuple(self.m_subscriptions.values())
        delivered = 0
        for subscription in subscriptions:
            if not _subscription_matches(
                subscription,
                thread_id=thread_id,
                run_id=run_id,
                connection_id=connection_id,
            ):
                continue
            for event in events:
                try:
                    subscription.queue.put_nowait(event)
                    delivered += 1
                except asyncio.QueueFull:
                    continue
        return delivered


def _subscription_matches(
    subscription: AgUiEventSubscription,
    *,
    thread_id: str | None,
    run_id: str | None,
    connection_id: str | None,
) -> bool:
    """Return whether one subscription should receive a published batch."""

    if connection_id is not None:
        return subscription.connection_id == connection_id
    if thread_id is not None and subscription.thread_id != thread_id:
        return False
    if run_id is not None and subscription.run_id != run_id:
        return False
    return thread_id is not None or run_id is not None


__all__ = [
    "AgUiEventHub",
    "AgUiEventPublishResult",
    "AgUiEventSubscription",
    "AgUiQueuedEvent",
    "AgUiReplayResult",
]
