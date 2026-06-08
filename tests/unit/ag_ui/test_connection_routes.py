from __future__ import annotations

import asyncio
import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

import houmao.ag_ui.routes as ag_ui_routes
from houmao.ag_ui.connection import AgUiConnectionRegistry
from houmao.ag_ui.diagnostics import AgUiDiagnostics
from houmao.ag_ui.models import AgUiConnectInput
from houmao.ag_ui.runtime import (
    AgUiHeadlessArtifactObservation,
    AgUiObservedRequestState,
    AgUiTuiObservation,
    ag_ui_target_transport_family_for_backend,
)
from houmao.ag_ui.routes import connect_event_stream, register_ag_ui_routes, run_event_stream
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayRequestCreateV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.gateway_service import create_app
from houmao.agents.realm_controller.backends.headless_output import CanonicalHeadlessEvent


def _status(**overrides: object) -> GatewayStatusV1:
    """Return one healthy gateway status sample."""

    values: dict[str, object] = {
        "attach_identity": "agent-1",
        "backend": "local_interactive",
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


def _connect_payload(**overrides: object) -> dict[str, object]:
    """Return one valid AG-UI connect payload."""

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
        "forwardedProps": {"authorization": "Bearer secret"},
    }
    payload.update(overrides)
    return payload


@dataclass
class _SpyRuntime:
    """Gateway runtime spy that detects work submission and lifecycle calls."""

    status_payload: GatewayStatusV1 = field(default_factory=_status)
    diagnostics: list[dict[str, object]] = field(default_factory=list)
    created_requests: list[GatewayRequestCreateV1] = field(default_factory=list)
    request_states: list[AgUiObservedRequestState | None] = field(default_factory=list)
    headless_events_path: Path | None = None
    prompt_submissions: int = 0
    queued_requests: int = 0
    stop_calls: int = 0
    abort_calls: int = 0
    interrupt_calls: int = 0
    restart_calls: int = 0
    shutdown_calls: int = 0

    def status(self) -> GatewayStatusV1:
        """Return the configured status without lifecycle side effects."""

        return self.status_payload

    def emit_diagnostic(self, **kwargs: object) -> None:
        """Capture diagnostics emitted by the gateway middleware."""

        self.diagnostics.append(dict(kwargs))

    def control_prompt(self, _payload: object) -> None:
        """Detect prompt-control submission."""

        self.prompt_submissions += 1

    def create_request(self, payload: GatewayRequestCreateV1) -> GatewayAcceptedRequestV1:
        """Detect queued gateway request creation."""

        self.queued_requests += 1
        self.created_requests.append(payload)
        return GatewayAcceptedRequestV1(
            request_id="request-1",
            request_kind=payload.kind,
            state="accepted",
            accepted_at_utc="2026-06-08T01:00:00Z",
            queue_depth=1,
            managed_agent_instance_epoch=1,
        )

    def ag_ui_request_state(self, request_id: str) -> AgUiObservedRequestState | None:
        """Return configured observed request state."""

        del request_id
        if not self.request_states:
            return None
        if len(self.request_states) == 1:
            return self.request_states[0]
        return self.request_states.pop(0)

    def ag_ui_target_transport_family(self) -> str:
        """Return the configured target family from status backend."""

        return ag_ui_target_transport_family_for_backend(str(self.status_payload.backend))

    def ag_ui_headless_artifact(self, run_id: str) -> AgUiHeadlessArtifactObservation | None:
        """Return configured headless artifact path."""

        if self.headless_events_path is None:
            return None
        return AgUiHeadlessArtifactObservation(
            run_id=run_id,
            turn_dir=self.headless_events_path.parent,
            canonical_events_path=self.headless_events_path,
            provider="codex",
            artifact_available=self.headless_events_path.is_file(),
        )

    def ag_ui_tui_observation(self) -> AgUiTuiObservation:
        """Return a compact fake TUI observation."""

        return AgUiTuiObservation(
            available=True,
            status={"backend": str(self.status_payload.backend), "turnPhase": "ready"},
            activity="TUI ready",
            final_text="final TUI answer",
        )

    def stop(self) -> None:
        """Detect unsupported stop lifecycle calls."""

        self.stop_calls += 1

    def abort(self) -> None:
        """Detect unsupported abort lifecycle calls."""

        self.abort_calls += 1

    def interrupt(self) -> None:
        """Detect unsupported interrupt lifecycle calls."""

        self.interrupt_calls += 1

    def restart(self) -> None:
        """Detect unsupported restart lifecycle calls."""

        self.restart_calls += 1

    def shutdown(self) -> None:
        """Detect unsupported shutdown lifecycle calls."""

        self.shutdown_calls += 1

    def assert_no_work_or_lifecycle_calls(self) -> None:
        """Assert that AG-UI routes did not submit work or manage lifecycle."""

        assert self.prompt_submissions == 0
        assert self.queued_requests == 0
        assert self.stop_calls == 0
        assert self.abort_calls == 0
        assert self.interrupt_calls == 0
        assert self.restart_calls == 0
        assert self.shutdown_calls == 0

    def assert_no_lifecycle_calls(self) -> None:
        """Assert that AG-UI streaming did not manage the agent lifecycle."""

        assert self.stop_calls == 0
        assert self.abort_calls == 0
        assert self.interrupt_calls == 0
        assert self.restart_calls == 0
        assert self.shutdown_calls == 0


