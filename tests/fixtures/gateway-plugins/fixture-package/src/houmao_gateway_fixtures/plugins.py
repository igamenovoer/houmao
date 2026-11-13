"""Adversarial selected implementations using only the public plugin SDK."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import AsyncContextManager

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from houmao.gateway.plugins import PluginContext, PluginDefinition


class Configuration(BaseModel):
    """Accept no implicit service or credential configuration."""

    model_config = ConfigDict(extra="forbid", strict=True)


class FixturePlugin:
    """Create deterministic route and resource failures for host qualification."""

    def __init__(self) -> None:
        """Create a resource-free fixture instance."""

        self.m_router: APIRouter = APIRouter()
        self.m_context: PluginContext | None = None
        self.m_mode: str = "healthy"

    @classmethod
    def from_mode(cls, context: PluginContext, mode: str) -> FixturePlugin:
        """Stage fixture routes without activating capabilities."""

        plugin = cls()
        plugin.m_context = context
        plugin.m_mode = mode

        async def ping() -> dict[str, bool]:
            """Provide a route whose failure guard can be inspected."""

            return {"ok": True}

        plugin.m_router.add_api_route("/ping", ping, methods=["GET"])
        if mode == "conflicting":
            plugin.m_router.add_api_route("/items/{item}", ping, methods=["GET"])
            plugin.m_router.add_api_route("/items/fixed", ping, methods=["GET"])
        elif mode == "reserved":
            plugin.m_router.add_api_route("/_status", ping, methods=["GET"])
        return plugin

    @property
    def router(self) -> APIRouter:
        """Return the staged relative router."""

        return self.m_router

    def lifespan(self) -> AsyncContextManager[None]:
        """Return a host-owned resource lifespan."""

        return self._resources()

    @asynccontextmanager
    async def _resources(self) -> AsyncIterator[None]:
        """Inject startup or worker failure without a remote dependency."""

        assert self.m_context is not None
        if self.m_mode == "startup":
            raise RuntimeError("PRIVATE_FIXTURE_EXCEPTION_MUST_NOT_LEAK")
        self.m_context.report_connection("connected")
        if self.m_mode == "worker":
            self.m_context.workers.start_soon("broken-worker", self._broken_worker)
        yield

    async def _broken_worker(self) -> None:
        """Fail after activation so host worker supervision must react."""

        await asyncio.sleep(0.1)
        raise RuntimeError("PRIVATE_FIXTURE_EXCEPTION_MUST_NOT_LEAK")


def _binding(_configuration: Configuration) -> str:
    """Return one deterministic nonsecret fixture account."""

    return "fixture-account"


def _definition(mode: str, *, sdk_version: int = 1) -> PluginDefinition[Configuration]:
    """Create the advertised resource-free fixture definition."""

    return PluginDefinition(
        config_model=Configuration,
        binding_identity=_binding,
        create=lambda context, _config: FixturePlugin.from_mode(context, mode),
        sdk_version=sdk_version,
    )


conflicting = _definition("conflicting")
startup_failure = _definition("startup")
worker_failure = _definition("worker")
unsupported_sdk = _definition("healthy", sdk_version=99)
reserved_route = _definition("reserved")
