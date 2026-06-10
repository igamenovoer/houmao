"""Retained fanout for agent-published AG-UI events."""

from __future__ import annotations

import asyncio
import base64
import json
from collections import deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Any, Literal, cast
from uuid import uuid4

from ag_ui.core import BaseEvent, Event
from pydantic import TypeAdapter, ValidationError

from houmao.ag_ui.connection import AgUiConnectionRecord

_EVENT_ADAPTER: TypeAdapter[Any] = TypeAdapter(Event)


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
class AgUiStoredEvent:
    """One retained replayable AG-UI event."""

    event_id: str
    sequence: int
    thread_id: str
    run_id: str | None
    connection_id: str | None
    event: BaseEvent


@dataclass(frozen=True)
class AgUiEventPublishResult:
    """Counts produced by one publish operation."""

    accepted_count: int
    stored_count: int
    delivered_count: int
    replay: Literal["none", "event_log_since_cursor"]


@dataclass(frozen=True)
class AgUiReplayResult:
    """Retained events selected for one connect-stream cursor."""

    status: Literal["not_replayable", "full_log", "after_cursor", "cursor_not_found"]
    events: tuple[AgUiQueuedEvent, ...]


class AgUiEventHub:
    """Bounded retained fanout for AG-UI events published to one gateway."""

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
            Stable identity encoded into assigned SSE event ids.
        event_log_path:
            Optional gateway-owned JSONL replay log. When present, retained
            events survive gateway process restarts.
        id_factory:
            Subscription id factory used by tests.
        max_queue_size:
            Maximum pending live frames for one subscription.
        max_events_per_thread:
            Retained replay window per thread.
        """

        self.m_lock: threading.Lock = threading.Lock()
        self.m_subscriptions: dict[str, AgUiEventSubscription] = {}
        self.m_id_factory: Callable[[], str] = id_factory or (lambda: f"agui-sub-{uuid4().hex}")
        self.m_agent_identity: str = agent_identity
        self.m_event_log_path: Path | None = event_log_path
        self.m_max_queue_size: int = max_queue_size
        self.m_max_events_per_thread: int = max(1, max_events_per_thread)
        self.m_events_by_thread: dict[str, deque[AgUiStoredEvent]] = {}
        self.m_next_sequence_by_thread: dict[str, int] = {}
        if self.m_event_log_path is not None:
            self._load_persisted_events()

    @property
    def replay_enabled(self) -> bool:
        """Return whether this hub can retain and replay thread-scoped events."""

        return self.m_max_events_per_thread > 0

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
        """Store, publish, and return counts for one event batch."""

        queued_events: tuple[AgUiQueuedEvent, ...]
        stored_count = 0
        if thread_id is None:
            queued_events = tuple(AgUiQueuedEvent(event=event) for event in events)
        else:
            stored_events = self._store_replay_events(
                events,
                thread_id=thread_id,
                run_id=run_id,
                connection_id=connection_id,
            )
            stored_count = len(stored_events)
            queued_events = tuple(
                AgUiQueuedEvent(event=stored.event, event_id=stored.event_id)
                for stored in stored_events
            )

        delivered_count = self._fanout(
            queued_events,
            thread_id=thread_id,
            run_id=run_id,
            connection_id=connection_id,
        )
        return AgUiEventPublishResult(
            accepted_count=len(events),
            stored_count=stored_count,
            delivered_count=delivered_count,
            replay="event_log_since_cursor" if stored_count > 0 else "none",
        )

    def replay_after(
        self,
        *,
        thread_id: str | None,
        last_seen_event_id: str | None,
    ) -> AgUiReplayResult:
        """Return retained events for ``thread_id`` after one optional cursor."""

        if thread_id is None:
            return AgUiReplayResult(status="not_replayable", events=())
        with self.m_lock:
            retained = tuple(self.m_events_by_thread.get(thread_id, ()))
        if last_seen_event_id is None:
            return AgUiReplayResult(
                status="full_log",
                events=tuple(
                    AgUiQueuedEvent(event=stored.event, event_id=stored.event_id)
                    for stored in retained
                ),
            )
        for index, stored in enumerate(retained):
            if stored.event_id == last_seen_event_id:
                return AgUiReplayResult(
                    status="after_cursor",
                    events=tuple(
                        AgUiQueuedEvent(event=event.event, event_id=event.event_id)
                        for event in retained[index + 1 :]
                    ),
                )
        return AgUiReplayResult(status="cursor_not_found", events=())

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

    def _store_replay_events(
        self,
        events: Sequence[BaseEvent],
        *,
        thread_id: str,
        run_id: str | None,
        connection_id: str | None,
    ) -> tuple[AgUiStoredEvent, ...]:
        """Append events to the retained per-thread replay log."""

        stored_events: list[AgUiStoredEvent] = []
        with self.m_lock:
            log = self.m_events_by_thread.setdefault(thread_id, deque())
            next_sequence = self.m_next_sequence_by_thread.get(thread_id, 1)
            for event in events:
                event_id = _format_event_id(
                    agent_identity=self.m_agent_identity,
                    thread_id=thread_id,
                    sequence=next_sequence,
                )
                stored = AgUiStoredEvent(
                    event_id=event_id,
                    sequence=next_sequence,
                    thread_id=thread_id,
                    run_id=run_id,
                    connection_id=connection_id,
                    event=event,
                )
                log.append(stored)
                stored_events.append(stored)
                next_sequence += 1
            self.m_next_sequence_by_thread[thread_id] = next_sequence
            trimmed = False
            while len(log) > self.m_max_events_per_thread:
                log.popleft()
                trimmed = True
            self._append_persisted_events_locked(stored_events)
            if trimmed:
                self._rewrite_persisted_events_locked()
        return tuple(stored_events)

    def _load_persisted_events(self) -> None:
        """Load retained events from the optional gateway-owned replay log."""

        if self.m_event_log_path is None or not self.m_event_log_path.is_file():
            return
        loaded: list[AgUiStoredEvent] = []
        try:
            lines = self.m_event_log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        for line in lines:
            try:
                payload = json.loads(line)
                stored = _stored_event_from_payload(payload)
            except (TypeError, ValueError, ValidationError, KeyError):
                continue
            loaded.append(stored)
        with self.m_lock:
            for stored in loaded:
                log = self.m_events_by_thread.setdefault(stored.thread_id, deque())
                log.append(stored)
                while len(log) > self.m_max_events_per_thread:
                    log.popleft()
                self.m_next_sequence_by_thread[stored.thread_id] = max(
                    self.m_next_sequence_by_thread.get(stored.thread_id, 1),
                    stored.sequence + 1,
                )

    def _append_persisted_events_locked(self, events: Iterable[AgUiStoredEvent]) -> None:
        """Append stored events to the optional JSONL replay log."""

        if self.m_event_log_path is None:
            return
        materialized = tuple(events)
        if not materialized:
            return
        try:
            self.m_event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.m_event_log_path.open("a", encoding="utf-8") as handle:
                for stored in materialized:
                    handle.write(json.dumps(_stored_event_payload(stored), sort_keys=True))
                    handle.write("\n")
        except OSError:
            return

    def _rewrite_persisted_events_locked(self) -> None:
        """Rewrite the optional JSONL replay log with the retained window only."""

        if self.m_event_log_path is None:
            return
        try:
            self.m_event_log_path.parent.mkdir(parents=True, exist_ok=True)
            retained = [
                stored
                for thread_events in self.m_events_by_thread.values()
                for stored in thread_events
            ]
            retained.sort(key=lambda stored: (stored.thread_id, stored.sequence))
            with self.m_event_log_path.open("w", encoding="utf-8") as handle:
                for stored in retained:
                    handle.write(json.dumps(_stored_event_payload(stored), sort_keys=True))
                    handle.write("\n")
        except OSError:
            return


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


def _format_event_id(*, agent_identity: str, thread_id: str, sequence: int) -> str:
    """Return a stable SSE id scoped to agent identity and AG-UI thread."""

    agent_token = _event_id_component(agent_identity)
    thread_token = _event_id_component(thread_id)
    return f"houmao-agui.v1.{agent_token}.{thread_token}.{sequence}"


def _event_id_component(value: str) -> str:
    """Encode one event-id component without leaking separator-sensitive bytes."""

    encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def _stored_event_payload(stored: AgUiStoredEvent) -> dict[str, object]:
    """Serialize one stored event for JSONL persistence."""

    payload: dict[str, object] = {
        "schemaVersion": 1,
        "eventId": stored.event_id,
        "sequence": stored.sequence,
        "threadId": stored.thread_id,
        "event": stored.event.model_dump(mode="json", by_alias=True, exclude_none=True),
    }
    if stored.run_id is not None:
        payload["runId"] = stored.run_id
    if stored.connection_id is not None:
        payload["connectionId"] = stored.connection_id
    return payload


def _stored_event_from_payload(payload: object) -> AgUiStoredEvent:
    """Parse one JSONL replay-log record."""

    if not isinstance(payload, dict):
        raise TypeError("stored AG-UI event record must be an object")
    event_payload = payload["event"]
    if not isinstance(event_payload, dict):
        raise TypeError("stored AG-UI event payload must be an object")
    event = cast(BaseEvent, _EVENT_ADAPTER.validate_python(event_payload))
    event_id = str(payload["eventId"])
    sequence = int(payload["sequence"])
    thread_id = str(payload["threadId"])
    run_id = payload.get("runId")
    connection_id = payload.get("connectionId")
    return AgUiStoredEvent(
        event_id=event_id,
        sequence=sequence,
        thread_id=thread_id,
        run_id=str(run_id) if run_id is not None else None,
        connection_id=str(connection_id) if connection_id is not None else None,
        event=event,
    )


__all__ = [
    "AgUiEventHub",
    "AgUiEventPublishResult",
    "AgUiEventSubscription",
    "AgUiQueuedEvent",
    "AgUiReplayResult",
    "AgUiStoredEvent",
]