class _DisconnectProbe:
    """Disconnect probe used to unit-test stream cleanup."""

    async def is_disconnected(self) -> bool:
        """Report that the test stream remains open until explicitly closed."""

        return False


def test_connection_registry_create_detach_unknown_and_active_listing() -> None:
    registry = AgUiConnectionRegistry(
        id_factory=lambda: "agui-1",
        clock=lambda: datetime(2026, 6, 8, 1, 2, 3, tzinfo=UTC),
    )

    record = registry.create(
        thread_id="thread-1",
        run_id="run-1",
        parent_run_id="run-parent",
        last_seen_event_id="event-1",
    )

    assert record.connection_id == "agui-1"
    assert record.detached is False
    assert registry.get("agui-1") == record
    assert registry.active_connections() == (record,)

    detached = registry.detach("agui-1")
    assert detached is not None
    assert detached.connection_id == "agui-1"
    assert detached.detached is True
    assert detached.detached_at_utc == datetime(2026, 6, 8, 1, 2, 3, tzinfo=UTC)
    assert registry.get("agui-1") is None
    assert registry.active_connections() == ()
    assert registry.detach("missing") is None


def test_connect_stream_initial_snapshot_and_client_close_detaches_only_connection() -> None:
    async def _run() -> None:
        runtime = _SpyRuntime()
        registry = AgUiConnectionRegistry(id_factory=lambda: "agui-1")
        connect_input = AgUiConnectInput.model_validate(_connect_payload(lastSeenEventId="event-1"))
        stream = connect_event_stream(
            runtime=runtime,
            registry=registry,
            connect_input=connect_input,
            request=_DisconnectProbe(),
            heartbeat_interval_seconds=0.01,
        )

        first_frame = await anext(stream)
        assert first_frame.startswith("data: ")
        payload = json.loads(first_frame.removeprefix("data: ").removesuffix("\n\n"))
        assert payload["type"] == "STATE_SNAPSHOT"
        assert payload["snapshot"]["houmao"]["connection"]["connectionId"] == "agui-1"
        assert payload["snapshot"]["houmao"]["connection"]["lastSeenEventId"] == "event-1"
        assert registry.get("agui-1") is not None

        await stream.aclose()
        assert registry.get("agui-1") is None
        runtime.assert_no_work_or_lifecycle_calls()

    asyncio.run(_run())


