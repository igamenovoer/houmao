from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from ag_ui.core import RunAgentInput
from fastapi import HTTPException

from houmao.ag_ui.runtime import AgUiTuiObservation
from houmao.ag_ui.service import AgUiRunService
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
)


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

    def status(self) -> GatewayStatusV1:
        """Return configured status."""

        return self.status_payload

    def create_request(self, request_payload: GatewayRequestCreateV1) -> GatewayAcceptedRequestV1:
        """Capture request creation."""

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
        return None

    def ag_ui_target_transport_family(self) -> str:
        """Return configured target family."""

        return self.target_family

    def ag_ui_headless_artifact(self, run_id: str) -> object | None:
        """Return no headless artifact for admission-only tests."""

        del run_id
        return None

    def ag_ui_tui_observation(self) -> AgUiTuiObservation:
        """Return unavailable TUI observation for admission-only tests."""

        return AgUiTuiObservation(available=False, status={})


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
