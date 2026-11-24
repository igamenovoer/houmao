"""FastAPI route registration for Houmao AG-UI attachment endpoints."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import json
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeVar

from ag_ui.core import BaseEvent, RunAgentInput, RunErrorEvent
from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from houmao.ag_ui.authoring import (
    AgUiEventPayload,
    HoumaoAgUiValidationError,
    parse_ag_ui_event_payloads,
    validate_ag_ui_event_sequence,
    validation_error_payload,
)
from houmao.ag_ui.authorization import (
    AG_UI,
    CLOSE,
    OBSERVE,
    PUBLISH,
    SUBMIT,
    UPDATE_DESTINATION,
    connection_resource,
    publish_resource,
    thread_resource,
)
from houmao.ag_ui.capabilities import AgUiCapabilityRuntime, build_ag_ui_capabilities
from houmao.ag_ui.connection import AgUiConnectionRegistry
from houmao.ag_ui.diagnostics import AgUiDiagnostics
from houmao.ag_ui.destination import (
    AgUiDestinationState,
    AgUiLastSentSource,
    AgUiThreadDestination,
)
from houmao.ag_ui.encoder import SSE_CONTENT_TYPE, encode_sse_comment, encode_sse_event
from houmao.ag_ui.event_hub import AgUiEventHub, AgUiEventSubscription, AgUiQueuedEvent
from houmao.ag_ui.models import (
    AgUiConnectInput,
    AgUiDetachResponse,
    AgUiDestinationStateResponse,
    AgUiEventPublishRequest,
    AgUiEventPublishResponse,
    AgUiSetActiveThreadRequest,
    AgUiStateSnapshotEvent,
    AgUiThreadDestinationResponse,
    HoumaoAgUiCapabilitiesResponse,
)
from houmao.ag_ui.runtime import AgUiRuntimeObservationProtocol
from houmao.ag_ui.service import AgUiAdmittedRun, AgUiRunService
from houmao.ag_ui.state import build_houmao_state_snapshot
from houmao.agents.realm_controller.gateway_models import GatewayRequestPayloadSubmitPromptV1
from houmao.gateway.authorization_models import AuthorizationDecision, Permission
from houmao.gateway.operations import OVERRIDE_MODEL, SELECT_SESSION

_DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 15.0
_DEFAULT_RUN_POLL_INTERVAL_SECONDS = 0.2
_ACCESS_REVALIDATION_SECONDS = 5.0


@dataclass(frozen=True)
class _ResolvedPublishDestination:
    """Resolved destination for one AG-UI publish request."""

    kind: Literal["message", "event", "connection", "active_thread", "default_sink"]
    thread_id: str | None
    run_id: str | None
    connection_id: str | None
    last_sent_source: AgUiLastSentSource


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
    access_current: Callable[[], bool] | None = None,
) -> AsyncIterator[str]:
    """Yield the AG-UI connect stream for one GUI attachment."""

    if not await _stream_access_current(access_current):
        return
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
        if not await _stream_access_current(access_current):
            detach_reason = "access_revoked"
            return
        yield encode_sse_event(AgUiStateSnapshotEvent(snapshot=snapshot))
        interval = (
            min(heartbeat_interval_seconds, _ACCESS_REVALIDATION_SECONDS)
            if access_current is not None
            else heartbeat_interval_seconds
        )
        while True:
            if await request.is_disconnected():
                detach_reason = "client_disconnected"
                break
            if subscription is None:
                await asyncio.sleep(interval)
                if await request.is_disconnected():
                    detach_reason = "client_disconnected"
                    break
                if not await _stream_access_current(access_current):
                    detach_reason = "access_revoked"
                    break
                yield encode_sse_comment("houmao ag-ui heartbeat")
                continue
            try:
                queued_event = await asyncio.wait_for(
                    subscription.queue.get(),
                    timeout=interval,
                )
            except TimeoutError:
                if await request.is_disconnected():
                    detach_reason = "client_disconnected"
                    break
                if not await _stream_access_current(access_current):
                    detach_reason = "access_revoked"
                    break
                yield encode_sse_comment("houmao ag-ui heartbeat")
                continue
            if not await _stream_access_current(access_current):
                detach_reason = "access_revoked"
                break
            yield encode_sse_event(queued_event.event, event_id=queued_event.event_id)
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
    access_current: Callable[[], bool] | None = None,
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
    guarded_events: AsyncGenerator[BaseEvent | AgUiQueuedEvent, None] | None = None
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
        guarded_events = _access_bound_events(event_source, access_current)
        async for stream_item in guarded_events:
            event, event_id = _stream_item_event(stream_item)
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
                yield encode_sse_event(event, event_id=event_id)
            except Exception as exc:
                outcome = "error"
                if diagnostics is not None:
                    diagnostics.stream_error(
                        stream_kind="run",
                        error_category=type(exc).__name__,
                        admitted_run=admitted_run,
                    )
                if await request.is_disconnected() or not await _stream_access_current(
                    access_current
                ):
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
        if not await request.is_disconnected() and await _stream_access_current(access_current):
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
        if guarded_events is not None:
            await guarded_events.aclose()


def register_ag_ui_routes(
    app: FastAPI,
    *,
    runtime: AgUiCapabilityRuntime | AgUiRuntimeObservationProtocol,
    registry: AgUiConnectionRegistry | None = None,
    event_hub: AgUiEventHub | None = None,
    event_log_path: Path | None = None,
    heartbeat_interval_seconds: float = _DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    run_poll_interval_seconds: float = _DEFAULT_RUN_POLL_INTERVAL_SECONDS,
    access_current: Callable[[Request], bool] | None = None,
    authorize_effects: Callable[[Request, tuple[Permission, ...]], AuthorizationDecision]
    | None = None,
    claim_effects: Callable[[AuthorizationDecision], None] | None = None,
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
    access_current:
        Verify the current authority held by the request's admitted stream.
    authorize_effects:
        Authorize exact effects after the handler resolves their destination.
    claim_effects:
        Fence immediate effects against concurrent changes to policy.

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
            resolved_event_hub = AgUiEventHub(
                agent_identity=_runtime_agent_identity(runtime),
                event_log_path=event_log_path,
            )
    app.state.ag_ui_event_hub = resolved_event_hub
    try:
        diagnostics = app.state.ag_ui_diagnostics
    except AttributeError:
        diagnostics = AgUiDiagnostics(runtime=runtime)
    app.state.ag_ui_diagnostics = diagnostics
    try:
        destination_state = app.state.ag_ui_destination_state
    except AttributeError:
        destination_state = AgUiDestinationState()
    app.state.ag_ui_destination_state = destination_state

    router = APIRouter(prefix="/v1/ag-ui")

    def _admit_immediate(request: Request, permission: Permission) -> None:
        """Authorize and fence an effect that the handler applies immediately."""

        if authorize_effects is not None:
            grant = authorize_effects(request, (permission,))
            if claim_effects is not None:
                claim_effects(grant)
            request.state.gateway_grant = grant

    @router.get("/capabilities", response_model=HoumaoAgUiCapabilitiesResponse)
    def _capabilities() -> HoumaoAgUiCapabilitiesResponse:
        """Serve conservative AG-UI capability discovery."""

        return build_ag_ui_capabilities(runtime, replay_enabled=resolved_event_hub.replay_enabled)

    @router.post("/connect")
    async def _connect(request: Request, request_payload: AgUiConnectInput) -> StreamingResponse:
        """Attach one GUI client and stream the initial state snapshot."""

        if authorize_effects is not None:
            await asyncio.to_thread(
                _admit_immediate,
                request,
                Permission(resource=thread_resource(request_payload.thread_id), action=OBSERVE),
            )
        stream = connect_event_stream(
            runtime=runtime,
            registry=resolved_registry,
            connect_input=request_payload,
            request=request,
            diagnostics=diagnostics,
            event_hub=resolved_event_hub,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            access_current=_request_access_check(request, access_current),
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
    def _disconnect(request: Request, connection_id: str) -> AgUiDetachResponse | JSONResponse:
        """Detach one GUI connection without touching the Houmao agent lifecycle."""

        _admit_immediate(
            request, Permission(resource=connection_resource(connection_id), action=CLOSE)
        )
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
        if authorize_effects is None:
            admitted_run = service.admit_run(request_payload)
        else:
            authorize = authorize_effects
            thread = thread_resource(request_payload.thread_id)
            observe = Permission(resource=thread, action=OBSERVE)
            submit = Permission(resource=thread, action=SUBMIT)

            def _authorize_run(
                payload: GatewayRequestPayloadSubmitPromptV1,
            ) -> AuthorizationDecision:
                """Check both run effects and any explicit native selection."""

                permissions = [submit, observe]
                if payload.chat_session is not None:
                    permissions.append(SELECT_SESSION)
                if payload.execution is not None:
                    permissions.append(OVERRIDE_MODEL)
                grant = authorize(request, tuple(permissions))
                request.state.gateway_grant = grant.model_copy(update={"permissions": (observe,)})
                return grant

            admitted_run = await asyncio.to_thread(
                service.admit_run, request_payload, authorize=_authorize_run
            )
        diagnostics.run_admitted(admitted_run)
        stream = run_event_stream(
            service=service,
            admitted_run=admitted_run,
            request=request,
            diagnostics=diagnostics,
            event_hub=resolved_event_hub,
            access_current=_request_access_check(request, access_current),
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
        request: Request,
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

        destination = _resolve_publish_destination(
            normalized_events=normalized_events,
            request_payload=request_payload,
            registry=resolved_registry,
            destination_state=destination_state,
        )
        if authorize_effects is not None:
            await asyncio.to_thread(
                _admit_immediate,
                request,
                Permission(
                    resource=publish_resource(
                        thread_id=destination.thread_id,
                        run_id=destination.run_id,
                        connection_id=destination.connection_id,
                    ),
                    action=PUBLISH,
                ),
            )
        if destination.kind == "default_sink":
            diagnostics.events_publish_default_sink(
                accepted_count=len(parsed_events),
                reason="no_destination",
            )
            return AgUiEventPublishResponse(
                accepted_count=len(parsed_events),
                stored_count=0,
                delivered_count=0,
                replay="none",
                destination_kind="default_sink",
                warnings=["default_sink_due_to_no_destination"],
            )
        publish_result = resolved_event_hub.publish(
            parsed_events,
            thread_id=destination.thread_id,
            run_id=destination.run_id,
            connection_id=destination.connection_id,
        )
        if destination.thread_id is not None:
            destination_state.set_last_sent_thread(
                destination.thread_id,
                source=destination.last_sent_source,
            )
        diagnostics.events_publish_accepted(
            thread_id=destination.thread_id,
            run_id=destination.run_id,
            connection_id=destination.connection_id,
            accepted_count=publish_result.accepted_count,
            stored_count=publish_result.stored_count,
            delivered_count=publish_result.delivered_count,
            replay=publish_result.replay,
        )
        return AgUiEventPublishResponse(
            accepted_count=publish_result.accepted_count,
            stored_count=publish_result.stored_count,
            delivered_count=publish_result.delivered_count,
            replay=publish_result.replay,
            thread_id=destination.thread_id,
            run_id=destination.run_id,
            connection_id=destination.connection_id,
            destination_kind=None if destination.kind == "message" else destination.kind,
        )

    @router.get(
        "/destination",
        response_model=AgUiDestinationStateResponse,
        response_model_exclude_none=True,
    )
    def _destination() -> AgUiDestinationStateResponse:
        """Return gateway-local AG-UI destination fallback state."""

        return _destination_state_response(destination_state)

    @router.get(
        "/active-thread",
        response_model=AgUiThreadDestinationResponse,
        response_model_exclude_none=True,
    )
    def _active_thread() -> AgUiThreadDestinationResponse:
        """Return the current GUI-selected active AG-UI thread."""

        return _thread_destination_response(destination_state.active_thread)

    @router.put(
        "/active-thread",
        response_model=AgUiThreadDestinationResponse,
        response_model_exclude_none=True,
    )
    def _set_active_thread(
        request: Request,
        request_payload: AgUiSetActiveThreadRequest,
    ) -> AgUiThreadDestinationResponse | JSONResponse:
        """Set the current GUI-selected active AG-UI thread."""

        try:
            thread_id = request_payload.thread_id.strip()
            if not thread_id:
                raise ValueError("active AG-UI thread id must be non-empty.")
            _admit_immediate(
                request,
                Permission(resource=thread_resource(thread_id), action=UPDATE_DESTINATION),
            )
            state = destination_state.set_active_thread(
                thread_id,
                source=request_payload.source,
            )
        except ValueError as exc:
            return JSONResponse(
                status_code=422,
                content={
                    "ok": False,
                    "code": "ag_ui_active_thread_invalid",
                    "message": str(exc),
                },
            )
        return _thread_destination_response(state)

    @router.delete(
        "/active-thread",
        response_model=AgUiThreadDestinationResponse,
        response_model_exclude_none=True,
    )
    def _clear_active_thread(
        request: Request,
        thread_id: str | None = Query(default=None, alias="threadId"),
    ) -> AgUiThreadDestinationResponse:
        """Clear the active AG-UI thread if the optional expected thread still matches."""

        def _admit_clear(current: str | None) -> None:
            """Authorize against the active thread held by the clear operation."""

            resource = thread_resource(current) if current is not None else AG_UI
            _admit_immediate(request, Permission(resource=resource, action=UPDATE_DESTINATION))

        return _thread_destination_response(
            destination_state.clear_active_thread(
                expected_thread_id=thread_id,
                authorize=_admit_clear if authorize_effects is not None else None,
            )
        )

    app.include_router(router)
    return resolved_registry


def _request_access_check(
    request: Request, access_current: Callable[[Request], bool] | None
) -> Callable[[], bool] | None:
    """Bind a revalidation callback to one admitted connection."""

    if access_current is None:
        return None
    return lambda: access_current(request)


async def _stream_access_current(access_current: Callable[[], bool] | None) -> bool:
    """Read current stream authority without blocking other requests."""

    return access_current is None or await asyncio.to_thread(access_current)


async def _access_bound_events(
    source: AsyncIterator[BaseEvent | AgUiQueuedEvent],
    access_current: Callable[[], bool] | None,
) -> AsyncGenerator[BaseEvent | AgUiQueuedEvent, None]:
    """Recheck before emission and periodically while an event is pending."""

    pending: asyncio.Task[BaseEvent | AgUiQueuedEvent] | None = None
    try:
        if access_current is None:
            async for item in source:
                yield item
            return
        while await _stream_access_current(access_current):
            if pending is None:
                pending = asyncio.create_task(_next_stream_event(source))
            done, _ = await asyncio.wait({pending}, timeout=_ACCESS_REVALIDATION_SECONDS)
            if not done:
                continue
            if not await _stream_access_current(access_current):
                return
            try:
                yield pending.result()
            except StopAsyncIteration:
                return
            pending = None
    finally:
        if pending is not None:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        source_close = getattr(source, "aclose", None)
        if callable(source_close):
            await source_close()


async def _merged_run_events(
    *,
    service: AgUiRunService,
    admitted_run: AgUiAdmittedRun,
    request: AgUiDisconnectProbe,
    subscription: AgUiEventSubscription,
) -> AsyncIterator[BaseEvent | AgUiQueuedEvent]:
    """Yield service events and matching agent-published events until the run ends."""

    source = service.stream_run_events(admitted_run=admitted_run, request=request)
    source_task: asyncio.Task[BaseEvent] = asyncio.create_task(_next_stream_event(source))
    published_task: asyncio.Task[AgUiQueuedEvent] = asyncio.create_task(subscription.queue.get())
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
        await asyncio.gather(source_task, published_task, return_exceptions=True)
        source_close = getattr(source, "aclose", None)
        if callable(source_close):
            with suppress(Exception):
                await source_close()


_StreamEventT = TypeVar("_StreamEventT", bound=BaseEvent | AgUiQueuedEvent)


async def _next_stream_event(source: AsyncIterator[_StreamEventT]) -> _StreamEventT:
    """Return the next event from one async iterator."""

    return await anext(source)


def _stream_item_event(item: BaseEvent | AgUiQueuedEvent) -> tuple[BaseEvent, str | None]:
    """Return the event payload and optional SSE id from a stream item."""

    if isinstance(item, AgUiQueuedEvent):
        return item.event, item.event_id
    return item, None


def _single_event_thread_id(events: list[AgUiEventPayload]) -> str | None:
    """Return one shared event-level thread id, if every present value agrees."""

    thread_ids = {
        thread_id
        for event in events
        if isinstance((thread_id := event.get("threadId")), str) and thread_id.strip()
    }
    if len(thread_ids) == 1:
        return next(iter(thread_ids))
    return None


def _resolve_publish_destination(
    *,
    normalized_events: list[AgUiEventPayload],
    request_payload: AgUiEventPublishRequest,
    registry: AgUiConnectionRegistry,
    destination_state: AgUiDestinationState,
) -> _ResolvedPublishDestination:
    """Resolve the destination for one validated publish request."""

    if request_payload.connection_id is not None:
        record = registry.get(request_payload.connection_id)
        return _ResolvedPublishDestination(
            kind="connection",
            thread_id=record.thread_id if record is not None else None,
            run_id=record.run_id if record is not None else request_payload.run_id,
            connection_id=request_payload.connection_id,
            last_sent_source="connection",
        )
    if request_payload.thread_id is not None or request_payload.run_id is not None:
        return _ResolvedPublishDestination(
            kind="message",
            thread_id=request_payload.thread_id,
            run_id=request_payload.run_id,
            connection_id=None,
            last_sent_source="explicit",
        )
    event_thread_id = _single_event_thread_id(normalized_events)
    if event_thread_id is not None:
        return _ResolvedPublishDestination(
            kind="event",
            thread_id=event_thread_id,
            run_id=None,
            connection_id=None,
            last_sent_source="event",
        )
    active_thread, _last_sent = destination_state.snapshot()
    if active_thread.thread_id is not None:
        return _ResolvedPublishDestination(
            kind="active_thread",
            thread_id=active_thread.thread_id,
            run_id=None,
            connection_id=None,
            last_sent_source="active_thread",
        )
    return _ResolvedPublishDestination(
        kind="default_sink",
        thread_id=None,
        run_id=None,
        connection_id=None,
        last_sent_source="explicit",
    )


def _destination_state_response(
    state: AgUiDestinationState,
) -> AgUiDestinationStateResponse:
    """Return a serializable destination fallback state response."""

    active_thread, last_sent = state.snapshot()
    return AgUiDestinationStateResponse(
        active_thread=_thread_destination_response(active_thread),
        last_sent_thread=_thread_destination_response(last_sent),
    )


def _thread_destination_response(
    state: AgUiThreadDestination,
) -> AgUiThreadDestinationResponse:
    """Return a serializable destination state slot response."""

    return AgUiThreadDestinationResponse(
        status=state.status,
        thread_id=state.thread_id,
        updated_at_utc=(
            state.updated_at_utc.isoformat().replace("+00:00", "Z")
            if state.updated_at_utc is not None
            else None
        ),
        source=state.source,
    )


def _runtime_agent_identity(
    runtime: AgUiCapabilityRuntime | AgUiRuntimeObservationProtocol,
) -> str:
    """Return a safe runtime identity for route-owned helper metadata."""

    try:
        status = runtime.status()
    except Exception:
        return "gateway"
    attach_identity = getattr(status, "attach_identity", None)
    if attach_identity is None:
        return "gateway"
    text = str(attach_identity).strip()
    return text or "gateway"


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
    event_thread_ids = {
        event_thread_id
        for event in events
        if isinstance((event_thread_id := event.get("threadId")), str) and event_thread_id.strip()
    }
    if thread_id is None and connection_id is None and len(event_thread_ids) > 1:
        raise HoumaoAgUiValidationError(
            "AG-UI event batch has multiple event-level thread ids.",
            repair_hint="Publish one thread at a time or pass an explicit --thread-id route.",
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
