"""FastAPI application factory for `houmao-server`."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
import signal
import threading
import time
from urllib import parse

from fastapi import APIRouter, FastAPI, Query, Response

from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
)
from houmao.version import get_version

from .config import HoumaoServerConfig
from .models import (
    HoumaoCurrentInstance,
    HoumaoHeadlessLaunchRequest,
    HoumaoHeadlessLaunchResponse,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoHealthResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayPromptControlResponse,
    HoumaoManagedAgentGatewayRequestAcceptedResponse,
    HoumaoManagedAgentGatewayRequestCreate,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentMailActionResponse,
    HoumaoManagedAgentMailCheckRequest,
    HoumaoManagedAgentMailCheckResponse,
    HoumaoManagedAgentMailReplyRequest,
    HoumaoManagedAgentMailSendRequest,
    HoumaoManagedAgentMailStateRequest,
    HoumaoManagedAgentMailStateResponse,
    HoumaoManagedAgentMailStatusResponse,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentRequestEnvelope,
    HoumaoManagedAgentStateResponse,
    HoumaoRegisterLaunchRequest,
    HoumaoRegisterLaunchResponse,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
    TerminalId,
)
from .service import HoumaoServerService


def create_app(
    *,
    config: HoumaoServerConfig | None = None,
    service: HoumaoServerService | None = None,
) -> FastAPI:
    """Create a configured `houmao-server` FastAPI application."""

    resolved_config = config or HoumaoServerConfig()
    resolved_service = service or HoumaoServerService(config=resolved_config)

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved_service.startup()
        app.state.houmao_service = resolved_service
        try:
            yield
        finally:
            resolved_service.shutdown()

    app = FastAPI(
        title="houmao-server",
        description="Houmao-owned CAO-compatible HTTP service",
        version=get_version(),
        lifespan=_lifespan,
    )

    cao_router = APIRouter(prefix="/cao")

    @app.get("/health", response_model_exclude_none=True)
    def health() -> HoumaoHealthResponse:
        return resolved_service.health_response()

    @app.get("/houmao/server/current-instance", response_model_exclude_none=True)
    def current_instance() -> HoumaoCurrentInstance:
        return resolved_service.current_instance_response()

    @app.post("/houmao/server/shutdown")
    def shutdown_server() -> dict[str, bool]:
        def _deferred_shutdown() -> None:
            time.sleep(0.1)
            os.kill(os.getpid(), signal.SIGTERM)

        threading.Thread(target=_deferred_shutdown, daemon=True).start()
        return {"success": True}

    @cao_router.get("/health")
    def cao_health() -> Response:
        return resolved_service.proxy(method="GET", path="/health").to_fastapi_response()

    @cao_router.post("/sessions", status_code=201)
    def create_session(
        provider: str,
        agent_profile: str,
        session_name: str | None = None,
        working_directory: str | None = None,
    ) -> Response:
        result = resolved_service.proxy(
            method="POST",
            path="/sessions",
            params=_drop_none(
                {
                    "provider": provider,
                    "agent_profile": agent_profile,
                    "session_name": session_name,
                    "working_directory": working_directory,
                }
            ),
        )
        if 200 <= result.status_code < 300:
            resolved_service.sync_created_terminal(result.json_payload)
        return result.to_fastapi_response()

    @cao_router.get("/sessions")
    def list_sessions() -> Response:
        return resolved_service.proxy(method="GET", path="/sessions").to_fastapi_response()

    @cao_router.get("/sessions/{session_name}")
    def get_session(session_name: str) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/sessions/{_quote_path_segment(session_name)}",
        ).to_fastapi_response()

    @cao_router.delete("/sessions/{session_name}")
    def delete_session(session_name: str) -> Response:
        result = resolved_service.proxy(
            method="DELETE",
            path=f"/sessions/{_quote_path_segment(session_name)}",
        )
        if 200 <= result.status_code < 300:
            resolved_service.handle_deleted_session(session_name)
        return result.to_fastapi_response()

    @cao_router.post("/sessions/{session_name}/terminals", status_code=201)
    def create_terminal(
        session_name: str,
        provider: str,
        agent_profile: str,
        working_directory: str | None = None,
    ) -> Response:
        result = resolved_service.proxy(
            method="POST",
            path=f"/sessions/{_quote_path_segment(session_name)}/terminals",
            params=_drop_none(
                {
                    "provider": provider,
                    "agent_profile": agent_profile,
                    "working_directory": working_directory,
                }
            ),
        )
        if 200 <= result.status_code < 300:
            resolved_service.sync_created_terminal(result.json_payload)
        return result.to_fastapi_response()

    @cao_router.get("/sessions/{session_name}/terminals")
    def list_session_terminals(session_name: str) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/sessions/{_quote_path_segment(session_name)}/terminals",
        ).to_fastapi_response()

    @cao_router.get("/terminals/{terminal_id}")
    def get_terminal(terminal_id: TerminalId) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/terminals/{_quote_path_segment(terminal_id)}",
        ).to_fastapi_response()

    @cao_router.get("/terminals/{terminal_id}/working-directory")
    def get_terminal_working_directory(terminal_id: TerminalId) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/working-directory",
        ).to_fastapi_response()

    @cao_router.post("/terminals/{terminal_id}/input")
    def send_input(terminal_id: TerminalId, message: str) -> Response:
        monotonic_ts = time.monotonic()
        resolved_service.emit_tracking_debug(
            stream="app-input",
            event_type="route_input_request",
            terminal_id=terminal_id,
            monotonic_ts=monotonic_ts,
            data={"message_length": len(message)},
        )
        result = resolved_service.proxy(
            method="POST",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/input",
            params={"message": message},
        )
        resolved_service.emit_tracking_debug(
            stream="app-input",
            event_type="route_input_proxy_result",
            terminal_id=terminal_id,
            monotonic_ts=monotonic_ts,
            data={"status_code": result.status_code},
        )
        if 200 <= result.status_code < 300:
            resolved_service.note_prompt_submission(terminal_id=terminal_id, message=message)
            resolved_service.emit_tracking_debug(
                stream="app-input",
                event_type="route_input_prompt_submission_recorded",
                terminal_id=terminal_id,
                monotonic_ts=monotonic_ts,
                data={"status_code": result.status_code},
            )
        return result.to_fastapi_response()

    @cao_router.get("/terminals/{terminal_id}/output")
    def get_output(terminal_id: TerminalId, mode: str = "full") -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/output",
            params={"mode": mode},
        ).to_fastapi_response()

    @cao_router.post("/terminals/{terminal_id}/exit")
    def exit_terminal(terminal_id: TerminalId) -> Response:
        return resolved_service.proxy(
            method="POST",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/exit",
        ).to_fastapi_response()

    @cao_router.delete("/terminals/{terminal_id}")
    def delete_terminal(terminal_id: TerminalId) -> Response:
        result = resolved_service.proxy(
            method="DELETE",
            path=f"/terminals/{_quote_path_segment(terminal_id)}",
        )
        if 200 <= result.status_code < 300:
            resolved_service.handle_deleted_terminal(terminal_id)
        return result.to_fastapi_response()

    @cao_router.post("/terminals/{receiver_id}/inbox/messages")
    def create_inbox_message(receiver_id: TerminalId, sender_id: str, message: str) -> Response:
        return resolved_service.proxy(
            method="POST",
            path=f"/terminals/{_quote_path_segment(receiver_id)}/inbox/messages",
            params={"sender_id": sender_id, "message": message},
        ).to_fastapi_response()

    @cao_router.get("/terminals/{terminal_id}/inbox/messages")
    def list_inbox_messages(
        terminal_id: TerminalId,
        limit: int = Query(default=10, le=100),
        status: str | None = Query(default=None),
    ) -> Response:
        return resolved_service.proxy(
            method="GET",
            path=f"/terminals/{_quote_path_segment(terminal_id)}/inbox/messages",
            params=_drop_none({"limit": str(limit), "status": status}),
        ).to_fastapi_response()

    @app.post("/houmao/launches/register")
    def register_launch(
        session_name: str,
        tool: str,
        terminal_id: str | None = None,
        observed_tool_version: str | None = None,
        manifest_path: str | None = None,
        session_root: str | None = None,
        agent_name: str | None = None,
        agent_id: str | None = None,
        tmux_session_name: str | None = None,
        tmux_window_name: str | None = None,
    ) -> HoumaoRegisterLaunchResponse:
        request_model = HoumaoRegisterLaunchRequest(
            session_name=session_name,
            terminal_id=terminal_id,
            tool=tool,
            observed_tool_version=observed_tool_version,
            manifest_path=manifest_path,
            session_root=session_root,
            agent_name=agent_name,
            agent_id=agent_id,
            tmux_session_name=tmux_session_name,
            tmux_window_name=tmux_window_name,
        )
        return resolved_service.register_launch(request_model)

    @app.get("/houmao/agents")
    def list_managed_agents() -> HoumaoManagedAgentListResponse:
        return resolved_service.list_managed_agents()

    @app.get("/houmao/agents/{agent_ref}")
    def managed_agent(agent_ref: str) -> HoumaoManagedAgentIdentity:
        return resolved_service.managed_agent(agent_ref)

    @app.get("/houmao/agents/{agent_ref}/state")
    def managed_agent_state(agent_ref: str) -> HoumaoManagedAgentStateResponse:
        return resolved_service.managed_agent_state(agent_ref)

    @app.get("/houmao/agents/{agent_ref}/state/detail")
    def managed_agent_state_detail(agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        return resolved_service.managed_agent_state_detail(agent_ref)

    @app.get("/houmao/agents/{agent_ref}/history")
    def managed_agent_history(
        agent_ref: str,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> HoumaoManagedAgentHistoryResponse:
        return resolved_service.managed_agent_history(agent_ref, limit=limit)

    @app.post("/houmao/agents/{agent_ref}/requests")
    def submit_managed_agent_request(
        agent_ref: str,
        request_model: HoumaoManagedAgentRequestEnvelope,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        return resolved_service.submit_managed_agent_request(agent_ref, request_model)

    @app.post("/houmao/agents/headless/launches")
    def launch_headless_agent(
        request_model: HoumaoHeadlessLaunchRequest,
    ) -> HoumaoHeadlessLaunchResponse:
        return resolved_service.launch_headless_agent(request_model)

    @app.post("/houmao/agents/{agent_ref}/stop")
    def stop_managed_agent(agent_ref: str) -> HoumaoManagedAgentActionResponse:
        return resolved_service.stop_managed_agent(agent_ref)

    @app.post("/houmao/agents/{agent_ref}/turns")
    def submit_headless_turn(
        agent_ref: str,
        request_model: HoumaoHeadlessTurnRequest,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        return resolved_service.submit_headless_turn(agent_ref, request_model)

    @app.get("/houmao/agents/{agent_ref}/turns/{turn_id}")
    def headless_turn_status(
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnStatusResponse:
        return resolved_service.headless_turn_status(agent_ref, turn_id)

    @app.get("/houmao/agents/{agent_ref}/turns/{turn_id}/events")
    def headless_turn_events(
        agent_ref: str,
        turn_id: str,
    ) -> HoumaoHeadlessTurnEventsResponse:
        return resolved_service.headless_turn_events(agent_ref, turn_id)

    @app.get("/houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout")
    def headless_turn_stdout(agent_ref: str, turn_id: str) -> Response:
        return Response(
            content=resolved_service.headless_turn_artifact_text(
                agent_ref,
                turn_id,
                artifact_name="stdout",
            ),
            media_type="text/plain",
        )

    @app.get("/houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr")
    def headless_turn_stderr(agent_ref: str, turn_id: str) -> Response:
        return Response(
            content=resolved_service.headless_turn_artifact_text(
                agent_ref,
                turn_id,
                artifact_name="stderr",
            ),
            media_type="text/plain",
        )

    @app.post("/houmao/agents/{agent_ref}/interrupt")
    def interrupt_managed_agent(agent_ref: str) -> HoumaoManagedAgentActionResponse:
        return resolved_service.interrupt_managed_agent(agent_ref)

    @app.get("/houmao/agents/{agent_ref}/gateway")
    def managed_agent_gateway_status(agent_ref: str) -> GatewayStatusV1:
        return resolved_service.managed_agent_gateway_status(agent_ref)

    @app.post("/houmao/agents/{agent_ref}/gateway/attach")
    def attach_managed_agent_gateway(agent_ref: str) -> GatewayStatusV1:
        return resolved_service.attach_managed_agent_gateway(agent_ref)

    @app.post("/houmao/agents/{agent_ref}/gateway/detach")
    def detach_managed_agent_gateway(agent_ref: str) -> GatewayStatusV1:
        return resolved_service.detach_managed_agent_gateway(agent_ref)

    @app.get("/houmao/agents/{agent_ref}/gateway/tui/state")
    def get_managed_agent_gateway_tui_state(agent_ref: str) -> HoumaoTerminalStateResponse:
        return resolved_service.get_managed_agent_gateway_tui_state(agent_ref)

    @app.get("/houmao/agents/{agent_ref}/gateway/tui/history")
    def get_managed_agent_gateway_tui_history(
        agent_ref: str,
        limit: int = Query(default=100, ge=0),
    ) -> HoumaoTerminalSnapshotHistoryResponse:
        return resolved_service.get_managed_agent_gateway_tui_history(agent_ref, limit=limit)

    @app.post("/houmao/agents/{agent_ref}/gateway/tui/note-prompt")
    def note_managed_agent_gateway_tui_prompt(
        agent_ref: str,
        request_model: GatewayRequestPayloadSubmitPromptV1,
    ) -> HoumaoTerminalStateResponse:
        return resolved_service.note_managed_agent_gateway_tui_prompt(
            agent_ref,
            prompt=request_model.prompt,
        )

    @app.post("/houmao/agents/{agent_ref}/gateway/requests")
    def submit_managed_agent_gateway_request(
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayRequestCreate,
    ) -> HoumaoManagedAgentGatewayRequestAcceptedResponse:
        return resolved_service.submit_managed_agent_gateway_request(agent_ref, request_model)

    @app.post("/houmao/agents/{agent_ref}/gateway/control/prompt")
    def control_managed_agent_gateway_prompt(
        agent_ref: str,
        request_model: HoumaoManagedAgentGatewayPromptControlRequest,
    ) -> HoumaoManagedAgentGatewayPromptControlResponse:
        return resolved_service.control_managed_agent_gateway_prompt(agent_ref, request_model)

    @app.post("/houmao/agents/{agent_ref}/gateway/control/send-keys")
    def send_managed_agent_gateway_control_input(
        agent_ref: str,
        request_model: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1:
        return resolved_service.send_managed_agent_gateway_control_input(agent_ref, request_model)

    @app.get("/houmao/agents/{agent_ref}/gateway/mail-notifier")
    def get_managed_agent_gateway_mail_notifier(agent_ref: str) -> GatewayMailNotifierStatusV1:
        return resolved_service.get_managed_agent_gateway_mail_notifier(agent_ref)

    @app.put("/houmao/agents/{agent_ref}/gateway/mail-notifier")
    def put_managed_agent_gateway_mail_notifier(
        agent_ref: str,
        request_model: GatewayMailNotifierPutV1,
    ) -> GatewayMailNotifierStatusV1:
        return resolved_service.put_managed_agent_gateway_mail_notifier(
            agent_ref,
            request_model,
        )

    @app.delete("/houmao/agents/{agent_ref}/gateway/mail-notifier")
    def delete_managed_agent_gateway_mail_notifier(
        agent_ref: str,
    ) -> GatewayMailNotifierStatusV1:
        return resolved_service.delete_managed_agent_gateway_mail_notifier(agent_ref)

    @app.get("/houmao/agents/{agent_ref}/mail/status")
    def managed_agent_mail_status(agent_ref: str) -> HoumaoManagedAgentMailStatusResponse:
        return resolved_service.managed_agent_mail_status(agent_ref)

    @app.get("/houmao/agents/{agent_ref}/mail/resolve-live")
    def managed_agent_mail_resolve_live(agent_ref: str) -> dict[str, object]:
        return resolved_service.managed_agent_mail_resolve_live(agent_ref)

    @app.post("/houmao/agents/{agent_ref}/mail/check")
    def check_managed_agent_mail(
        agent_ref: str,
        request_model: HoumaoManagedAgentMailCheckRequest,
    ) -> HoumaoManagedAgentMailCheckResponse:
        return resolved_service.check_managed_agent_mail(agent_ref, request_model)

    @app.post("/houmao/agents/{agent_ref}/mail/send")
    def send_managed_agent_mail(
        agent_ref: str,
        request_model: HoumaoManagedAgentMailSendRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        return resolved_service.send_managed_agent_mail(agent_ref, request_model)

    @app.post("/houmao/agents/{agent_ref}/mail/reply")
    def reply_managed_agent_mail(
        agent_ref: str,
        request_model: HoumaoManagedAgentMailReplyRequest,
    ) -> HoumaoManagedAgentMailActionResponse:
        return resolved_service.reply_managed_agent_mail(agent_ref, request_model)

    @app.post("/houmao/agents/{agent_ref}/mail/state")
    def update_managed_agent_mail_state(
        agent_ref: str,
        request_model: HoumaoManagedAgentMailStateRequest,
    ) -> HoumaoManagedAgentMailStateResponse:
        return resolved_service.update_managed_agent_mail_state(agent_ref, request_model)

    @app.get("/houmao/terminals/{terminal_id}/state")
    def terminal_state(terminal_id: TerminalId) -> HoumaoTerminalStateResponse:
        return resolved_service.terminal_state(terminal_id)

    @app.get("/houmao/terminals/{terminal_id}/history")
    def terminal_history(
        terminal_id: TerminalId,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> HoumaoTerminalHistoryResponse:
        return resolved_service.terminal_history(terminal_id, limit=limit)

    app.include_router(cao_router)

    return app


def _drop_none(values: dict[str, str | None]) -> dict[str, str]:
    return {key: value for key, value in values.items() if value is not None}


def _quote_path_segment(value: str) -> str:
    """Percent-encode one child-CAO path segment."""

    return parse.quote(value, safe="")
