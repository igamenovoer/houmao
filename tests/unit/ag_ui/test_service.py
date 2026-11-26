from __future__ import annotations

from dataclasses import dataclass, field, replace

import pytest
from ag_ui.core import RunAgentInput
from fastapi import HTTPException

from houmao.ag_ui.runtime import AgUiObservedRequestState, AgUiTuiObservation
from houmao.ag_ui.service import AgUiRunService
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayServiceRequestSnapshotV1,
    GatewayStatusV1,
    GatewayWebControlStateV1,
)
from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.models import SessionEvent
from tests.unit.agents.realm_controller.test_dsh_web_observation import _metadata


def _status(**overrides: object) -> GatewayStatusV1:
    """Return one healthy gateway status sample."""

    values: dict[str, object] = {
        "attach_identity": "agent-1",
        "backend": "codex_headless",
        "tmux_session_name": "tmux-agent-1",
        "gateway_health": "healthy",
        "managed_agent_connectivity": "connected",
        "managed_agent_recovery": "idle",
        "request_admission": "open",
        "terminal_surface_eligibility": "ready",
        "active_execution": "idle",
        "execution_mode": "detached_process",
        "queue_depth": 0,
        "gateway_host": "127.0.0.1",
        "gateway_port": 43123,
        "managed_agent_instance_epoch": 1,
        "managed_agent_instance_id": "instance-1",
    }
    values.update(overrides)
    return GatewayStatusV1.model_validate(values)


def _run_input(**overrides: object) -> RunAgentInput:
    """Build one AG-UI run input for service tests."""

    payload: dict[str, object] = {
        "threadId": "thread-1",
        "runId": "run-1",
        "state": {},
        "messages": [
            {
                "id": "message-1",
                "role": "user",
                "content": "hello",
            }
        ],
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }
    payload.update(overrides)
    return RunAgentInput.model_validate(payload)


@dataclass
class _Runtime:
    """Fake AG-UI runtime observation implementation."""

    status_payload: GatewayStatusV1 = field(default_factory=_status)
    target_family: str = "headless"
    created_requests: list[GatewayRequestCreateV1] = field(default_factory=list)
    observed_request: AgUiObservedRequestState | None = None

    def status(self) -> GatewayStatusV1:
        """Return configured status."""

        return self.status_payload

    def create_request(
        self, request_payload: GatewayRequestCreateV1, *, ready_only: bool = False
    ) -> GatewayAcceptedRequestV1:
        """Capture request creation."""

        assert ready_only
        self.created_requests.append(request_payload)
        return GatewayAcceptedRequestV1(
            request_id="request-1",
            request_kind=request_payload.kind,
            state="accepted",
            accepted_at_utc="2026-06-08T01:00:00Z",
            queue_depth=1,
            managed_agent_instance_epoch=1,
        )

    def ag_ui_request_state(self, request_id: str) -> object | None:
        """Return no observed request state for admission-only tests."""

        del request_id
        return self.observed_request

    def ag_ui_target_transport_family(self) -> str:
        """Return configured target family."""

        return self.target_family

    def ag_ui_headless_artifact(self, run_id: str) -> object | None:
        """Return no headless artifact for admission-only tests."""

        del run_id
        return None

    def ag_ui_tui_observation(self) -> AgUiTuiObservation:
        """Return unavailable TUI observation for admission-only tests."""

        return AgUiTuiObservation(
            available=False, status={}, final_text="Uncorrelated human output"
        )

    def ag_ui_web_observation(self) -> GatewayWebControlStateV1:
        """Return the exact configured Web conversation observation."""

        assert self.status_payload.web is not None
        return self.status_payload.web


