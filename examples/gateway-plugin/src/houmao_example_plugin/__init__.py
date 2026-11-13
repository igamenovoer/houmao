"""An independently packaged example of the public gateway plugin SDK."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import AsyncContextManager

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from houmao.gateway.plugins import (
    PluginContext,
    PluginDefinition,
    PluginDispatchError,
    PluginDispatchResult,
    PluginEvent,
)


class NotificationConfiguration(BaseModel):
    """Select the instance's fixed service account and credential requirement."""

    model_config = ConfigDict(extra="forbid", strict=True)

    account: str = Field(min_length=1, max_length=128)
    require_credentials: bool = False


class RefreshRequest(BaseModel):
    """Request refresh of the existing selected source without overrides."""

    model_config = ConfigDict(extra="forbid", strict=True)


class NotificationPlugin:
    """Expose owner inspection and immediate notification delivery.

    The example treats ``account`` as an already provisioned service identity.
    Its heartbeat demonstrates a supervised connection worker without creating
    a second messaging service or requiring a provider endpoint.
    """

    def __init__(self) -> None:
        """Create a resource-free plugin instance."""

        self.m_context: PluginContext | None = None
        self.m_configuration: NotificationConfiguration | None = None
        self.m_router: APIRouter = APIRouter()

    @classmethod
    def from_config(
        cls, context: PluginContext, configuration: NotificationConfiguration
    ) -> NotificationPlugin:
        """Prepare routes without reading credentials or starting workers."""

        plugin = cls()
        plugin.m_context = context
        plugin.m_configuration = configuration

        @plugin.m_router.get("/owner")
        async def owner() -> dict[str, str]:
            """Return fixed public identities rather than caller-selected senders."""

            return {
                "agent_id": context.owner.agent_id,
                "runtime_session_id": context.owner.runtime_session_id,
                "instance_id": context.instance_id,
                "binding_id": context.binding_id,
                "account": configuration.account,
            }

        @plugin.m_router.post("/notify", response_model=PluginDispatchResult)
        async def notify(event: PluginEvent) -> PluginDispatchResult:
            """Dispatch now or propagate the failure to the sender."""

            try:
                result = await context.events.dispatch(event)
            except PluginDispatchError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
            # Save only the successful source cursor, never a message/retry spool.
            context.state.path("last-dispatched-id.txt").write_text(
                event.source_event_id + "\n", encoding="utf-8"
            )
            return result

        @plugin.m_router.post("/refresh-credentials")
        async def refresh_credentials(_request: RefreshRequest) -> dict[str, bool]:
            """Reopen only the already selected credential source."""

            if configuration.require_credentials:
                plugin._validate_credentials()
            return {"refreshed": configuration.require_credentials}

        return plugin

    @property
    def router(self) -> APIRouter:
        """Return relative routes for host namespace validation."""

        return self.m_router

    def lifespan(self) -> AsyncContextManager[None]:
        """Return the resource lifespan controlled by the gateway host."""

        return self._resource_lifespan()

    @asynccontextmanager
    async def _resource_lifespan(self) -> AsyncIterator[None]:
        """Validate the selected identity and start a cooperative worker."""

        assert self.m_context is not None
        assert self.m_configuration is not None
        if self.m_configuration.require_credentials:
            self._validate_credentials()
        self.m_context.report_connection("connected")
        self.m_context.workers.start_soon("heartbeat", self._heartbeat)
        yield

    async def _heartbeat(self) -> None:
        """Demonstrate a cancellable worker without retaining message payloads."""

        assert self.m_context is not None
        while True:
            await asyncio.sleep(30)
            self.m_context.log("example_heartbeat", fields={"alive": True})

    def _validate_credentials(self) -> None:
        """Verify the selected document belongs to the configured account."""

        assert self.m_context is not None
        assert self.m_configuration is not None
        credentials = self.m_context.credentials.read()
        if credentials.get("account") != self.m_configuration.account:
            raise ValueError("Selected credentials do not match the configured service account")


def _binding_identity(configuration: NotificationConfiguration) -> str:
    """Keep account identity stable across restarts and credential rotation."""

    return "example-account:" + configuration.account


definition = PluginDefinition(
    config_model=NotificationConfiguration,
    binding_identity=_binding_identity,
    create=NotificationPlugin.from_config,
    sdk_version=1,
)