def test_connect_stream_records_safe_diagnostics_and_active_counts() -> None:
    async def _run() -> None:
        runtime = _SpyRuntime()
        diagnostics = AgUiDiagnostics(runtime=runtime)
        registry = AgUiConnectionRegistry(id_factory=lambda: "agui-1")
        connect_input = AgUiConnectInput.model_validate(_connect_payload(lastSeenEventId="event-1"))
        stream = connect_event_stream(
            runtime=runtime,
            registry=registry,
            connect_input=connect_input,
            request=_DisconnectProbe(),
            diagnostics=diagnostics,
            heartbeat_interval_seconds=0.01,
        )

        assert diagnostics.active_counts() == {
            "activeAgUiConnections": 0,
            "activeAgUiRuns": 0,
        }
        await anext(stream)
        assert diagnostics.active_counts() == {
            "activeAgUiConnections": 1,
            "activeAgUiRuns": 0,
        }
        await stream.aclose()

        assert diagnostics.active_counts() == {
            "activeAgUiConnections": 0,
            "activeAgUiRuns": 0,
        }
        event_names = [str(entry["event"]) for entry in runtime.diagnostics]
        assert "gateway.ag_ui_connection_started" in event_names
        assert "gateway.ag_ui_connection_detached" in event_names
        rendered = json.dumps(runtime.diagnostics, sort_keys=True)
        assert "Bearer secret" not in rendered
        assert "hello" not in rendered
        runtime.assert_no_work_or_lifecycle_calls()

    asyncio.run(_run())


def test_create_app_registers_ag_ui_routes_and_preserves_existing_status_route() -> None:
    app = create_app(runtime=_SpyRuntime())  # type: ignore[arg-type]
    inventory = {
        (route.path, frozenset(route.methods or set()))
        for route in app.routes
        if hasattr(route, "methods")
    }

    assert ("/v1/ag-ui/capabilities", frozenset({"GET"})) in inventory
    assert ("/v1/ag-ui/connect", frozenset({"POST"})) in inventory
    assert ("/v1/ag-ui/runs", frozenset({"POST"})) in inventory
    assert ("/v1/ag-ui/connections/{connection_id}", frozenset({"DELETE"})) in inventory
    assert ("/v1/status", frozenset({"GET"})) in inventory


