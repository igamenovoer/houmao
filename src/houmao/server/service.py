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

from houmao.agents.realm_controller.backends.headless_base import HeadlessInteractiveSession
from houmao.agents.realm_controller.backends.headless_runner import (
    load_headless_turn_events,
    read_headless_turn_return_code,
)
from houmao.cao.models import CaoTerminal
from houmao.cao.no_proxy import scoped_loopback_no_proxy_for_cao_base_url
from houmao.agents.realm_controller.errors import LaunchPlanError, SessionManifestError
from houmao.agents.realm_controller.launch_plan import backend_for_tool
from houmao.agents.realm_controller.loaders import load_brain_manifest, load_role_package
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    resume_runtime_session,
    start_runtime_session,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    list_tmux_panes,
    run_tmux,
    tmux_session_exists,
    tmux_error_detail,
)
from houmao.server.managed_agents import (
    ManagedHeadlessActiveTurnRecord,
    ManagedHeadlessAuthorityRecord,
    ManagedHeadlessStore,
    ManagedHeadlessTurnRecord,
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

from houmao.server.child_cao import ChildCaoInstallError, ChildCaoManager
from houmao.server.config import HoumaoServerConfig
from houmao.server.models import (
    ChildCaoStatus,
    HoumaoCurrentInstance,
    HoumaoErrorDetail,
    HoumaoHeadlessLaunchRequest,
    HoumaoHeadlessLaunchResponse,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEvent,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoHealthResponse,
    HoumaoInstallAgentProfileRequest,
    HoumaoInstallAgentProfileResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentHistoryEntry,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
    HoumaoProbeSnapshot,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
)
from houmao.server.tracking_debug import TrackingDebugSink

LOGGER = logging.getLogger(__name__)


class _ManagedHeadlessAgentHandle:
    """One live native headless managed-agent runtime binding."""

    def __init__(
        self,
        *,
        authority: ManagedHeadlessAuthorityRecord,
        controller: RuntimeSessionController,
    ) -> None:
        """Initialize the managed headless handle."""

        self.m_authority = authority
        self.m_controller = controller
        self.m_active_thread: threading.Thread | None = None

    @property
    def authority(self) -> ManagedHeadlessAuthorityRecord:
        """Return the persisted authority record."""

        return self.m_authority

    @property
    def controller(self) -> RuntimeSessionController:
        """Return the bound runtime controller."""

        return self.m_controller

    @property
    def active_thread(self) -> threading.Thread | None:
        """Return the optional active background turn thread."""

        return self.m_active_thread

    def set_active_thread(self, value: threading.Thread | None) -> None:
        """Update the active background turn thread binding."""

        self.m_active_thread = value


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
        managed_headless_store: ManagedHeadlessStore | None = None,
        transport_resolver: TmuxTransportResolver | None = None,
        process_inspector: PaneProcessInspector | None = None,
        parser_adapter: OfficialTuiParserAdapter | None = None,
        tracking_debug_sink: TrackingDebugSink | None = None,
    ) -> None:
        """Initialize the service runtime."""

        self.m_config = config
        self.m_transport = transport or UrlLibProxyTransport()
        self.m_child_manager = child_manager or ChildCaoManager(config=config)
        self.m_known_session_registry = known_session_registry or KnownSessionRegistry(
            config=config
        )
        self.m_managed_headless_store = managed_headless_store or ManagedHeadlessStore(
            config=config
        )
        self.m_transport_resolver = transport_resolver or TmuxTransportResolver()
        self.m_process_inspector = process_inspector or PaneProcessInspector(
            supported_processes=config.supported_tui_processes
        )
        self.m_parser_adapter = parser_adapter or OfficialTuiParserAdapter()
        self.m_tracking_debug_sink = tracking_debug_sink or TrackingDebugSink.from_env()
        self.m_lock = threading.RLock()
        self.m_trackers: dict[str, LiveSessionTracker] = {}
        self.m_terminal_aliases: dict[str, str] = {}
        self.m_headless_agents: dict[str, _ManagedHeadlessAgentHandle] = {}
        self.m_supervisor = TuiTrackingSupervisor(runtime=self)

    def startup(self) -> None:
        """Start the service runtime."""

        self._ensure_directories()
        self.m_managed_headless_store.ensure_directories()
        if self.m_config.startup_child:
            self.m_child_manager.start()
        self._write_current_instance()
        self._rebuild_headless_agents()
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

    def install_agent_profile(
        self, request_model: HoumaoInstallAgentProfileRequest
    ) -> HoumaoInstallAgentProfileResponse:
        """Install one agent profile into the server-managed child CAO state."""

        working_directory = (
            Path(request_model.working_directory).expanduser().resolve()
            if request_model.working_directory is not None
            else None
        )
        if working_directory is not None and (
            not working_directory.exists() or not working_directory.is_dir()
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Pair-owned install requires an existing working directory when one is "
                    "provided."
                ),
            )

        try:
            install_result = self.m_child_manager.install_agent_profile(
                agent_source=request_model.agent_source,
                provider=request_model.provider,
                working_directory=working_directory,
            )
        except ChildCaoInstallError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        if install_result.returncode != 0:
            LOGGER.warning(
                "Pair-owned install failed for provider=%s agent_source=%s returncode=%s "
                "stdout=%r stderr=%r",
                request_model.provider,
                request_model.agent_source,
                install_result.returncode,
                install_result.stdout,
                install_result.stderr,
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Pair-owned install failed through managed child CAO state for "
                    f"provider `{request_model.provider}` and agent source "
                    f"`{request_model.agent_source}` (exit code {install_result.returncode})."
                ),
            )

        LOGGER.info(
            "Pair-owned install completed for provider=%s agent_source=%s",
            request_model.provider,
            request_model.agent_source,
        )
        return HoumaoInstallAgentProfileResponse(
            success=True,
            agent_source=request_model.agent_source,
            provider=request_model.provider,
            detail=(
                "Pair-owned install completed through managed child CAO state for "
                f"provider `{request_model.provider}` and agent source "
                f"`{request_model.agent_source}`."
            ),
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
        """Record one server-owned turn anchor after a successful input submission."""

        monotonic_ts = time.monotonic()
        try:
            tracker = self._tracker_for_terminal_alias(terminal_id)
        except HTTPException:
            self.emit_tracking_debug(
                stream="service-prompt-submission",
                event_type="note_prompt_submission_unknown_terminal",
                terminal_id=terminal_id,
                monotonic_ts=monotonic_ts,
                data={
                    "message_excerpt": _message_excerpt(message),
                    "message_sha1": _message_sha1(message),
                },
            )
            return

        identity = tracker.current_state().tracked_session
        self.emit_tracking_debug(
            stream="service-prompt-submission",
            event_type="note_prompt_submission_called",
            terminal_id=terminal_id,
            tracked_session_id=identity.tracked_session_id,
            tool=identity.tool,
            monotonic_ts=monotonic_ts,
            data={
                "message_excerpt": _message_excerpt(message),
                "message_sha1": _message_sha1(message),
            },
        )
        state = tracker.note_prompt_submission(
            message=message,
            observed_at_utc=utc_now_iso(),
            monotonic_ts=monotonic_ts,
        )
        self.emit_tracking_debug(
            stream="service-prompt-submission",
            event_type="note_prompt_submission_recorded",
            terminal_id=state.terminal_id,
            tracked_session_id=state.tracked_session.tracked_session_id,
            tool=state.tracked_session.tool,
            monotonic_ts=monotonic_ts,
            anchor_id=getattr(tracker.m_active_turn_anchor, "anchor_id", None),
            data={
                "completion_authority": state.lifecycle_authority.completion_authority,
                "turn_anchor_state": state.lifecycle_authority.turn_anchor_state,
                "completion_monitoring_armed": (
                    state.lifecycle_authority.completion_monitoring_armed
                ),
            },
        )

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

    def list_managed_agents(self) -> HoumaoManagedAgentListResponse:
        """Return the shared managed-agent discovery surface."""

        self._ensure_tui_trackers_seeded()
        identities: list[HoumaoManagedAgentIdentity] = []
        with self.m_lock:
            trackers = list(self.m_trackers.values())
            headless_handles = list(self.m_headless_agents.values())

        for tracker in trackers:
            identities.append(self._managed_identity_from_tui_tracker(tracker))
        for handle in headless_handles:
            identities.append(self._managed_identity_from_headless_handle(handle))

        identities.sort(key=lambda item: (item.transport, item.tracked_agent_id))
        return HoumaoManagedAgentListResponse(agents=identities)

    def managed_agent(self, agent_ref: str) -> HoumaoManagedAgentIdentity:
        """Return one managed-agent identity from the shared surface."""

        resolved = self._resolve_managed_agent_ref(agent_ref)
        if resolved["transport"] == "tui":
            tracker = self._tracker_for_session_id(resolved["tracked_agent_id"])
            return self._managed_identity_from_tui_tracker(tracker)

        handle = self._require_headless_handle(resolved["tracked_agent_id"])
        return self._managed_identity_from_headless_handle(handle)

    def managed_agent_state(self, agent_ref: str) -> HoumaoManagedAgentStateResponse:
        """Return the shared coarse state for one managed agent."""

        resolved = self._resolve_managed_agent_ref(agent_ref)
        if resolved["transport"] == "tui":
            tracker = self._tracker_for_session_id(resolved["tracked_agent_id"])
            return self._managed_state_from_tui_tracker(tracker)

        tracked_agent_id = resolved["tracked_agent_id"]
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        handle = self._require_headless_handle(tracked_agent_id)
        return self._managed_state_from_headless_handle(handle)

    def managed_agent_history(
        self,
        agent_ref: str,
        *,
        limit: int,
    ) -> HoumaoManagedAgentHistoryResponse:
        """Return bounded coarse recent history for one managed agent."""

        resolved = self._resolve_managed_agent_ref(agent_ref)
        if resolved["transport"] == "tui":
            tracker = self._tracker_for_session_id(resolved["tracked_agent_id"])
            raw_history = tracker.history(limit=limit)
            return HoumaoManagedAgentHistoryResponse(
                tracked_agent_id=raw_history.tracked_session_id,
                entries=[
                    HoumaoManagedAgentHistoryEntry(
                        recorded_at_utc=entry.recorded_at_utc,
                        summary=entry.summary,
                        availability=_availability_from_tui_transition(entry),
                        turn_phase=_turn_phase_from_tui_operator_status(entry.operator_status),
                        last_turn_result=_last_turn_result_from_tui_operator_status(
                            entry.operator_status
                        ),
                        turn_id=None,
                    )
                    for entry in raw_history.entries
                ],
            )

        tracked_agent_id = resolved["tracked_agent_id"]
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        return HoumaoManagedAgentHistoryResponse(
            tracked_agent_id=tracked_agent_id,
            entries=self._headless_history_entries(
                tracked_agent_id=tracked_agent_id,
                limit=limit,
            ),
        )

    def launch_headless_agent(
        self,
        request_model: HoumaoHeadlessLaunchRequest,
    ) -> HoumaoHeadlessLaunchResponse:
        """Launch one server-managed native headless agent."""

        resolved_tool = request_model.tool.strip()
        try:
            resolved_workdir = Path(request_model.working_directory).expanduser().resolve(strict=True)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=422,
                detail="Native headless launch requires an existing working_directory.",
            ) from exc
        if not resolved_workdir.is_dir():
            raise HTTPException(
                status_code=422,
                detail="Native headless launch requires working_directory to be a directory.",
            )

        agent_def_dir = Path(request_model.agent_def_dir).expanduser().resolve()
        if not agent_def_dir.is_dir():
            raise HTTPException(
                status_code=422,
                detail="Native headless launch requires an existing agent_def_dir directory.",
            )

        brain_manifest_path = Path(request_model.brain_manifest_path).expanduser().resolve()
        if not brain_manifest_path.is_file():
            raise HTTPException(
                status_code=422,
                detail="Native headless launch requires an existing brain_manifest_path file.",
            )

        try:
            manifest = load_brain_manifest(brain_manifest_path)
            load_role_package(agent_def_dir, request_model.role_name)
        except (LaunchPlanError, SessionManifestError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        manifest_tool = str(manifest.get("inputs", {}).get("tool", "")).strip()
        if manifest_tool != resolved_tool:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Native headless launch requires tool to match "
                    f"brain_manifest_path inputs.tool; got request={resolved_tool!r} "
                    f"manifest={manifest_tool!r}."
                ),
            )

        try:
            controller = start_runtime_session(
                agent_def_dir=agent_def_dir,
                brain_manifest_path=brain_manifest_path,
                role_name=request_model.role_name,
                backend=backend_for_tool(resolved_tool),
                working_directory=resolved_workdir,
                api_base_url=self.m_config.api_base_url,
                agent_identity=request_model.agent_name,
                agent_id=request_model.agent_id,
            )
        except (LaunchPlanError, SessionManifestError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        tracked_agent_id = controller.manifest_path.parent.name
        authority = ManagedHeadlessAuthorityRecord(
            tracked_agent_id=tracked_agent_id,
            backend=controller.launch_plan.backend,
            tool=resolved_tool,
            manifest_path=str(controller.manifest_path),
            session_root=str(controller.manifest_path.parent),
            tmux_session_name=self._require_controller_tmux_session_name(controller),
            agent_def_dir=str(agent_def_dir),
            agent_name=controller.agent_identity,
            agent_id=controller.agent_id,
            created_at_utc=utc_now_iso(),
            updated_at_utc=utc_now_iso(),
        )
        self.m_managed_headless_store.write_authority(authority)
        handle = _ManagedHeadlessAgentHandle(authority=authority, controller=controller)
        with self.m_lock:
            self.m_headless_agents[tracked_agent_id] = handle

        identity = self._managed_identity_from_headless_handle(handle)
        return HoumaoHeadlessLaunchResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            identity=identity,
            manifest_path=str(controller.manifest_path),
            session_root=str(controller.manifest_path.parent),
            detail=(
                f"Native headless agent `{tracked_agent_id}` launched for tool "
                f"`{resolved_tool}`."
            ),
        )

    def stop_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Stop one managed headless agent and delete its server authority."""

        resolved = self._resolve_managed_agent_ref(agent_ref)
        if resolved["transport"] != "headless":
            raise HTTPException(
                status_code=400,
                detail="Managed-agent stop is only supported for native headless agents in v1.",
            )

        tracked_agent_id = resolved["tracked_agent_id"]
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        handle = self._require_headless_handle(tracked_agent_id)
        active_turn = self.m_managed_headless_store.read_active_turn(tracked_agent_id=tracked_agent_id)
        if active_turn is not None:
            self._interrupt_active_turn_record(active_turn)
            active_thread = handle.active_thread
            if active_thread is not None:
                active_thread.join(timeout=5.0)

        result = handle.controller.stop(force_cleanup=True)
        if result.status != "ok":
            raise HTTPException(status_code=502, detail=result.detail)

        self.m_managed_headless_store.delete_agent(tracked_agent_id=tracked_agent_id)
        with self.m_lock:
            self.m_headless_agents.pop(tracked_agent_id, None)
        return HoumaoManagedAgentActionResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            detail=result.detail,
            turn_id=active_turn.turn_id if active_turn is not None else None,
        )

    def submit_headless_turn(
        self,
        agent_ref: str,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        """Accept one prompt for a managed native headless agent."""

        resolved = self._resolve_managed_agent_ref(agent_ref)
        if resolved["transport"] != "headless":
            raise HTTPException(
                status_code=400,
                detail="Headless turn submission is only supported for native headless agents.",
            )

        tracked_agent_id = resolved["tracked_agent_id"]
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        handle = self._require_headless_handle(tracked_agent_id)
        if self.m_managed_headless_store.read_active_turn(tracked_agent_id=tracked_agent_id) is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Managed headless turn submission rejected because this agent already "
                    "has an active turn."
                ),
            )

        backend_turn_index = self._next_headless_backend_turn_index(handle.controller)
        turn_id = f"turn-{_message_sha1(f'{tracked_agent_id}:{backend_turn_index}:{time.time()}')[:12]}"
        turn_artifact_dir = self._headless_turn_artifacts_root(handle.controller) / turn_id
        turn_record = ManagedHeadlessTurnRecord(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            turn_index=backend_turn_index,
            status="active",
            started_at_utc=utc_now_iso(),
            turn_artifact_dir=str(turn_artifact_dir),
            tmux_session_name=self._require_controller_tmux_session_name(handle.controller),
            tmux_window_name=turn_id,
            history_summary=f"Turn {turn_id} accepted.",
        )
        active_turn = ManagedHeadlessActiveTurnRecord(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            turn_index=backend_turn_index,
            turn_artifact_dir=str(turn_artifact_dir),
            started_at_utc=turn_record.started_at_utc,
            tmux_session_name=turn_record.tmux_session_name,
            tmux_window_name=turn_id,
        )
        self.m_managed_headless_store.write_turn_record(turn_record)
        self.m_managed_headless_store.write_active_turn(active_turn)

        worker = threading.Thread(
            target=self._run_headless_turn_worker,
            kwargs={
                "tracked_agent_id": tracked_agent_id,
                "turn_id": turn_id,
                "prompt": request_model.prompt,
            },
            daemon=True,
            name=f"houmao-headless-turn-{tracked_agent_id}-{turn_id}",
        )
        handle.set_active_thread(worker)
        worker.start()

        return HoumaoHeadlessTurnAcceptedResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            turn_index=backend_turn_index,
            status="active",
            detail=f"Managed headless turn `{turn_id}` accepted.",
        )

    def headless_turn_status(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnStatusResponse:
        """Return one managed headless turn status."""

        tracked_agent_id = self._require_headless_agent_ref(agent_ref)
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        turn_record = self._require_turn_record(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
        )
        return self._headless_turn_status_response(turn_record)

    def headless_turn_events(
        self,
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnEventsResponse:
        """Return structured events for one managed headless turn."""

        tracked_agent_id = self._require_headless_agent_ref(agent_ref)
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        turn_record = self._require_turn_record(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
        )
        stdout_path = Path(turn_record.stdout_path) if turn_record.stdout_path is not None else None
        entries: list[HoumaoHeadlessTurnEvent] = []
        if stdout_path is not None and stdout_path.exists():
            for event in load_headless_turn_events(
                stdout_path=stdout_path,
                output_format=self._headless_output_format(
                    tracked_agent_id=tracked_agent_id,
                ),
                turn_index=turn_record.turn_index,
            ):
                entries.append(
                    HoumaoHeadlessTurnEvent(
                        kind=event.kind,
                        message=event.message,
                        turn_index=event.turn_index,
                        timestamp_utc=event.timestamp_utc,
                        payload=event.payload,
                    )
                )
        return HoumaoHeadlessTurnEventsResponse(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            entries=entries,
        )

    def headless_turn_artifact_text(
        self,
        agent_ref: str,
        turn_id: str,
        *,
        artifact_name: str,
    ) -> str:
        """Return one raw persisted headless artifact as text."""

        tracked_agent_id = self._require_headless_agent_ref(agent_ref)
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        turn_record = self._require_turn_record(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
        )
        if artifact_name == "stdout":
            artifact_path = Path(turn_record.stdout_path) if turn_record.stdout_path is not None else None
        elif artifact_name == "stderr":
            artifact_path = Path(turn_record.stderr_path) if turn_record.stderr_path is not None else None
        else:
            raise HTTPException(status_code=400, detail=f"Unknown headless artifact `{artifact_name}`.")

        if artifact_path is None or not artifact_path.exists():
            return ""
        return artifact_path.read_text(encoding="utf-8")

    def interrupt_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Interrupt the active turn for one managed headless agent."""

        tracked_agent_id = self._require_headless_agent_ref(agent_ref)
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        active_turn = self.m_managed_headless_store.read_active_turn(tracked_agent_id=tracked_agent_id)
        if active_turn is None:
            return HoumaoManagedAgentActionResponse(
                success=True,
                tracked_agent_id=tracked_agent_id,
                detail="No active headless turn is running.",
                turn_id=None,
            )

        self._interrupt_active_turn_record(active_turn)
        return HoumaoManagedAgentActionResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            detail=f"Best-effort interrupt requested for turn `{active_turn.turn_id}`.",
            turn_id=active_turn.turn_id,
        )

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
                    completion_stability_seconds=self.m_config.completion_stability_seconds,
                    unknown_to_stalled_timeout_seconds=self.m_config.unknown_to_stalled_timeout_seconds,
                    tracking_debug_sink=self.m_tracking_debug_sink,
                )
                self.m_trackers[record.tracked_session_id] = tracker
            else:
                tracker.set_identity(identity)
            for alias, tracked_session_id in list(self.m_terminal_aliases.items()):
                if tracked_session_id == record.tracked_session_id and alias != record.terminal_id:
                    self.m_terminal_aliases.pop(alias, None)
            self.m_terminal_aliases[record.terminal_id] = record.tracked_session_id

    def emit_tracking_debug(
        self,
        *,
        stream: str,
        event_type: str,
        monotonic_ts: float | None = None,
        terminal_id: str | None = None,
        tracked_session_id: str | None = None,
        tool: str | None = None,
        cycle_seq: int | None = None,
        anchor_id: int | None = None,
        data: dict[str, object] | None = None,
    ) -> None:
        """Emit one structured tracking-debug event when enabled."""

        if self.m_tracking_debug_sink is None:
            return
        self.m_tracking_debug_sink.emit(
            stream=stream,
            event_type=event_type,
            monotonic_ts=monotonic_ts,
            terminal_id=terminal_id,
            tracked_session_id=tracked_session_id,
            tool=tool,
            cycle_seq=cycle_seq,
            anchor_id=anchor_id,
            data=data,
        )

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
            matched_process_names=list(process_inspection.matched_process_names),
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


def _message_excerpt(message: str) -> str | None:
    """Return one short collapsed message excerpt for debug events."""

    collapsed = " ".join(message.split())
    if not collapsed:
        return None
    if len(collapsed) <= 120:
        return collapsed
    return f"{collapsed[:117]}..."


def _message_sha1(message: str) -> str:
    """Return one stable digest for a submitted prompt payload."""

    return hashlib.sha1(message.encode("utf-8")).hexdigest()


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
