"""FastAPI application factory for ``houmao-passive-server``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayMailActionResponseV1,
    GatewayMailCheckRequestV1,
    GatewayMailCheckResponseV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStatusV1,
    GatewayRequestCreateV1,
    GatewayStatusV1,
)
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.models import (
    DiscoveredAgentConflictResponse,
    DiscoveredAgentListResponse,
    DiscoveredAgentSummary,
    PassiveCurrentInstance,
    PassiveHealthResponse,
    PassiveShutdownResponse,
)
from houmao.passive_server.service import PassiveServerService


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
        version="0.1.0",
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

    @app.post("/houmao/agents/{agent_ref}/gateway/requests")
    def gateway_create_request(
        agent_ref: str, payload: GatewayRequestCreateV1
    ) -> GatewayAcceptedRequestV1:
        result = resolved_service.gateway_create_request(agent_ref, payload)
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

    @app.post("/houmao/agents/{agent_ref}/mail/reply")
    def gateway_mail_reply(
        agent_ref: str, payload: GatewayMailReplyRequestV1
    ) -> GatewayMailActionResponseV1:
        result = resolved_service.gateway_mail_reply(agent_ref, payload)
        if isinstance(result, tuple):
            return JSONResponse(status_code=result[0], content=result[1])  # type: ignore[return-value]
        return result

    return app
