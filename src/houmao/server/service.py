"""Core service runtime for `houmao-server`.

This service serves the CAO-compatible control surface locally while owning
live tmux/process observation and in-memory TUI tracking directly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeVar, cast
from urllib import error, parse, request

from fastapi import HTTPException, Response
from pydantic import BaseModel

from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayHeadlessControlStateV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.gateway_storage import (
    build_offline_gateway_status,
    refresh_internal_gateway_publication,
    gateway_paths_from_session_root,
    gateway_paths_from_manifest_path,
    load_gateway_status,
    resolve_internal_gateway_attach_contract,
)
from houmao.agents.realm_controller.backends.headless_base import HeadlessInteractiveSession
from houmao.agents.realm_controller.backends.headless_runner import (
    load_headless_turn_events,
    load_headless_process_metadata,
    read_headless_turn_return_code,
)
from houmao.cao.models import CaoTerminal
from houmao.cao.no_proxy import scoped_loopback_no_proxy_for_cao_base_url
from houmao.agents.realm_controller.errors import (
    GatewayHttpError,
    LaunchPlanError,
    SessionManifestError,
)
from houmao.agents.realm_controller.launch_plan import backend_for_tool
from houmao.agents.realm_controller.loaders import load_brain_manifest, load_role_package
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
    update_session_manifest,
)
from houmao.agents.realm_controller.registry_storage import (
    publish_live_agent_record,
    remove_live_agent_record,
    resolve_live_agent_record,
    resolve_live_agent_record_by_agent_id,
)
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    resume_runtime_session,
    start_runtime_session,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    HEADLESS_AGENT_WINDOW_NAME,
    TmuxCommandError,
    headless_agent_pane_target,
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

from houmao.server.config import HoumaoServerConfig
from houmao.server.control_core import CompatibilityControlCore, LocalCompatibilityTransport
from houmao.server.models import (
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
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayRequestAcceptedResponse,
    HoumaoManagedAgentGatewayRequestCreate,
    ManagedAgentAvailability,
    HoumaoManagedAgentHistoryEntry,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentMailActionResponse,
    HoumaoManagedAgentMailCheckRequest,
    HoumaoManagedAgentMailCheckResponse,
    HoumaoManagedAgentMailReplyRequest,
    HoumaoManagedAgentMailSendRequest,
    HoumaoManagedAgentMailStatusResponse,
    HoumaoManagedAgentMailboxSummaryView,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentRequestEnvelope,
    ManagedAgentLastTurnResult,
    HoumaoManagedAgentHeadlessDetailView,
    HoumaoManagedAgentInterruptRequest,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentSubmitPromptRequest,
    HoumaoManagedAgentGatewaySummaryView,
    HoumaoTrackedSessionIdentity,
    HoumaoManagedAgentTuiDetailView,
    HoumaoManagedAgentTurnView,
    HoumaoProbeSnapshot,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
)
from houmao.server.tracking_debug import TrackingDebugSink

LOGGER = logging.getLogger(__name__)

_GatewayModelT = TypeVar(
    "_GatewayModelT",
    bound=BaseModel,
)


@dataclass(frozen=True)
class ManagedAgentControlPlane:
    """Typed internal managed-agent control-plane seam."""

    tracked_agent_id: str
    transport: Literal["tui", "headless"]
    owner: Literal["direct", "gateway"]
    summary_state: Callable[[], HoumaoManagedAgentStateResponse]
    detail_response: Callable[[], HoumaoManagedAgentDetailResponse]
    history_response: Callable[[int], HoumaoManagedAgentHistoryResponse]
    submit_request: Callable[
        [HoumaoManagedAgentRequestEnvelope, str], HoumaoManagedAgentRequestAcceptedResponse
    ]
    gateway_summary: Callable[[], HoumaoManagedAgentGatewaySummaryView | None]
    submit_headless_turn: (
        Callable[[HoumaoHeadlessTurnRequest], HoumaoHeadlessTurnAcceptedResponse] | None
    ) = None
    terminal_state: Callable[[], HoumaoTerminalStateResponse] | None = None
    terminal_history: Callable[[int], HoumaoTerminalHistoryResponse] | None = None


class _ManagedHeadlessAgentHandle:
    """One live native headless managed-agent runtime binding."""

    def __init__(
        self,
        *,
        authority: ManagedHeadlessAuthorityRecord,
        controller: RuntimeSessionController | None,
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
    def controller(self) -> RuntimeSessionController | None:
        """Return the optional bound runtime controller."""

        return self.m_controller

    @property
    def active_thread(self) -> threading.Thread | None:
        """Return the optional active background turn thread."""

        return self.m_active_thread

    def set_active_thread(self, value: threading.Thread | None) -> None:
        """Update the active background turn thread binding."""

        self.m_active_thread = value

    def set_controller(self, value: RuntimeSessionController | None) -> None:
        """Update the optional runtime controller binding."""

        self.m_controller = value


class ProxyResponse:
    """One proxied CAO-compatible response."""

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
    """Transport contract for proxied CAO-compatible requests."""

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> ProxyResponse:
        """Send one CAO-compatible request."""


class UrlLibProxyTransport:
    """urllib-based CAO-compatible proxy transport."""

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> ProxyResponse:
        """Send one CAO-compatible request with urllib."""

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
                detail=f"Compatibility transport is unavailable: {reason}",
            ) from exc


class LocalCompatibilityTransportBridge:
    """Proxy-transport bridge that dispatches into the native control core."""

    def __init__(self, *, transport: LocalCompatibilityTransport) -> None:
        """Initialize the bridge transport."""

        self.m_transport = transport

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> ProxyResponse:
        """Dispatch one CAO-compatible request locally."""

        del base_url
        status_code, payload = self.m_transport.dispatch(
            method=method,
            path=path,
            params=params,
        )
        body = json.dumps(payload).encode("utf-8")
        return ProxyResponse(
            status_code=status_code,
            body=body,
            content_type="application/json",
            json_payload=payload,
        )


class HoumaoServerService:
    """Application-owned `houmao-server` runtime state."""

    def __init__(
        self,
        *,
        config: HoumaoServerConfig,
        transport: ProxyTransport | None = None,
        control_core: CompatibilityControlCore | None = None,
        child_manager: object | None = None,
        known_session_registry: KnownSessionRegistry | None = None,
        managed_headless_store: ManagedHeadlessStore | None = None,
        transport_resolver: TmuxTransportResolver | None = None,
        process_inspector: PaneProcessInspector | None = None,
        parser_adapter: OfficialTuiParserAdapter | None = None,
        tracking_debug_sink: TrackingDebugSink | None = None,
    ) -> None:
        """Initialize the service runtime."""

        del child_manager
        self.m_config = config
        self.m_control_core = control_core or CompatibilityControlCore(config=config)
        self.m_transport = transport or LocalCompatibilityTransportBridge(
            transport=LocalCompatibilityTransport(control_core=self.m_control_core)
        )
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
        self.m_control_core.startup()
        self._write_current_instance()
        self._rebuild_headless_agents()
        self.m_supervisor.start()
        self.m_supervisor.request_reconcile()

    def shutdown(self) -> None:
        """Stop the service runtime."""

        self.m_supervisor.stop()
        self.m_control_core.shutdown()

    def proxy(
        self, *, method: str, path: str, params: dict[str, str] | None = None
    ) -> ProxyResponse:
        """Dispatch one CAO-compatible request through the compatibility transport."""

        return self.m_transport.request(
            base_url=self.m_config.api_base_url,
            method=method,
            path=path,
            params=params,
        )

    def health_response(self) -> HoumaoHealthResponse:
        """Build the compatibility-safe health payload."""

        return HoumaoHealthResponse(
            status="ok",
            service="cli-agent-orchestrator",
        )

    def current_instance_response(self) -> HoumaoCurrentInstance:
        """Return the current server instance payload."""

        return HoumaoCurrentInstance(
            pid=os.getpid(),
            api_base_url=self.m_config.api_base_url,
            server_root=str(self.m_config.server_root),
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

        state = tracker.current_state()
        identity = state.tracked_session
        client = self._live_gateway_client_for_session_root(identity.session_root)
        if client is not None:
            self.emit_tracking_debug(
                stream="service-prompt-submission",
                event_type="note_prompt_submission_forwarding_to_gateway",
                terminal_id=terminal_id,
                tracked_session_id=identity.tracked_session_id,
                tool=identity.tool,
                monotonic_ts=monotonic_ts,
                data={
                    "message_excerpt": _message_excerpt(message),
                    "message_sha1": _message_sha1(message),
                },
            )
            try:
                self._invoke_live_gateway(lambda: client.note_tui_prompt_submission(prompt=message))
                return
            except HTTPException as exc:
                self.emit_tracking_debug(
                    stream="service-prompt-submission",
                    event_type="note_prompt_submission_gateway_forward_failed",
                    terminal_id=terminal_id,
                    tracked_session_id=identity.tracked_session_id,
                    tool=identity.tool,
                    monotonic_ts=monotonic_ts,
                    data={
                        "detail": str(exc.detail),
                        "message_excerpt": _message_excerpt(message),
                        "message_sha1": _message_sha1(message),
                    },
                )

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
        lifecycle_authority = state.lifecycle_authority
        self.emit_tracking_debug(
            stream="service-prompt-submission",
            event_type="note_prompt_submission_recorded",
            terminal_id=state.terminal_id,
            tracked_session_id=state.tracked_session.tracked_session_id,
            tool=state.tracked_session.tool,
            monotonic_ts=monotonic_ts,
            anchor_id=getattr(tracker.m_active_turn_anchor, "anchor_id", None),
            data={
                "completion_authority": (
                    lifecycle_authority.completion_authority
                    if lifecycle_authority is not None
                    else None
                ),
                "turn_anchor_state": (
                    lifecycle_authority.turn_anchor_state
                    if lifecycle_authority is not None
                    else None
                ),
                "completion_monitoring_armed": (
                    lifecycle_authority.completion_monitoring_armed
                    if lifecycle_authority is not None
                    else None
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
                    detail="The compatibility control surface returned an invalid terminal payload during launch registration.",
                )
            terminal_id = str(first.get("id", "")).strip() or None
            if terminal_id is None:
                raise HTTPException(
                    status_code=502,
                    detail="The compatibility launch registration payload is missing terminal id.",
                )

        proxy = self.proxy(
            method="GET",
            path=f"/terminals/{parse.quote(terminal_id, safe='')}",
        )
        payload = proxy.json_payload
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=502,
                detail="The compatibility control surface returned an invalid terminal payload during launch registration.",
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

        control_plane = self._control_plane_for_terminal(terminal_id, operation="state")
        assert control_plane.terminal_state is not None
        return control_plane.terminal_state()

    def terminal_history(self, terminal_id: str, *, limit: int) -> HoumaoTerminalHistoryResponse:
        """Return bounded in-memory recent history for one terminal alias."""

        control_plane = self._control_plane_for_terminal(terminal_id, operation="history")
        assert control_plane.terminal_history is not None
        return control_plane.terminal_history(limit)

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

        control_plane = self._control_plane_for_managed_agent(agent_ref, operation="state")
        return control_plane.summary_state()

    def managed_agent_state_detail(self, agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        """Return transport-specific detail for one managed agent."""

        control_plane = self._control_plane_for_managed_agent(agent_ref, operation="detail")
        return control_plane.detail_response()

    def managed_agent_history(
        self,
        agent_ref: str,
        *,
        limit: int,
    ) -> HoumaoManagedAgentHistoryResponse:
        """Return bounded coarse recent history for one managed agent."""

        control_plane = self._control_plane_for_managed_agent(agent_ref, operation="history")
        return control_plane.history_response(limit)

    def submit_managed_agent_request(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentRequestEnvelope,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        """Accept one transport-neutral managed-agent request."""

        request_id = self._managed_request_id(
            agent_ref=agent_ref, request_kind=request_model.request_kind
        )
        control_plane = self._control_plane_for_managed_agent(agent_ref, operation="request")
        return control_plane.submit_request(request_model, request_id)

    def launch_headless_agent(
        self,
        request_model: HoumaoHeadlessLaunchRequest,
    ) -> HoumaoHeadlessLaunchResponse:
        """Launch one server-managed native headless agent."""

        resolved_tool = request_model.tool.strip()
        try:
            resolved_workdir = (
                Path(request_model.working_directory).expanduser().resolve(strict=True)
            )
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

        resolved_role_name = None
        if request_model.role_name is not None and request_model.role_name.strip():
            resolved_role_name = request_model.role_name.strip()

        try:
            manifest = load_brain_manifest(brain_manifest_path)
            if resolved_role_name is not None:
                load_role_package(agent_def_dir, resolved_role_name)
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
            resolved_backend = backend_for_tool(resolved_tool)
            if resolved_backend not in {"claude_headless", "codex_headless", "gemini_headless"}:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Native headless launch for tool `{resolved_tool}` did not resolve to "
                        "a supported headless backend."
                    ),
                )
            resolved_headless_backend = cast(
                Literal["claude_headless", "codex_headless", "gemini_headless"],
                resolved_backend,
            )
            controller = start_runtime_session(
                agent_def_dir=agent_def_dir,
                brain_manifest_path=brain_manifest_path,
                role_name=resolved_role_name,
                backend=resolved_headless_backend,
                working_directory=resolved_workdir,
                api_base_url=self.m_config.api_base_url,
                agent_identity=request_model.agent_name,
                agent_id=request_model.agent_id,
                mailbox_transport=(
                    request_model.mailbox.transport if request_model.mailbox is not None else None
                ),
                mailbox_root=(
                    Path(request_model.mailbox.filesystem_root).expanduser().resolve()
                    if request_model.mailbox is not None
                    and request_model.mailbox.filesystem_root is not None
                    else None
                ),
                mailbox_principal_id=(
                    request_model.mailbox.principal_id
                    if request_model.mailbox is not None
                    else None
                ),
                mailbox_address=(
                    request_model.mailbox.address if request_model.mailbox is not None else None
                ),
                mailbox_stalwart_base_url=(
                    request_model.mailbox.stalwart_base_url
                    if request_model.mailbox is not None
                    else None
                ),
                mailbox_stalwart_jmap_url=(
                    request_model.mailbox.stalwart_jmap_url
                    if request_model.mailbox is not None
                    else None
                ),
                mailbox_stalwart_management_url=(
                    request_model.mailbox.stalwart_management_url
                    if request_model.mailbox is not None
                    else None
                ),
                mailbox_stalwart_login_identity=(
                    request_model.mailbox.stalwart_login_identity
                    if request_model.mailbox is not None
                    else None
                ),
                registry_launch_authority="external",
            )
        except (LaunchPlanError, SessionManifestError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        try:
            self._publish_server_launched_registry_record(controller)
        except (OSError, SessionManifestError) as exc:
            try:
                controller.stop(force_cleanup=True)
            except Exception:
                LOGGER.warning(
                    "Failed to rollback managed headless launch after shared-registry publish failure",
                    exc_info=True,
                )
            raise HTTPException(
                status_code=503,
                detail=f"Managed headless launch could not publish shared-registry state: {exc}",
            ) from exc

        tracked_agent_id = controller.manifest_path.parent.name
        authority = ManagedHeadlessAuthorityRecord(
            tracked_agent_id=tracked_agent_id,
            backend=resolved_headless_backend,
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
        self._publish_server_managed_headless_gateway_metadata(authority)
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
                f"Native headless agent `{tracked_agent_id}` launched for tool `{resolved_tool}`."
            ),
        )

    def stop_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Stop one managed agent through the pair-owned transport lifecycle."""

        resolved = self._resolve_managed_agent_ref(agent_ref)
        if resolved["transport"] == "tui":
            tracker = self._tracker_for_session_id(resolved["tracked_agent_id"])
            identity = tracker.current_state().tracked_session
            session_name = identity.session_name.strip()
            proxy_response = self.proxy(
                method="DELETE",
                path=f"/sessions/{parse.quote(session_name, safe='')}",
            )
            self._require_successful_proxy_action(
                proxy_response,
                failure_status_code=503,
                failure_detail=(
                    "Managed-agent stop failed through the pair-managed session-delete lifecycle."
                ),
            )
            try:
                self._clear_shared_registry_record_for_terminated_agent(
                    agent_name=identity.agent_name,
                    agent_id=identity.agent_id,
                    manifest_path=(
                        Path(identity.manifest_path).expanduser().resolve()
                        if identity.manifest_path is not None
                        else None
                    ),
                    session_name=session_name,
                )
            except OSError as exc:
                LOGGER.warning(
                    "Shared-registry cleanup failed after managed TUI stop for session `%s`: %s",
                    session_name,
                    exc,
                )
            self.handle_deleted_session(session_name)
            return HoumaoManagedAgentActionResponse(
                success=True,
                tracked_agent_id=resolved["tracked_agent_id"],
                detail=self._proxy_action_detail(
                    proxy_response,
                    fallback=f"Managed TUI agent `{session_name}` stopped.",
                ),
                turn_id=None,
            )

        tracked_agent_id = resolved["tracked_agent_id"]
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        handle = self._require_headless_handle(tracked_agent_id)
        active_turn = self.m_managed_headless_store.read_active_turn(
            tracked_agent_id=tracked_agent_id
        )
        if active_turn is not None:
            self._interrupt_active_turn_record(active_turn)
            active_thread = handle.active_thread
            if active_thread is not None:
                active_thread.join(timeout=5.0)

        if handle.controller is not None:
            result = handle.controller.stop(force_cleanup=True)
            if result.status != "ok":
                raise HTTPException(status_code=502, detail=result.detail)
            detail = result.detail
        else:
            detail = (
                f"Deleted managed headless authority for `{tracked_agent_id}` without an "
                "active resumable controller."
            )
        try:
            self._clear_shared_registry_record_for_terminated_agent(
                agent_name=handle.authority.agent_name,
                agent_id=handle.authority.agent_id,
                manifest_path=Path(handle.authority.manifest_path).expanduser().resolve(),
                session_name=handle.authority.tmux_session_name,
            )
        except OSError as exc:
            LOGGER.warning(
                "Shared-registry cleanup failed after managed headless stop for `%s`: %s",
                tracked_agent_id,
                exc,
            )

        self.m_managed_headless_store.delete_agent(tracked_agent_id=tracked_agent_id)
        with self.m_lock:
            self.m_headless_agents.pop(tracked_agent_id, None)
        return HoumaoManagedAgentActionResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            detail=detail,
            turn_id=active_turn.turn_id if active_turn is not None else None,
        )

    def submit_headless_turn(
        self,
        agent_ref: str,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        """Accept one prompt for a managed native headless agent."""

        control_plane = self._control_plane_for_managed_agent(agent_ref, operation="headless_turn")
        if control_plane.transport != "headless" or control_plane.submit_headless_turn is None:
            raise HTTPException(
                status_code=400,
                detail="Headless turn submission is only supported for native headless agents.",
            )
        return control_plane.submit_headless_turn(request_model)

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
            artifact_path = (
                Path(turn_record.stdout_path) if turn_record.stdout_path is not None else None
            )
        elif artifact_name == "stderr":
            artifact_path = (
                Path(turn_record.stderr_path) if turn_record.stderr_path is not None else None
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown headless artifact `{artifact_name}`."
            )

        if artifact_path is None or not artifact_path.exists():
            return ""
        return artifact_path.read_text(encoding="utf-8")

    def interrupt_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentActionResponse:
        """Interrupt the active turn for one managed headless agent."""

        control_plane = self._control_plane_for_managed_agent(agent_ref, operation="interrupt")
        if control_plane.transport != "headless":
            raise HTTPException(
                status_code=400,
                detail="This route only supports native headless managed agents.",
            )
        accepted = control_plane.submit_request(
            HoumaoManagedAgentInterruptRequest(),
            self._managed_request_id(agent_ref=agent_ref, request_kind="interrupt"),
        )
        return HoumaoManagedAgentActionResponse(
            success=True,
            tracked_agent_id=accepted.tracked_agent_id,
            detail=accepted.detail,
            turn_id=accepted.headless_turn_id,
        )

    def managed_agent_gateway_status(self, agent_ref: str) -> GatewayStatusV1:
        """Return gateway status for one managed agent."""

        gateway_context = self._managed_gateway_context(agent_ref)
        session_root = gateway_context.get("session_root")
        if isinstance(session_root, str):
            client = self._live_gateway_client_for_session_root(session_root)
            if client is not None:
                return self._invoke_live_gateway(client.status)
        return cast(GatewayStatusV1, gateway_context["status"])

    def attach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        """Attach or reuse a live gateway for one managed agent."""

        gateway_context = self._managed_gateway_context(agent_ref)
        status = cast(GatewayStatusV1, gateway_context["status"])
        controller = cast(RuntimeSessionController | None, gateway_context["controller"])
        if (
            status.gateway_health == "healthy"
            and status.request_admission != "blocked_reconciliation"
        ):
            return status
        if status.request_admission == "blocked_reconciliation":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Gateway attach is blocked because the existing live gateway requires "
                    "managed-agent reconciliation."
                ),
            )
        if controller is None:
            raise HTTPException(
                status_code=503,
                detail="Managed-agent gateway attach is unavailable because runtime control is not resumable.",
            )
        attach_result = controller.attach_gateway()
        if attach_result.status != "ok":
            detail = attach_result.detail.lower()
            if "already in use" in detail or "reconciliation" in detail:
                raise HTTPException(status_code=409, detail=attach_result.detail)
            raise HTTPException(status_code=503, detail=attach_result.detail)
        if gateway_context.get("transport") == "headless":
            try:
                self._publish_server_launched_registry_record(controller)
            except (OSError, SessionManifestError) as exc:
                LOGGER.warning(
                    "Shared-registry refresh failed after managed headless gateway attach for `%s`: %s",
                    gateway_context["tracked_agent_id"],
                    exc,
                )
        return self._gateway_status_for_session_root(
            Path(cast(str, gateway_context["session_root"]))
        )

    def detach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        """Detach any live gateway for one managed agent."""

        gateway_context = self._managed_gateway_context(agent_ref)
        controller = cast(RuntimeSessionController | None, gateway_context["controller"])
        if controller is None:
            return cast(GatewayStatusV1, gateway_context["status"])
        detach_result = controller.detach_gateway()
        if detach_result.status != "ok":
            raise HTTPException(status_code=503, detail=detach_result.detail)
        if gateway_context.get("transport") == "headless":
            try:
                self._publish_server_launched_registry_record(controller)
            except (OSError, SessionManifestError) as exc:
                LOGGER.warning(
                    "Shared-registry refresh failed after managed headless gateway detach for `%s`: %s",
                    gateway_context["tracked_agent_id"],
                    exc,
                )
        return self._gateway_status_for_session_root(
            Path(cast(str, gateway_context["session_root"]))
        )

    def get_managed_agent_gateway_tui_state(self, agent_ref: str) -> HoumaoTerminalStateResponse:
        """Return raw gateway-owned TUI state for one managed agent."""

        client = self._require_live_managed_gateway_client(agent_ref)
        return self._invoke_live_gateway(client.get_tui_state)

    def get_managed_agent_gateway_tui_history(
        self,
        agent_ref: str,
        *,
        limit: int = 100,
    ) -> HoumaoTerminalSnapshotHistoryResponse:
        """Return raw gateway-owned TUI snapshot history for one managed agent."""

        client = self._require_live_managed_gateway_client(agent_ref)
        return self._invoke_live_gateway(lambda: client.get_tui_history(limit=limit))

    def note_managed_agent_gateway_tui_prompt(
        self,
        agent_ref: str,
        *,
        prompt: str,
    ) -> HoumaoTerminalStateResponse:
        """Record prompt-note provenance through one managed agent's live gateway."""

        client = self._require_live_managed_gateway_client(agent_ref)
        return self._invoke_live_gateway(lambda: client.note_tui_prompt_submission(prompt=prompt))

    def submit_managed_agent_gateway_request(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayRequestCreate,
    ) -> HoumaoManagedAgentGatewayRequestAcceptedResponse:
        """Proxy one gateway-mediated managed-agent request through a live gateway."""

        client = self._require_live_managed_gateway_client(agent_ref)
        response = self._invoke_live_gateway(
            lambda: client.create_request(
                GatewayRequestCreateV1.model_validate(request_model.model_dump(mode="json"))
            )
        )
        return HoumaoManagedAgentGatewayRequestAcceptedResponse.model_validate(
            response.model_dump(mode="json")
        )

    def send_managed_agent_gateway_control_input(
        self,
        agent_ref: str,
        request_model: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1:
        """Proxy one managed-agent raw control-input request through a live gateway."""

        client = self._require_live_managed_gateway_client(agent_ref)
        return self._invoke_live_gateway(lambda: client.send_control_input(request_model))

    def get_managed_agent_gateway_mail_notifier(
        self, agent_ref: str
    ) -> GatewayMailNotifierStatusV1:
        """Return live gateway mail-notifier status for one managed agent."""

        client = self._require_live_managed_gateway_client(agent_ref)
        return self._invoke_live_gateway(client.get_mail_notifier)

    def put_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
        request_model: GatewayMailNotifierPutV1,
    ) -> GatewayMailNotifierStatusV1:
        """Enable or update live gateway notifier state for one managed agent."""

        client = self._require_live_managed_gateway_client(agent_ref)
        return self._invoke_live_gateway(lambda: client.put_mail_notifier(request_model))

    def delete_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
    ) -> GatewayMailNotifierStatusV1:
        """Disable live gateway notifier state for one managed agent."""

        client = self._require_live_managed_gateway_client(agent_ref)
        return self._invoke_live_gateway(client.delete_mail_notifier)

    def managed_agent_mail_status(self, agent_ref: str) -> HoumaoManagedAgentMailStatusResponse:
        """Return pair-owned mailbox status for one managed agent."""

        client = self._require_live_managed_mail_gateway_client(agent_ref)
        response = self._invoke_live_gateway(client.mail_status)
        return HoumaoManagedAgentMailStatusResponse.model_validate(response.model_dump(mode="json"))

    def check_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailCheckRequest,
    ) -> HoumaoManagedAgentMailCheckResponse:
        """Check pair-owned mailbox contents for one managed agent."""

        client = self._require_live_managed_mail_gateway_client(agent_ref)
        response = self._invoke_live_gateway(lambda: client.check_mail(request_model))
        return HoumaoManagedAgentMailCheckResponse.model_validate(response.model_dump(mode="json"))

    def send_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailSendRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Send one pair-owned mailbox message for a managed agent."""

        client = self._require_live_managed_mail_gateway_client(agent_ref)
        response = self._invoke_live_gateway(lambda: client.send_mail(request_model))
        return HoumaoManagedAgentMailActionResponse.model_validate(response.model_dump(mode="json"))

    def reply_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailReplyRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        """Reply through the pair-owned mailbox facade for one managed agent."""

        client = self._require_live_managed_mail_gateway_client(agent_ref)
        response = self._invoke_live_gateway(lambda: client.reply_mail(request_model))
        return HoumaoManagedAgentMailActionResponse.model_validate(response.model_dump(mode="json"))

    def refresh_terminal_state(self, terminal_id: str) -> HoumaoTerminalStateResponse:
        """Poll one known tracked terminal immediately and return the updated state."""

        control_plane = self._control_plane_for_terminal(terminal_id, operation="refresh")
        assert control_plane.terminal_state is not None
        if control_plane.owner == "gateway":
            return control_plane.terminal_state()
        tracked_session_id = self._tracked_session_id_for_terminal_alias(terminal_id)
        self.poll_known_session(tracked_session_id)
        return control_plane.terminal_state()

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
        if self._live_gateway_client_for_session_root(identity.session_root) is not None:
            return True
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
                output_text=None,
            )
            return False

        try:
            target = self.m_transport_resolver.resolve_target(
                session_name=identity.tmux_session_name,
                window_name=identity.tmux_window_name,
                window_index=self._tracked_tui_target_window_index(identity),
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
                output_text=None,
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
                output_text=None,
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
                output_text=None,
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
                output_text=None,
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
                output_text=None,
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
                output_text=output_text,
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
                    output_text=output_text,
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
            output_text=output_text,
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
            self.m_config.state_dir,
            self.m_config.history_dir,
            self.m_config.sessions_dir,
            self.m_config.managed_agents_root,
            self.m_config.compatibility_state_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _ensure_tui_trackers_seeded(self) -> None:
        """Refresh in-memory TUI tracker seeds from the authoritative registry."""

        for record in self.load_live_known_sessions().values():
            self.ensure_known_session(record)

    def _rebuild_headless_agents(self) -> None:
        """Rebuild native headless managed agents from server-owned authority."""

        rebuilt: dict[str, _ManagedHeadlessAgentHandle] = {}
        for authority in self.m_managed_headless_store.list_authority_records():
            controller = self._resume_headless_controller(authority)
            rebuilt[authority.tracked_agent_id] = _ManagedHeadlessAgentHandle(
                authority=authority,
                controller=controller,
            )

        with self.m_lock:
            self.m_headless_agents = rebuilt

        for tracked_agent_id in list(rebuilt):
            self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)

    def _resume_headless_controller(
        self,
        authority: ManagedHeadlessAuthorityRecord,
    ) -> RuntimeSessionController | None:
        """Resume one headless runtime controller from server-owned authority."""

        manifest_path = Path(authority.manifest_path).expanduser().resolve()
        agent_def_dir = Path(authority.agent_def_dir).expanduser().resolve()
        if not manifest_path.is_file() or not agent_def_dir.is_dir():
            return None
        try:
            controller = resume_runtime_session(
                agent_def_dir=agent_def_dir,
                session_manifest_path=manifest_path,
            )
            self._publish_server_managed_headless_gateway_metadata(authority)
            if controller.registry_launch_authority != "runtime":
                try:
                    self._publish_server_launched_registry_record(controller)
                except (OSError, SessionManifestError) as exc:
                    LOGGER.warning(
                        "Shared-registry refresh failed while rebuilding managed headless `%s`: %s",
                        authority.tracked_agent_id,
                        exc,
                    )
            return controller
        except (LaunchPlanError, SessionManifestError, RuntimeError):
            return None

    def _resolve_managed_agent_ref(self, agent_ref: str) -> dict[str, str]:
        """Resolve one shared managed-agent reference through explicit aliases."""

        candidate = agent_ref.strip()
        if not candidate:
            raise HTTPException(
                status_code=404, detail="Managed agent reference must not be empty."
            )

        self._ensure_tui_trackers_seeded()
        matches: list[dict[str, str]] = []

        with self.m_lock:
            trackers = list(self.m_trackers.values())
            headless_handles = list(self.m_headless_agents.values())

        for tracker in trackers:
            state = tracker.current_state()
            identity = state.tracked_session
            aliases = {
                identity.tracked_session_id,
                identity.session_name,
                *identity.terminal_aliases,
            }
            if identity.agent_name is not None:
                aliases.add(identity.agent_name)
            if identity.agent_id is not None:
                aliases.add(identity.agent_id)
            if candidate in aliases:
                matches.append(
                    {
                        "transport": "tui",
                        "tracked_agent_id": identity.tracked_session_id,
                    }
                )

        for handle in headless_handles:
            authority = handle.authority
            aliases = {
                authority.tracked_agent_id,
            }
            if authority.agent_name is not None:
                aliases.add(authority.agent_name)
            if authority.agent_id is not None:
                aliases.add(authority.agent_id)
            if candidate in aliases:
                matches.append(
                    {
                        "transport": "headless",
                        "tracked_agent_id": authority.tracked_agent_id,
                    }
                )

        deduped = {(match["transport"], match["tracked_agent_id"]): match for match in matches}
        if not deduped:
            raise HTTPException(status_code=404, detail=f"Unknown managed agent `{candidate}`.")
        if len(deduped) > 1:
            raise HTTPException(
                status_code=409,
                detail=f"Managed agent reference `{candidate}` is ambiguous.",
            )
        return next(iter(deduped.values()))

    def _require_headless_handle(self, tracked_agent_id: str) -> _ManagedHeadlessAgentHandle:
        """Return one required native headless managed-agent handle."""

        with self.m_lock:
            handle = self.m_headless_agents.get(tracked_agent_id)
        if handle is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown native headless managed agent `{tracked_agent_id}`.",
            )
        return handle

    def _require_headless_agent_ref(self, agent_ref: str) -> str:
        """Resolve one agent reference and require native headless transport."""

        resolved = self._resolve_managed_agent_ref(agent_ref)
        if resolved["transport"] != "headless":
            raise HTTPException(
                status_code=400,
                detail="This route only supports native headless managed agents.",
            )
        return resolved["tracked_agent_id"]

    def _control_plane_for_managed_agent(
        self,
        agent_ref: str,
        *,
        operation: str,
    ) -> ManagedAgentControlPlane:
        """Resolve one managed-agent interaction onto its current control plane."""

        resolved = self._resolve_managed_agent_ref(agent_ref)
        if resolved["transport"] == "tui":
            tracker = self._tracker_for_session_id(resolved["tracked_agent_id"])
            return self._resolve_tui_control_plane(tracker=tracker, operation=operation)

        tracked_agent_id = resolved["tracked_agent_id"]
        self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
        handle = self._require_headless_handle(tracked_agent_id)
        return self._resolve_headless_control_plane(handle=handle, operation=operation)

    def _control_plane_for_terminal(
        self,
        terminal_id: str,
        *,
        operation: str,
    ) -> ManagedAgentControlPlane:
        """Resolve one terminal-keyed TUI interaction onto its current control plane."""

        tracker = self._tracker_for_terminal_alias(terminal_id)
        return self._resolve_tui_control_plane(tracker=tracker, operation=operation)

    def _resolve_tui_control_plane(
        self,
        *,
        tracker: LiveSessionTracker,
        operation: str,
    ) -> ManagedAgentControlPlane:
        """Choose gateway-backed or direct TUI control for one tracker."""

        session_root = tracker.current_state().tracked_session.session_root
        client = self._live_gateway_client_for_session_root(session_root)
        if client is not None:
            return self._gateway_tui_control_plane(tracker=tracker, client=client)

        gateway_status = self._optional_gateway_status_for_session_root(session_root)
        if operation == "request" and gateway_status is not None:
            if gateway_status.request_admission == "blocked_reconciliation":
                raise HTTPException(
                    status_code=409,
                    detail="Gateway admission is blocked pending managed-agent reconciliation.",
                )
        return self._direct_tui_control_plane(tracker=tracker, gateway_status=gateway_status)

    def _resolve_headless_control_plane(
        self,
        *,
        handle: _ManagedHeadlessAgentHandle,
        operation: str,
    ) -> ManagedAgentControlPlane:
        """Choose gateway-backed or direct headless control for one managed agent."""

        client = self._live_gateway_client_for_session_root(handle.authority.session_root)
        if client is not None:
            return self._gateway_headless_control_plane(handle=handle, client=client)

        gateway_status = self._optional_gateway_status_for_session_root(
            handle.authority.session_root
        )
        if operation in {"request", "headless_turn", "interrupt"} and gateway_status is not None:
            if gateway_status.request_admission == "blocked_reconciliation":
                raise HTTPException(
                    status_code=409,
                    detail="Gateway admission is blocked pending managed-agent reconciliation.",
                )
            if gateway_status.gateway_health == "healthy":
                raise HTTPException(
                    status_code=503,
                    detail="Managed headless control is unavailable because the attached gateway is unreachable.",
                )
        return self._direct_headless_control_plane(
            handle=handle,
            gateway_status=gateway_status,
        )

    def _direct_tui_control_plane(
        self,
        *,
        tracker: LiveSessionTracker,
        gateway_status: GatewayStatusV1 | None,
    ) -> ManagedAgentControlPlane:
        """Build the direct fallback control plane for one tracked TUI agent."""

        tracked_agent_id = tracker.current_state().tracked_session.tracked_session_id
        direct_gateway_summary = self._fallback_gateway_summary(gateway_status)

        def _summary_state() -> HoumaoManagedAgentStateResponse:
            return self._managed_state_from_tui_state(
                tracker.current_state(),
                gateway_summary=direct_gateway_summary,
            )

        def _detail_response() -> HoumaoManagedAgentDetailResponse:
            state = tracker.current_state()
            summary_state = self._managed_state_from_tui_state(
                state,
                gateway_summary=direct_gateway_summary,
            )
            return HoumaoManagedAgentDetailResponse(
                tracked_agent_id=summary_state.tracked_agent_id,
                identity=summary_state.identity,
                summary_state=summary_state,
                detail=self._managed_tui_detail_from_state(state),
            )

        return ManagedAgentControlPlane(
            tracked_agent_id=tracked_agent_id,
            transport="tui",
            owner="direct",
            summary_state=_summary_state,
            detail_response=_detail_response,
            history_response=lambda limit: self._managed_tui_history_response(
                tracker.history(limit=limit)
            ),
            submit_request=lambda request_model, request_id: self._submit_tui_managed_request(
                tracker=tracker,
                request_model=request_model,
                request_id=request_id,
            ),
            gateway_summary=lambda: direct_gateway_summary,
            terminal_state=tracker.current_state,
            terminal_history=lambda limit: tracker.history(limit=limit),
        )

    def _gateway_tui_control_plane(
        self,
        *,
        tracker: LiveSessionTracker,
        client: GatewayClient,
    ) -> ManagedAgentControlPlane:
        """Build the gateway-backed control plane for one TUI managed agent."""

        tracked_agent_id = tracker.current_state().tracked_session.tracked_session_id

        def _gateway_summary() -> HoumaoManagedAgentGatewaySummaryView | None:
            status = self._invoke_live_gateway(client.status)
            return self._gateway_summary_from_status(status)

        def _summary_state() -> HoumaoManagedAgentStateResponse:
            state = self._invoke_live_gateway(client.get_tui_state)
            return self._managed_state_from_tui_state(
                state,
                gateway_summary=_gateway_summary(),
            )

        def _detail_response() -> HoumaoManagedAgentDetailResponse:
            state = self._invoke_live_gateway(client.get_tui_state)
            summary_state = self._managed_state_from_tui_state(
                state,
                gateway_summary=_gateway_summary(),
            )
            return HoumaoManagedAgentDetailResponse(
                tracked_agent_id=summary_state.tracked_agent_id,
                identity=summary_state.identity,
                summary_state=summary_state,
                detail=self._managed_tui_detail_from_state(state),
            )

        def _submit_request(
            request_model: HoumaoManagedAgentRequestEnvelope,
            request_id: str,
        ) -> HoumaoManagedAgentRequestAcceptedResponse:
            if isinstance(request_model, HoumaoManagedAgentSubmitPromptRequest):
                self._invoke_live_gateway(
                    lambda: client.create_request(
                        GatewayRequestCreateV1(
                            kind="submit_prompt",
                            payload=GatewayRequestPayloadSubmitPromptV1(
                                prompt=request_model.prompt
                            ),
                        )
                    )
                )
                return HoumaoManagedAgentRequestAcceptedResponse(
                    success=True,
                    tracked_agent_id=tracked_agent_id,
                    request_id=request_id,
                    request_kind=request_model.request_kind,
                    disposition="accepted",
                    detail="Managed-agent prompt request accepted for gateway delivery.",
                )

            self._invoke_live_gateway(
                lambda: client.create_request(
                    GatewayRequestCreateV1(
                        kind="interrupt",
                        payload=GatewayRequestPayloadInterruptV1(),
                    )
                )
            )
            return HoumaoManagedAgentRequestAcceptedResponse(
                success=True,
                tracked_agent_id=tracked_agent_id,
                request_id=request_id,
                request_kind=request_model.request_kind,
                disposition="accepted",
                detail="Managed-agent interrupt request accepted for gateway delivery.",
            )

        return ManagedAgentControlPlane(
            tracked_agent_id=tracked_agent_id,
            transport="tui",
            owner="gateway",
            summary_state=_summary_state,
            detail_response=_detail_response,
            history_response=lambda limit: self._managed_tui_history_response(
                self._recent_transition_history_from_state(
                    self._invoke_live_gateway(client.get_tui_state),
                    limit=limit,
                )
            ),
            submit_request=_submit_request,
            gateway_summary=_gateway_summary,
            terminal_state=lambda: self._invoke_live_gateway(client.get_tui_state),
            terminal_history=lambda limit: self._recent_transition_history_from_state(
                self._invoke_live_gateway(client.get_tui_state),
                limit=limit,
            ),
        )

    def _direct_headless_control_plane(
        self,
        *,
        handle: _ManagedHeadlessAgentHandle,
        gateway_status: GatewayStatusV1 | None,
    ) -> ManagedAgentControlPlane:
        """Build the direct fallback control plane for one managed headless agent."""

        tracked_agent_id = handle.authority.tracked_agent_id
        direct_gateway_summary = self._fallback_gateway_summary(gateway_status)

        def _summary_state() -> HoumaoManagedAgentStateResponse:
            return self._managed_state_from_headless_handle(
                handle,
                gateway_summary=direct_gateway_summary,
            )

        def _detail_response() -> HoumaoManagedAgentDetailResponse:
            summary_state = self._managed_state_from_headless_handle(
                handle,
                gateway_summary=direct_gateway_summary,
            )
            detail = self._managed_headless_detail_from_handle(
                handle,
                summary_state=summary_state,
            )
            return HoumaoManagedAgentDetailResponse(
                tracked_agent_id=summary_state.tracked_agent_id,
                identity=summary_state.identity,
                summary_state=summary_state,
                detail=detail,
            )

        return ManagedAgentControlPlane(
            tracked_agent_id=tracked_agent_id,
            transport="headless",
            owner="direct",
            summary_state=_summary_state,
            detail_response=_detail_response,
            history_response=lambda limit: HoumaoManagedAgentHistoryResponse(
                tracked_agent_id=tracked_agent_id,
                entries=self._headless_history_entries(
                    tracked_agent_id=tracked_agent_id,
                    limit=limit,
                ),
            ),
            submit_request=lambda request_model, request_id: self._submit_headless_managed_request(
                handle=handle,
                request_model=request_model,
                request_id=request_id,
            ),
            gateway_summary=lambda: direct_gateway_summary,
            submit_headless_turn=lambda request_model: self._submit_headless_turn_direct(
                handle=handle,
                request_model=request_model,
            ),
        )

    def _gateway_headless_control_plane(
        self,
        *,
        handle: _ManagedHeadlessAgentHandle,
        client: GatewayClient,
    ) -> ManagedAgentControlPlane:
        """Build the gateway-backed control plane for one managed headless agent."""

        tracked_agent_id = handle.authority.tracked_agent_id

        def _gateway_summary() -> HoumaoManagedAgentGatewaySummaryView | None:
            status = self._invoke_live_gateway(client.status)
            return self._gateway_summary_from_status(status)

        def _summary_state() -> HoumaoManagedAgentStateResponse:
            self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
            control_state = self._invoke_live_gateway(client.get_headless_control_state)
            return self._managed_state_from_gateway_headless_handle(
                handle,
                control_state=control_state,
                gateway_summary=_gateway_summary(),
            )

        def _detail_response() -> HoumaoManagedAgentDetailResponse:
            self._reconcile_headless_active_turn(tracked_agent_id=tracked_agent_id)
            control_state = self._invoke_live_gateway(client.get_headless_control_state)
            summary_state = self._managed_state_from_gateway_headless_handle(
                handle,
                control_state=control_state,
                gateway_summary=_gateway_summary(),
            )
            detail = self._managed_headless_detail_from_gateway_handle(
                handle,
                control_state=control_state,
                summary_state=summary_state,
            )
            return HoumaoManagedAgentDetailResponse(
                tracked_agent_id=summary_state.tracked_agent_id,
                identity=summary_state.identity,
                summary_state=summary_state,
                detail=detail,
            )

        def _submit_request(
            request_model: HoumaoManagedAgentRequestEnvelope,
            request_id: str,
        ) -> HoumaoManagedAgentRequestAcceptedResponse:
            if isinstance(request_model, HoumaoManagedAgentSubmitPromptRequest):
                accepted = self._submit_headless_turn_via_gateway(
                    handle=handle,
                    client=client,
                    request_model=HoumaoHeadlessTurnRequest(prompt=request_model.prompt),
                )
                return self._headless_request_accepted_response(
                    tracked_agent_id=tracked_agent_id,
                    request_id=request_id,
                    request_kind=request_model.request_kind,
                    accepted=accepted,
                )
            return self._submit_headless_interrupt_via_gateway(
                handle=handle,
                client=client,
                request_id=request_id,
            )

        return ManagedAgentControlPlane(
            tracked_agent_id=tracked_agent_id,
            transport="headless",
            owner="gateway",
            summary_state=_summary_state,
            detail_response=_detail_response,
            history_response=lambda limit: HoumaoManagedAgentHistoryResponse(
                tracked_agent_id=tracked_agent_id,
                entries=self._headless_history_entries(
                    tracked_agent_id=tracked_agent_id,
                    limit=limit,
                ),
            ),
            submit_request=_submit_request,
            gateway_summary=_gateway_summary,
            submit_headless_turn=lambda request_model: self._submit_headless_turn_via_gateway(
                handle=handle,
                client=client,
                request_model=request_model,
            ),
        )

    def _managed_identity_from_tui_state(
        self,
        state: HoumaoTerminalStateResponse,
    ) -> HoumaoManagedAgentIdentity:
        """Project one TUI tracked-state sample into the shared identity model."""

        identity = state.tracked_session
        return HoumaoManagedAgentIdentity(
            tracked_agent_id=identity.tracked_session_id,
            transport="tui",
            tool=identity.tool,
            session_name=identity.session_name,
            terminal_id=state.terminal_id,
            runtime_session_id=None,
            tmux_session_name=identity.tmux_session_name,
            tmux_window_name=identity.tmux_window_name,
            manifest_path=identity.manifest_path,
            session_root=identity.session_root,
            agent_name=identity.agent_name,
            agent_id=identity.agent_id,
        )

    def _managed_identity_from_tui_tracker(
        self,
        tracker: LiveSessionTracker,
    ) -> HoumaoManagedAgentIdentity:
        """Project one TUI tracker into the shared managed-agent identity model."""

        return self._managed_identity_from_tui_state(tracker.current_state())

    def _tracked_tui_target_window_index(
        self, identity: HoumaoTrackedSessionIdentity
    ) -> str | None:
        """Return the contractual tmux window index for one tracked TUI session."""

        manifest_path_value = identity.manifest_path
        if manifest_path_value is None:
            return None
        try:
            handle = load_session_manifest(Path(manifest_path_value).expanduser().resolve())
            payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        except (LaunchPlanError, SessionManifestError, OSError):
            return None
        if payload.backend in {"houmao_server_rest", "local_interactive"}:
            return "0"
        return None

    def _managed_identity_from_headless_handle(
        self,
        handle: _ManagedHeadlessAgentHandle,
    ) -> HoumaoManagedAgentIdentity:
        """Project one headless handle into the shared managed-agent identity model."""

        authority = handle.authority
        return HoumaoManagedAgentIdentity(
            tracked_agent_id=authority.tracked_agent_id,
            transport="headless",
            tool=authority.tool,
            session_name=None,
            terminal_id=None,
            runtime_session_id=authority.tracked_agent_id,
            tmux_session_name=authority.tmux_session_name,
            tmux_window_name=HEADLESS_AGENT_WINDOW_NAME,
            manifest_path=authority.manifest_path,
            session_root=authority.session_root,
            agent_name=authority.agent_name,
            agent_id=authority.agent_id,
        )

    def _managed_state_from_tui_state(
        self,
        state: HoumaoTerminalStateResponse,
        *,
        gateway_summary: HoumaoManagedAgentGatewaySummaryView | None,
    ) -> HoumaoManagedAgentStateResponse:
        """Project one TUI tracked-state sample into the shared coarse state model."""

        availability = _availability_from_tui_state(state)
        turn_phase = state.turn.phase
        last_result = state.last_turn.result
        diagnostics: list[HoumaoErrorDetail] = []
        if state.diagnostics.probe_error is not None:
            diagnostics.append(state.diagnostics.probe_error)
        if state.diagnostics.parse_error is not None:
            diagnostics.append(state.diagnostics.parse_error)

        return HoumaoManagedAgentStateResponse(
            tracked_agent_id=state.tracked_session.tracked_session_id,
            identity=self._managed_identity_from_tui_state(state),
            availability=availability,
            turn=HoumaoManagedAgentTurnView(
                phase=turn_phase,
                active_turn_id=(
                    f"tui-anchor:{state.tracked_session.tracked_session_id}"
                    if turn_phase == "active"
                    else None
                ),
            ),
            last_turn=HoumaoManagedAgentLastTurnView(
                result=last_result,
                turn_id=None,
                turn_index=None,
                updated_at_utc=state.last_turn.updated_at_utc,
            ),
            diagnostics=diagnostics,
            mailbox=self._mailbox_summary_for_tui_identity(state.tracked_session),
            gateway=gateway_summary,
        )

    def _managed_state_from_tui_tracker(
        self,
        tracker: LiveSessionTracker,
    ) -> HoumaoManagedAgentStateResponse:
        """Project one TUI tracker into the shared coarse state model."""

        current = tracker.current_state()
        return self._managed_state_from_tui_state(
            current,
            gateway_summary=self._gateway_summary_for_session_root(
                current.tracked_session.session_root
            ),
        )

    def _managed_state_from_headless_handle(
        self,
        handle: _ManagedHeadlessAgentHandle,
        *,
        gateway_summary: HoumaoManagedAgentGatewaySummaryView | None = None,
    ) -> HoumaoManagedAgentStateResponse:
        """Project one headless handle into the shared coarse state model."""

        authority = handle.authority
        active_turn = self.m_managed_headless_store.read_active_turn(
            tracked_agent_id=authority.tracked_agent_id
        )
        latest_turn = self._latest_headless_turn_record(tracked_agent_id=authority.tracked_agent_id)
        diagnostics: list[HoumaoErrorDetail] = []
        if handle.controller is None:
            availability: ManagedAgentAvailability = "unavailable"
            diagnostics.append(
                HoumaoErrorDetail(
                    kind="runtime_resume_unavailable",
                    message=(
                        "Managed headless authority exists, but the runtime controller could "
                        "not be resumed from persisted state."
                    ),
                )
            )
        elif tmux_session_exists(session_name=authority.tmux_session_name):
            availability = "available"
        else:
            availability = "unavailable"
            diagnostics.append(
                HoumaoErrorDetail(
                    kind="tmux_session_missing",
                    message=(
                        f"Native headless tmux session `{authority.tmux_session_name}` is not live."
                    ),
                )
            )

        if active_turn is not None:
            turn_view = HoumaoManagedAgentTurnView(
                phase="active",
                active_turn_id=active_turn.turn_id,
            )
        else:
            turn_view = HoumaoManagedAgentTurnView(
                phase="ready" if availability == "available" else "unknown",
                active_turn_id=None,
            )

        last_result: ManagedAgentLastTurnResult = "none"
        last_turn_id: str | None = None
        last_turn_index: int | None = None
        updated_at_utc: str | None = None
        if latest_turn is not None:
            last_result = _last_turn_result_from_headless_status(latest_turn.status)
            last_turn_id = latest_turn.turn_id
            last_turn_index = latest_turn.turn_index
            updated_at_utc = latest_turn.completed_at_utc or latest_turn.started_at_utc

        return HoumaoManagedAgentStateResponse(
            tracked_agent_id=authority.tracked_agent_id,
            identity=self._managed_identity_from_headless_handle(handle),
            availability=availability,
            turn=turn_view,
            last_turn=HoumaoManagedAgentLastTurnView(
                result=last_result,
                turn_id=last_turn_id,
                turn_index=last_turn_index,
                updated_at_utc=updated_at_utc,
            ),
            diagnostics=diagnostics,
            mailbox=self._mailbox_summary_for_headless_handle(handle),
            gateway=(
                gateway_summary
                if gateway_summary is not None
                else self._gateway_summary_for_session_root(authority.session_root)
            ),
        )

    def _managed_state_from_gateway_headless_handle(
        self,
        handle: _ManagedHeadlessAgentHandle,
        *,
        control_state: GatewayHeadlessControlStateV1,
        gateway_summary: HoumaoManagedAgentGatewaySummaryView | None,
    ) -> HoumaoManagedAgentStateResponse:
        """Project live gateway-backed headless control posture into shared state."""

        authority = handle.authority
        active_turn = self.m_managed_headless_store.read_active_turn(
            tracked_agent_id=authority.tracked_agent_id
        )
        latest_turn = self._latest_headless_turn_record(tracked_agent_id=authority.tracked_agent_id)
        diagnostics: list[HoumaoErrorDetail] = []

        availability: ManagedAgentAvailability
        if control_state.request_admission == "blocked_reconciliation":
            availability = "error"
            diagnostics.append(
                HoumaoErrorDetail(
                    kind="gateway_reconciliation_required",
                    message="Gateway admission is blocked pending managed-agent reconciliation.",
                )
            )
        elif not control_state.runtime_resumable:
            availability = "unavailable"
            diagnostics.append(
                HoumaoErrorDetail(
                    kind="runtime_resume_unavailable",
                    message=(
                        "Managed headless authority exists, but the runtime controller could "
                        "not be resumed from persisted state."
                    ),
                )
            )
        elif control_state.tmux_session_live:
            availability = "available"
        else:
            availability = "unavailable"
            diagnostics.append(
                HoumaoErrorDetail(
                    kind="tmux_session_missing",
                    message=(
                        f"Native headless tmux session `{authority.tmux_session_name}` is not live."
                    ),
                )
            )

        active_turn_id = control_state.active_turn_id
        if active_turn_id is not None:
            turn_view = HoumaoManagedAgentTurnView(
                phase="active",
                active_turn_id=active_turn_id,
            )
        else:
            turn_view = HoumaoManagedAgentTurnView(
                phase="ready" if availability == "available" else "unknown",
                active_turn_id=None,
            )

        last_result: ManagedAgentLastTurnResult = "none"
        last_turn_id: str | None = None
        last_turn_index: int | None = None
        updated_at_utc: str | None = None
        if latest_turn is not None:
            last_result = _last_turn_result_from_headless_status(latest_turn.status)
            last_turn_id = latest_turn.turn_id
            last_turn_index = latest_turn.turn_index
            updated_at_utc = latest_turn.completed_at_utc or latest_turn.started_at_utc
        elif active_turn is not None and active_turn_id is not None:
            updated_at_utc = active_turn.started_at_utc

        return HoumaoManagedAgentStateResponse(
            tracked_agent_id=authority.tracked_agent_id,
            identity=self._managed_identity_from_headless_handle(handle),
            availability=availability,
            turn=turn_view,
            last_turn=HoumaoManagedAgentLastTurnView(
                result=last_result,
                turn_id=last_turn_id,
                turn_index=last_turn_index,
                updated_at_utc=updated_at_utc,
            ),
            diagnostics=diagnostics,
            mailbox=self._mailbox_summary_for_headless_handle(handle),
            gateway=gateway_summary,
        )

    def _managed_tui_detail_from_state(
        self,
        state: HoumaoTerminalStateResponse,
    ) -> HoumaoManagedAgentTuiDetailView:
        """Project one tracked-state sample into the managed-agent TUI detail contract."""

        terminal_id = state.terminal_id
        return HoumaoManagedAgentTuiDetailView(
            terminal_id=terminal_id,
            canonical_terminal_state_route=f"/houmao/terminals/{terminal_id}/state",
            canonical_terminal_history_route=f"/houmao/terminals/{terminal_id}/history",
            diagnostics=state.diagnostics,
            probe_snapshot=state.probe_snapshot,
            parsed_surface=state.parsed_surface,
            surface=state.surface,
            stability=state.stability,
        )

    def _managed_tui_detail_from_tracker(
        self,
        tracker: LiveSessionTracker,
    ) -> HoumaoManagedAgentTuiDetailView:
        """Project one tracker into the managed-agent TUI detail contract."""

        return self._managed_tui_detail_from_state(tracker.current_state())

    def _managed_tui_history_response(
        self,
        raw_history: HoumaoTerminalHistoryResponse,
    ) -> HoumaoManagedAgentHistoryResponse:
        """Project raw TUI history into the managed-agent shared history envelope."""

        return HoumaoManagedAgentHistoryResponse(
            tracked_agent_id=raw_history.tracked_session_id,
            entries=[
                HoumaoManagedAgentHistoryEntry(
                    recorded_at_utc=entry.recorded_at_utc,
                    summary=entry.summary,
                    availability=_availability_from_tui_transition(entry),
                    turn_phase=entry.turn_phase,
                    last_turn_result=entry.last_turn_result,
                    turn_id=None,
                )
                for entry in raw_history.entries
            ],
        )

    def _recent_transition_history_from_state(
        self,
        state: HoumaoTerminalStateResponse,
        *,
        limit: int,
    ) -> HoumaoTerminalHistoryResponse:
        """Project recent transitions from current state into the raw history envelope."""

        entries = list(state.recent_transitions[-limit:] if limit > 0 else state.recent_transitions)
        return HoumaoTerminalHistoryResponse(
            terminal_id=state.terminal_id,
            tracked_session_id=state.tracked_session.tracked_session_id,
            entries=entries,
        )

    def _managed_headless_detail_from_handle(
        self,
        handle: _ManagedHeadlessAgentHandle,
        *,
        summary_state: HoumaoManagedAgentStateResponse,
    ) -> HoumaoManagedAgentHeadlessDetailView:
        """Project one headless handle into the managed-agent detail contract."""

        authority = handle.authority
        active_turn = self.m_managed_headless_store.read_active_turn(
            tracked_agent_id=authority.tracked_agent_id
        )
        latest_turn = self._latest_headless_turn_record(tracked_agent_id=authority.tracked_agent_id)
        tmux_session_live = tmux_session_exists(session_name=authority.tmux_session_name)
        return HoumaoManagedAgentHeadlessDetailView(
            runtime_resumable=handle.controller is not None,
            tmux_session_live=tmux_session_live,
            can_accept_prompt_now=summary_state.availability == "available" and active_turn is None,
            interruptible=active_turn is not None,
            turn=summary_state.turn,
            last_turn=summary_state.last_turn,
            active_turn_started_at_utc=active_turn.started_at_utc
            if active_turn is not None
            else None,
            active_turn_interrupt_requested_at_utc=(
                active_turn.interrupt_requested_at_utc if active_turn is not None else None
            ),
            last_turn_status=latest_turn.status if latest_turn is not None else None,
            last_turn_started_at_utc=latest_turn.started_at_utc
            if latest_turn is not None
            else None,
            last_turn_completed_at_utc=(
                latest_turn.completed_at_utc if latest_turn is not None else None
            ),
            last_turn_completion_source=(
                latest_turn.completion_source if latest_turn is not None else None
            ),
            last_turn_returncode=latest_turn.returncode if latest_turn is not None else None,
            last_turn_history_summary=(
                latest_turn.history_summary if latest_turn is not None else None
            ),
            last_turn_error=latest_turn.error if latest_turn is not None else None,
            mailbox=summary_state.mailbox,
            gateway=summary_state.gateway,
            diagnostics=list(summary_state.diagnostics),
        )

    def _managed_headless_detail_from_gateway_handle(
        self,
        handle: _ManagedHeadlessAgentHandle,
        *,
        control_state: GatewayHeadlessControlStateV1,
        summary_state: HoumaoManagedAgentStateResponse,
    ) -> HoumaoManagedAgentHeadlessDetailView:
        """Project gateway-backed live headless posture into the detail contract."""

        authority = handle.authority
        active_turn = self.m_managed_headless_store.read_active_turn(
            tracked_agent_id=authority.tracked_agent_id
        )
        latest_turn = self._latest_headless_turn_record(tracked_agent_id=authority.tracked_agent_id)
        return HoumaoManagedAgentHeadlessDetailView(
            runtime_resumable=control_state.runtime_resumable,
            tmux_session_live=control_state.tmux_session_live,
            can_accept_prompt_now=control_state.can_accept_prompt_now,
            interruptible=control_state.interruptible,
            turn=summary_state.turn,
            last_turn=summary_state.last_turn,
            active_turn_started_at_utc=active_turn.started_at_utc
            if active_turn is not None
            else None,
            active_turn_interrupt_requested_at_utc=(
                active_turn.interrupt_requested_at_utc if active_turn is not None else None
            ),
            last_turn_status=latest_turn.status if latest_turn is not None else None,
            last_turn_started_at_utc=latest_turn.started_at_utc
            if latest_turn is not None
            else None,
            last_turn_completed_at_utc=(
                latest_turn.completed_at_utc if latest_turn is not None else None
            ),
            last_turn_completion_source=(
                latest_turn.completion_source if latest_turn is not None else None
            ),
            last_turn_returncode=latest_turn.returncode if latest_turn is not None else None,
            last_turn_history_summary=(
                latest_turn.history_summary if latest_turn is not None else None
            ),
            last_turn_error=latest_turn.error if latest_turn is not None else None,
            mailbox=summary_state.mailbox,
            gateway=summary_state.gateway,
            diagnostics=list(summary_state.diagnostics),
        )

    def _managed_request_id(self, *, agent_ref: str, request_kind: str) -> str:
        """Return one stable server-owned managed request identifier."""

        digest = _message_sha1(f"{agent_ref}:{request_kind}:{time.time()}")
        return f"mreq-{digest[:12]}"

    def _submit_tui_managed_request(
        self,
        *,
        tracker: LiveSessionTracker,
        request_model: HoumaoManagedAgentRequestEnvelope,
        request_id: str,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        """Deliver one transport-neutral request to a tracked TUI agent."""

        current = tracker.current_state()
        summary_state = self._managed_state_from_tui_tracker(tracker)
        if summary_state.availability != "available":
            raise HTTPException(
                status_code=503,
                detail="Managed-agent request submission is unavailable because the TUI agent is not operable.",
            )
        terminal_id = self._require_terminal_id_from_tracked_identity(current.tracked_session)
        terminal_path = parse.quote(terminal_id, safe="")

        if isinstance(request_model, HoumaoManagedAgentSubmitPromptRequest):
            proxy_response = self.proxy(
                method="POST",
                path=f"/terminals/{terminal_path}/input",
                params={"message": request_model.prompt},
            )
            self._require_successful_proxy_action(
                proxy_response,
                failure_status_code=503,
                failure_detail="Managed-agent prompt submission failed through the compatibility transport.",
            )
            self.note_prompt_submission(terminal_id=terminal_id, message=request_model.prompt)
            return HoumaoManagedAgentRequestAcceptedResponse(
                success=True,
                tracked_agent_id=summary_state.tracked_agent_id,
                request_id=request_id,
                request_kind=request_model.request_kind,
                disposition="accepted",
                detail="Managed-agent prompt request accepted for TUI delivery.",
            )

        if summary_state.turn.phase != "active":
            return HoumaoManagedAgentRequestAcceptedResponse(
                success=True,
                tracked_agent_id=summary_state.tracked_agent_id,
                request_id=request_id,
                request_kind=request_model.request_kind,
                disposition="no_op",
                detail="No active interruptible TUI work is running.",
            )

        proxy_response = self.proxy(
            method="POST",
            path=f"/terminals/{terminal_path}/exit",
        )
        self._require_successful_proxy_action(
            proxy_response,
            failure_status_code=503,
            failure_detail="Managed-agent interrupt delivery failed through the compatibility transport.",
        )
        return HoumaoManagedAgentRequestAcceptedResponse(
            success=True,
            tracked_agent_id=summary_state.tracked_agent_id,
            request_id=request_id,
            request_kind=request_model.request_kind,
            disposition="accepted",
            detail="Managed-agent interrupt request accepted for TUI delivery.",
        )

    def _headless_request_accepted_response(
        self,
        *,
        tracked_agent_id: str,
        request_id: str,
        request_kind: str,
        accepted: HoumaoHeadlessTurnAcceptedResponse,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        """Project one accepted headless turn into the transport-neutral request envelope."""

        return HoumaoManagedAgentRequestAcceptedResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            request_id=request_id,
            request_kind=cast(Literal["submit_prompt", "interrupt"], request_kind),
            disposition="accepted",
            detail=accepted.detail,
            headless_turn_id=accepted.turn_id,
            headless_turn_index=accepted.turn_index,
        )

    def _provision_headless_turn(
        self,
        *,
        handle: _ManagedHeadlessAgentHandle,
    ) -> tuple[
        RuntimeSessionController, ManagedHeadlessTurnRecord, ManagedHeadlessActiveTurnRecord
    ]:
        """Create the durable server-owned turn identity before live execution admission."""

        tracked_agent_id = handle.authority.tracked_agent_id
        controller = self._resume_or_get_headless_controller(handle)
        if controller is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Managed headless authority exists, but prompt submission is unavailable "
                    "because the runtime controller could not be resumed."
                ),
            )
        if (
            self.m_managed_headless_store.read_active_turn(tracked_agent_id=tracked_agent_id)
            is not None
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Managed headless turn submission rejected because this agent already "
                    "has an active turn."
                ),
            )

        backend_turn_index = self._next_headless_backend_turn_index(controller)
        turn_id = (
            f"turn-{_message_sha1(f'{tracked_agent_id}:{backend_turn_index}:{time.time()}')[:12]}"
        )
        turn_artifact_dir = self._headless_turn_artifacts_root(controller) / turn_id
        process_path = turn_artifact_dir / "process.json"
        tmux_window_name = HEADLESS_AGENT_WINDOW_NAME
        turn_record = ManagedHeadlessTurnRecord(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            turn_index=backend_turn_index,
            status="active",
            started_at_utc=utc_now_iso(),
            turn_artifact_dir=str(turn_artifact_dir),
            tmux_session_name=self._require_controller_tmux_session_name(controller),
            tmux_window_name=tmux_window_name,
            process_path=str(process_path),
            history_summary=f"Turn {turn_id} accepted.",
        )
        active_turn = ManagedHeadlessActiveTurnRecord(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            turn_index=backend_turn_index,
            turn_artifact_dir=str(turn_artifact_dir),
            started_at_utc=turn_record.started_at_utc,
            tmux_session_name=turn_record.tmux_session_name,
            tmux_window_name=tmux_window_name,
            process_path=str(process_path),
        )
        self.m_managed_headless_store.write_turn_record(turn_record)
        self.m_managed_headless_store.write_active_turn(active_turn)
        return controller, turn_record, active_turn

    def _submit_headless_turn_direct(
        self,
        *,
        handle: _ManagedHeadlessAgentHandle,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        """Accept one direct-fallback managed headless turn."""

        _, turn_record, _ = self._provision_headless_turn(handle=handle)
        tracked_agent_id = handle.authority.tracked_agent_id
        worker = threading.Thread(
            target=self._run_headless_turn_worker,
            kwargs={
                "tracked_agent_id": tracked_agent_id,
                "turn_id": turn_record.turn_id,
                "prompt": request_model.prompt,
            },
            daemon=True,
            name=f"houmao-headless-turn-{tracked_agent_id}-{turn_record.turn_id}",
        )
        handle.set_active_thread(worker)
        worker.start()

        return HoumaoHeadlessTurnAcceptedResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_record.turn_id,
            turn_index=turn_record.turn_index,
            status="active",
            detail=f"Managed headless turn `{turn_record.turn_id}` accepted.",
        )

    def _submit_headless_turn_via_gateway(
        self,
        *,
        handle: _ManagedHeadlessAgentHandle,
        client: GatewayClient,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        """Accept one managed headless turn through the attached gateway control plane."""

        tracked_agent_id = handle.authority.tracked_agent_id
        control_state = self._invoke_live_gateway(client.get_headless_control_state)
        if control_state.request_admission == "blocked_reconciliation":
            raise HTTPException(
                status_code=409,
                detail="Gateway admission is blocked pending managed-agent reconciliation.",
            )
        if control_state.active_execution == "running" or control_state.active_turn_id is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Managed headless turn submission rejected because this agent already "
                    "has an active turn."
                ),
            )
        if not control_state.runtime_resumable or not control_state.tmux_session_live:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Managed-agent prompt submission is unavailable because authoritative "
                    "headless runtime control is not currently operable."
                ),
            )
        if control_state.request_admission != "open":
            raise HTTPException(
                status_code=503,
                detail=(
                    "Managed-agent prompt submission is unavailable because authoritative "
                    "headless runtime control is not currently operable."
                ),
            )

        _, turn_record, _ = self._provision_headless_turn(handle=handle)
        try:
            self._invoke_live_gateway(
                lambda: client.create_request(
                    GatewayRequestCreateV1(
                        kind="submit_prompt",
                        payload=GatewayRequestPayloadSubmitPromptV1(
                            prompt=request_model.prompt,
                            turn_id=turn_record.turn_id,
                        ),
                    )
                )
            )
        except HTTPException:
            self.m_managed_headless_store.clear_active_turn(tracked_agent_id=tracked_agent_id)
            self.m_managed_headless_store.delete_turn_record(
                tracked_agent_id=tracked_agent_id,
                turn_id=turn_record.turn_id,
            )
            raise

        return HoumaoHeadlessTurnAcceptedResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_record.turn_id,
            turn_index=turn_record.turn_index,
            status="active",
            detail=f"Managed headless turn `{turn_record.turn_id}` accepted.",
        )

    def _submit_headless_interrupt_via_gateway(
        self,
        *,
        handle: _ManagedHeadlessAgentHandle,
        client: GatewayClient,
        request_id: str,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        """Queue one managed headless interrupt through the attached gateway control plane."""

        tracked_agent_id = handle.authority.tracked_agent_id
        active_turn = self.m_managed_headless_store.read_active_turn(
            tracked_agent_id=tracked_agent_id
        )
        if active_turn is None:
            return HoumaoManagedAgentRequestAcceptedResponse(
                success=True,
                tracked_agent_id=tracked_agent_id,
                request_id=request_id,
                request_kind="interrupt",
                disposition="no_op",
                detail="No active interruptible headless work is running.",
            )

        prior_turn_record = self.m_managed_headless_store.read_turn_record(
            tracked_agent_id=tracked_agent_id,
            turn_id=active_turn.turn_id,
        )
        self._record_interrupt_request(active_turn)
        try:
            self._invoke_live_gateway(
                lambda: client.create_request(
                    GatewayRequestCreateV1(
                        kind="interrupt",
                        payload=GatewayRequestPayloadInterruptV1(),
                    )
                )
            )
        except HTTPException:
            self.m_managed_headless_store.write_active_turn(active_turn)
            if prior_turn_record is not None:
                self.m_managed_headless_store.write_turn_record(prior_turn_record)
            raise

        return HoumaoManagedAgentRequestAcceptedResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            request_id=request_id,
            request_kind="interrupt",
            disposition="accepted",
            detail=f"Best-effort interrupt requested for turn `{active_turn.turn_id}`.",
            headless_turn_id=active_turn.turn_id,
            headless_turn_index=active_turn.turn_index,
        )

    def _submit_headless_managed_request(
        self,
        *,
        handle: _ManagedHeadlessAgentHandle,
        request_model: HoumaoManagedAgentRequestEnvelope,
        request_id: str,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        """Deliver one transport-neutral request to a managed headless agent."""

        tracked_agent_id = handle.authority.tracked_agent_id
        controller = self._resume_or_get_headless_controller(handle)
        if isinstance(request_model, HoumaoManagedAgentSubmitPromptRequest):
            if controller is None or not tmux_session_exists(
                session_name=handle.authority.tmux_session_name
            ):
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Managed-agent prompt submission is unavailable because authoritative "
                        "headless runtime control is not currently operable."
                    ),
                )
            if (
                self.m_managed_headless_store.read_active_turn(tracked_agent_id=tracked_agent_id)
                is not None
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Managed-agent prompt submission rejected because this headless agent "
                        "already has an active managed turn."
                    ),
                )
            accepted = self._submit_headless_turn_direct(
                handle=handle,
                request_model=HoumaoHeadlessTurnRequest(prompt=request_model.prompt),
            )
            return self._headless_request_accepted_response(
                tracked_agent_id=tracked_agent_id,
                request_id=request_id,
                request_kind=request_model.request_kind,
                accepted=accepted,
            )

        active_turn = self.m_managed_headless_store.read_active_turn(
            tracked_agent_id=tracked_agent_id
        )
        if active_turn is None:
            return HoumaoManagedAgentRequestAcceptedResponse(
                success=True,
                tracked_agent_id=tracked_agent_id,
                request_id=request_id,
                request_kind=request_model.request_kind,
                disposition="no_op",
                detail="No active interruptible headless work is running.",
            )

        self._interrupt_active_turn_record(active_turn)
        return HoumaoManagedAgentRequestAcceptedResponse(
            success=True,
            tracked_agent_id=tracked_agent_id,
            request_id=request_id,
            request_kind=request_model.request_kind,
            disposition="accepted",
            detail=f"Best-effort interrupt requested for turn `{active_turn.turn_id}`.",
            headless_turn_id=active_turn.turn_id,
            headless_turn_index=active_turn.turn_index,
        )

    def _require_successful_proxy_action(
        self,
        proxy_response: ProxyResponse,
        *,
        failure_status_code: int,
        failure_detail: str,
    ) -> None:
        """Require one proxied compatibility action to succeed."""

        if not 200 <= proxy_response.status_code < 300:
            detail = self._proxy_action_detail(proxy_response, fallback=failure_detail)
            raise HTTPException(status_code=failure_status_code, detail=detail)
        payload = proxy_response.json_payload
        if isinstance(payload, dict) and payload.get("success") is False:
            detail = self._proxy_action_detail(proxy_response, fallback=failure_detail)
            raise HTTPException(status_code=failure_status_code, detail=detail)

    def _proxy_action_detail(self, proxy_response: ProxyResponse, *, fallback: str) -> str:
        """Return a concise error detail for one proxied compatibility action."""

        payload = proxy_response.json_payload
        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, str) and detail.strip():
                return detail.strip()
        return fallback

    def _require_terminal_id_from_tracked_identity(self, identity: object) -> str:
        """Return the canonical terminal id from tracked-session identity state."""

        aliases = getattr(identity, "terminal_aliases", ())
        if isinstance(aliases, list) and aliases:
            first = aliases[0]
            if isinstance(first, str) and first.strip():
                return first
        raise HTTPException(
            status_code=503,
            detail="Managed TUI agent is missing a terminal alias required for server-owned control.",
        )

    def _mailbox_summary_for_tui_tracker(
        self,
        tracker: LiveSessionTracker,
    ) -> HoumaoManagedAgentMailboxSummaryView | None:
        """Return optional redacted mailbox summary for one tracked TUI agent."""

        return self._mailbox_summary_for_tui_identity(tracker.current_state().tracked_session)

    def _mailbox_summary_for_tui_identity(
        self,
        identity: HoumaoTrackedSessionIdentity,
    ) -> HoumaoManagedAgentMailboxSummaryView | None:
        """Return optional redacted mailbox summary for one tracked TUI identity."""

        shared_registry_record = self._shared_registry_record_for_identity(
            agent_name=identity.agent_name,
            agent_id=identity.agent_id,
        )
        mailbox = getattr(shared_registry_record, "mailbox", None)
        if mailbox is not None:
            return self._mailbox_summary_from_payload(mailbox)
        if identity.manifest_path is None:
            return None
        return self._mailbox_summary_from_manifest_path(Path(identity.manifest_path))

    def _mailbox_summary_for_headless_handle(
        self,
        handle: _ManagedHeadlessAgentHandle,
    ) -> HoumaoManagedAgentMailboxSummaryView | None:
        """Return optional redacted mailbox summary for one managed headless agent."""

        controller = handle.controller
        if controller is not None:
            return self._mailbox_summary_from_payload(
                getattr(controller.launch_plan, "mailbox", None)
            )
        return self._mailbox_summary_from_manifest_path(Path(handle.authority.manifest_path))

    def _mailbox_summary_from_manifest_path(
        self,
        manifest_path: Path,
    ) -> HoumaoManagedAgentMailboxSummaryView | None:
        """Return mailbox summary from one persisted session manifest when available."""

        try:
            handle = load_session_manifest(manifest_path.resolve())
            payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        except (SessionManifestError, FileNotFoundError):
            return None
        return self._mailbox_summary_from_payload(payload.launch_plan.mailbox)

    def _mailbox_summary_from_payload(
        self,
        mailbox: object | None,
    ) -> HoumaoManagedAgentMailboxSummaryView | None:
        """Return redacted mailbox summary from one runtime or registry payload."""

        if mailbox is None:
            return None
        transport = getattr(mailbox, "transport", None)
        principal_id = getattr(mailbox, "principal_id", None)
        address = getattr(mailbox, "address", None)
        if transport not in {"filesystem", "stalwart"}:
            return None
        return HoumaoManagedAgentMailboxSummaryView(
            transport=transport,
            principal_id=principal_id,
            address=address,
        )

    def _shared_registry_record_for_identity(
        self,
        *,
        agent_name: str | None,
        agent_id: str | None,
    ) -> object | None:
        """Return optional shared-registry evidence for one managed identity."""

        if agent_id is not None:
            return resolve_live_agent_record_by_agent_id(agent_id)
        if agent_name is not None:
            return resolve_live_agent_record(agent_name)
        return None

    def _gateway_summary_for_session_root(
        self,
        session_root: str | None,
    ) -> HoumaoManagedAgentGatewaySummaryView | None:
        """Return redacted gateway summary for one runtime-owned session root."""

        status = self._optional_gateway_status_for_session_root(session_root)
        if status is None:
            return None
        return self._gateway_summary_from_status(status)

    def _optional_gateway_status_for_session_root(
        self,
        session_root: str | None,
    ) -> GatewayStatusV1 | None:
        """Return optional gateway status for one session root."""

        if session_root is None:
            return None
        try:
            return self._gateway_status_for_session_root(Path(session_root))
        except HTTPException:
            return None

    def _live_gateway_client_for_session_root(
        self,
        session_root: str | None,
    ) -> GatewayClient | None:
        """Return a live gateway client for one session root when healthy and reachable."""

        status = self._optional_gateway_status_for_session_root(session_root)
        if (
            status is None
            or status.gateway_health != "healthy"
            or status.gateway_host is None
            or status.gateway_port is None
        ):
            return None
        client = GatewayClient(
            endpoint=GatewayEndpoint(host=status.gateway_host, port=status.gateway_port),
        )
        try:
            client.health()
        except GatewayHttpError:
            return None
        return client

    def _fallback_gateway_summary(
        self,
        gateway_status: GatewayStatusV1 | None,
    ) -> HoumaoManagedAgentGatewaySummaryView | None:
        """Return a safe fallback gateway summary for direct control paths."""

        if gateway_status is None or gateway_status.gateway_health == "healthy":
            return None
        return self._gateway_summary_from_status(gateway_status)

    def _gateway_summary_from_status(
        self,
        status: GatewayStatusV1,
    ) -> HoumaoManagedAgentGatewaySummaryView:
        """Project one gateway status payload into the public summary view."""

        return HoumaoManagedAgentGatewaySummaryView(
            gateway_health=status.gateway_health,
            managed_agent_connectivity=status.managed_agent_connectivity,
            managed_agent_recovery=status.managed_agent_recovery,
            request_admission=status.request_admission,
            active_execution=status.active_execution,
            queue_depth=status.queue_depth,
            gateway_host=status.gateway_host,
            gateway_port=status.gateway_port,
        )

    def _gateway_status_for_session_root(self, session_root: Path) -> GatewayStatusV1:
        """Return gateway status from one runtime-owned session root."""

        paths = gateway_paths_from_session_root(session_root=session_root.resolve())
        if paths.state_path.is_file():
            try:
                return load_gateway_status(paths.state_path)
            except SessionManifestError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
        try:
            attach_contract = resolve_internal_gateway_attach_contract(paths)
        except SessionManifestError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return build_offline_gateway_status(
            attach_contract=attach_contract,
            managed_agent_instance_epoch=0,
        )

    def _managed_gateway_context(self, agent_ref: str) -> dict[str, object]:
        """Resolve gateway-capable runtime context for one managed agent."""

        resolved = self._resolve_managed_agent_ref(agent_ref)
        if resolved["transport"] == "headless":
            handle = self._require_headless_handle(resolved["tracked_agent_id"])
            headless_session_root = handle.authority.session_root
            controller = self._resume_or_get_headless_controller(handle)
            status = self._gateway_status_for_session_root(Path(headless_session_root))
            return {
                "tracked_agent_id": resolved["tracked_agent_id"],
                "transport": "headless",
                "session_root": headless_session_root,
                "controller": controller,
                "status": status,
            }

        tracker = self._tracker_for_session_id(resolved["tracked_agent_id"])
        current = tracker.current_state()
        tui_session_root = current.tracked_session.session_root
        if tui_session_root is None:
            raise HTTPException(
                status_code=422,
                detail="Managed TUI agent does not expose a runtime-owned session root for gateway operations.",
            )
        controller = self._controller_for_tui_tracker(tracker)
        if controller is not None:
            try:
                status = controller.gateway_status()
            except SessionManifestError:
                status = self._gateway_status_for_session_root(Path(tui_session_root))
        else:
            status = self._gateway_status_for_session_root(Path(tui_session_root))
        return {
            "tracked_agent_id": resolved["tracked_agent_id"],
            "transport": "tui",
            "session_root": tui_session_root,
            "controller": controller,
            "status": status,
        }

    def _publish_server_launched_registry_record(
        self,
        controller: RuntimeSessionController,
    ) -> None:
        """Publish or refresh one non-runtime-launched registry record."""

        if controller.registry_launch_authority == "runtime":
            return
        record = controller.build_shared_registry_record()
        if record is None:
            raise SessionManifestError(
                "Managed runtime controller could not build a shared-registry record."
            )
        publish_live_agent_record(record)

    def _clear_shared_registry_record_for_terminated_agent(
        self,
        *,
        agent_name: str | None,
        agent_id: str | None,
        manifest_path: Path | None,
        session_name: str | None,
    ) -> bool:
        """Remove one shared-registry record when it still matches the terminated agent."""

        record = self._shared_registry_record_for_identity(agent_name=agent_name, agent_id=agent_id)
        if record is None:
            return False

        record_agent_id = getattr(record, "agent_id", None)
        if not isinstance(record_agent_id, str) or not record_agent_id.strip():
            return False
        record_generation_id = getattr(record, "generation_id", None)
        record_manifest_path = getattr(getattr(record, "runtime", None), "manifest_path", None)
        record_session_name = getattr(getattr(record, "terminal", None), "session_name", None)

        if manifest_path is not None and isinstance(record_manifest_path, str):
            if Path(record_manifest_path).expanduser().resolve() != manifest_path.resolve():
                return False
        if session_name is not None and isinstance(record_session_name, str):
            if record_session_name.strip() != session_name.strip():
                return False

        return remove_live_agent_record(
            record_agent_id,
            generation_id=record_generation_id if isinstance(record_generation_id, str) else None,
        )

    def _resume_or_get_headless_controller(
        self,
        handle: _ManagedHeadlessAgentHandle,
    ) -> RuntimeSessionController | None:
        """Return the live or resumable controller for one managed headless agent."""

        if handle.controller is not None:
            return handle.controller
        controller = self._resume_headless_controller(handle.authority)
        if controller is not None:
            handle.set_controller(controller)
        return controller

    def _publish_server_managed_headless_gateway_metadata(
        self,
        authority: ManagedHeadlessAuthorityRecord,
    ) -> None:
        """Publish server-managed control-plane metadata into the manifest-backed authority."""

        manifest_path = Path(authority.manifest_path).expanduser().resolve()
        paths = gateway_paths_from_manifest_path(manifest_path)
        try:
            handle = load_session_manifest(manifest_path)
            payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        except SessionManifestError:
            return
        if payload.backend not in {"claude_headless", "codex_headless", "gemini_headless"}:
            return
        gateway_authority = (
            payload.gateway_authority.model_dump(mode="json")
            if payload.gateway_authority is not None
            else {"attach": {}, "control": {}}
        )
        for endpoint_name in ("attach", "control"):
            endpoint = gateway_authority.get(endpoint_name)
            updated_endpoint = dict(endpoint) if isinstance(endpoint, dict) else {}
            updated_endpoint["api_base_url"] = self.m_config.api_base_url
            updated_endpoint["managed_agent_ref"] = authority.tracked_agent_id
            gateway_authority[endpoint_name] = updated_endpoint
        try:
            update_session_manifest(
                manifest_path,
                {"gateway_authority": gateway_authority},
            )
        except SessionManifestError:
            return
        if paths is not None and paths.gateway_root.exists():
            refresh_internal_gateway_publication(paths)

    def _controller_for_tui_tracker(
        self,
        tracker: LiveSessionTracker,
    ) -> RuntimeSessionController | None:
        """Resume one runtime controller for a tracked TUI session when possible."""

        current = tracker.current_state()
        manifest_path_value = current.tracked_session.manifest_path
        if manifest_path_value is None:
            return None
        shared_registry_record = self._shared_registry_record_for_identity(
            agent_name=current.tracked_session.agent_name,
            agent_id=current.tracked_session.agent_id,
        )
        if shared_registry_record is None:
            return None
        agent_def_dir_value = getattr(
            getattr(shared_registry_record, "runtime", None), "agent_def_dir", None
        )
        if not isinstance(agent_def_dir_value, str) or not agent_def_dir_value.strip():
            return None
        try:
            return resume_runtime_session(
                agent_def_dir=Path(agent_def_dir_value).expanduser().resolve(),
                session_manifest_path=Path(manifest_path_value).expanduser().resolve(),
            )
        except (LaunchPlanError, SessionManifestError, RuntimeError):
            return None

    def _invoke_live_gateway(
        self,
        call: Callable[[], _GatewayModelT],
    ) -> _GatewayModelT:
        """Translate one gateway client failure into an HTTPException."""

        try:
            return call()
        except GatewayHttpError as exc:
            raise HTTPException(status_code=exc.status_code or 503, detail=exc.detail) from exc

    def _require_live_managed_gateway_client(self, agent_ref: str) -> GatewayClient:
        """Return a live gateway client for one managed agent or fail."""

        gateway_context = self._managed_gateway_context(agent_ref)
        session_root = gateway_context.get("session_root")
        if not isinstance(session_root, str):
            raise HTTPException(
                status_code=503,
                detail="No live gateway is attached for this managed agent.",
            )
        client = self._live_gateway_client_for_session_root(session_root)
        if client is None:
            raise HTTPException(
                status_code=503,
                detail="No live gateway is attached for this managed agent.",
            )
        return client

    def _require_live_managed_mail_gateway_client(self, agent_ref: str) -> GatewayClient:
        """Require pair-owned mailbox capability plus a live gateway client."""

        summary_state = self.managed_agent_state(agent_ref)
        if summary_state.mailbox is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Managed-agent mail follow-up is unavailable because this managed agent "
                    "does not expose pair-owned mailbox capability."
                ),
            )
        return self._require_live_managed_gateway_client(agent_ref)

    def _latest_headless_turn_record(
        self,
        *,
        tracked_agent_id: str,
    ) -> ManagedHeadlessTurnRecord | None:
        """Return the latest persisted headless turn record when present."""

        turn_records = self.m_managed_headless_store.list_turn_records(
            tracked_agent_id=tracked_agent_id
        )
        if not turn_records:
            return None
        turn_records.sort(
            key=lambda record: (
                record.completed_at_utc or "",
                record.started_at_utc,
                record.turn_id,
            ),
            reverse=True,
        )
        return turn_records[0]

    def _headless_history_entries(
        self,
        *,
        tracked_agent_id: str,
        limit: int,
    ) -> list[HoumaoManagedAgentHistoryEntry]:
        """Project bounded coarse headless turn history for the shared route."""

        turn_records = self.m_managed_headless_store.list_turn_records(
            tracked_agent_id=tracked_agent_id
        )
        turn_records.sort(
            key=lambda record: (record.started_at_utc, record.turn_id),
            reverse=True,
        )
        entries: list[HoumaoManagedAgentHistoryEntry] = []
        for record in turn_records[:limit]:
            entries.append(
                HoumaoManagedAgentHistoryEntry(
                    recorded_at_utc=record.completed_at_utc or record.started_at_utc,
                    summary=record.history_summary
                    or f"Turn {record.turn_id} status={record.status}.",
                    availability="available" if record.status == "active" else "unavailable",
                    turn_phase="active" if record.status == "active" else "ready",
                    last_turn_result=_last_turn_result_from_headless_status(record.status),
                    turn_id=record.turn_id,
                )
            )
        return entries

    def _reconcile_headless_active_turn(self, *, tracked_agent_id: str) -> None:
        """Refresh one persisted active headless turn against execution evidence."""

        active_turn = self.m_managed_headless_store.read_active_turn(
            tracked_agent_id=tracked_agent_id
        )
        if active_turn is None:
            return
        gateway_active_turn_id = self._gateway_active_headless_turn_id(
            tracked_agent_id=tracked_agent_id
        )
        self._refresh_headless_turn_record(
            tracked_agent_id=tracked_agent_id,
            turn_id=active_turn.turn_id,
            error_detail=None,
            gateway_active_turn_id=gateway_active_turn_id,
        )

    def _refresh_headless_turn_record(
        self,
        *,
        tracked_agent_id: str,
        turn_id: str,
        error_detail: str | None,
        gateway_active_turn_id: str | None = None,
    ) -> ManagedHeadlessTurnRecord | None:
        """Refresh one headless turn from durable results and execution liveness."""

        turn_record = self.m_managed_headless_store.read_turn_record(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
        )
        active_turn = self.m_managed_headless_store.read_active_turn(
            tracked_agent_id=tracked_agent_id
        )
        if turn_record is None:
            if active_turn is not None and active_turn.turn_id == turn_id:
                self.m_managed_headless_store.clear_active_turn(tracked_agent_id=tracked_agent_id)
            return None
        if active_turn is not None and active_turn.turn_id != turn_id:
            active_turn = None

        legacy_missing_execution_metadata = self._is_legacy_headless_execution_metadata_missing(
            turn_record=turn_record,
            active_turn=active_turn,
        )
        turn_record, active_turn, process_metadata_error = self._sync_headless_process_metadata(
            tracked_agent_id=tracked_agent_id,
            turn_record=turn_record,
            active_turn=active_turn,
        )

        if active_turn is None:
            return turn_record
        if gateway_active_turn_id is not None and gateway_active_turn_id == turn_id:
            return turn_record

        turn_dir = Path(turn_record.turn_artifact_dir)
        stdout_path = turn_dir / "stdout.jsonl"
        stderr_path = turn_dir / "stderr.log"
        status_path = turn_dir / "exitcode"
        interrupt_requested_at_utc = (
            active_turn.interrupt_requested_at_utc or turn_record.interrupt_requested_at_utc
        )

        returncode: int | None = None
        completion_source = turn_record.completion_source
        final_status: Literal["active", "completed", "failed", "interrupted"]
        if status_path.exists():
            returncode = read_headless_turn_return_code(status_path=status_path)
            if returncode == 0:
                final_status = "completed"
            elif interrupt_requested_at_utc is not None:
                final_status = "interrupted"
            else:
                final_status = "failed"
            if stdout_path.exists():
                events = load_headless_turn_events(
                    stdout_path=stdout_path,
                    output_format=self._headless_output_format(tracked_agent_id=tracked_agent_id),
                    turn_index=turn_record.turn_index,
                )
                for event in reversed(events):
                    payload = event.payload
                    if not isinstance(payload, dict):
                        continue
                    payload_source = payload.get("completion_source")
                    if isinstance(payload_source, str) and payload_source.strip():
                        completion_source = payload_source.strip()
                        break
        elif self._headless_execution_is_live(
            tracked_agent_id=tracked_agent_id,
            turn_record=turn_record,
            active_turn=active_turn,
        ):
            return turn_record
        elif interrupt_requested_at_utc is not None:
            final_status = "interrupted"
        else:
            final_status = "failed"

        final_error = error_detail
        if final_status == "failed" and final_error is None:
            final_error = self._headless_failed_execution_detail(
                turn_record=turn_record,
                active_turn=active_turn,
                legacy_missing_execution_metadata=legacy_missing_execution_metadata,
                process_metadata_error=process_metadata_error,
            )

        history_summary = {
            "completed": f"Turn {turn_id} completed successfully.",
            "failed": f"Turn {turn_id} failed.",
            "interrupted": f"Turn {turn_id} interrupted.",
            "active": f"Turn {turn_id} is still active.",
        }[final_status]

        updated_record = turn_record.model_copy(
            update={
                "status": final_status,
                "completed_at_utc": utc_now_iso(),
                "stdout_path": str(stdout_path) if stdout_path.exists() else None,
                "stderr_path": str(stderr_path) if stderr_path.exists() else None,
                "status_path": str(status_path) if status_path.exists() else None,
                "completion_source": completion_source,
                "returncode": returncode,
                "error": final_error,
                "interrupt_requested_at_utc": interrupt_requested_at_utc,
                "history_summary": history_summary,
            }
        )
        self.m_managed_headless_store.write_turn_record(updated_record)
        self.m_managed_headless_store.clear_active_turn(tracked_agent_id=tracked_agent_id)
        return updated_record

    def _gateway_active_headless_turn_id(self, *, tracked_agent_id: str) -> str | None:
        """Return the live gateway-owned active turn id when one is attached and healthy."""

        with self.m_lock:
            handle = self.m_headless_agents.get(tracked_agent_id)
        if handle is None:
            return None
        authority = getattr(handle, "authority", None)
        session_root = getattr(authority, "session_root", None)
        if not isinstance(session_root, str):
            return None
        client = self._live_gateway_client_for_session_root(session_root)
        if client is None:
            return None
        try:
            return self._invoke_live_gateway(client.get_headless_control_state).active_turn_id
        except HTTPException:
            return None

    def _next_headless_backend_turn_index(
        self,
        controller: RuntimeSessionController,
    ) -> int:
        """Return the next runtime-backed headless turn index."""

        backend_session = controller.backend_session
        if not isinstance(backend_session, HeadlessInteractiveSession):
            raise HTTPException(
                status_code=500,
                detail="Managed headless controller is not bound to a headless backend session.",
            )
        return int(backend_session.state.turn_index) + 1

    def _headless_turn_artifacts_root(self, controller: RuntimeSessionController) -> Path:
        """Return the persisted turn-artifacts root for one headless controller."""

        return (
            controller.manifest_path.parent / f"{controller.manifest_path.stem}.turn-artifacts"
        ).resolve()

    def _headless_output_format(self, *, tracked_agent_id: str) -> str:
        """Return the configured headless output format for one managed agent."""

        handle = self._require_headless_handle(tracked_agent_id)
        if handle.controller is None:
            return "stream-json"
        output_format = handle.controller.launch_plan.metadata.get("headless_output_format")
        if isinstance(output_format, str) and output_format.strip():
            return output_format
        return "stream-json"

    def _run_headless_turn_worker(
        self,
        *,
        tracked_agent_id: str,
        turn_id: str,
        prompt: str,
    ) -> None:
        """Execute one accepted headless turn in a background thread."""

        handle = self._require_headless_handle(tracked_agent_id)
        controller = handle.controller
        if controller is None:
            handle.set_active_thread(None)
            self._refresh_headless_turn_record(
                tracked_agent_id=tracked_agent_id,
                turn_id=turn_id,
                error_detail=(
                    "Managed headless runtime controller is unavailable during background "
                    "turn execution."
                ),
            )
            return
        backend_session = controller.backend_session
        if not isinstance(backend_session, HeadlessInteractiveSession):
            handle.set_active_thread(None)
            self._refresh_headless_turn_record(
                tracked_agent_id=tracked_agent_id,
                turn_id=turn_id,
                error_detail="Managed headless controller is missing a headless backend session.",
            )
            return

        error_detail: str | None = None
        try:
            backend_session.send_prompt(prompt, turn_artifact_dir_name=turn_id)
        except Exception as exc:
            error_detail = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                controller.persist_manifest()
            except Exception as exc:
                if error_detail is None:
                    error_detail = f"{type(exc).__name__}: {exc}"
            handle.set_active_thread(None)
            self._refresh_headless_turn_record(
                tracked_agent_id=tracked_agent_id,
                turn_id=turn_id,
                error_detail=error_detail,
            )

    def _finalize_headless_turn_record(
        self,
        *,
        tracked_agent_id: str,
        turn_id: str,
        error_detail: str | None,
    ) -> None:
        """Refresh one headless turn record from durable artifact evidence."""

        self._refresh_headless_turn_record(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            error_detail=error_detail,
        )

    def _sync_headless_process_metadata(
        self,
        *,
        tracked_agent_id: str,
        turn_record: ManagedHeadlessTurnRecord,
        active_turn: ManagedHeadlessActiveTurnRecord | None,
    ) -> tuple[
        ManagedHeadlessTurnRecord,
        ManagedHeadlessActiveTurnRecord | None,
        str | None,
    ]:
        """Mirror durable process metadata from runner artifacts into store records."""

        process_path = self._headless_process_path(turn_record=turn_record, active_turn=active_turn)
        metadata_error: str | None = None
        runner_pid: int | None = None
        child_pid: int | None = None
        process_started_at_utc: str | None = None

        if process_path.exists():
            try:
                process_metadata = load_headless_process_metadata(process_path=process_path)
            except (ValueError, json.JSONDecodeError) as exc:
                metadata_error = f"Invalid headless process metadata at `{process_path}`: {exc}"
            else:
                runner_pid = process_metadata.runner_pid
                child_pid = process_metadata.child_pid
                process_started_at_utc = process_metadata.launched_at_utc

        turn_updates: dict[str, str | int | None] = {}
        process_path_text = str(process_path)
        if turn_record.process_path != process_path_text:
            turn_updates["process_path"] = process_path_text
        if runner_pid is not None and turn_record.runner_pid != runner_pid:
            turn_updates["runner_pid"] = runner_pid
        if child_pid is not None and turn_record.child_pid != child_pid:
            turn_updates["child_pid"] = child_pid
        if (
            process_started_at_utc is not None
            and turn_record.process_started_at_utc != process_started_at_utc
        ):
            turn_updates["process_started_at_utc"] = process_started_at_utc
        if turn_updates:
            turn_record = turn_record.model_copy(update=turn_updates)
            self.m_managed_headless_store.write_turn_record(turn_record)

        if active_turn is not None:
            active_updates: dict[str, str | int | None] = {}
            if active_turn.process_path != process_path_text:
                active_updates["process_path"] = process_path_text
            if runner_pid is not None and active_turn.runner_pid != runner_pid:
                active_updates["runner_pid"] = runner_pid
            if child_pid is not None and active_turn.child_pid != child_pid:
                active_updates["child_pid"] = child_pid
            if (
                process_started_at_utc is not None
                and active_turn.process_started_at_utc != process_started_at_utc
            ):
                active_updates["process_started_at_utc"] = process_started_at_utc
            if active_updates:
                active_turn = active_turn.model_copy(update=active_updates)
                self.m_managed_headless_store.write_active_turn(active_turn)

        return turn_record, active_turn, metadata_error

    def _headless_process_path(
        self,
        *,
        turn_record: ManagedHeadlessTurnRecord,
        active_turn: ManagedHeadlessActiveTurnRecord | None,
    ) -> Path:
        """Return the durable process-metadata path for one headless turn."""

        candidate = None
        if active_turn is not None and active_turn.process_path is not None:
            candidate = active_turn.process_path
        elif turn_record.process_path is not None:
            candidate = turn_record.process_path
        if candidate is not None:
            return Path(candidate)
        return Path(turn_record.turn_artifact_dir) / "process.json"

    def _is_legacy_headless_execution_metadata_missing(
        self,
        *,
        turn_record: ManagedHeadlessTurnRecord,
        active_turn: ManagedHeadlessActiveTurnRecord | None,
    ) -> bool:
        """Return whether one active headless turn predates execution-evidence metadata."""

        if turn_record.process_path is not None or turn_record.runner_pid is not None:
            return False
        if turn_record.child_pid is not None or turn_record.process_started_at_utc is not None:
            return False
        if active_turn is None:
            return False
        return (
            active_turn.process_path is None
            and active_turn.runner_pid is None
            and active_turn.child_pid is None
            and active_turn.process_started_at_utc is None
        )

    def _headless_execution_is_live(
        self,
        *,
        tracked_agent_id: str,
        turn_record: ManagedHeadlessTurnRecord,
        active_turn: ManagedHeadlessActiveTurnRecord,
    ) -> bool:
        """Return whether one managed headless turn still has live execution evidence."""

        if self._headless_active_thread_is_live(tracked_agent_id=tracked_agent_id):
            return True
        for pid in (
            active_turn.child_pid,
            turn_record.child_pid,
            active_turn.runner_pid,
            turn_record.runner_pid,
        ):
            if self._pid_is_live(pid):
                return True
        return False

    def _headless_active_thread_is_live(self, *, tracked_agent_id: str) -> bool:
        """Return whether one managed headless agent still has a live worker thread."""

        with self.m_lock:
            handle = self.m_headless_agents.get(tracked_agent_id)
        if handle is None:
            return False
        active_thread = handle.active_thread
        if active_thread is None:
            return False
        if not active_thread.is_alive():
            handle.set_active_thread(None)
            return False
        return True

    def _pid_is_live(self, pid: int | None) -> bool:
        """Return whether one pid still appears to be live."""

        if pid is None:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _headless_failed_execution_detail(
        self,
        *,
        turn_record: ManagedHeadlessTurnRecord,
        active_turn: ManagedHeadlessActiveTurnRecord | None,
        legacy_missing_execution_metadata: bool,
        process_metadata_error: str | None,
    ) -> str:
        """Return the failure detail for a no-evidence managed headless terminal state."""

        if process_metadata_error is not None:
            return process_metadata_error
        if legacy_missing_execution_metadata:
            return "Pre-migration active turn without execution-evidence metadata."
        process_path = self._headless_process_path(turn_record=turn_record, active_turn=active_turn)
        if not process_path.exists():
            return "Headless execution ended without durable completion or process metadata."
        return "Headless execution ended without durable completion."

    def _require_turn_record(
        self,
        *,
        tracked_agent_id: str,
        turn_id: str,
    ) -> ManagedHeadlessTurnRecord:
        """Return one required persisted headless turn record."""

        turn_record = self.m_managed_headless_store.read_turn_record(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
        )
        if turn_record is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown managed headless turn `{turn_id}` for `{tracked_agent_id}`.",
            )
        return turn_record

    def _headless_turn_status_response(
        self,
        turn_record: ManagedHeadlessTurnRecord,
    ) -> HoumaoHeadlessTurnStatusResponse:
        """Convert one persisted turn record into the public status response."""

        return HoumaoHeadlessTurnStatusResponse(
            tracked_agent_id=turn_record.tracked_agent_id,
            turn_id=turn_record.turn_id,
            turn_index=turn_record.turn_index,
            status=turn_record.status,
            started_at_utc=turn_record.started_at_utc,
            completed_at_utc=turn_record.completed_at_utc,
            returncode=turn_record.returncode,
            completion_source=turn_record.completion_source,
            stdout_path=turn_record.stdout_path,
            stderr_path=turn_record.stderr_path,
            status_path=turn_record.status_path,
            history_summary=turn_record.history_summary,
            error=turn_record.error,
        )

    def _interrupt_active_turn_record(
        self,
        active_turn: ManagedHeadlessActiveTurnRecord,
    ) -> None:
        """Deliver a best-effort interrupt through execution identity first."""

        updated_active_turn, turn_record = self._record_interrupt_request(active_turn)

        if self._interrupt_live_headless_handle(tracked_agent_id=active_turn.tracked_agent_id):
            return
        if self._interrupt_persisted_headless_process(
            turn_record=turn_record,
            active_turn=updated_active_turn,
        ):
            return
        self._interrupt_headless_tmux_target(active_turn=updated_active_turn)

    def _record_interrupt_request(
        self,
        active_turn: ManagedHeadlessActiveTurnRecord,
    ) -> tuple[ManagedHeadlessActiveTurnRecord, ManagedHeadlessTurnRecord | None]:
        """Persist the operator's interrupt intent without delivering the signal."""

        interrupted_at = utc_now_iso()
        updated_active_turn = active_turn.model_copy(
            update={"interrupt_requested_at_utc": interrupted_at}
        )
        self.m_managed_headless_store.write_active_turn(updated_active_turn)

        turn_record = self.m_managed_headless_store.read_turn_record(
            tracked_agent_id=active_turn.tracked_agent_id,
            turn_id=active_turn.turn_id,
        )
        if turn_record is not None:
            turn_record = turn_record.model_copy(
                update={"interrupt_requested_at_utc": interrupted_at}
            )
            self.m_managed_headless_store.write_turn_record(turn_record)
        return updated_active_turn, turn_record

    def _interrupt_live_headless_handle(self, *, tracked_agent_id: str) -> bool:
        """Interrupt one live in-memory headless execution handle when present."""

        with self.m_lock:
            handle = self.m_headless_agents.get(tracked_agent_id)
        if handle is None or not self._headless_active_thread_is_live(
            tracked_agent_id=tracked_agent_id
        ):
            return False
        controller = handle.controller
        if controller is None:
            return False
        backend_session = controller.backend_session
        if not isinstance(backend_session, HeadlessInteractiveSession):
            return False
        result = backend_session.interrupt()
        if result.status == "ok":
            return True
        raise HTTPException(status_code=502, detail=result.detail)

    def _interrupt_persisted_headless_process(
        self,
        *,
        turn_record: ManagedHeadlessTurnRecord | None,
        active_turn: ManagedHeadlessActiveTurnRecord,
    ) -> bool:
        """Interrupt one persisted headless execution identity when present."""

        candidates: list[int] = []
        for pid in (
            active_turn.child_pid,
            turn_record.child_pid if turn_record is not None else None,
            active_turn.runner_pid,
            turn_record.runner_pid if turn_record is not None else None,
        ):
            if pid is not None and pid not in candidates:
                candidates.append(pid)
        for pid in candidates:
            if self._signal_pid_best_effort(pid=pid):
                return True
        return False

    def _signal_pid_best_effort(self, *, pid: int) -> bool:
        """Send SIGTERM to one pid when it still appears to be live."""

        try:
            os.kill(pid, 15)
        except ProcessLookupError:
            return False
        except PermissionError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to interrupt managed headless pid `{pid}`: {exc}",
            ) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to interrupt managed headless pid `{pid}`: {exc}",
            ) from exc
        return True

    def _interrupt_headless_tmux_target(
        self,
        *,
        active_turn: ManagedHeadlessActiveTurnRecord,
    ) -> None:
        """Interrupt one headless turn through tmux as a last-resort fallback."""

        target = headless_agent_pane_target(session_name=active_turn.tmux_session_name)
        try:
            result = run_tmux(["send-keys", "-t", target, "C-c"])
        except TmuxCommandError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if result.returncode == 0:
            return
        detail = (tmux_error_detail(result) or "unknown tmux error").lower()
        if (
            "can't find pane" in detail
            or "can't find window" in detail
            or "no server running" in detail
        ):
            return
        raise HTTPException(
            status_code=502,
            detail=f"Failed to interrupt tmux headless agent surface `{target}`: {detail}",
        )

    def _require_controller_tmux_session_name(self, controller: RuntimeSessionController) -> str:
        """Return the bound tmux session name for one headless controller."""

        session_name = controller.tmux_session_name
        if session_name is not None and session_name.strip():
            return session_name
        backend_session = controller.backend_session
        if isinstance(backend_session, HeadlessInteractiveSession):
            resolved = backend_session.state.tmux_session_name
            if resolved is not None and resolved.strip():
                return resolved
        raise HTTPException(
            status_code=500,
            detail="Managed headless controller is missing a tmux session binding.",
        )

    def _write_current_instance(self) -> None:
        """Persist the current server instance and pid files."""

        payload = self.current_instance_response().model_dump(mode="json", exclude_none=True)
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


