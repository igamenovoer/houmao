"""Safe diagnostics and counters for Houmao AG-UI streams."""

from __future__ import annotations

import threading
from time import monotonic
from typing import Literal, Protocol, TYPE_CHECKING

from houmao.ag_ui.connection import AgUiConnectionRecord

if TYPE_CHECKING:
    from houmao.ag_ui.service import AgUiAdmittedRun

AgUiDiagnosticLevel = Literal["info", "warning", "error"]


class AgUiDiagnosticRuntime(Protocol):
    """Runtime diagnostic sink used by AG-UI helpers when available."""

    def emit_diagnostic(
        self,
        *,
        level: AgUiDiagnosticLevel,
        event: str,
        fields: dict[str, object] | None = None,
        dedup_key: str | None = None,
    ) -> None:
        """Emit one safe diagnostic record."""


class AgUiDiagnostics:
    """Track AG-UI stream counts and emit payload-safe diagnostics."""

    def __init__(self, *, runtime: object) -> None:
        """Initialize diagnostics for one route registration."""

        self.m_runtime: object = runtime
        self.m_lock: threading.Lock = threading.Lock()
        self.m_active_connections: int = 0
        self.m_active_runs: int = 0
        self.m_connection_started_at: dict[str, float] = {}
        self.m_run_started_at: dict[str, float] = {}

    def active_counts(self) -> dict[str, int]:
        """Return current AG-UI stream counts."""

        with self.m_lock:
            return {
                "activeAgUiConnections": self.m_active_connections,
                "activeAgUiRuns": self.m_active_runs,
            }

    def connection_started(self, record: AgUiConnectionRecord) -> None:
        """Record one active GUI attachment stream."""

        with self.m_lock:
            self.m_active_connections += 1
            self.m_connection_started_at[record.connection_id] = monotonic()
            counts = self._counts_locked()
        self._emit(
            level="info",
            event="gateway.ag_ui_connection_started",
            fields={
                **self._connection_fields(record),
                **counts,
            },
        )

    def connection_detached(self, record: AgUiConnectionRecord, *, reason: str) -> None:
        """Record cleanup for one GUI attachment stream."""

        with self.m_lock:
            self.m_active_connections = max(0, self.m_active_connections - 1)
            started_at = self.m_connection_started_at.pop(record.connection_id, None)
            counts = self._counts_locked()
        fields = {
            **self._connection_fields(record),
            **counts,
            "detachReason": reason,
        }
        duration_ms = _duration_ms_since(started_at)
        if duration_ms is not None:
            fields["durationMs"] = duration_ms
        self._emit(
            level="info",
            event="gateway.ag_ui_connection_detached",
            fields=fields,
        )

    def explicit_disconnect(
        self,
        *,
        connection_id: str,
        detached: bool,
    ) -> None:
        """Record an explicit AG-UI disconnect route call."""

        fields: dict[str, object] = {
            "connectionId": connection_id,
            "detached": detached,
            **self.active_counts(),
        }
        self._emit(
            level="info" if detached else "warning",
            event="gateway.ag_ui_connection_explicit_disconnect",
            fields=fields,
        )

    def run_admitted(self, admitted_run: "AgUiAdmittedRun") -> None:
        """Record successful pre-stream AG-UI run admission."""

        self._emit(
            level="info",
            event="gateway.ag_ui_run_admitted",
            fields={
                **self._run_fields(admitted_run),
                **self.active_counts(),
            },
        )

    def run_stream_started(self, admitted_run: "AgUiAdmittedRun") -> None:
        """Record one active AG-UI run stream."""

        run_id = admitted_run.run_input.run_id
        with self.m_lock:
            self.m_active_runs += 1
            self.m_run_started_at[run_id] = monotonic()
            counts = self._counts_locked()
        self._emit(
            level="info",
            event="gateway.ag_ui_run_stream_started",
            fields={
                **self._run_fields(admitted_run),
                **counts,
            },
        )

    def run_stream_completed(
        self,
        admitted_run: "AgUiAdmittedRun",
        *,
        outcome: str,
    ) -> None:
        """Record terminal AG-UI run stream cleanup."""

        run_id = admitted_run.run_input.run_id
        with self.m_lock:
            self.m_active_runs = max(0, self.m_active_runs - 1)
            started_at = self.m_run_started_at.pop(run_id, None)
            counts = self._counts_locked()
        fields = {
            **self._run_fields(admitted_run),
            **counts,
            "terminalOutcome": outcome,
        }
        duration_ms = _duration_ms_since(started_at)
        if duration_ms is not None:
            fields["durationMs"] = duration_ms
        self._emit(
            level="info" if outcome == "finished" else "warning",
            event="gateway.ag_ui_run_stream_completed",
            fields=fields,
        )

    def run_client_disconnected(self, admitted_run: "AgUiAdmittedRun") -> None:
        """Record client-side detachment from an AG-UI run stream."""

        self._emit(
            level="info",
            event="gateway.ag_ui_run_client_disconnected",
            fields={
                **self._run_fields(admitted_run),
                **self.active_counts(),
            },
        )

    def stream_error(
        self,
        *,
        stream_kind: str,
        error_category: str,
        admitted_run: "AgUiAdmittedRun | None" = None,
        connection: AgUiConnectionRecord | None = None,
    ) -> None:
        """Record a stream error without raw request or state payloads."""

        fields: dict[str, object] = {
            "streamKind": stream_kind,
            "errorCategory": error_category,
            **self.active_counts(),
        }
        if admitted_run is not None:
            fields.update(self._run_fields(admitted_run))
        if connection is not None:
            fields.update(self._connection_fields(connection))
        self._emit(
            level="error",
            event="gateway.ag_ui_stream_error",
            fields=fields,
            dedup_key=f"ag-ui-stream-error:{stream_kind}:{error_category}",
        )

    def _counts_locked(self) -> dict[str, int]:
        """Return counts while the caller holds the lock."""

        return {
            "activeAgUiConnections": self.m_active_connections,
            "activeAgUiRuns": self.m_active_runs,
        }

    def _emit(
        self,
        *,
        level: AgUiDiagnosticLevel,
        event: str,
        fields: dict[str, object],
        dedup_key: str | None = None,
    ) -> None:
        """Emit to the runtime diagnostic sink when it exposes one."""

        emitter = getattr(self.m_runtime, "emit_diagnostic", None)
        if not callable(emitter):
            return
        emitter(level=level, event=event, fields=fields, dedup_key=dedup_key)

    def _connection_fields(self, record: AgUiConnectionRecord) -> dict[str, object]:
        """Return safe diagnostic fields for one connection."""

        fields: dict[str, object] = {
            "connectionId": record.connection_id,
            "threadId": record.thread_id,
            "runId": record.run_id,
        }
        if record.parent_run_id is not None:
            fields["parentRunId"] = record.parent_run_id
        if record.last_seen_event_id is not None:
            fields["lastSeenEventId"] = record.last_seen_event_id
        return fields

    def _run_fields(self, admitted_run: "AgUiAdmittedRun") -> dict[str, object]:
        """Return safe diagnostic fields for one admitted run."""

        fields: dict[str, object] = {
            "threadId": admitted_run.run_input.thread_id,
            "runId": admitted_run.run_input.run_id,
            "gatewayRequestId": admitted_run.accepted_request.request_id,
            "targetTransportFamily": admitted_run.target_transport_family,
        }
        if admitted_run.run_input.parent_run_id is not None:
            fields["parentRunId"] = admitted_run.run_input.parent_run_id
        return fields


def _duration_ms_since(started_at: float | None) -> int | None:
    """Return elapsed milliseconds since one monotonic timestamp."""

    if started_at is None:
        return None
    return int((monotonic() - started_at) * 1000)