@pytest.mark.anyio
@pytest.mark.parametrize("replacement", [False, True])
async def test_kimi_web_run_emits_only_its_matching_native_answer(replacement: bool) -> None:
    """A recorded assistant answer cannot settle an unrelated Web incarnation."""

    metadata = _metadata()
    identity = metadata.identity
    web = GatewayWebControlStateV1(
        identity=identity,
        origin=metadata.origin,
        browser_url=metadata.browser_url,
        availability="available",
        observed_at_utc="2026-06-08T01:00:00Z",
        sequence=0,
        cursor=0,
    )
    returned_identity = (
        identity.model_copy(update={"host_incarnation": "replacement"}) if replacement else identity
    )
    runtime = _Runtime(
        target_family="web",
        status_payload=_status(backend="kimi_web", web=web),
        observed_request=AgUiObservedRequestState(
            request_id="request-1",
            request_kind="submit_prompt",
            state="completed",
            accepted_at_utc="2026-06-08T01:00:00Z",
            result={
                "operation_id": "request-1",
                "outcome": "completed",
                "source": "web_native",
                "native_session_id": identity.native_session_id,
                "native_turn_ids": ["8"],
                "identity": returned_identity.model_dump(mode="json"),
                "assistant_text": "Owned Kimi reply",
            },
        ),
    )
    service = AgUiRunService(runtime=runtime)  # type: ignore[arg-type]
    admitted = service.admit_run(_run_input())
    submit = runtime.created_requests[0].payload
    assert isinstance(submit, GatewayRequestPayloadSubmitPromptV1)
    assert submit.chat_session is not None and submit.chat_session.id == identity.native_session_id
    events = [
        event
        async for event in service.stream_run_events(
            admitted_run=admitted, request=_ConnectedRequest()
        )
    ]
    assert events[-1].type.value == ("RUN_ERROR" if replacement else "RUN_FINISHED")
    assert any("Owned Kimi reply" in event.model_dump_json() for event in events) is not replacement


class _ConnectedRequest:
    disconnected = False

    async def is_disconnected(self) -> bool:
        """Report whether the test client still receives SSE events."""

        return self.disconnected


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("family", "result", "expected_terminal"),
    [
        ("tui", None, "RUN_FINISHED"),
        ("service", {"operation_id": "different-request", "outcome": "completed"}, "RUN_ERROR"),
        (
            "service",
            {
                "operation_id": "request-1",
                "outcome": "completed",
                "source": "service_native",
                "native_session_id": "native-session",
                "service_incarnation": "native-owner",
                "native_turn_ids": ["native-turn"],
            },
            "RUN_ERROR",
        ),
    ],
)
async def test_run_reports_only_correlated_completion(family, result, expected_terminal) -> None:
    """Unattributed native or TUI activity cannot become assistant output for this run."""

    runtime = _Runtime(
        target_family=family,
        status_payload=_status(mode="service", backend="dsh_acp", service=_ready_service())
        if family == "service"
        else _status(),
        observed_request=AgUiObservedRequestState(
            request_id="request-1",
            request_kind="submit_prompt",
            state="completed",
            accepted_at_utc="2026-06-08T01:00:00Z",
            result=result,
        ),
    )
    service = AgUiRunService(runtime=runtime)  # type: ignore[arg-type]
    admitted = service.admit_run(_run_input())
    events = [
        event
        async for event in service.stream_run_events(
            admitted_run=admitted, request=_ConnectedRequest()
        )
    ]
    assert events[-1].type.value == expected_terminal
    assert all("Uncorrelated human output" not in event.model_dump_json() for event in events)


def _ready_service() -> ManagedControlObservationV1:
    """Use the native conversation and incarnation that AG-UI will pin."""

    return ManagedControlObservationV1(
        source="service_native",
        freshness="current",
        connection_ready=True,
        owner_available=True,
        can_accept_prompt_now=True,
        native_session_id="native-session",
        service_incarnation="native-owner",
    )