def _availability_from_tui_state(
    state: HoumaoTerminalStateResponse,
) -> ManagedAgentAvailability:
    """Map one TUI live state into the shared coarse availability enum."""

    if state.diagnostics.availability == "error":
        return "error"
    if state.diagnostics.availability in {"unavailable", "tui_down"}:
        return "unavailable"
    return "available"


def _availability_from_tui_transition(entry: object) -> ManagedAgentAvailability:
    """Map one TUI transition entry into the shared coarse availability enum."""

    diagnostics_availability = getattr(entry, "diagnostics_availability", "unknown")
    if diagnostics_availability == "error":
        return "error"
    if diagnostics_availability in {"unavailable", "tui_down"}:
        return "unavailable"
    return "available"


def _last_turn_result_from_headless_status(status: str) -> ManagedAgentLastTurnResult:
    """Map one headless turn status into the shared coarse last-turn result."""

    if status == "completed":
        return "success"
    if status == "interrupted":
        return "interrupted"
    if status in {"failed", "unknown"}:
        return "known_failure"
    return "none"


def _is_safe_registration_session_name(session_name: str) -> bool:
    """Return whether one session name is safe for server-owned registration storage."""

    if not session_name or session_name != session_name.strip():
        return False
    if session_name in {".", ".."}:
        return False
    if "/" in session_name or "\\" in session_name or "\x00" in session_name:
        return False
    return True