def test_capabilities_route_reports_conservative_support() -> None:
    runtime = _SpyRuntime()
    app = FastAPI()
    register_ag_ui_routes(app, runtime=runtime)
    client = TestClient(app)

    response = client.get("/v1/ag-ui/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["capabilities"]["transport"]["streaming"] is True
    assert body["capabilities"]["state"]["snapshots"] is True
    assert body["capabilities"]["state"]["deltas"] is False
    assert body["houmao"]["features"]["taskRunSubmission"] is True
    assert body["houmao"]["features"]["generatedGraphics"] is False
    assert body["houmao"]["features"]["frontendToolExecution"] is False
    assert body["houmao"]["agentLifecycleManagedByGui"] is False
    runtime.assert_no_work_or_lifecycle_calls()


def test_connect_route_returns_sse_state_snapshot_and_does_not_submit_work() -> None:
    async def _run() -> None:
        runtime = _SpyRuntime()
        app = FastAPI()
        registry = AgUiConnectionRegistry(id_factory=lambda: "agui-1")
        register_ag_ui_routes(
            app,
            runtime=runtime,
            registry=registry,
            heartbeat_interval_seconds=0.01,
        )
        route = next(
            route
            for route in app.routes
            if isinstance(route, APIRoute) and route.path == "/v1/ag-ui/connect"
        )
        response = await route.endpoint(
            _DisconnectProbe(),
            AgUiConnectInput.model_validate(_connect_payload()),
        )
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"

        first_frame = await anext(response.body_iterator)
        if isinstance(first_frame, bytes):
            first_frame = first_frame.decode("utf-8")
        payload = json.loads(first_frame.removeprefix("data: ").removesuffix("\n\n"))
        await response.body_iterator.aclose()

        assert payload["type"] == "STATE_SNAPSHOT"
        assert payload["snapshot"]["houmao"]["connection"]["connectionId"] == "agui-1"
        assert "RUN_STARTED" not in json.dumps(payload)
        runtime.assert_no_work_or_lifecycle_calls()

    asyncio.run(_run())


def test_disconnect_routes_remove_only_connection_bookkeeping() -> None:
    runtime = _SpyRuntime()
    app = FastAPI()
    registry = AgUiConnectionRegistry(id_factory=lambda: "agui-1")
    register_ag_ui_routes(app, runtime=runtime, registry=registry)
    client = TestClient(app)
    record = registry.create(thread_id="thread-1", run_id="run-1")

    response = client.delete(f"/v1/ag-ui/connections/{record.connection_id}")

    assert response.status_code == 200
    assert response.json() == {
        "status": "detached",
        "connectionId": "agui-1",
        "detached": True,
        "detail": "AG-UI connection detached. Houmao agent lifecycle was not modified.",
    }
    explicit_disconnect = [
        entry
        for entry in runtime.diagnostics
        if entry["event"] == "gateway.ag_ui_connection_explicit_disconnect"
    ][0]
    assert explicit_disconnect["fields"]["detached"] is True  # type: ignore[index]
    assert registry.get("agui-1") is None
    runtime.assert_no_work_or_lifecycle_calls()

    unknown_response = client.delete("/v1/ag-ui/connections/missing")
    assert unknown_response.status_code == 404
    assert unknown_response.json() == {
        "status": "not_found",
        "connectionId": "missing",
        "detached": False,
        "detail": "AG-UI connection is unknown or already detached.",
    }
    missing_disconnect = [
        entry
        for entry in runtime.diagnostics
        if entry["event"] == "gateway.ag_ui_connection_explicit_disconnect"
    ][1]
    assert missing_disconnect["fields"]["detached"] is False  # type: ignore[index]
    runtime.assert_no_work_or_lifecycle_calls()


def _completed_request_state(state: str = "completed") -> AgUiObservedRequestState:
    """Return one terminal fake request state."""

    return AgUiObservedRequestState(
        request_id="request-1",
        request_kind="submit_prompt",
        state=state,
        accepted_at_utc="2026-06-08T01:00:00Z",
        finished_at_utc="2026-06-08T01:00:02Z",
        error_detail="boom" if state == "failed" else None,
    )


def _sse_payloads(response_text: str) -> list[dict[str, object]]:
    """Parse simple AG-UI SSE data frames from a response body."""

    payloads: list[dict[str, object]] = []
    for frame in response_text.split("\n\n"):
        if not frame.startswith("data: "):
            continue
        payloads.append(json.loads(frame.removeprefix("data: ")))
    return payloads


def test_runs_route_streams_headless_lifecycle_text_and_finished_event(tmp_path: Path) -> None:
    canonical_path = tmp_path / "canonical-events.jsonl"
    canonical_event = CanonicalHeadlessEvent(
        kind="assistant",
        message="assistant",
        turn_index=1,
        provider="codex",
        provider_event_type="assistant.text",
        data={"text": "hello from canonical"},
    )
    canonical_path.write_text(
        json.dumps(canonical_event.to_artifact_record(), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    runtime = _SpyRuntime(
        status_payload=_status(backend="codex_headless"),
        request_states=[_completed_request_state()],
        headless_events_path=canonical_path,
    )
    app = FastAPI()
    register_ag_ui_routes(app, runtime=runtime, run_poll_interval_seconds=0)
    client = TestClient(app)

    response = client.post("/v1/ag-ui/runs", json=_connect_payload())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    payloads = _sse_payloads(response.text)
    assert [payload["type"] for payload in payloads] == [
        "RUN_STARTED",
        "TEXT_MESSAGE_START",
        "TEXT_MESSAGE_CONTENT",
        "TEXT_MESSAGE_END",
        "RUN_FINISHED",
    ]
    assert payloads[0]["threadId"] == "thread-1"
    assert payloads[0]["runId"] == "run-1"
    assert payloads[2]["delta"] == "hello from canonical"
    assert runtime.created_requests[0].payload.turn_id == "run-1"  # type: ignore[union-attr]
    diagnostics = app.state.ag_ui_diagnostics
    assert diagnostics.active_counts() == {
        "activeAgUiConnections": 0,
        "activeAgUiRuns": 0,
    }
    event_names = [str(entry["event"]) for entry in runtime.diagnostics]
    assert "gateway.ag_ui_run_admitted" in event_names
    assert "gateway.ag_ui_run_stream_started" in event_names
    assert "gateway.ag_ui_run_stream_completed" in event_names
    rendered_diagnostics = json.dumps(runtime.diagnostics, sort_keys=True)
    assert "hello" not in rendered_diagnostics
    assert "Bearer secret" not in rendered_diagnostics
    runtime.assert_no_lifecycle_calls()


def test_runs_route_rejects_invalid_input_before_stream_or_work() -> None:
    runtime = _SpyRuntime(status_payload=_status(backend="codex_headless"))
    app = FastAPI()
    register_ag_ui_routes(app, runtime=runtime, run_poll_interval_seconds=0)
    client = TestClient(app)

    payload = _connect_payload(
        messages=[
            {
                "id": "message-1",
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "url", "value": "https://example.invalid/image.png"},
                    }
                ],
            }
        ]
    )
    response = client.post("/v1/ag-ui/runs", json=payload)

    assert response.status_code == 422
    assert "RUN_STARTED" not in response.text
    assert app.state.ag_ui_diagnostics.active_counts() == {
        "activeAgUiConnections": 0,
        "activeAgUiRuns": 0,
    }
    runtime.assert_no_work_or_lifecycle_calls()


