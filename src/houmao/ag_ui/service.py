"""AG-UI run admission and stream orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from ag_ui.core import BaseEvent, RunAgentInput
from fastapi import HTTPException
from pydantic import ValidationError

from houmao.ag_ui.mapper import AgUiEventMapper
from houmao.ag_ui.prompt import (
    AgUiPromptConversion,
    AgUiPromptConversionError,
    convert_run_agent_input,
)
from houmao.ag_ui.runtime import (
    AgUiObservedRequestState,
    AgUiRuntimeObservationProtocol,
    AgUiTargetTransportFamily,
)
from houmao.ag_ui.state import JsonObject
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayChatSessionSelectorV1,
    GatewayExecutionOverrideV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayWebControlStateV1,
    GatewayWebExecutionIdentityV1,
)
from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.backends.headless_output import (
    CanonicalHeadlessEvent,
    load_canonical_headless_events,
)


class AgUiRunDisconnectProbe(Protocol):
    """Subset of request disconnect state needed by AG-UI run streams."""

    async def is_disconnected(self) -> bool:
        """Return whether the HTTP client disconnected."""


@dataclass(frozen=True)
class AgUiAdmittedRun:
    """One AG-UI run admitted into the Houmao gateway request queue."""

    run_input: RunAgentInput
    accepted_request: GatewayAcceptedRequestV1
    prompt_conversion: AgUiPromptConversion
    target_transport_family: AgUiTargetTransportFamily
    native_service_session_id: str | None = None
    service_incarnation: str | None = None
    native_web_identity: GatewayWebExecutionIdentityV1 | None = None


class AgUiRunService:
    """Service boundary for AG-UI run admission and observation."""

    def __init__(
        self,
        *,
        runtime: AgUiRuntimeObservationProtocol,
        poll_interval_seconds: float = 0.2,
        observation_timeout_seconds: float = 300.0,
    ) -> None:
        """Initialize the service with one gateway runtime."""

        self.m_runtime: AgUiRuntimeObservationProtocol = runtime
        self.m_poll_interval_seconds: float = poll_interval_seconds
        self.m_observation_timeout_seconds: float = observation_timeout_seconds

    def admit_run(self, run_input: RunAgentInput) -> AgUiAdmittedRun:
        """Admit one AG-UI run through existing gateway request controls."""

        try:
            prompt_conversion = convert_run_agent_input(run_input)
            request_payload = self._gateway_request_payload(
                run_input=run_input,
                prompt_conversion=prompt_conversion,
            )
        except AgUiPromptConversionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        target_transport_family = self.m_runtime.ag_ui_target_transport_family()
        if target_transport_family == "unknown":
            raise HTTPException(
                status_code=503,
                detail="AG-UI run submission is unavailable for this gateway target.",
            )

        status = self.m_runtime.status()
        if str(status.active_execution) != "idle" or status.queue_depth > 0:
            raise HTTPException(
                status_code=409,
                detail="AG-UI run admission is blocked because the target already has active or queued work.",
            )
        if str(status.request_admission) != "open":
            raise HTTPException(
                status_code=503,
                detail="AG-UI run admission is blocked because the gateway cannot accept prompt work.",
            )

        native_service_session_id = None
        service_incarnation = None
        native_web_identity = None
        if target_transport_family == "service":
            service = getattr(status, "service", None)
            if not isinstance(service, ManagedControlObservationV1) or (
                service.can_accept_prompt_now is not True
                or service.native_session_id is None
                or service.service_incarnation is None
            ):
                raise HTTPException(status_code=503, detail="The native service is unavailable")
            native_service_session_id = service.native_session_id
            service_incarnation = service.service_incarnation
            submit = request_payload.payload
            assert isinstance(submit, GatewayRequestPayloadSubmitPromptV1)
            if submit.chat_session is None or submit.chat_session.mode == "current":
                request_payload = request_payload.model_copy(
                    update={
                        "payload": submit.model_copy(
                            update={
                                "chat_session": GatewayChatSessionSelectorV1(
                                    mode="exact", id=native_service_session_id
                                )
                            }
                        )
                    }
                )

        if target_transport_family == "web":
            web = getattr(status, "web", None)
            if isinstance(web, GatewayWebControlStateV1):
                native_web_identity = web.identity
                submit = request_payload.payload
                assert isinstance(submit, GatewayRequestPayloadSubmitPromptV1)
                if submit.chat_session is None or submit.chat_session.mode == "current":
                    request_payload = request_payload.model_copy(
                        update={
                            "payload": submit.model_copy(
                                update={
                                    "chat_session": GatewayChatSessionSelectorV1(
                                        mode="exact", id=web.identity.native_session_id
                                    )
                                }
                            )
                        }
                    )

        accepted_request = self.m_runtime.create_request(request_payload, ready_only=True)
        return AgUiAdmittedRun(
            run_input=run_input,
            accepted_request=accepted_request,
            prompt_conversion=prompt_conversion,
            target_transport_family=target_transport_family,
            native_service_session_id=native_service_session_id,
            service_incarnation=service_incarnation,
            native_web_identity=native_web_identity,
        )

    async def stream_run_events(
        self,
        *,
        admitted_run: AgUiAdmittedRun,
        request: AgUiRunDisconnectProbe,
    ) -> AsyncIterator[BaseEvent]:
        """Yield AG-UI events for one already-admitted run."""

        mapper = AgUiEventMapper(
            thread_id=admitted_run.run_input.thread_id,
            run_id=admitted_run.run_input.run_id,
            parent_run_id=admitted_run.run_input.parent_run_id,
        )
        emitted_headless_count = 0
        emitted_tui_initial = False
        emitted_web_state: str | None = None
        emitted_service_state: str | None = None
        web_sequence = 0
        deadline = monotonic() + self.m_observation_timeout_seconds
        yield mapper.run_started_event(admitted_run.run_input)
        try:
            while True:
                if await request.is_disconnected():
                    return

                request_state = self.m_runtime.ag_ui_request_state(
                    admitted_run.accepted_request.request_id
                )
                if (
                    request_state is not None
                    and request_state.request_id != admitted_run.accepted_request.request_id
                ):
                    yield mapper.run_error_event(
                        message="The owner returned evidence for a different request.",
                        code="houmao_native_outcome_uncertain",
                    )
                    return
                service_request = None
                if admitted_run.target_transport_family == "service":
                    service_request = request_state.service_request if request_state else None
                    if service_request is not None:
                        if (
                            service_request.request_id != admitted_run.accepted_request.request_id
                            or service_request.native_session_id
                            != admitted_run.native_service_session_id
                            or service_request.service_incarnation
                            != admitted_run.service_incarnation
                        ):
                            yield mapper.run_error_event(
                                message="The owner returned evidence for a different native service request.",
                                code="houmao_native_outcome_uncertain",
                            )
                            return
                        if service_request.state != emitted_service_state:
                            for event in mapper.map_service_request(service_request):
                                yield event
                            emitted_service_state = service_request.state
                if admitted_run.target_transport_family == "headless":
                    emitted_headless_count, headless_events = self._headless_tail_events(
                        admitted_run=admitted_run,
                        mapper=mapper,
                        emitted_count=emitted_headless_count,
                    )
                    for event in headless_events:
                        yield event
                elif admitted_run.target_transport_family == "tui" and not emitted_tui_initial:
                    observation = self.m_runtime.ag_ui_tui_observation()
                    for event in mapper.map_tui_observation(
                        observation,
                        sequence_index=0,
                        include_final_text=False,
                    ):
                        yield event
                    emitted_tui_initial = True
                elif admitted_run.target_transport_family == "web":
                    web_state = self.m_runtime.ag_ui_web_observation()
                    if (
                        admitted_run.native_web_identity is not None
                        and web_state.identity != admitted_run.native_web_identity
                    ):
                        yield mapper.run_error_event(
                            message="The Web host or its native conversation changed.",
                            code="houmao_native_outcome_uncertain",
                        )
                        return
                    content = web_state.model_dump_json(exclude={"observed_at_utc"})
                    if content != emitted_web_state:
                        for event in mapper.map_web_observation(
                            web_state, sequence_index=web_sequence
                        ):
                            yield event
                        emitted_web_state = content
                        web_sequence += 1

                if request_state is not None and request_state.terminal:
                    if admitted_run.target_transport_family == "headless":
                        emitted_headless_count, headless_events = self._headless_tail_events(
                            admitted_run=admitted_run,
                            mapper=mapper,
                            emitted_count=emitted_headless_count,
                        )
                        for event in headless_events:
                            yield event
                    elif admitted_run.target_transport_family == "tui":
                        observation = self.m_runtime.ag_ui_tui_observation()
                        for event in mapper.map_tui_observation(
                            observation,
                            sequence_index=1,
                            include_final_text=False,
                        ):
                            yield event
                    elif admitted_run.target_transport_family == "web":
                        for event in mapper.map_web_observation(
                            self.m_runtime.ag_ui_web_observation(),
                            sequence_index=web_sequence,
                        ):
                            yield event

                    if request_state.state == "uncertain" or (
                        admitted_run.target_transport_family in {"service", "web"}
                        and request_state.state == "completed"
                        and not _request_has_native_completion(request_state, admitted_run)
                    ):
                        yield mapper.run_error_event(
                            message="The owner could not verify native completion for this request.",
                            code="houmao_native_outcome_uncertain",
                        )
                    elif request_state.failed:
                        message = request_state.error_detail or "Houmao gateway request failed."
                        yield mapper.run_error_event(
                            message=message,
                            code="houmao_gateway_request_failed",
                        )
                    else:
                        if service_request is not None:
                            for event in mapper.map_service_request(
                                service_request, include_final_text=True
                            ):
                                yield event
                        if admitted_run.target_transport_family == "web" and isinstance(
                            request_state.result, dict
                        ):
                            assistant = request_state.result.get("assistant_text")
                            if isinstance(assistant, str):
                                for event in mapper.map_web_assistant_text(assistant):
                                    yield event
                        yield mapper.run_finished_event(
                            result=_run_finished_result(admitted_run, request_state.state)
                        )
                    return

                if monotonic() >= deadline:
                    yield mapper.run_error_event(
                        message="The observation deadline expired before a verified request outcome.",
                        code="houmao_native_outcome_uncertain",
                    )
                    return
                await asyncio.sleep(self.m_poll_interval_seconds)
        except Exception:
            yield mapper.run_error_event(
                message="AG-UI run stream failed after admission.",
                code="houmao_run_stream_failed",
            )

    def _gateway_request_payload(
        self,
        *,
        run_input: RunAgentInput,
        prompt_conversion: AgUiPromptConversion,
    ) -> GatewayRequestCreateV1:
        """Build the gateway request for one converted AG-UI run."""

        forwarded_props = prompt_conversion.forwarded_props
        chat_session = (
            GatewayChatSessionSelectorV1.model_validate(forwarded_props.chat_session)
            if forwarded_props.chat_session is not None
            else None
        )
        execution = (
            GatewayExecutionOverrideV1.model_validate(forwarded_props.execution)
            if forwarded_props.execution is not None
            else None
        )
        return GatewayRequestCreateV1(
            kind="submit_prompt",
            payload=GatewayRequestPayloadSubmitPromptV1(
                prompt=prompt_conversion.prompt,
                turn_id=run_input.run_id,
                chat_session=chat_session,
                execution=execution,
            ),
        )

    def _headless_tail_events(
        self,
        *,
        admitted_run: AgUiAdmittedRun,
        mapper: AgUiEventMapper,
        emitted_count: int,
    ) -> tuple[int, list[BaseEvent]]:
        """Return any canonical headless events not yet sent."""

        events = _headless_events_for_run(
            runtime=self.m_runtime,
            run_id=admitted_run.run_input.run_id,
        )
        if emitted_count >= len(events):
            return emitted_count, []
        mapped_events: list[BaseEvent] = []
        for sequence_index, event in enumerate(events[emitted_count:], start=emitted_count):
            mapped_events.extend(mapper.map_headless_event(event, sequence_index=sequence_index))
        return len(events), mapped_events


def _headless_events_for_run(
    *,
    runtime: AgUiRuntimeObservationProtocol,
    run_id: str,
) -> list[CanonicalHeadlessEvent]:
    """Load canonical headless events for one AG-UI run id when available."""

    observation = runtime.ag_ui_headless_artifact(run_id)
    if observation is None:
        return []
    return load_canonical_headless_events(canonical_path=observation.canonical_events_path)


def _run_finished_result(admitted_run: AgUiAdmittedRun, request_state: str) -> JsonObject:
    """Return compact AG-UI run-finished metadata."""

    result: JsonObject = {
        "gatewayRequestId": admitted_run.accepted_request.request_id,
        "gatewayRequestState": request_state,
        "targetTransportFamily": admitted_run.target_transport_family,
    }
    if admitted_run.target_transport_family == "tui" and request_state == "completed":
        result["completionEvidence"] = "terminal_handoff"
        result["providerCompletion"] = "unconfirmed"
    return result


def _request_has_native_completion(state: AgUiObservedRequestState, run: AgUiAdmittedRun) -> bool:
    """Require native evidence associated with the exact delivered request."""

    receipt = state.result
    if not isinstance(receipt, dict):
        return False
    operation = receipt.get("operation_id")
    session = receipt.get("native_session_id")
    turns = receipt.get("native_turn_ids")
    if run.target_transport_family == "service":
        snapshot = state.service_request
        if (
            receipt.get("source") != "service_native"
            or session != run.native_service_session_id
            or receipt.get("service_incarnation") != run.service_incarnation
            or snapshot is None
            or snapshot.state != "completed"
            or turns != [snapshot.native_turn_id]
        ):
            return False
    if run.target_transport_family == "web" and run.native_web_identity is not None:
        if (
            receipt.get("source") != "web_native"
            or receipt.get("identity") != run.native_web_identity.model_dump(mode="json")
            or session != run.native_web_identity.native_session_id
        ):
            return False
        expected_prompt = run.accepted_request.native_prompt_id
        if expected_prompt is not None and receipt.get("native_prompt_id") != expected_prompt:
            return False
    return (
        receipt.get("outcome") == "completed"
        and operation == state.request_id
        and receipt.get("source") in ("web_native", "service_native")
        and isinstance(session, str)
        and bool(session)
        and isinstance(turns, list)
        and bool(turns)
        and all(isinstance(turn, str) and bool(turn) for turn in turns)
    )
