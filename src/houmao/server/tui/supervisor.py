"""Supervisor and worker lifecycle for server-owned live TUI tracking."""

from __future__ import annotations

import threading
from typing import Protocol

from houmao.server.tui.registry import KnownSessionRecord


class TrackingRuntime(Protocol):
    """Runtime contract required by the tracking supervisor."""

    def watch_poll_interval_seconds(self) -> float:
        """Return the tracking poll interval."""

    def load_live_known_sessions(self) -> dict[str, KnownSessionRecord]:
        """Load live known sessions from the authoritative registration seed."""

    def ensure_known_session(self, record: KnownSessionRecord) -> None:
        """Ensure tracker state exists for one live known session."""

    def poll_known_session(self, tracked_session_id: str) -> bool:
        """Poll one tracked session and return whether the worker should continue."""


class SessionWatchWorker:
    """Background worker for one known tracked session."""

    def __init__(self, *, runtime: TrackingRuntime, tracked_session_id: str) -> None:
        """Initialize the worker."""

        self.m_runtime = runtime
        self.m_tracked_session_id = tracked_session_id
        self.m_stop_event = threading.Event()
        self.m_thread = threading.Thread(
            target=self._run,
            name=f"houmao-watch-{tracked_session_id}",
            daemon=True,
        )

    def start(self) -> None:
        """Start the worker thread."""

        self.m_thread.start()

    def stop(self, *, join: bool = True) -> None:
        """Request worker termination."""

        self.m_stop_event.set()
        if join:
            self.m_thread.join(timeout=2.0)

    def is_alive(self) -> bool:
        """Return whether the worker thread is still alive."""

        return self.m_thread.is_alive()

    def _run(self) -> None:
        while not self.m_stop_event.is_set():
            keep_running = self.m_runtime.poll_known_session(self.m_tracked_session_id)
            if not keep_running:
                return
            self.m_stop_event.wait(self.m_runtime.watch_poll_interval_seconds())


class TuiTrackingSupervisor:
    """Reconcile live known sessions against active watch workers."""

    def __init__(self, *, runtime: TrackingRuntime) -> None:
        """Initialize the supervisor."""

        self.m_runtime = runtime
        self.m_stop_event = threading.Event()
        self.m_wake_event = threading.Event()
        self.m_lock = threading.RLock()
        self.m_workers: dict[str, SessionWatchWorker] = {}
        self.m_started = False
        self.m_thread = threading.Thread(
            target=self._run,
            name="houmao-watch-supervisor",
            daemon=True,
        )

    def start(self) -> None:
        """Start the supervisor thread."""

        self.m_started = True
        self.m_thread.start()

    def stop(self) -> None:
        """Stop the supervisor and all child workers."""

        self.m_stop_event.set()
        self.m_wake_event.set()
        if self.m_started:
            self.m_thread.join(timeout=2.0)
        with self.m_lock:
            workers = list(self.m_workers.values())
            self.m_workers.clear()
        for worker in workers:
            worker.stop(join=True)

    def request_reconcile(self) -> None:
        """Request an out-of-band reconcile pass."""

        self.m_wake_event.set()

    def _run(self) -> None:
        while not self.m_stop_event.is_set():
            self._reconcile_once()
            self.m_wake_event.wait(self.m_runtime.watch_poll_interval_seconds())
            self.m_wake_event.clear()

    def _reconcile_once(self) -> None:
        live_sessions = self.m_runtime.load_live_known_sessions()
        live_ids = set(live_sessions)

        with self.m_lock:
            stale_ids = [
                tracked_session_id
                for tracked_session_id, worker in self.m_workers.items()
                if tracked_session_id not in live_ids or not worker.is_alive()
            ]
            for tracked_session_id in stale_ids:
                worker = self.m_workers.pop(tracked_session_id)
                worker.stop(join=True)

            for tracked_session_id, record in live_sessions.items():
                self.m_runtime.ensure_known_session(record)
                if tracked_session_id in self.m_workers:
                    continue
                worker = SessionWatchWorker(
                    runtime=self.m_runtime,
                    tracked_session_id=tracked_session_id,
                )
                self.m_workers[tracked_session_id] = worker
                worker.start()