def test_runs_route_rejects_busy_and_unavailable_targets_before_streaming() -> None:
    cases = [
        (_status(backend="codex_headless", active_execution="running"), 409),
        (_status(backend="codex_headless", queue_depth=1), 409),
        (_status(backend="codex_headless", request_admission="blocked_unavailable"), 503),
    ]
    for status_payload, status_code in cases:
        runtime = _SpyRuntime(status_payload=status_payload)
        app = FastAPI()
        register_ag_ui_routes(app, runtime=runtime, run_poll_interval_seconds=0)
        client = TestClient(app)

        response = client.post("/v1/ag-ui/runs", json=_connect_payload())

        assert response.status_code == status_code
        assert "RUN_STARTED" not in response.text
        assert app.state.ag_ui_diagnostics.active_counts() == {
            "activeAgUiConnections": 0,
            "activeAgUiRuns": 0,
        }
        runtime.assert_no_work_or_lifecycle_calls()


def test_runs_route_converts_post_admission_failure_to_run_error() -> None:
    runtime = _SpyRuntime(
        status_payload=_status(backend="codex_headless"),
        request_states=[_completed_request_state("failed")],
    )
    app = FastAPI()
    register_ag_ui_routes(app, runtime=runtime, run_poll_interval_seconds=0)
    client = TestClient(app)

    response = client.post("/v1/ag-ui/runs", json=_connect_payload())

    assert response.status_code == 200
    payloads = _sse_payloads(response.text)
    assert [payload["type"] for payload in payloads] == ["RUN_STARTED", "RUN_ERROR"]
    assert payloads[1]["message"] == "boom"
    assert app.state.ag_ui_diagnostics.active_counts() == {
        "activeAgUiConnections": 0,
        "activeAgUiRuns": 0,
    }
    runtime.assert_no_lifecycle_calls()


def test_runs_route_streams_tui_activity_and_final_text_without_tool_calls() -> None:
    runtime = _SpyRuntime(
        status_payload=_status(backend="local_interactive"),
        request_states=[_completed_request_state()],
    )
    app = FastAPI()
    register_ag_ui_routes(app, runtime=runtime, run_poll_interval_seconds=0)
    client = TestClient(app)

    response = client.post("/v1/ag-ui/runs", json=_connect_payload())

    assert response.status_code == 200
    payloads = _sse_payloads(response.text)
    event_types = [payload["type"] for payload in payloads]
    assert event_types == [
        "RUN_STARTED",
        "ACTIVITY_SNAPSHOT",
        "ACTIVITY_SNAPSHOT",
        "TEXT_MESSAGE_START",
        "TEXT_MESSAGE_CONTENT",
        "TEXT_MESSAGE_END",
        "RUN_FINISHED",
    ]
    assert payloads[4]["delta"] == "final TUI answer"
    assert "TOOL_CALL_START" not in set(event_types)
    runtime.assert_no_lifecycle_calls()


