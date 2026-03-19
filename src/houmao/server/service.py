"""Core service runtime for `houmao-server`."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib import error, parse, request

from fastapi import HTTPException, Response

from houmao.cao.models import CaoTerminal
from houmao.cao.no_proxy import scoped_loopback_no_proxy_for_cao_base_url

from .child_cao import ChildCaoManager
from .config import HoumaoServerConfig
from .models import (
    ChildCaoStatus,
    HoumaoCurrentInstance,
    HoumaoExternalActivity,
    HoumaoHealthResponse,
    HoumaoOperatorState,
    HoumaoOwnedWork,
    HoumaoRawObservation,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryEntry,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateRecord,
    HoumaoTerminalStateResponse,
)

_STATUS_TO_OPERATOR_STATE: dict[str, str] = {
    "idle": "ready",
    "completed": "completed",
    "processing": "processing",
    "waiting_user_answer": "waiting_user_answer",
    "error": "error",
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _default_operator_state() -> HoumaoOperatorState:
    """Return the initial terminal operator-state."""

    return HoumaoOperatorState(
        status="unknown",
        detail="No observation has been recorded yet.",
        updated_at_utc=_utc_now(),
    )


@dataclass(frozen=True)
class ProxyResponse:
    """One proxied child-CAO response."""

    status_code: int
    body: bytes
    content_type: str
    json_payload: object | None

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
            content_type = exc.headers.get_content_type() if exc.headers is not None else "text/plain"
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


@dataclass
class TerminalRegistryState:
    """In-memory terminal watch state."""

    terminal: CaoTerminal
    raw_observation: HoumaoRawObservation | None = None
    owned_work: HoumaoOwnedWork = field(default_factory=HoumaoOwnedWork)
    external_activity: HoumaoExternalActivity = field(default_factory=HoumaoExternalActivity)
    operator_state: HoumaoOperatorState = field(default_factory=_default_operator_state)
    last_output_hash: str | None = None


class TerminalWatchWorker:
    """Background polling worker for one live terminal."""

    def __init__(self, *, service: "HoumaoServerService", terminal_id: str) -> None:
        self.m_service = service
        self.m_terminal_id = terminal_id
        self.m_stop_event = threading.Event()
        self.m_thread = threading.Thread(
            target=self._run,
            name=f"houmao-watch-{terminal_id}",
            daemon=True,
        )

    def start(self) -> None:
        """Start the polling thread."""

        self.m_thread.start()

    def stop(self, *, join: bool = True) -> None:
        """Request worker termination."""

        self.m_stop_event.set()
        if join:
            self.m_thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self.m_stop_event.is_set():
            try:
                self.m_service.refresh_terminal_state(self.m_terminal_id)
            except Exception:
                self.m_service.mark_terminal_unavailable(self.m_terminal_id)
            self.m_stop_event.wait(self.m_service.m_config.watch_poll_interval_seconds)


class HoumaoServerService:
    """Application-owned `houmao-server` runtime state."""

    def __init__(
        self,
        *,
        config: HoumaoServerConfig,
        transport: ProxyTransport | None = None,
        child_manager: ChildCaoManager | None = None,
    ) -> None:
        self.m_config = config
        self.m_transport = transport or UrlLibProxyTransport()
        self.m_child_manager = child_manager or ChildCaoManager(config=config)
        self.m_lock = threading.RLock()
        self.m_terminals: dict[str, TerminalRegistryState] = {}
        self.m_workers: dict[str, TerminalWatchWorker] = {}
        self.m_sessions: dict[str, set[str]] = {}

    def startup(self) -> None:
        """Start the service runtime."""

        self._ensure_directories()
        if self.m_config.startup_child:
            self.m_child_manager.start()
        self._write_current_instance()
        self._seed_from_child()

    def shutdown(self) -> None:
        """Stop the service runtime."""

        with self.m_lock:
            workers = list(self.m_workers.values())
            self.m_workers.clear()
        for worker in workers:
            worker.stop(join=True)
        if self.m_config.startup_child:
            try:
                self.m_child_manager.stop()
            except Exception:
                pass

    def proxy(self, *, method: str, path: str, params: dict[str, str] | None = None) -> ProxyResponse:
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
        """Register one terminal payload returned by the child CAO API."""

        if not isinstance(payload, dict):
            return
        terminal = CaoTerminal.model_validate(payload)
        self._ensure_terminal_registration(terminal)

    def handle_deleted_terminal(self, terminal_id: str) -> None:
        """Remove one terminal from the in-memory registry."""

        with self.m_lock:
            worker = self.m_workers.pop(terminal_id, None)
            state = self.m_terminals.pop(terminal_id, None)
            if state is not None:
                session_terminals = self.m_sessions.get(state.terminal.session_name)
                if session_terminals is not None:
                    session_terminals.discard(terminal_id)
                    if not session_terminals:
                        self.m_sessions.pop(state.terminal.session_name, None)
        if worker is not None:
            worker.stop(join=True)

    def handle_deleted_session(self, session_name: str) -> None:
        """Remove all known session-owned terminals."""

        terminal_ids = sorted(self.m_sessions.get(session_name, set()))
        for terminal_id in terminal_ids:
            self.handle_deleted_terminal(terminal_id)

    def note_prompt_submission(self, *, terminal_id: str, message: str) -> None:
        """Record one server-owned prompt submission."""

        with self.m_lock:
            state = self.m_terminals.get(terminal_id)
            if state is None:
                return
            state.owned_work = HoumaoOwnedWork(
                request_id=uuid.uuid4().hex,
                submitted_at_utc=_utc_now(),
                completed_at_utc=None,
                message_excerpt=message[:200],
                state="submitted",
            )

    def register_launch(self, request_model: HoumaoRegisterLaunchRequest) -> HoumaoRegisterLaunchResponse:
        """Register one delegated CLI launch into the server-owned registry."""

        session_name = request_model.session_name
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
        terminal = CaoTerminal.model_validate(payload)
        self._ensure_terminal_registration(terminal)

        registration_dir = (self.m_config.sessions_dir / session_name).resolve()
        registration_dir.mkdir(parents=True, exist_ok=True)
        registration_path = registration_dir / "registration.json"
        registration_path.write_text(
            json.dumps(request_model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return HoumaoRegisterLaunchResponse(
            success=True,
            session_name=session_name,
            terminal_id=terminal_id,
        )

    def terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        """Return the latest terminal state view."""

        with self.m_lock:
            state = self.m_terminals.get(terminal_id)
            if state is None:
                raise HTTPException(status_code=404, detail=f"Unknown terminal `{terminal_id}`.")
            return HoumaoTerminalStateResponse(
                terminal=state.terminal,
                raw_observation=state.raw_observation,
                owned_work=state.owned_work,
                external_activity=state.external_activity,
                operator_state=state.operator_state,
            )

    def terminal_history(self, terminal_id: str, *, limit: int) -> HoumaoTerminalHistoryResponse:
        """Return recent append-only terminal history entries."""

        history_dir = self._terminal_history_dir(terminal_id)
        entries: list[HoumaoTerminalHistoryEntry] = []
        for file_name in ("samples.ndjson", "transitions.ndjson"):
            path = history_dir / file_name
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                entries.append(HoumaoTerminalHistoryEntry.model_validate(payload))
        entries.sort(key=lambda item: item.recorded_at_utc)
        if limit > 0:
            entries = entries[-limit:]
        return HoumaoTerminalHistoryResponse(terminal_id=terminal_id, entries=entries)

    def refresh_terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        """Poll the child CAO API and update one terminal watch snapshot."""

        terminal_proxy = self.proxy(
            method="GET",
            path=f"/terminals/{parse.quote(terminal_id, safe='')}",
        )
        output_proxy = self.proxy(
            method="GET",
            path=f"/terminals/{parse.quote(terminal_id, safe='')}/output",
            params={"mode": "full"},
        )
        if not isinstance(terminal_proxy.json_payload, dict):
            raise HTTPException(status_code=502, detail="Terminal lookup returned invalid JSON.")
        terminal = CaoTerminal.model_validate(terminal_proxy.json_payload)
        output_text = ""
        if isinstance(output_proxy.json_payload, dict):
            output_text = str(output_proxy.json_payload.get("output", ""))

        now = _utc_now()
        output_hash = hashlib.sha1(output_text.encode("utf-8")).hexdigest()
        observation = HoumaoRawObservation(
            observed_at_utc=now,
            terminal_id=terminal.id,
            session_name=terminal.session_name,
            backend_status=terminal.status.value if terminal.status is not None else None,
            output_hash=output_hash,
            output_length=len(output_text),
            output_excerpt=output_text[-4000:],
        )

        with self.m_lock:
            state = self.m_terminals.get(terminal_id)
            if state is None:
                state = TerminalRegistryState(terminal=terminal)
                self.m_terminals[terminal_id] = state
            previous_hash = state.last_output_hash
            previous_status = (
                state.operator_state.status if state.operator_state is not None else "unknown"
            )
            state.terminal = terminal
            state.raw_observation = observation
            state.last_output_hash = output_hash
            if previous_hash is not None and previous_hash != output_hash and state.owned_work.state == "idle":
                state.external_activity = HoumaoExternalActivity(
                    last_changed_at_utc=now,
                    output_hash=output_hash,
                )
            if state.owned_work.state == "submitted" and terminal.status is not None and terminal.status.value in {
                "idle",
                "completed",
                "waiting_user_answer",
                "error",
            }:
                state.owned_work = HoumaoOwnedWork(
                    request_id=state.owned_work.request_id,
                    submitted_at_utc=state.owned_work.submitted_at_utc,
                    completed_at_utc=now,
                    message_excerpt=state.owned_work.message_excerpt,
                    state="completed",
                )
            elif state.owned_work.state == "completed":
                state.owned_work = HoumaoOwnedWork(
                    request_id=state.owned_work.request_id,
                    submitted_at_utc=state.owned_work.submitted_at_utc,
                    completed_at_utc=state.owned_work.completed_at_utc,
                    message_excerpt=state.owned_work.message_excerpt,
                    state="idle",
                )
            operator_status = _STATUS_TO_OPERATOR_STATE.get(
                terminal.status.value if terminal.status is not None else "unknown",
                "unknown",
            )
            state.operator_state = HoumaoOperatorState(
                status=operator_status,  # type: ignore[arg-type]
                detail=(
                    f"Terminal status is `{terminal.status.value}`."
                    if terminal.status is not None
                    else "Terminal status is unavailable."
                ),
                updated_at_utc=now,
            )
            response = HoumaoTerminalStateResponse(
                terminal=state.terminal,
                raw_observation=state.raw_observation,
                owned_work=state.owned_work,
                external_activity=state.external_activity,
                operator_state=state.operator_state,
            )

        self._write_terminal_state(response)
        self._append_history_entry(
            terminal_id=terminal_id,
            kind="sample",
            payload=response.model_dump(mode="json"),
            recorded_at_utc=now,
        )
        if previous_status != response.operator_state.status:
            self._append_history_entry(
                terminal_id=terminal_id,
                kind="transition",
                payload={
                    "from_status": previous_status,
                    "to_status": response.operator_state.status,
                    "detail": response.operator_state.detail,
                },
                recorded_at_utc=now,
            )
        return response

    def mark_terminal_unavailable(self, terminal_id: str) -> None:
        """Record an unavailable state for a watched terminal."""

        with self.m_lock:
            state = self.m_terminals.get(terminal_id)
            if state is None:
                return
            state.operator_state = HoumaoOperatorState(
                status="unavailable",
                detail="Child CAO terminal polling failed.",
                updated_at_utc=_utc_now(),
            )

    def _seed_from_child(self) -> None:
        """Best-effort discovery of existing child-managed sessions and terminals."""

        try:
            proxy = self.proxy(method="GET", path="/sessions")
        except HTTPException:
            return
        payload = proxy.json_payload
        if not isinstance(payload, list):
            return
        for session in payload:
            if not isinstance(session, dict):
                continue
            session_name = str(session.get("id", "")).strip()
            if not session_name:
                continue
            terminals_proxy = self.proxy(
                method="GET",
                path=f"/sessions/{parse.quote(session_name, safe='')}/terminals",
            )
            terminals_payload = terminals_proxy.json_payload
            if not isinstance(terminals_payload, list):
                continue
            for terminal_payload in terminals_payload:
                if not isinstance(terminal_payload, dict):
                    continue
                try:
                    terminal = CaoTerminal.model_validate(terminal_payload)
                except Exception:
                    continue
                self._ensure_terminal_registration(terminal)

    def _ensure_terminal_registration(self, terminal: CaoTerminal) -> None:
        with self.m_lock:
            existing = self.m_terminals.get(terminal.id)
            if existing is None:
                self.m_terminals[terminal.id] = TerminalRegistryState(terminal=terminal)
            else:
                existing.terminal = terminal
            session_terminals = self.m_sessions.setdefault(terminal.session_name, set())
            session_terminals.add(terminal.id)
            if terminal.id not in self.m_workers:
                worker = TerminalWatchWorker(service=self, terminal_id=terminal.id)
                self.m_workers[terminal.id] = worker
                worker.start()

    def _ensure_directories(self) -> None:
        for path in (
            self.m_config.server_root,
            self.m_config.logs_dir,
            self.m_config.run_dir,
            self.m_config.state_dir,
            self.m_config.history_dir,
            self.m_config.sessions_dir,
            self.m_config.child_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _write_current_instance(self) -> None:
        payload = self.current_instance_response().model_dump(mode="json")
        self.m_config.current_instance_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.m_config.pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")

    def _terminal_state_path(self, terminal_id: str) -> Path:
        return (self.m_config.terminal_state_root / terminal_id / "current.json").resolve()

    def _terminal_history_dir(self, terminal_id: str) -> Path:
        return (self.m_config.terminal_history_root / terminal_id).resolve()

    def _write_terminal_state(self, response: HoumaoTerminalStateResponse) -> None:
        path = self._terminal_state_path(response.terminal.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = HoumaoTerminalStateRecord(state=response)
        path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _append_history_entry(
        self,
        *,
        terminal_id: str,
        kind: str,
        payload: dict[str, object],
        recorded_at_utc: str,
    ) -> None:
        history_dir = self._terminal_history_dir(terminal_id)
        history_dir.mkdir(parents=True, exist_ok=True)
        path = history_dir / ("samples.ndjson" if kind == "sample" else "transitions.ndjson")
        entry = HoumaoTerminalHistoryEntry(
            recorded_at_utc=recorded_at_utc,
            kind="sample" if kind == "sample" else "transition",
            payload=payload,
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.model_dump(mode="json"), sort_keys=True) + "\n")


def _try_parse_json_bytes(payload: bytes) -> object | None:
    if not payload:
        return None
    try:
        decoded: object = json.loads(payload.decode("utf-8"))
        return decoded
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
