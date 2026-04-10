"""FastAPI application factory for ``houmao-passive-server``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.responses import Response

from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayHeadlessControlStateV1,
    GatewayMailActionResponseV1,
    GatewayMailCheckRequestV1,
    GatewayMailCheckResponseV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayMailPostRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStatusV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderCreateResultV1,
    GatewayReminderDeleteResultV1,
    GatewayReminderListV1,
    GatewayReminderPutV1,
    GatewayReminderV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
)
from houmao.version import get_version
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.models import (
    AgentTuiDetailResponse,
    AgentTuiHistoryResponse,
    AgentTuiStateResponse,
    DiscoveredAgentConflictResponse,
    DiscoveredAgentListResponse,
    DiscoveredAgentSummary,
    PassiveAgentActionResponse,
    PassiveCurrentInstance,
    PassiveHeadlessLaunchRequest,
    PassiveHeadlessLaunchResponse,
    PassiveHeadlessTurnAcceptedResponse,
    PassiveHeadlessTurnEventsResponse,
    PassiveHeadlessTurnRequest,
    PassiveHeadlessTurnStatusResponse,
    PassiveHealthResponse,
    PassiveNotImplementedResponse,
    PassivePromptRequest,
    PassiveRequestAcceptedResponse,
    PassiveShutdownResponse,
)
from houmao.passive_server.service import PassiveServerService
from houmao.server.models import (
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayNextPromptSessionRequest,
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayPromptControlResponse,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
)


def create_app(
    *,
    config: PassiveServerConfig | None = None,
    service: PassiveServerService | None = None,
) -> FastAPI:
    """Create a configured ``houmao-passive-server`` FastAPI application."""

    resolved_config = config or PassiveServerConfig()
    resolved_service = service or PassiveServerService(config=resolved_config)

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved_service.startup()
        app.state.passive_service = resolved_service
        try:
            yield
        finally:
            resolved_service.shutdown()

    app = FastAPI(
        title="houmao-passive-server",
        description="Registry-first passive server for distributed agent coordination",
        version=get_version(),
        lifespan=_lifespan,
    )

    @app.get("/health")
    def health() -> PassiveHealthResponse:
        return resolved_service.health()

    @app.get("/houmao/server/current-instance")
    def current_instance() -> PassiveCurrentInstance:
        return resolved_service.current_instance()

    @app.post("/houmao/server/shutdown")
    def shutdown_server() -> PassiveShutdownResponse:
        resolved_service.request_shutdown()
        return PassiveShutdownResponse()

    @app.get("/houmao/agents")
    def list_agents() -> DiscoveredAgentListResponse:
        return resolved_service.list_agents()

    @app.get("/houmao/agents/{agent_ref}")
    def resolve_agent(agent_ref: str) -> DiscoveredAgentSummary:
        result = resolved_service.resolve_agent(agent_ref)
        if result is None:
            return JSONResponse(  # type: ignore[return-value]
                status_code=404,
                content={"detail": f"Agent not found: {agent_ref}"},
            )
        if isinstance(result, DiscoveredAgentConflictResponse):
            return JSONResponse(  # type: ignore[return-value]
                status_code=409,
                content=result.model_dump(mode="json"),
            )
        return result

    # -- gateway proxy routes -------------------------------------------------

    @app.get("/houmao/agents/{agent_ref}/gateway")
    def gateway_status(agent_ref: str) -> GatewayStatusV1:
        result = resolved_service.gateway_status(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/gateway/tui/state")
    def gateway_tui_state(agent_ref: str) -> HoumaoTerminalStateResponse:
        result = resolved_service.gateway_tui_state(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/gateway/tui/history")
    def gateway_tui_history(
        agent_ref: str,
        limit: int = 100,
    ) -> HoumaoTerminalSnapshotHistoryResponse:
        result = resolved_service.gateway_tui_history(agent_ref, limit=limit)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/gateway/tui/note-prompt")
    def gateway_tui_note_prompt(
        agent_ref: str,
        payload: GatewayRequestPayloadSubmitPromptV1,
    ) -> HoumaoTerminalStateResponse:
        result = resolved_service.gateway_tui_note_prompt(agent_ref, prompt=payload.prompt)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/gateway/control/headless/state")
    def gateway_headless_control_state(agent_ref: str) -> GatewayHeadlessControlStateV1:
        result = resolved_service.gateway_headless_control_state(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session")
    def gateway_headless_next_prompt_session(
        agent_ref: str,
        payload: HoumaoManagedAgentGatewayNextPromptSessionRequest,
    ) -> GatewayHeadlessControlStateV1:
        result = resolved_service.gateway_headless_next_prompt_session(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/gateway/requests")
    def gateway_create_request(
        agent_ref: str, payload: GatewayRequestCreateV1
    ) -> GatewayAcceptedRequestV1:
        result = resolved_service.gateway_create_request(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/gateway/control/prompt")
    def gateway_control_prompt(
        agent_ref: str,
        payload: HoumaoManagedAgentGatewayPromptControlRequest,
    ) -> HoumaoManagedAgentGatewayPromptControlResponse:
        result = resolved_service.gateway_control_prompt(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/gateway/control/send-keys")
    def gateway_send_control_input(
        agent_ref: str, payload: GatewayControlInputRequestV1
    ) -> GatewayControlInputResultV1:
        result = resolved_service.gateway_send_control_input(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/gateway/attach")
    def gateway_attach(agent_ref: str) -> PassiveNotImplementedResponse:
        return JSONResponse(  # type: ignore[return-value]
            status_code=501,
            content=PassiveNotImplementedResponse(
                detail=(
                    "Gateway attach is not supported by houmao-passive-server. "
                    f"Use: houmao-mgr agents gateway attach {agent_ref}"
                ),
            ).model_dump(mode="json"),
        )

    @app.post("/houmao/agents/{agent_ref}/gateway/detach")
    def gateway_detach(agent_ref: str) -> PassiveNotImplementedResponse:
        return JSONResponse(  # type: ignore[return-value]
            status_code=501,
            content=PassiveNotImplementedResponse(
                detail=(
                    "Gateway detach is not supported by houmao-passive-server. "
                    f"Use: houmao-mgr agents gateway detach {agent_ref}"
                ),
            ).model_dump(mode="json"),
        )

    @app.get("/houmao/agents/{agent_ref}/gateway/mail-notifier")
    def gateway_mail_notifier_status(agent_ref: str) -> GatewayMailNotifierStatusV1:
        result = resolved_service.gateway_mail_notifier_status(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.put("/houmao/agents/{agent_ref}/gateway/mail-notifier")
    def gateway_mail_notifier_enable(
        agent_ref: str, payload: GatewayMailNotifierPutV1
    ) -> GatewayMailNotifierStatusV1:
        result = resolved_service.gateway_mail_notifier_enable(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.delete("/houmao/agents/{agent_ref}/gateway/mail-notifier")
    def gateway_mail_notifier_disable(agent_ref: str) -> GatewayMailNotifierStatusV1:
        result = resolved_service.gateway_mail_notifier_disable(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/gateway/reminders")
    def gateway_reminders(agent_ref: str) -> GatewayReminderListV1:
        result = resolved_service.gateway_reminders(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/gateway/reminders")
    def gateway_create_reminders(
        agent_ref: str,
        payload: GatewayReminderCreateBatchV1,
    ) -> GatewayReminderCreateResultV1:
        result = resolved_service.gateway_create_reminders(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}")
    def gateway_get_reminder(agent_ref: str, reminder_id: str) -> GatewayReminderV1:
        result = resolved_service.gateway_get_reminder(agent_ref, reminder_id)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.put("/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}")
    def gateway_put_reminder(
        agent_ref: str,
        reminder_id: str,
        payload: GatewayReminderPutV1,
    ) -> GatewayReminderV1:
        result = resolved_service.gateway_put_reminder(agent_ref, reminder_id, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.delete("/houmao/agents/{agent_ref}/gateway/reminders/{reminder_id}")
    def gateway_delete_reminder(
        agent_ref: str,
        reminder_id: str,
    ) -> GatewayReminderDeleteResultV1:
        result = resolved_service.gateway_delete_reminder(agent_ref, reminder_id)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/mail/status")
    def gateway_mail_status(agent_ref: str) -> GatewayMailStatusV1:
        result = resolved_service.gateway_mail_status(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/mail/check")
    def gateway_mail_check(
        agent_ref: str, payload: GatewayMailCheckRequestV1
    ) -> GatewayMailCheckResponseV1:
        result = resolved_service.gateway_mail_check(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/mail/send")
    def gateway_mail_send(
        agent_ref: str, payload: GatewayMailSendRequestV1
    ) -> GatewayMailActionResponseV1:
        result = resolved_service.gateway_mail_send(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/mail/post")
    def gateway_mail_post(
        agent_ref: str, payload: GatewayMailPostRequestV1
    ) -> GatewayMailActionResponseV1:
        result = resolved_service.gateway_mail_post(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/mail/reply")
    def gateway_mail_reply(
        agent_ref: str, payload: GatewayMailReplyRequestV1
    ) -> GatewayMailActionResponseV1:
        result = resolved_service.gateway_mail_reply(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    # -- TUI observation routes -----------------------------------------------

    @app.get("/houmao/agents/{agent_ref}/state")
    def agent_state(agent_ref: str) -> AgentTuiStateResponse:
        result = resolved_service.agent_state(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/state/detail")
    def agent_state_detail(agent_ref: str) -> AgentTuiDetailResponse:
        result = resolved_service.agent_state_detail(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/history")
    def agent_history(agent_ref: str, limit: int = 50) -> AgentTuiHistoryResponse:
        result = resolved_service.agent_history(agent_ref, limit=limit)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/managed-state")
    def managed_agent_state(agent_ref: str) -> HoumaoManagedAgentStateResponse:
        result = resolved_service.managed_agent_state(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/managed-state/detail")
    def managed_agent_state_detail(agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        result = resolved_service.managed_agent_state_detail(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/managed-history")
    def managed_agent_history(
        agent_ref: str,
        limit: int = 50,
    ) -> HoumaoManagedAgentHistoryResponse:
        result = resolved_service.managed_agent_history(agent_ref, limit=limit)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    # -- request submission routes (Tier 6) -----------------------------------

    @app.post("/houmao/agents/{agent_ref}/requests")
    def submit_request(
        agent_ref: str, payload: PassivePromptRequest
    ) -> PassiveRequestAcceptedResponse:
        result = resolved_service.submit_request(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/interrupt")
    def interrupt_agent(agent_ref: str) -> PassiveAgentActionResponse:
        result = resolved_service.interrupt_agent(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/stop")
    def stop_agent(agent_ref: str) -> PassiveAgentActionResponse:
        result = resolved_service.stop_agent(agent_ref)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    # -- headless management routes (Tier 7) ----------------------------------

    @app.post("/houmao/agents/headless/launches")
    def launch_headless(
        payload: PassiveHeadlessLaunchRequest,
    ) -> PassiveHeadlessLaunchResponse:
        result = resolved_service.launch_headless(payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.post("/houmao/agents/{agent_ref}/turns")
    def submit_turn(
        agent_ref: str, payload: PassiveHeadlessTurnRequest
    ) -> PassiveHeadlessTurnAcceptedResponse:
        result = resolved_service.submit_turn(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/turns/{turn_id}")
    def turn_status(agent_ref: str, turn_id: str) -> PassiveHeadlessTurnStatusResponse:
        result = resolved_service.turn_status(agent_ref, turn_id)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/turns/{turn_id}/events")
    def turn_events(agent_ref: str, turn_id: str) -> PassiveHeadlessTurnEventsResponse:
        result = resolved_service.turn_events(agent_ref, turn_id)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    @app.get("/houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/{name}")
    def turn_artifact(agent_ref: str, turn_id: str, name: str) -> Response:
        result = resolved_service.turn_artifact_text(agent_ref, turn_id, name)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])
        return Response(content=result, media_type="text/plain")

    return app