@pytest.mark.anyio
@pytest.mark.parametrize("replacement", [None, "session", "admission", "disconnect"])
async def test_hermes_tui_stream_tracks_its_queued_native_admission(
    replacement: str | None,
) -> None:
    """A queued run stays open and settles only with evidence for its conversation."""

    queued = {
        "operation_id": "request-1",
        "source": "tui_native",
        "native_session_id": "native-session",
        "native_turn_ids": ["admission-1"],
        "outcome": "queued",
    }
    runtime = _Runtime(
        target_family="native_tui",
        status_payload=_status(
            mode="tui",
            backend="hermes_tui",
            observation=_ready_service().model_copy(update={"source": "tui_native"}),
        ),
        observed_request=AgUiObservedRequestState(
            request_id="request-1",
            request_kind="submit_prompt",
            state="observing",
            accepted_at_utc="2026-06-08T01:00:00Z",
            result=queued,
        ),
    )
    service = AgUiRunService(runtime=runtime)  # type: ignore[arg-type]
    admitted = service.admit_run(_run_input())
    connection = _ConnectedRequest()
    stream = service.stream_run_events(admitted_run=admitted, request=connection)
    events = [await anext(stream), await anext(stream)]
    assert [event.type.value for event in events] == ["RUN_STARTED", "ACTIVITY_SNAPSHOT"]
    assert "queued" in events[1].model_dump_json()
    if replacement == "disconnect":
        connection.disconnected = True
        assert [event async for event in stream] == []
        assert runtime.observed_request is not None and runtime.observed_request.result == queued
        return
    assert runtime.observed_request is not None
    runtime.observed_request = replace(
        runtime.observed_request,
        state="completed",
        result={
            **queued,
            "native_session_id": "another-conversation"
            if replacement == "session"
            else "native-session",
            "native_turn_ids": [
                "another-admission" if replacement == "admission" else "admission-1"
            ],
            "outcome": "completed",
            "assistant_text": "Receipt-bound text",
        },
    )
    events.extend([event async for event in stream])
    assert events[-1].type.value == ("RUN_FINISHED" if replacement is None else "RUN_ERROR")
    assert any("Receipt-bound text" in event.model_dump_json() for event in events) is (
        replacement is None
    )
    assert all("Uncorrelated human output" not in event.model_dump_json() for event in events)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("backend", "incarnation", "state"),
    [
        ("dsh_acp", "native-owner", "completed"),
        ("dsh_acp", "replacement-owner", "completed"),
        ("kimi_acp", "native-owner", "completed"),
        ("kimi_acp", "replacement-owner", "completed"),
        ("kimi_acp", "native-owner", "failed"),
        ("codex_app_server", "native-owner", "completed"),
        ("codex_app_server", "replacement-owner", "completed"),
        ("codex_app_server", "native-owner", "failed"),
    ],
)
async def test_service_stream_uses_only_the_admitted_native_request(
    backend: str, incarnation: str, state: str
) -> None:
    """The exact service turn emits assistant text and an unrelated turn cannot."""

    native_turn = "0" if backend == "kimi_acp" else "native-turn"
    snapshot = GatewayServiceRequestSnapshotV1(
        request_id="request-1",
        generation_id="generation",
        service_incarnation=incarnation,
        native_session_id="native-session",
        native_turn_id=native_turn,
        state=state,
        events=[
            SessionEvent(
                kind="assistant",
                message="ADMITTED_REPLY",
                turn_index=1,
                payload={"native_session_id": "native-session", "native_turn_id": native_turn},
            ),
            SessionEvent(
                kind="assistant",
                message="UNRELATED_REPLY",
                turn_index=2,
                payload={"native_session_id": "native-session", "native_turn_id": "other-turn"},
            ),
        ],
    )
    runtime = _Runtime(
        target_family="service",
        status_payload=_status(mode="service", backend=backend, service=_ready_service()),
        observed_request=AgUiObservedRequestState(
            request_id="request-1",
            request_kind="submit_prompt",
            state=state,
            accepted_at_utc="2026-06-08T01:00:00Z",
            result={
                "operation_id": "request-1",
                "outcome": state,
                "source": "service_native",
                "native_session_id": "native-session",
                "service_incarnation": incarnation,
                "native_turn_ids": [native_turn],
            },
            service_request=snapshot,
        ),
    )
    service = AgUiRunService(runtime=runtime)  # type: ignore[arg-type]
    admitted = service.admit_run(_run_input())
    request = runtime.created_requests[0].payload
    assert isinstance(request, GatewayRequestPayloadSubmitPromptV1)
    assert request.chat_session is not None
    assert request.chat_session.mode == "exact" and request.chat_session.id == "native-session"
    stream = service.stream_run_events(admitted_run=admitted, request=_ConnectedRequest())
    events = []
    if backend == "codex_app_server" and state == "completed" and incarnation == "native-owner":
        settled = runtime.observed_request
        assert settled is not None
        runtime.observed_request = replace(
            settled,
            state="running",
            result=None,
            service_request=snapshot.model_copy(update={"state": "handed_off", "events": []}),
        )
        events = [await anext(stream), await anext(stream)]
        assert [event.type.value for event in events] == ["RUN_STARTED", "ACTIVITY_SNAPSHOT"]
        assert native_turn in events[-1].model_dump_json()
        runtime.observed_request = settled
    events.extend([event async for event in stream])
    serialized = " ".join(event.model_dump_json() for event in events)
    assert "UNRELATED_REPLY" not in serialized
    if incarnation == "native-owner" and state == "completed":
        assert "ADMITTED_REPLY" in serialized
        assert events[-1].type.value == "RUN_FINISHED"
    else:
        assert "ADMITTED_REPLY" not in serialized
        assert events[-1].type.value == "RUN_ERROR"


