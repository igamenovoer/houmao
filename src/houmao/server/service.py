"""Core service runtime for `houmao-server`.

This service keeps CAO-compatible control delegation behind the child server
while owning live tmux/process observation and in-memory TUI tracking directly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Protocol
from urllib import error, parse, request

from fastapi import HTTPException, Response

from houmao.cao.models import CaoTerminal
from houmao.cao.no_proxy import scoped_loopback_no_proxy_for_cao_base_url
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    tmux_session_exists,
)
from houmao.server.tui import (
    KnownSessionRecord,
    KnownSessionRegistry,
    LiveSessionTracker,
    OfficialTuiParserAdapter,
    PaneProcessInspector,
    SessionWatchWorker,
    TuiTrackingSupervisor,
    TmuxTransportResolver,
    known_session_record_from_registration,
)
from houmao.server.tui.tracking import utc_now_iso

from houmao.server.child_cao import ChildCaoManager
from houmao.server.config import HoumaoServerConfig
from houmao.server.models import (
    ChildCaoStatus,
    HoumaoCurrentInstance,
    HoumaoErrorDetail,
    HoumaoHealthResponse,
    HoumaoProbeSnapshot,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
)

LOGGER = logging.getLogger(__name__)


class ProxyResponse:
    """One proxied child-CAO response."""

    def __init__(
        self,
        *,
        status_code: int,
        body: bytes,
        content_type: str,
        json_payload: object | None,
    ) -> None:
        """Initialize the proxy response."""

        self.status_code = status_code
        self.body = body
        self.content_type = content_type
        self.json_payload = json_payload

    def to_fastapi_response(self) -> Response:
        """Convert the proxied result into a FastAPI response."""

        return Response(
            content=self.body,
            status_code=self.status_code,
            media_type=self.content_type or "application/json",
        )


class ProxyTransport(Protocol):
    """Transport contract for proxied child-CAO requests."""

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> ProxyResponse:
        """Send one child-CAO request."""


class UrlLibProxyTransport:
    """urllib-based child-CAO proxy transport."""

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> ProxyResponse:
        """Send one child-CAO request with urllib."""

        encoded_params = parse.urlencode(params or {})
        url = f"{base_url.rstrip('/')}{path}"
        if encoded_params:
            url = f"{url}?{encoded_params}"

        data: bytes | None = None
        if method.upper() in {"POST", "PUT", "PATCH"}:
            data = b""

        req = request.Request(
            url,
            data=data,
            method=method.upper(),
            headers={"Accept": "application/json"},
        )
        try:
            with scoped_loopback_no_proxy_for_cao_base_url(base_url):
                with request.urlopen(req, timeout=15.0) as response:
                    body = response.read()
                    content_type = response.headers.get_content_type()
                    return ProxyResponse(
                        status_code=int(response.status),
                        body=body,
                        content_type=content_type,
                        json_payload=_try_parse_json_bytes(body),
                    )
        except error.HTTPError as exc:
            body = exc.read()
            content_type = (
                exc.headers.get_content_type() if exc.headers is not None else "text/plain"
            )
            return ProxyResponse(
                status_code=int(exc.code),
                body=body,
                content_type=content_type,
                json_payload=_try_parse_json_bytes(body),
            )
        except (error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Child `cao-server` is unavailable: {reason}",
            ) from exc


class HoumaoServerService:
    """Application-owned `houmao-server` runtime state."""

    def __init__(
        self,
        *,
        config: HoumaoServerConfig,
        transport: ProxyTransport | None = None,
        child_manager: ChildCaoManager | None = None,
        known_session_registry: KnownSessionRegistry | None = None,
        transport_resolver: TmuxTransportResolver | None = None,
        process_inspector: PaneProcessInspector | None = None,
        parser_adapter: OfficialTuiParserAdapter | None = None,
    ) -> None:
        """Initialize the service runtime."""

        self.m_config = config
        self.m_transport = transport or UrlLibProxyTransport()
        self.m_child_manager = child_manager or ChildCaoManager(config=config)
        self.m_known_session_registry = known_session_registry or KnownSessionRegistry(
            config=config
        )
        self.m_transport_resolver = transport_resolver or TmuxTransportResolver()
        self.m_process_inspector = process_inspector or PaneProcessInspector(
            supported_processes=config.supported_tui_processes
        )
        self.m_parser_adapter = parser_adapter or OfficialTuiParserAdapter()
        self.m_lock = threading.RLock()
        self.m_trackers: dict[str, LiveSessionTracker] = {}
        self.m_terminal_aliases: dict[str, str] = {}
        self.m_supervisor = TuiTrackingSupervisor(runtime=self)

    def startup(self) -> None:
        """Start the service runtime."""

        self._ensure_directories()
        if self.m_config.startup_child:
            self.m_child_manager.start()
        self._write_current_instance()
        self.m_supervisor.start()
        self.m_supervisor.request_reconcile()

    def shutdown(self) -> None:
        """Stop the service runtime."""

        self.m_supervisor.stop()
        if self.m_config.startup_child:
            try:
                self.m_child_manager.stop()
            except Exception:
                pass

    def proxy(
        self, *, method: str, path: str, params: dict[str, str] | None = None
    ) -> ProxyResponse:
        """Proxy one CAO-compatible request to the child server."""

        return self.m_transport.request(
            base_url=self.m_config.child_api_base_url,
            method=method,
            path=path,
            params=params,
        )

    def health_response(self) -> HoumaoHealthResponse:
        """Build the compatibility-safe health payload."""

        return HoumaoHealthResponse(
            status="ok",
            service="cli-agent-orchestrator",
            child_cao=self.child_status(),
        )

    def current_instance_response(self) -> HoumaoCurrentInstance:
        """Return the current server instance payload."""

        return HoumaoCurrentInstance(
            pid=os.getpid(),
            api_base_url=self.m_config.api_base_url,
            server_root=str(self.m_config.server_root),
            child_cao=self.child_status(),
        )

    def child_status(self) -> ChildCaoStatus:
        """Return child-CAO lifecycle metadata."""

        inspection = self.m_child_manager.inspect()
        return ChildCaoStatus(
            api_base_url=inspection.config.base_url,
            healthy=inspection.status.healthy,
            health_status=inspection.status.health_status,
            service=inspection.status.service,
            error=inspection.status.error,
            derived_port=self.m_config.public_port + 1,
            ownership_file=(
                str(self.m_child_manager.ownership_file_path())
                if self.m_child_manager.ownership_file_path().exists()
                else None
            ),
        )

    def sync_created_terminal(self, payload: object) -> None:
        """Accept the proxied create payload without admitting tracking authority."""

        del payload

    def handle_deleted_terminal(self, terminal_id: str) -> None:
        """Remove one terminal and its registration-backed tracker state."""

        tracked_session_id = self.m_terminal_aliases.get(terminal_id)
        if tracked_session_id is None:
            return
        self._remove_registration_dir(session_name=tracked_session_id)
        self._forget_tracker(tracked_session_id=tracked_session_id)
        self.m_supervisor.request_reconcile()

    def handle_deleted_session(self, session_name: str) -> None:
        """Remove one session and its registration-backed tracker state."""

        self._remove_registration_dir(session_name=session_name)
        self._forget_tracker(tracked_session_id=session_name)
        self.m_supervisor.request_reconcile()

    def note_prompt_submission(self, *, terminal_id: str, message: str) -> None:
        """Accept prompt-submission notifications for compatibility."""

        del terminal_id
        del message

    def register_launch(
        self, request_model: HoumaoRegisterLaunchRequest
    ) -> HoumaoRegisterLaunchResponse:
        """Register one delegated CLI launch into the server-owned registry."""

        session_name = self._validated_registration_session_name(request_model.session_name)
        terminal_id = request_model.terminal_id
        if terminal_id is None:
            proxy = self.proxy(
                method="GET",
                path=f"/sessions/{parse.quote(session_name, safe='')}/terminals",
            )
            payload = proxy.json_payload
            if not isinstance(payload, list) or not payload:
                raise HTTPException(
                    status_code=404,
                    detail=f"Could not discover terminals for session `{session_name}`.",
                )
            first = payload[0]
            if not isinstance(first, dict):
                raise HTTPException(
                    status_code=502,
                    detail="Child CAO returned an invalid terminal payload during launch registration.",
                )
            terminal_id = str(first.get("id", "")).strip() or None
            if terminal_id is None:
                raise HTTPException(
                    status_code=502,
                    detail="Child CAO launch registration payload is missing terminal id.",
                )

        proxy = self.proxy(
            method="GET",
            path=f"/terminals/{parse.quote(terminal_id, safe='')}",
        )
        payload = proxy.json_payload
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=502,
                detail="Child CAO returned an invalid terminal payload during launch registration.",
            )
        CaoTerminal.model_validate(payload)

        registration_dir = self._registration_dir_for_session_name(session_name, strict=True)
        assert registration_dir is not None
        registration_dir.mkdir(parents=True, exist_ok=True)
        registration_path = registration_dir / "registration.json"
        persisted_request = request_model.model_copy(
            update={
                "session_name": session_name,
                "terminal_id": terminal_id,
            }
        )
        registration_path.write_text(
            json.dumps(persisted_request.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._ensure_tracker_for_registered_launch(request_model=persisted_request)
        self.m_supervisor.request_reconcile()

        return HoumaoRegisterLaunchResponse(
            success=True,
            session_name=session_name,
            terminal_id=terminal_id,
        )

    def terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        """Return the latest in-memory tracked terminal state."""

        tracker = self._tracker_for_terminal_alias(terminal_id)
        return tracker.current_state()

    def terminal_history(self, terminal_id: str, *, limit: int) -> HoumaoTerminalHistoryResponse:
        """Return bounded in-memory recent history for one terminal alias."""

        tracker = self._tracker_for_terminal_alias(terminal_id)
        return tracker.history(limit=limit)

    def refresh_terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        """Poll one known tracked terminal immediately and return the updated state."""

        tracked_session_id = self._tracked_session_id_for_terminal_alias(terminal_id)
        self.poll_known_session(tracked_session_id)
        tracker = self._tracker_for_terminal_alias(terminal_id)
        return tracker.current_state()

    def watch_poll_interval_seconds(self) -> float:
        """Return the configured tracking poll interval."""

        return self.m_config.watch_poll_interval_seconds

    def load_live_known_sessions(self) -> dict[str, KnownSessionRecord]:
        """Return live known sessions from the authoritative registry seed."""

        return self.m_known_session_registry.load_live_sessions()

    def ensure_known_session(self, record: KnownSessionRecord) -> None:
        """Ensure tracker state exists for one known session."""

        identity = record.to_identity()
        with self.m_lock:
            tracker = self.m_trackers.get(record.tracked_session_id)
            if tracker is None:
                tracker = LiveSessionTracker(
                    identity=identity,
                    recent_transition_limit=self.m_config.recent_transition_limit,
                    stability_threshold_seconds=self.m_config.stability_threshold_seconds,
                )
                self.m_trackers[record.tracked_session_id] = tracker
            else:
                tracker.set_identity(identity)
            for alias, tracked_session_id in list(self.m_terminal_aliases.items()):
                if tracked_session_id == record.tracked_session_id and alias != record.terminal_id:
                    self.m_terminal_aliases.pop(alias, None)
            self.m_terminal_aliases[record.terminal_id] = record.tracked_session_id

    def handle_poll_exception(self, tracked_session_id: str, exc: Exception) -> None:
        """Record one unexpected worker-poll failure and keep polling eligible."""

        LOGGER.exception(
            "Unexpected poll failure for tracked session `%s`.",
            tracked_session_id,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        try:
            tracker = self._tracker_for_session_id(tracked_session_id)
        except HTTPException:
            return

        identity = tracker.current_state().tracked_session
        tracker.record_cycle(
            identity=identity,
            observed_at_utc=utc_now_iso(),
            monotonic_ts=time.monotonic(),
            transport_state="probe_error",
            process_state="probe_error",
            parse_status="probe_error",
            probe_snapshot=None,
            probe_error=HoumaoErrorDetail(
                kind="tracking_runtime_error",
                message=f"Unexpected tracking failure: {type(exc).__name__}: {exc}",
            ),
            parse_error=None,
            parsed_surface=None,
        )

    def release_known_session(self, tracked_session_id: str) -> None:
        """Release one tracked session from live in-memory authority."""

        self._forget_tracker(tracked_session_id=tracked_session_id)

    def poll_known_session(self, tracked_session_id: str) -> bool:
        """Poll one tracked session and return whether the worker should continue."""

        tracker = self._tracker_for_session_id(tracked_session_id)
        identity = tracker.current_state().tracked_session
        observed_at_utc = utc_now_iso()
        monotonic_ts = time.monotonic()

        if not tmux_session_exists(session_name=identity.tmux_session_name):
            tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="tmux_missing",
                process_state="unknown",
                parse_status="transport_unavailable",
                probe_snapshot=None,
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
            )
            return False

        try:
            target = self.m_transport_resolver.resolve_target(
                session_name=identity.tmux_session_name,
                window_name=identity.tmux_window_name,
            )
        except TmuxCommandError as exc:
            tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="probe_error",
                process_state="probe_error",
                parse_status="probe_error",
                probe_snapshot=None,
                probe_error=HoumaoErrorDetail(
                    kind="tmux_probe_error",
                    message=str(exc),
                ),
                parse_error=None,
                parsed_surface=None,
            )
            return True

        process_inspection = self.m_process_inspector.inspect(
            tool=identity.tool,
            pane_pid=target.pane.pane_pid,
        )
        probe_snapshot = HoumaoProbeSnapshot(
            observed_at_utc=observed_at_utc,
            pane_id=target.pane.pane_id,
            pane_pid=target.pane.pane_pid,
            matched_process_names=process_inspection.matched_process_names,
        )
        if process_inspection.process_state == "probe_error":
            tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="tmux_up",
                process_state="probe_error",
                parse_status="probe_error",
                probe_snapshot=probe_snapshot,
                probe_error=HoumaoErrorDetail(
                    kind="process_probe_error",
                    message=process_inspection.error_message or "Process inspection failed.",
                ),
                parse_error=None,
                parsed_surface=None,
            )
            return True

        if process_inspection.process_state == "unsupported_tool":
            tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="tmux_up",
                process_state="unsupported_tool",
                parse_status="unsupported_tool",
                probe_snapshot=probe_snapshot,
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
            )
            return True

        if process_inspection.process_state == "tui_down":
            tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="tmux_up",
                process_state="tui_down",
                parse_status="skipped_tui_down",
                probe_snapshot=probe_snapshot,
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
            )
            return True

        try:
            output_text = self.m_transport_resolver.capture_text(target=target)
        except TmuxCommandError as exc:
            tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="probe_error",
                process_state="probe_error",
                parse_status="probe_error",
                probe_snapshot=probe_snapshot,
                probe_error=HoumaoErrorDetail(
                    kind="tmux_capture_error",
                    message=str(exc),
                ),
                parse_error=None,
                parsed_surface=None,
            )
            return True

        probe_snapshot = probe_snapshot.model_copy(
            update={
                "captured_text_hash": hashlib.sha1(output_text.encode("utf-8")).hexdigest(),
                "captured_text_length": len(output_text),
                "captured_text_excerpt": output_text[-4000:],
            }
        )

        if not self.m_parser_adapter.supports_tool(tool=identity.tool):
            tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="tmux_up",
                process_state="unsupported_tool",
                parse_status="unsupported_tool",
                probe_snapshot=probe_snapshot,
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
            )
            return True

        baseline_pos = tracker.baseline_pos
        if baseline_pos is None:
            try:
                baseline_pos = self.m_parser_adapter.capture_baseline(
                    tool=identity.tool,
                    output_text=output_text,
                )
            except Exception as exc:
                tracker.record_cycle(
                    identity=identity,
                    observed_at_utc=observed_at_utc,
                    monotonic_ts=monotonic_ts,
                    transport_state="tmux_up",
                    process_state="tui_up",
                    parse_status="parse_error",
                    probe_snapshot=probe_snapshot,
                    probe_error=None,
                    parse_error=HoumaoErrorDetail(
                        kind="parse_baseline_error",
                        message=str(exc),
                    ),
                    parsed_surface=None,
                )
                return True
            tracker.set_baseline_pos(baseline_pos)

        parse_result = self.m_parser_adapter.parse(
            tool=identity.tool,
            output_text=output_text,
            baseline_pos=baseline_pos,
        )
        tracker.record_cycle(
            identity=identity,
            observed_at_utc=observed_at_utc,
            monotonic_ts=monotonic_ts,
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status="parsed" if parse_result.parsed_surface is not None else "parse_error",
            probe_snapshot=probe_snapshot,
            probe_error=None,
            parse_error=parse_result.parse_error,
            parsed_surface=parse_result.parsed_surface,
        )
        return True

    def _tracker_for_terminal_alias(self, terminal_id: str) -> LiveSessionTracker:
        """Return the tracker bound to one terminal alias."""

        tracked_session_id = self._tracked_session_id_for_terminal_alias(terminal_id)
        return self._tracker_for_session_id(tracked_session_id)

    def _tracked_session_id_for_terminal_alias(self, terminal_id: str) -> str:
        """Resolve one terminal alias into the tracked session id."""

        with self.m_lock:
            tracked_session_id = self.m_terminal_aliases.get(terminal_id)
        if tracked_session_id is not None:
            return tracked_session_id

        self.m_supervisor.request_reconcile()
        live_sessions = self.load_live_known_sessions()
        for record in live_sessions.values():
            if record.terminal_id != terminal_id:
                continue
            self.ensure_known_session(record)
            return record.tracked_session_id
        raise HTTPException(status_code=404, detail=f"Unknown terminal `{terminal_id}`.")

    def _tracker_for_session_id(self, tracked_session_id: str) -> LiveSessionTracker:
        """Return the tracker bound to one tracked session id."""

        with self.m_lock:
            tracker = self.m_trackers.get(tracked_session_id)
        if tracker is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown tracked session `{tracked_session_id}`.",
            )
        return tracker

    def _forget_tracker(self, *, tracked_session_id: str) -> None:
        """Forget one tracker and all of its terminal aliases."""

        with self.m_lock:
            self.m_trackers.pop(tracked_session_id, None)
            for alias, bound_session_id in list(self.m_terminal_aliases.items()):
                if bound_session_id == tracked_session_id:
                    self.m_terminal_aliases.pop(alias, None)

    def _remove_registration_dir(self, *, session_name: str) -> None:
        """Remove one server-owned registration directory."""

        path = self._registration_dir_for_session_name(session_name, strict=False)
        if path is not None and path.exists():
            shutil.rmtree(path, ignore_errors=False)

    def _ensure_directories(self) -> None:
        """Create the directories owned by the service runtime."""

        for path in (
            self.m_config.server_root,
            self.m_config.logs_dir,
            self.m_config.run_dir,
            self.m_config.sessions_dir,
            self.m_config.child_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _write_current_instance(self) -> None:
        """Persist the current server instance and pid files."""

        payload = self.current_instance_response().model_dump(mode="json")
        self.m_config.current_instance_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.m_config.pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")

    def _ensure_tracker_for_registered_launch(
        self,
        *,
        request_model: HoumaoRegisterLaunchRequest,
    ) -> None:
        """Create or refresh dormant tracker state from one registration request."""

        terminal_id = request_model.terminal_id
        if terminal_id is None:
            return
        record = known_session_record_from_registration(
            registration=request_model,
            allow_shared_registry_enrichment=False,
        )
        if record is not None:
            self.ensure_known_session(record)

    def _validated_registration_session_name(self, session_name: str) -> str:
        """Return one validated registration storage key or fail."""

        if not _is_safe_registration_session_name(session_name):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid server-owned registration session name. "
                    "Expected a single non-empty path component without path separators."
                ),
            )
        return session_name

    def _registration_dir_for_session_name(
        self,
        session_name: str,
        *,
        strict: bool,
    ) -> Path | None:
        """Resolve one registration directory under the server-owned sessions root."""

        if not _is_safe_registration_session_name(session_name):
            if strict:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Invalid server-owned registration session name. "
                        "Expected a single non-empty path component without path separators."
                    ),
                )
            LOGGER.warning(
                "Skipping registration cleanup for invalid session key `%s`.", session_name
            )
            return None

        sessions_root = self.m_config.sessions_dir.resolve()
        path = (sessions_root / session_name).resolve()
        if not path.is_relative_to(sessions_root):
            if strict:
                raise HTTPException(
                    status_code=400,
                    detail="Registration path escaped the server-owned sessions root.",
                )
            LOGGER.warning(
                "Skipping registration cleanup for escaped session key `%s`.", session_name
            )
            return None
        return path


def _try_parse_json_bytes(body: bytes) -> object | None:
    """Return optional JSON payload parsed from raw bytes."""

    if not body:
        return None
    try:
        payload: object = json.loads(body.decode("utf-8"))
        return payload
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


TerminalWatchWorker = SessionWatchWorker


def _is_safe_registration_session_name(session_name: str) -> bool:
    """Return whether one session name is safe for server-owned registration storage."""

    if not session_name or session_name != session_name.strip():
        return False
    if session_name in {".", ".."}:
        return False
    if "/" in session_name or "\\" in session_name or "\x00" in session_name:
        return False
    return True
