"""FastAPI application factory for ``houmao-passive-server``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.models import (
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

    return app
