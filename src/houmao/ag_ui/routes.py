"""FastAPI route registration for Houmao AG-UI attachment endpoints."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import json
from collections.abc import AsyncIterator
from typing import Protocol

from ag_ui.core import BaseEvent, RunAgentInput, RunErrorEvent
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from houmao.ag_ui.authoring import (
    AgUiEventPayload,
    HoumaoAgUiValidationError,
    parse_ag_ui_event_payloads,
    validate_ag_ui_event_sequence,
    validation_error_payload,
)
from houmao.ag_ui.capabilities import AgUiCapabilityRuntime, build_ag_ui_capabilities
from houmao.ag_ui.connection import AgUiConnectionRegistry
from houmao.ag_ui.diagnostics import AgUiDiagnostics
from houmao.ag_ui.encoder import SSE_CONTENT_TYPE, encode_sse_comment, encode_sse_event
from houmao.ag_ui.event_hub import AgUiEventHub, AgUiEventSubscription
from houmao.ag_ui.models import (
    AgUiConnectInput,
    AgUiDetachResponse,
    AgUiEventPublishRequest,
    AgUiEventPublishResponse,
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
    diagnostics: AgUiDiagnostics | None = None,
    event_hub: AgUiEventHub | None = None,
    heartbeat_interval_seconds: float = _DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
) -> AsyncIterator[str]:
    """Yield the AG-UI connect stream for one GUI attachment."""

    record = registry.create_from_input(connect_input)
    subscription = event_hub.subscribe_connection(record) if event_hub is not None else None
    if diagnostics is not None:
        diagnostics.connection_started(record)
    detach_reason = "stream_closed"
    try:
        snapshot = build_houmao_state_snapshot(
            status=runtime.status(),
            connection=record,
        )
        yield encode_sse_event(AgUiStateSnapshotEvent(snapshot=snapshot))
        while True:
            if await request.is_disconnected():
                detach_reason = "client_disconnected"
                break
            if subscription is None:
                await asyncio.sleep(heartbeat_interval_seconds)
                if await request.is_disconnected():
                    detach_reason = "client_disconnected"
                    break
                yield encode_sse_comment("houmao ag-ui heartbeat")
                continue
            try:
                event = await asyncio.wait_for(
                    subscription.queue.get(),
                    timeout=heartbeat_interval_seconds,
                )
            except TimeoutError:
                if await request.is_disconnected():
                    detach_reason = "client_disconnected"
                    break
                yield encode_sse_comment("houmao ag-ui heartbeat")
                continue
            yield encode_sse_event(event)
    except Exception as exc:
        detach_reason = "stream_error"
        if diagnostics is not None:
            diagnostics.stream_error(
                stream_kind="connect",
                error_category=type(exc).__name__,
                connection=record,
            )
        raise
    finally:
        if subscription is not None and event_hub is not None:
            event_hub.unsubscribe(subscription.subscription_id)
        registry.detach(record.connection_id)
        if diagnostics is not None:
            diagnostics.connection_detached(record, reason=detach_reason)


async def run_event_stream(
    *,
    service: AgUiRunService,
    admitted_run: AgUiAdmittedRun,
    request: AgUiDisconnectProbe,
    diagnostics: AgUiDiagnostics | None = None,
    event_hub: AgUiEventHub | None = None,
) -> AsyncIterator[str]:
    """Yield encoded AG-UI SSE frames for one admitted run."""

    if diagnostics is not None:
        diagnostics.run_stream_started(admitted_run)
    outcome = "detached"
    subscription = (
        event_hub.subscribe(
            thread_id=admitted_run.run_input.thread_id,
            run_id=admitted_run.run_input.run_id,
        )
        if event_hub is not None
        else None
    )
    try:
        event_source = (
            service.stream_run_events(admitted_run=admitted_run, request=request)
            if subscription is None
            else _merged_run_events(
                service=service,
                admitted_run=admitted_run,
                request=request,
                subscription=subscription,
            )
        )
        async for event in event_source:
            event_payload = _event_payload(event)
            event_type = _event_type_from_payload(event_payload)
            if event_type == "RUN_FINISHED":
                outcome = "finished"
            elif event_type == "RUN_ERROR":
                outcome = "error"
                code = event_payload.get("code")
                if diagnostics is not None and code == "houmao_run_stream_failed":
                    diagnostics.stream_error(
                        stream_kind="run",
                        error_category=str(code),
                        admitted_run=admitted_run,
                    )
            try:
                yield encode_sse_event(event)
            except Exception as exc:
                outcome = "error"
                if diagnostics is not None:
                    diagnostics.stream_error(
                        stream_kind="run",
                        error_category=type(exc).__name__,
                        admitted_run=admitted_run,
                    )
                if await request.is_disconnected():
                    if diagnostics is not None:
                        diagnostics.run_client_disconnected(admitted_run)
                    return
                yield _encoded_run_error_frame(
                    message="AG-UI run stream failed after admission.",
                    code="houmao_run_stream_failed",
                )
                return
        if outcome == "detached" and await request.is_disconnected():
            if diagnostics is not None:
                diagnostics.run_client_disconnected(admitted_run)
    except Exception as exc:
        outcome = "error"
        if diagnostics is not None:
            diagnostics.stream_error(
                stream_kind="run",
                error_category=type(exc).__name__,
                admitted_run=admitted_run,
            )
        if not await request.is_disconnected():
            yield _encoded_run_error_frame(
                message="AG-UI run stream failed after admission.",
                code="houmao_run_stream_failed",
            )
        else:
            if diagnostics is not None:
                diagnostics.run_client_disconnected(admitted_run)
    finally:
        if subscription is not None and event_hub is not None:
            event_hub.unsubscribe(subscription.subscription_id)
        if diagnostics is not None:
            diagnostics.run_stream_completed(admitted_run, outcome=outcome)


def register_ag_ui_routes(
    app: FastAPI,
    *,
    runtime: AgUiCapabilityRuntime | AgUiRuntimeObservationProtocol,
    registry: AgUiConnectionRegistry | None = None,
    event_hub: AgUiEventHub | None = None,
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
    resolved_event_hub = event_hub
    if resolved_event_hub is None:
        try:
            resolved_event_hub = app.state.ag_ui_event_hub
        except AttributeError:
            resolved_event_hub = AgUiEventHub()
    app.state.ag_ui_event_hub = resolved_event_hub
    try:
        diagnostics = app.state.ag_ui_diagnostics
    except AttributeError:
        diagnostics = AgUiDiagnostics(runtime=runtime)
    app.state.ag_ui_diagnostics = diagnostics

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
            diagnostics=diagnostics,
            event_hub=resolved_event_hub,
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
        diagnostics.explicit_disconnect(
            connection_id=connection_id,
            detached=detached is not None,
        )
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
        diagnostics.run_admitted(admitted_run)
        stream = run_event_stream(
            service=service,
            admitted_run=admitted_run,
            request=request,
            diagnostics=diagnostics,
            event_hub=resolved_event_hub,
        )
        return StreamingResponse(
            stream,
            media_type=SSE_CONTENT_TYPE,
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post(
        "/events",
        response_model=AgUiEventPublishResponse,
        response_model_exclude_none=True,
    )
    async def _events(
        request_payload: AgUiEventPublishRequest,
    ) -> AgUiEventPublishResponse | JSONResponse:
        """Accept already-standard AG-UI events and fan them out to matching streams."""

        try:
            normalized_events = validate_ag_ui_event_sequence(request_payload.events)
            _validate_publish_routing(
                events=normalized_events,
                thread_id=request_payload.thread_id,
                run_id=request_payload.run_id,
                connection_id=request_payload.connection_id,
            )
            parsed_events = parse_ag_ui_event_payloads(normalized_events)
        except HoumaoAgUiValidationError as exc:
            diagnostics.events_publish_rejected(
                thread_id=request_payload.thread_id,
                run_id=request_payload.run_id,
                connection_id=request_payload.connection_id,
                event_count=(
                    len(request_payload.events)
                    if isinstance(request_payload.events, list)
                    else None
                ),
                rejection_reason=_publish_rejection_reason(exc),
            )
            return JSONResponse(
                status_code=422,
                content=validation_error_payload(exc),
            )

        delivered_count = resolved_event_hub.publish(
            parsed_events,
            thread_id=request_payload.thread_id,
            run_id=request_payload.run_id,
            connection_id=request_payload.connection_id,
        )
        diagnostics.events_publish_accepted(
            thread_id=request_payload.thread_id,
            run_id=request_payload.run_id,
            connection_id=request_payload.connection_id,
            accepted_count=len(parsed_events),
            delivered_count=delivered_count,
        )
        return AgUiEventPublishResponse(
            accepted_count=len(parsed_events),
            delivered_count=delivered_count,
            thread_id=request_payload.thread_id,
            run_id=request_payload.run_id,
            connection_id=request_payload.connection_id,
        )

    app.include_router(router)
    return resolved_registry


async def _merged_run_events(
    *,
    service: AgUiRunService,
    admitted_run: AgUiAdmittedRun,
    request: AgUiDisconnectProbe,
    subscription: AgUiEventSubscription,
) -> AsyncIterator[BaseEvent]:
    """Yield service events and matching agent-published events until the run ends."""

    source = service.stream_run_events(admitted_run=admitted_run, request=request)
    source_task: asyncio.Task[BaseEvent] = asyncio.create_task(_next_stream_event(source))
    published_task: asyncio.Task[BaseEvent] = asyncio.create_task(subscription.queue.get())
    try:
        while True:
            done, _pending = await asyncio.wait(
                {source_task, published_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if source_task in done:
                try:
                    yield source_task.result()
                except StopAsyncIteration:
                    return
                source_task = asyncio.create_task(_next_stream_event(source))
            if published_task in done:
                yield published_task.result()
                published_task = asyncio.create_task(subscription.queue.get())
    finally:
        for task in (source_task, published_task):
            task.cancel()
        source_close = getattr(source, "aclose", None)
        if callable(source_close):
            with suppress(Exception):
                await source_close()


async def _next_stream_event(source: AsyncIterator[BaseEvent]) -> BaseEvent:
    """Return the next event from one async iterator."""

    return await anext(source)


def _validate_publish_routing(
    *,
    events: list[AgUiEventPayload],
    thread_id: str | None,
    run_id: str | None,
    connection_id: str | None,
) -> None:
    """Validate explicit gateway fanout routing metadata for one publish batch."""

    if not events:
        raise HoumaoAgUiValidationError(
            "AG-UI publish requires at least one event.",
            repair_hint="Render a component first or provide a non-empty AG-UI event batch.",
        )
    if thread_id is None and run_id is None and connection_id is None:
        raise HoumaoAgUiValidationError(
            "AG-UI publish requires `threadId`, `runId`, or `connectionId` routing.",
            repair_hint="Pass --thread-id, --run-id, or --connection-id to the publish command.",
        )
    for index, event in enumerate(events):
        event_thread_id = event.get("threadId")
        if thread_id is not None and event_thread_id is not None and event_thread_id != thread_id:
            raise HoumaoAgUiValidationError(
                "AG-UI event thread routing conflicts with the publish route.",
                event_index=index,
                field_paths=["threadId"],
            )
        event_run_id = event.get("runId")
        if run_id is not None and event_run_id is not None and event_run_id != run_id:
            raise HoumaoAgUiValidationError(
                "AG-UI event run routing conflicts with the publish route.",
                event_index=index,
                field_paths=["runId"],
            )


def _publish_rejection_reason(exc: HoumaoAgUiValidationError) -> str:
    """Return a compact diagnostic category for a publish rejection."""

    if exc.event_index is not None:
        return "invalid_event"
    if "batch" in str(exc).lower():
        return "invalid_batch"
    if "routing" in str(exc).lower():
        return "invalid_routing"
    return "invalid_request"


def _event_payload(event: BaseEvent) -> dict[str, object]:
    """Return one event payload for diagnostic type inspection."""

    return event.model_dump(mode="json", by_alias=True, exclude_none=True)


def _event_type_from_payload(payload: dict[str, object]) -> str:
    """Return the AG-UI event type without exposing event content."""

    event_type = payload.get("type")
    if isinstance(event_type, str):
        return event_type
    return "UNKNOWN"


def _encoded_run_error_frame(*, message: str, code: str) -> str:
    """Return a RUN_ERROR frame, falling back to raw JSON if model encoding fails."""

    try:
        return encode_sse_event(RunErrorEvent(message=message, code=code))
    except Exception:
        payload = {"type": "RUN_ERROR", "message": message, "code": code}
        return f"data: {json.dumps(payload, sort_keys=True)}\n\n"
