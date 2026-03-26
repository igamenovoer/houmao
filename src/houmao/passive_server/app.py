"""FastAPI application factory for ``houmao-passive-server``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

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

    return app