def test_run_stream_disconnect_detaches_without_lifecycle_calls() -> None:
    async def _run() -> None:
        from houmao.ag_ui.service import AgUiRunService

        class _DisconnectAfterStart:
            async def is_disconnected(self) -> bool:
                return True

        runtime = _SpyRuntime(status_payload=_status(backend="codex_headless"))
        service = AgUiRunService(runtime=runtime, poll_interval_seconds=0)  # type: ignore[arg-type]
        admitted = service.admit_run(AgUiConnectInput.model_validate(_connect_payload()))
        stream = service.stream_run_events(admitted_run=admitted, request=_DisconnectAfterStart())

        first_event = await anext(stream)
        assert first_event.model_dump(mode="json", by_alias=True)["type"] == "RUN_STARTED"
        try:
            await anext(stream)
        except StopAsyncIteration:
            pass
        else:  # pragma: no cover - defensive assertion
            raise AssertionError("stream should stop after disconnect")

        assert runtime.queued_requests == 1
        runtime.assert_no_lifecycle_calls()

    asyncio.run(_run())


def test_run_stream_client_abort_records_detach_and_cleans_active_count() -> None:
    async def _run() -> None:
        from houmao.ag_ui.service import AgUiRunService

        class _DisconnectAfterStart:
            async def is_disconnected(self) -> bool:
                return True

        runtime = _SpyRuntime(status_payload=_status(backend="codex_headless"))
        diagnostics = AgUiDiagnostics(runtime=runtime)
        service = AgUiRunService(runtime=runtime, poll_interval_seconds=0)  # type: ignore[arg-type]
        admitted = service.admit_run(AgUiConnectInput.model_validate(_connect_payload()))
        stream = run_event_stream(
            service=service,
            admitted_run=admitted,
            request=_DisconnectAfterStart(),
            diagnostics=diagnostics,
        )

        first_frame = await anext(stream)
        assert json.loads(first_frame.removeprefix("data: ").removesuffix("\n\n"))["type"] == (
            "RUN_STARTED"
        )
        try:
            await anext(stream)
        except StopAsyncIteration:
            pass
        else:  # pragma: no cover - defensive assertion
            raise AssertionError("stream should stop after disconnect")

        assert diagnostics.active_counts() == {
            "activeAgUiConnections": 0,
            "activeAgUiRuns": 0,
        }
        event_names = [str(entry["event"]) for entry in runtime.diagnostics]
        assert "gateway.ag_ui_run_client_disconnected" in event_names
        assert "gateway.ag_ui_run_stream_completed" in event_names
        runtime.assert_no_lifecycle_calls()

    asyncio.run(_run())


def test_run_stream_encoder_error_emits_run_error_and_cleans_active_count(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    canonical_path = tmp_path / "canonical-events.jsonl"
    canonical_event = CanonicalHeadlessEvent(
        kind="assistant",
        message="assistant",
        turn_index=1,
        provider="codex",
        provider_event_type="assistant.text",
        data={"text": "hello from canonical"},
    )
    canonical_path.write_text(
        json.dumps(canonical_event.to_artifact_record(), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    runtime = _SpyRuntime(
        status_payload=_status(backend="codex_headless"),
        request_states=[_completed_request_state()],
        headless_events_path=canonical_path,
    )
    app = FastAPI()
    register_ag_ui_routes(app, runtime=runtime, run_poll_interval_seconds=0)
    original_encode = ag_ui_routes.encode_sse_event

    def _flaky_encode(event: object) -> str:
        payload = event.model_dump(mode="json", by_alias=True, exclude_none=True)  # type: ignore[attr-defined]
        if payload["type"] == "RUN_STARTED":
            return original_encode(event)  # type: ignore[arg-type]
        raise RuntimeError("encoder boom")

    monkeypatch.setattr(ag_ui_routes, "encode_sse_event", _flaky_encode)
    client = TestClient(app)

    response = client.post("/v1/ag-ui/runs", json=_connect_payload())

    assert response.status_code == 200
    payloads = _sse_payloads(response.text)
    assert [payload["type"] for payload in payloads] == ["RUN_STARTED", "RUN_ERROR"]
    assert payloads[1]["code"] == "houmao_run_stream_failed"
    assert app.state.ag_ui_diagnostics.active_counts() == {
        "activeAgUiConnections": 0,
        "activeAgUiRuns": 0,
    }
    stream_errors = [
        entry for entry in runtime.diagnostics if entry["event"] == "gateway.ag_ui_stream_error"
    ]
    assert stream_errors
    assert stream_errors[0]["fields"]["errorCategory"] == "RuntimeError"  # type: ignore[index]
    runtime.assert_no_lifecycle_calls()