def test_service_admits_run_with_gateway_turn_id_and_metadata() -> None:
    runtime = _Runtime()
    service = AgUiRunService(runtime=runtime)  # type: ignore[arg-type]

    admitted = service.admit_run(
        _run_input(
            forwardedProps={
                "houmao": {
                    "chatSession": {"mode": "exact", "id": "session-1"},
                    "execution": {"model": {"name": "gpt-5.4"}},
                },
                "unmanaged": "ignored",
            }
        )
    )

    assert admitted.accepted_request.request_id == "request-1"
    assert admitted.target_transport_family == "headless"
    assert len(runtime.created_requests) == 1
    request = runtime.created_requests[0]
    assert request.kind == "submit_prompt"
    assert isinstance(request.payload, GatewayRequestPayloadSubmitPromptV1)
    assert request.payload.turn_id == "run-1"
    assert request.payload.chat_session is not None
    assert request.payload.chat_session.mode == "exact"
    assert request.payload.chat_session.id == "session-1"
    assert request.payload.execution is not None
    assert request.payload.execution.model.name == "gpt-5.4"
    assert "unmanaged" in request.payload.prompt
    assert "ignored" not in request.payload.prompt


@pytest.mark.parametrize(
    ("status_payload", "status_code"),
    [
        (_status(active_execution="running"), 409),
        (_status(queue_depth=1), 409),
        (_status(request_admission="blocked_unavailable"), 503),
    ],
)
def test_service_rejects_busy_or_unavailable_target_before_request_creation(
    status_payload: GatewayStatusV1,
    status_code: int,
) -> None:
    runtime = _Runtime(status_payload=status_payload)
    service = AgUiRunService(runtime=runtime)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        service.admit_run(_run_input())

    assert exc_info.value.status_code == status_code
    assert runtime.created_requests == []


def test_service_rejects_unknown_target_before_request_creation() -> None:
    runtime = _Runtime(target_family="unknown")
    service = AgUiRunService(runtime=runtime)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        service.admit_run(_run_input())

    assert exc_info.value.status_code == 503
    assert runtime.created_requests == []


def test_service_rejects_invalid_input_before_request_creation() -> None:
    runtime = _Runtime()
    service = AgUiRunService(runtime=runtime)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        service.admit_run(
            _run_input(
                messages=[
                    {
                        "id": "user-1",
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "url",
                                    "value": "https://example.invalid/image.png",
                                },
                            }
                        ],
                    }
                ]
            )
        )

    assert exc_info.value.status_code == 422
    assert runtime.created_requests == []


def test_service_rejects_invalid_forwarded_props_before_request_creation() -> None:
    runtime = _Runtime()
    service = AgUiRunService(runtime=runtime)  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        service.admit_run(_run_input(forwardedProps={"houmao": {"chatSession": {"mode": "exact"}}}))

    assert exc_info.value.status_code == 422
    assert runtime.created_requests == []
