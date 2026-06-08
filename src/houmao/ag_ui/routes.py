"""FastAPI route registration for Houmao AG-UI attachment endpoints."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol

from ag_ui.core import RunAgentInput
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from houmao.ag_ui.capabilities import AgUiCapabilityRuntime, build_ag_ui_capabilities
from houmao.ag_ui.connection import AgUiConnectionRegistry
from houmao.ag_ui.encoder import SSE_CONTENT_TYPE, encode_sse_comment, encode_sse_event
from houmao.ag_ui.models import (
    AgUiConnectInput,
    AgUiDetachResponse,
    AgUiStateSnapshotEvent,
    HoumaoAgUiCapabilitiesResponse,
)
from houmao.ag_ui.runtime import AgUiRuntimeObservationProtocol
from houmao.ag_ui.service import AgUiAdmittedRun, AgUiRunService
from houmao.ag_ui.state import build_houmao_state_snapshot

_DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 15.0
_DEFAULT_RUN_POLL_INTERVAL_SECONDS = 0.2


class AgUiDisconnectProbe(Protocol):
    """Subset of FastAPI request state needed by AG-UI stream generators."""

    async def is_disconnected(self) -> bool:
        """Return whether the HTTP client disconnected."""


async def connect_event_stream(
    *,
    runtime: AgUiCapabilityRuntime,
    registry: AgUiConnectionRegistry,
    connect_input: AgUiConnectInput,
    request: AgUiDisconnectProbe,
    heartbeat_interval_seconds: float = _DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
) -> AsyncIterator[str]:
    """Yield the AG-UI connect stream for one GUI attachment."""

    record = registry.create_from_input(connect_input)
    try:
        snapshot = build_houmao_state_snapshot(
            status=runtime.status(),
            connection=record,
        )
        yield encode_sse_event(AgUiStateSnapshotEvent(snapshot=snapshot))
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(heartbeat_interval_seconds)
            if await request.is_disconnected():
                break
            yield encode_sse_comment("houmao ag-ui heartbeat")
    finally:
        registry.detach(record.connection_id)


async def run_event_stream(
    *,
    service: AgUiRunService,
    admitted_run: AgUiAdmittedRun,
    request: AgUiDisconnectProbe,
) -> AsyncIterator[str]:
    """Yield encoded AG-UI SSE frames for one admitted run."""

    async for event in service.stream_run_events(admitted_run=admitted_run, request=request):
        yield encode_sse_event(event)


def register_ag_ui_routes(
    app: FastAPI,
    *,
    runtime: AgUiCapabilityRuntime | AgUiRuntimeObservationProtocol,
    registry: AgUiConnectionRegistry | None = None,
    heartbeat_interval_seconds: float = _DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    run_poll_interval_seconds: float = _DEFAULT_RUN_POLL_INTERVAL_SECONDS,
) -> AgUiConnectionRegistry:
    """Register AG-UI attachment routes on one FastAPI app.

    Parameters
    ----------
    app:
        FastAPI app or router-backed application serving the live gateway.
    runtime:
        Gateway runtime that owns the observed Houmao agent.
    registry:
        Optional registry override used by tests.
    heartbeat_interval_seconds:
        Delay between SSE comment heartbeats after the initial snapshot.

    Returns
    -------
    AgUiConnectionRegistry
        Registry backing the registered AG-UI routes.
    """

    resolved_registry = registry
    if resolved_registry is None:
        try:
            resolved_registry = app.state.ag_ui_connection_registry
        except AttributeError:
            resolved_registry = AgUiConnectionRegistry()
    app.state.ag_ui_connection_registry = resolved_registry

    router = APIRouter(prefix="/v1/ag-ui")

    @router.get("/capabilities", response_model=HoumaoAgUiCapabilitiesResponse)
    def _capabilities() -> HoumaoAgUiCapabilitiesResponse:
        """Serve conservative AG-UI capability discovery."""

        return build_ag_ui_capabilities(runtime)

    @router.post("/connect")
    async def _connect(request: Request, request_payload: AgUiConnectInput) -> StreamingResponse:
        """Attach one GUI client and stream the initial state snapshot."""

        stream = connect_event_stream(
            runtime=runtime,
            registry=resolved_registry,
            connect_input=request_payload,
            request=request,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        return StreamingResponse(
            stream,
            media_type=SSE_CONTENT_TYPE,
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @router.delete(
        "/connections/{connection_id}",
        response_model=AgUiDetachResponse,
        responses={404: {"model": AgUiDetachResponse}},
    )
    def _disconnect(connection_id: str) -> AgUiDetachResponse | JSONResponse:
        """Detach one GUI connection without touching the Houmao agent lifecycle."""

        detached = resolved_registry.detach(connection_id)
        if detached is None:
            response = AgUiDetachResponse(
                status="not_found",
                connection_id=connection_id,
                detached=False,
                detail="AG-UI connection is unknown or already detached.",
            )
            return JSONResponse(
                status_code=404,
                content=response.model_dump(mode="json", by_alias=True),
            )
        return AgUiDetachResponse(
            status="detached",
            connection_id=connection_id,
            detached=True,
            detail="AG-UI connection detached. Houmao agent lifecycle was not modified.",
        )

    @router.post(
        "/runs",
    )
    async def _runs(request: Request, request_payload: RunAgentInput) -> StreamingResponse:
        """Admit one AG-UI run and stream mapped Houmao output."""

        service = AgUiRunService(
            runtime=runtime,  # type: ignore[arg-type]
            poll_interval_seconds=run_poll_interval_seconds,
        )
        admitted_run = service.admit_run(request_payload)
        stream = run_event_stream(service=service, admitted_run=admitted_run, request=request)
        return StreamingResponse(
            stream,
            media_type=SSE_CONTENT_TYPE,
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    app.include_router(router)
    return resolved_registry
