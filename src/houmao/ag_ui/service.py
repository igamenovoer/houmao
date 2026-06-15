"""AG-UI run admission and stream orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
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
)
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


class AgUiRunService:
    """Service boundary for AG-UI run admission and observation."""

    def __init__(
        self,
        *,
        runtime: AgUiRuntimeObservationProtocol,
        poll_interval_seconds: float = 0.2,
    ) -> None:
        """Initialize the service with one gateway runtime."""

        self.m_runtime: AgUiRuntimeObservationProtocol = runtime
        self.m_poll_interval_seconds: float = poll_interval_seconds

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

        accepted_request = self.m_runtime.create_request(request_payload)
        return AgUiAdmittedRun(
            run_input=run_input,
            accepted_request=accepted_request,
            prompt_conversion=prompt_conversion,
            target_transport_family=target_transport_family,
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
        yield mapper.run_started_event(admitted_run.run_input)
        try:
            while True:
                if await request.is_disconnected():
                    return

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

                request_state = self.m_runtime.ag_ui_request_state(
                    admitted_run.accepted_request.request_id
                )
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
                            include_final_text=True,
                        ):
                            yield event

                    if request_state.failed:
                        message = request_state.error_detail or "Houmao gateway request failed."
                        yield mapper.run_error_event(
                            message=message,
                            code="houmao_gateway_request_failed",
                        )
                    else:
                        yield mapper.run_finished_event(
                            result=_run_finished_result(admitted_run, request_state.state)
                        )
                    return

                await asyncio.sleep(self.m_poll_interval_seconds)
        except Exception as exc:
            yield mapper.run_error_event(
                message=f"AG-UI run stream failed after admission: {exc}",
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

    return {
        "gatewayRequestId": admitted_run.accepted_request.request_id,
        "gatewayRequestState": request_state,
        "targetTransportFamily": admitted_run.target_transport_family,
    }
