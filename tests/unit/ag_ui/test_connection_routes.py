from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from houmao.ag_ui.connection import AgUiConnectionRegistry
from houmao.ag_ui.models import AgUiConnectInput
from houmao.ag_ui.routes import connect_event_stream, register_ag_ui_routes
from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.agents.realm_controller.gateway_service import create_app


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

    def create_request(self, _payload: object) -> None:
        """Detect queued gateway request creation."""

        self.queued_requests += 1

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
        connect_input = AgUiConnectInput.model_validate(
            _connect_payload(lastSeenEventId="event-1")
        )
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
    assert body["houmao"]["features"]["taskRunSubmission"] is False
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
    runtime.assert_no_work_or_lifecycle_calls()


def test_runs_route_is_deterministically_unavailable_and_does_not_start_stream_or_work() -> None:
    runtime = _SpyRuntime()
    app = FastAPI()
    register_ag_ui_routes(app, runtime=runtime)
    client = TestClient(app)

    response = client.post("/v1/ag-ui/runs", json=_connect_payload())

    assert response.status_code == 501
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status": "unavailable",
        "code": "ag_ui_runs_unavailable",
        "detail": "AG-UI task runs are not enabled for this Houmao gateway milestone.",
    }
    assert "RUN_STARTED" not in response.text
    runtime.assert_no_work_or_lifecycle_calls()
