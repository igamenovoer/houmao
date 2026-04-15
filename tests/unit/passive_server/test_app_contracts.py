"""Tests for passive-server HTTP route contracts."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayControlInputResultV1,
    GatewayMailActionResponseV1,
    GatewayMailListResponseV1,
    GatewayMailNotifierMode,
    GatewayMailNotifierStatusV1,
    GatewayMailStatusV1,
    GatewayMailboxMessageV1,
    GatewayMailboxParticipantV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderCreateResultV1,
    GatewayReminderDeleteResultV1,
    GatewayReminderDefinitionV1,
    GatewayReminderListV1,
    GatewayReminderPutV1,
    GatewayReminderV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.models import SessionEvent
from houmao.agents.realm_controller.registry_models import RegistryGatewayV1
from houmao.passive_server.app import create_app
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, _summary_from_record
from houmao.passive_server.service import PassiveServerService
from houmao.server.models import (
    HoumaoManagedAgentGatewayPromptControlResponse,
    HoumaoTerminalSnapshotHistoryEntry,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedDiagnostics,
    HoumaoTrackedLastTurn,
    HoumaoTrackedSessionIdentity,
    HoumaoTrackedSurface,
    HoumaoTrackedTurn,
    HoumaoStabilityMetadata,
)
from tests.unit.passive_server.test_discovery import _make_record
from tests.unit.passive_server.test_headless_service import (
    _FakeHeadlessBackendSession,
    _FakeRuntimeController,
    _join_turn_worker,
    _seed_managed_handle,
)


def _make_client(tmp_path: object) -> TestClient:
    """Build a test client with an isolated runtime root and no real polling."""

    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=Path(str(tmp_path)),
    )
    svc = PassiveServerService(config=config)
    app = create_app(config=config, service=svc)

    # Patch discovery start/stop so the test doesn't spawn real polling threads.
    _orig_enter = app.router.lifespan_context

    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _patched_lifespan(a: object) -> AsyncIterator[None]:
        with (
            patch.object(svc.m_discovery, "start"),
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "start"),
            patch.object(svc.m_observation, "stop"),
            patch.object(svc.m_headless, "start"),
            patch.object(svc.m_headless, "stop"),
        ):
            async with _orig_enter(a) as val:
                yield val

    app.router.lifespan_context = _patched_lifespan  # type: ignore[assignment]
    return TestClient(app)


def test_passive_gateway_memory_routes_expose_resolve_without_reindex(tmp_path: object) -> None:
    """Passive proxy route inventory exposes path discovery and omits memo indexing."""

    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=Path(str(tmp_path)),
    )
    svc = PassiveServerService(config=config)
    app = create_app(config=config, service=svc)
    routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
        if method not in {"HEAD", "OPTIONS"}
    }

    assert (
        "POST",
        "/houmao/agents/{agent_ref}/gateway/memory/pages/resolve",
    ) in routes
    assert (
        "POST",
        "/houmao/agents/{agent_ref}/gateway/memory/reindex",
    ) not in routes


class TestHealthEndpoint:
    """GET /health."""

    def test_returns_200(self, tmp_path: object) -> None:
        client = _make_client(tmp_path)
        with client:
            resp = client.get("/health")
        assert resp.status_code == 200

    def test_identifies_passive_server(self, tmp_path: object) -> None:
        client = _make_client(tmp_path)
        with client:
            body = client.get("/health").json()
        assert body["houmao_service"] == "houmao-passive-server"
        assert body["status"] == "ok"

    def test_no_cao_fields(self, tmp_path: object) -> None:
        client = _make_client(tmp_path)
        with client:
            body = client.get("/health").json()
        assert "service" not in body
        assert "child_cao" not in body


class TestCurrentInstanceEndpoint:
    """GET /houmao/server/current-instance."""

    def test_returns_200(self, tmp_path: object) -> None:
        client = _make_client(tmp_path)
        with client:
            resp = client.get("/houmao/server/current-instance")
        assert resp.status_code == 200

    def test_contains_required_fields(self, tmp_path: object) -> None:
        client = _make_client(tmp_path)
        with client:
            body = client.get("/houmao/server/current-instance").json()
        assert body["schema_version"] == 1
        assert body["status"] == "ok"
        assert body["pid"] == os.getpid()
        assert body["api_base_url"] == "http://127.0.0.1:19891"
        assert "server_root" in body
        assert "started_at_utc" in body

    def test_no_child_cao_field(self, tmp_path: object) -> None:
        client = _make_client(tmp_path)
        with client:
            body = client.get("/houmao/server/current-instance").json()
        assert "child_cao" not in body


class TestShutdownEndpoint:
    """POST /houmao/server/shutdown."""

    def test_returns_200_with_ok(self, tmp_path: object, monkeypatch: object) -> None:
        """Verify response shape without actually killing the process."""

        import houmao.passive_server.service as svc_module

        # Neuter the deferred shutdown to avoid killing the test process.
        monkeypatch.setattr(svc_module.PassiveServerService, "request_shutdown", lambda self: None)

        client = _make_client(tmp_path)
        with client:
            resp = client.post("/houmao/server/shutdown")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Agent endpoint helpers
# ---------------------------------------------------------------------------


def _make_agent_client(tmp_path: object, agents: list[DiscoveredAgent]) -> TestClient:
    """Build a test client pre-populated with discovered agents."""

    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=Path(str(tmp_path)),
    )
    svc = PassiveServerService(config=config)
    svc.m_discovery.m_index.replace({a.record.agent_id: a for a in agents})
    app = create_app(config=config, service=svc)

    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    _orig_enter = app.router.lifespan_context

    @asynccontextmanager
    async def _patched_lifespan(a: object) -> AsyncIterator[None]:
        with (
            patch.object(svc.m_discovery, "start"),
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "start"),
            patch.object(svc.m_observation, "stop"),
            patch.object(svc.m_headless, "start"),
            patch.object(svc.m_headless, "stop"),
        ):
            async with _orig_enter(a) as val:
                yield val

    app.router.lifespan_context = _patched_lifespan  # type: ignore[assignment]
    return TestClient(app)


def _agent(
    agent_id: str = "abc123",
    agent_name: str = "HOUMAO-alpha",
    session_name: str = "HOUMAO-alpha-abc123",
    *,
    tool: str = "claude",
    backend: str = "claude_headless",
) -> DiscoveredAgent:
    record = _make_record(
        agent_id=agent_id,
        agent_name=agent_name,
        session_name=session_name,
        tool=tool,
        backend=backend,
    )
    return DiscoveredAgent(record=record, summary=_summary_from_record(record))


# ---------------------------------------------------------------------------
# Agent listing endpoint
# ---------------------------------------------------------------------------


class TestListAgentsEndpoint:
    """GET /houmao/agents."""

    def test_returns_200_with_agents(self, tmp_path: object) -> None:
        a1 = _agent(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1")
        a2 = _agent(agent_id="b1", agent_name="HOUMAO-beta", session_name="s2")
        client = _make_agent_client(tmp_path, [a1, a2])
        with client:
            resp = client.get("/houmao/agents")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["agents"]) == 2
        assert body["agents"][0]["agent_name"] == "HOUMAO-alpha"
        assert body["agents"][1]["agent_name"] == "HOUMAO-beta"

    def test_returns_200_empty(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents")
        assert resp.status_code == 200
        assert resp.json()["agents"] == []

    def test_agent_fields_present(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents")
        agent = resp.json()["agents"][0]
        for field in (
            "agent_id",
            "agent_name",
            "generation_id",
            "tool",
            "backend",
            "tmux_session_name",
            "manifest_path",
            "session_root",
            "has_gateway",
            "has_mailbox",
            "published_at",
            "lease_expires_at",
        ):
            assert field in agent, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Agent resolution endpoint
# ---------------------------------------------------------------------------


class TestResolveAgentEndpoint:
    """GET /houmao/agents/{agent_ref}."""

    def test_resolve_by_id_returns_200(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent(agent_id="abc123")])
        with client:
            resp = client.get("/houmao/agents/abc123")
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == "abc123"

    def test_resolve_by_name_returns_200(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent(agent_name="HOUMAO-alpha")])
        with client:
            resp = client.get("/houmao/agents/alpha")
        assert resp.status_code == 200
        assert resp.json()["agent_name"] == "HOUMAO-alpha"

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/nonexistent")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    def test_ambiguous_returns_409(self, tmp_path: object) -> None:
        a1 = _agent(agent_id="abc123", agent_name="HOUMAO-alpha", session_name="s1")
        a2 = _agent(agent_id="def456", agent_name="HOUMAO-alpha", session_name="s2")
        client = _make_agent_client(tmp_path, [a1, a2])
        with client:
            resp = client.get("/houmao/agents/alpha")
        assert resp.status_code == 409
        body = resp.json()
        assert "agent_ids" in body
        assert set(body["agent_ids"]) == {"abc123", "def456"}


# ---------------------------------------------------------------------------
# Gateway proxy endpoint helpers
# ---------------------------------------------------------------------------


def _agent_with_gateway(
    agent_id: str = "abc123",
    agent_name: str = "HOUMAO-alpha",
    session_name: str = "HOUMAO-alpha-abc123",
    gateway_host: str = "127.0.0.1",
    gateway_port: int = 9901,
) -> DiscoveredAgent:
    """Create a DiscoveredAgent with live gateway coordinates."""

    record = _make_record(agent_id=agent_id, agent_name=agent_name, session_name=session_name)
    record.gateway = RegistryGatewayV1(
        host=gateway_host,  # type: ignore[arg-type]
        port=gateway_port,
        state_path="/tmp/gw/state.json",
        protocol_version="v1",
    )
    return DiscoveredAgent(record=record, summary=_summary_from_record(record))


def _stub_gateway_status() -> GatewayStatusV1:
    """Create a minimal valid GatewayStatusV1 for mocking."""

    return GatewayStatusV1(
        attach_identity="test",
        backend="claude_headless",
        tmux_session_name="sess",
        gateway_health="healthy",
        managed_agent_connectivity="connected",
        managed_agent_recovery="idle",
        request_admission="open",
        terminal_surface_eligibility="ready",
        active_execution="idle",
        queue_depth=0,
        gateway_host="127.0.0.1",
        gateway_port=9901,
        managed_agent_instance_epoch=1,
    )


def _stub_accepted_request() -> GatewayAcceptedRequestV1:
    """Create a minimal valid GatewayAcceptedRequestV1 for mocking."""

    return GatewayAcceptedRequestV1(
        request_id="r1",
        request_kind="submit_prompt",
        state="accepted",
        accepted_at_utc="2026-01-01T00:00:00Z",
        queue_depth=1,
        managed_agent_instance_epoch=1,
    )


def _stub_control_input_result() -> GatewayControlInputResultV1:
    """Create a minimal valid GatewayControlInputResultV1 for mocking."""

    return GatewayControlInputResultV1(detail="delivered")


def _stub_prompt_control_result() -> HoumaoManagedAgentGatewayPromptControlResponse:
    """Create a minimal valid prompt-control response for mocking."""

    return HoumaoManagedAgentGatewayPromptControlResponse(
        sent=True,
        forced=False,
        detail="Prompt dispatched.",
    )


def _stub_mail_status() -> GatewayMailStatusV1:
    """Create a minimal valid GatewayMailStatusV1 for mocking."""

    return GatewayMailStatusV1(
        transport="filesystem",
        principal_id="p1",
        address="agent@local",
        bindings_version="v1",
    )


def _stub_mail_list_response() -> GatewayMailListResponseV1:
    """Create a minimal valid GatewayMailListResponseV1 for mocking."""

    return GatewayMailListResponseV1(
        transport="filesystem",
        principal_id="p1",
        address="agent@local",
        box="inbox",
        message_count=0,
        open_count=0,
        unread_count=0,
        messages=[],
    )


def _stub_mail_action_response(operation: str = "send") -> GatewayMailActionResponseV1:
    """Create a minimal valid GatewayMailActionResponseV1 for mocking."""

    return GatewayMailActionResponseV1(
        operation=operation,  # type: ignore[arg-type]
        transport="filesystem",
        principal_id="p1",
        address="agent@local",
        message=GatewayMailboxMessageV1(
            message_ref="msg-1",
            created_at_utc="2026-01-01T00:00:00Z",
            subject="Test",
            sender=GatewayMailboxParticipantV1(address="sender@local"),
            to=[GatewayMailboxParticipantV1(address="recipient@local")],
        ),
    )


def _stub_mail_notifier_status(
    *,
    enabled: bool,
    interval_seconds: int | None,
    mode: GatewayMailNotifierMode = "any_inbox",
) -> GatewayMailNotifierStatusV1:
    """Create a minimal valid GatewayMailNotifierStatusV1 for mocking."""

    return GatewayMailNotifierStatusV1(
        enabled=enabled,
        interval_seconds=interval_seconds,
        mode=mode,
        supported=True,
        support_error=None,
        last_poll_at_utc=None,
        last_notification_at_utc=None,
        last_error=None,
    )


def _stub_reminder(
    *,
    reminder_id: str = "greminder-1",
    ranking: int = 0,
    selection_state: str = "effective",
    blocked_by_reminder_id: str | None = None,
) -> GatewayReminderV1:
    """Create a minimal valid GatewayReminderV1 for mocking."""

    return GatewayReminderV1(
        reminder_id=reminder_id,
        mode="one_off",
        delivery_kind="prompt",
        title="Check inbox",
        prompt="Review the inbox now.",
        ranking=ranking,
        paused=False,
        selection_state=selection_state,  # type: ignore[arg-type]
        delivery_state="scheduled",
        created_at_utc="2026-04-09T00:00:00+00:00",
        next_due_at_utc="2026-04-09T00:05:00+00:00",
        blocked_by_reminder_id=blocked_by_reminder_id,
    )


def _stub_reminder_list() -> GatewayReminderListV1:
    """Create a minimal valid GatewayReminderListV1 for mocking."""

    reminder = _stub_reminder()
    return GatewayReminderListV1(
        effective_reminder_id=reminder.reminder_id,
        reminders=[reminder],
    )


def _stub_reminder_create_result() -> GatewayReminderCreateResultV1:
    """Create a minimal valid GatewayReminderCreateResultV1 for mocking."""

    reminder = _stub_reminder()
    return GatewayReminderCreateResultV1(
        effective_reminder_id=reminder.reminder_id,
        reminders=[reminder],
    )


def _stub_reminder_delete_result() -> GatewayReminderDeleteResultV1:
    """Create a minimal valid GatewayReminderDeleteResultV1 for mocking."""

    return GatewayReminderDeleteResultV1(
        reminder_id="greminder-1",
        detail="deleted",
    )


def _stub_tui_state() -> HoumaoTerminalStateResponse:
    """Create a minimal valid HoumaoTerminalStateResponse for gateway TUI mocks."""

    return HoumaoTerminalStateResponse(
        terminal_id="term-123",
        tracked_session=HoumaoTrackedSessionIdentity(
            tracked_session_id="tracked-123",
            session_name="HOUMAO-alpha-abc123",
            tool="claude",
            tmux_session_name="HOUMAO-alpha-abc123",
            terminal_aliases=["term-123"],
        ),
        diagnostics=HoumaoTrackedDiagnostics(
            availability="available",
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status="parsed",
            probe_error=None,
            parse_error=None,
        ),
        probe_snapshot=None,
        parsed_surface=None,
        surface=HoumaoTrackedSurface(
            accepting_input="yes",
            editing_input="no",
            ready_posture="yes",
        ),
        turn=HoumaoTrackedTurn(phase="ready"),
        last_turn=HoumaoTrackedLastTurn(result="none", source="none", updated_at_utc=None),
        stability=HoumaoStabilityMetadata(
            signature="stable",
            stable=True,
            stable_for_seconds=3.0,
            stable_since_utc="2026-03-27T00:00:00+00:00",
        ),
        recent_transitions=[],
    )


def _stub_tui_history(limit: int) -> HoumaoTerminalSnapshotHistoryResponse:
    """Create a minimal valid snapshot history response for gateway TUI mocks."""

    state = _stub_tui_state()
    return HoumaoTerminalSnapshotHistoryResponse(
        terminal_id=state.terminal_id,
        tracked_session_id=state.tracked_session.tracked_session_id,
        entries=[
            HoumaoTerminalSnapshotHistoryEntry(
                recorded_at_utc="2026-03-27T00:00:00+00:00",
                diagnostics=state.diagnostics,
                probe_snapshot=None,
                parsed_surface=None,
                surface=state.surface,
                turn=state.turn,
                last_turn=state.last_turn,
                stability=state.stability.model_copy(update={"signature": f"history-{limit}"}),
            )
        ],
    )


# ---------------------------------------------------------------------------
# Gateway status endpoint
# ---------------------------------------------------------------------------


class TestGatewayStatusEndpoint:
    """GET /houmao/agents/{agent_ref}/gateway."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client, patch.object(GatewayClient, "status", return_value=_stub_gateway_status()):
            resp = client.get("/houmao/agents/abc123/gateway")
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/nonexistent/gateway")
        assert resp.status_code == 404

    def test_ambiguous_returns_409(self, tmp_path: object) -> None:
        a1 = _agent_with_gateway(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1")
        a2 = _agent_with_gateway(agent_id="a2", agent_name="HOUMAO-alpha", session_name="s2")
        client = _make_agent_client(tmp_path, [a1, a2])
        with client:
            resp = client.get("/houmao/agents/alpha/gateway")
        assert resp.status_code == 409

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/gateway")
        assert resp.status_code == 502

    def test_gateway_error_returns_502(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "status",
                side_effect=GatewayHttpError(
                    method="GET", url="http://127.0.0.1:9901/v1/status", detail="refused"
                ),
            ),
        ):
            resp = client.get("/houmao/agents/abc123/gateway")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Gateway TUI endpoints
# ---------------------------------------------------------------------------


class TestGatewayTuiEndpoint:
    """GET|POST /houmao/agents/{agent_ref}/gateway/tui/*."""

    def test_state_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client, patch.object(GatewayClient, "get_tui_state", return_value=_stub_tui_state()):
            resp = client.get("/houmao/agents/abc123/gateway/tui/state")
        assert resp.status_code == 200

    def test_history_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "get_tui_history",
                side_effect=lambda *, limit: _stub_tui_history(limit),
            ),
        ):
            resp = client.get("/houmao/agents/abc123/gateway/tui/history?limit=7")
        assert resp.status_code == 200
        assert resp.json()["entries"][0]["stability"]["signature"] == "history-7"

    def test_note_prompt_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "note_tui_prompt_submission",
                return_value=_stub_tui_state(),
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/gateway/tui/note-prompt",
                json={"prompt": "hello"},
            )
        assert resp.status_code == 200

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/gateway/tui/state")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Gateway request submission endpoint
# ---------------------------------------------------------------------------


class TestGatewayCreateRequestEndpoint:
    """POST /houmao/agents/{agent_ref}/gateway/requests."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(GatewayClient, "create_request", return_value=_stub_accepted_request()),
        ):
            resp = client.post(
                "/houmao/agents/abc123/gateway/requests",
                json={
                    "schema_version": 1,
                    "kind": "submit_prompt",
                    "payload": {"prompt": "hello"},
                },
            )
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post(
                "/houmao/agents/unknown/gateway/requests",
                json={
                    "schema_version": 1,
                    "kind": "submit_prompt",
                    "payload": {"prompt": "hello"},
                },
            )
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post(
                "/houmao/agents/abc123/gateway/requests",
                json={
                    "schema_version": 1,
                    "kind": "submit_prompt",
                    "payload": {"prompt": "hello"},
                },
            )
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Gateway prompt-control endpoint
# ---------------------------------------------------------------------------


class TestGatewayPromptControlEndpoint:
    """POST /houmao/agents/{agent_ref}/gateway/control/prompt."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient, "control_prompt", return_value=_stub_prompt_control_result()
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/gateway/control/prompt",
                json={"schema_version": 1, "prompt": "hello", "force": True},
            )
        assert resp.status_code == 200
        assert resp.json()["sent"] is True
        assert resp.json()["forced"] is False

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post(
                "/houmao/agents/unknown/gateway/control/prompt",
                json={"schema_version": 1, "prompt": "hello", "force": False},
            )
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post(
                "/houmao/agents/abc123/gateway/control/prompt",
                json={"schema_version": 1, "prompt": "hello", "force": False},
            )
        assert resp.status_code == 502

    def test_gateway_error_preserves_status_and_structured_detail(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "control_prompt",
                side_effect=GatewayHttpError(
                    method="POST",
                    url="http://127.0.0.1:9901/v1/control/prompt",
                    status_code=409,
                    detail='{"action":"submit_prompt","detail":"not ready","error_code":"not_ready","forced":false,"sent":false,"status":"error"}',
                ),
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/gateway/control/prompt",
                json={"schema_version": 1, "prompt": "hello", "force": False},
            )
        assert resp.status_code == 409
        assert resp.json()["detail"]["error_code"] == "not_ready"


# ---------------------------------------------------------------------------
# Gateway control-input endpoint
# ---------------------------------------------------------------------------


class TestGatewayControlInputEndpoint:
    """POST /houmao/agents/{agent_ref}/gateway/control/send-keys."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "send_control_input",
                return_value=_stub_control_input_result(),
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/gateway/control/send-keys",
                json={
                    "sequence": "<[Escape]>",
                    "escape_special_keys": False,
                },
            )
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post(
                "/houmao/agents/unknown/gateway/control/send-keys",
                json={
                    "sequence": "<[Escape]>",
                    "escape_special_keys": False,
                },
            )
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post(
                "/houmao/agents/abc123/gateway/control/send-keys",
                json={
                    "sequence": "<[Escape]>",
                    "escape_special_keys": False,
                },
            )
        assert resp.status_code == 502

    def test_gateway_error_returns_502(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "send_control_input",
                side_effect=GatewayHttpError(
                    method="POST",
                    url="http://127.0.0.1:9901/v1/control/send-keys",
                    detail="refused",
                ),
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/gateway/control/send-keys",
                json={
                    "sequence": "<[Escape]>",
                    "escape_special_keys": False,
                },
            )
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Gateway mail-notifier endpoints
# ---------------------------------------------------------------------------


class TestGatewayMailNotifierEndpoint:
    """GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier."""

    def test_status_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "get_mail_notifier",
                return_value=_stub_mail_notifier_status(enabled=False, interval_seconds=None),
            ),
        ):
            resp = client.get("/houmao/agents/abc123/gateway/mail-notifier")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "any_inbox"

    def test_enable_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "put_mail_notifier",
                return_value=_stub_mail_notifier_status(
                    enabled=True,
                    interval_seconds=60,
                    mode="unread_only",
                ),
            ) as put_mail_notifier,
        ):
            resp = client.put(
                "/houmao/agents/abc123/gateway/mail-notifier",
                json={"schema_version": 1, "interval_seconds": 60, "mode": "unread_only"},
            )
        assert resp.status_code == 200
        assert resp.json()["mode"] == "unread_only"
        assert put_mail_notifier.call_args.args[0].mode == "unread_only"

    def test_enable_rejects_invalid_mode(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client:
            resp = client.put(
                "/houmao/agents/abc123/gateway/mail-notifier",
                json={"schema_version": 1, "interval_seconds": 60, "mode": "bad_mode"},
            )
        assert resp.status_code == 422

    def test_disable_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "delete_mail_notifier",
                return_value=_stub_mail_notifier_status(enabled=False, interval_seconds=None),
            ),
        ):
            resp = client.delete("/houmao/agents/abc123/gateway/mail-notifier")
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/unknown/gateway/mail-notifier")
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/gateway/mail-notifier")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Gateway reminder endpoints
# ---------------------------------------------------------------------------


class TestGatewayReminderEndpoints:
    """Reminder proxy routes under `/houmao/agents/{agent_ref}/gateway/reminders...`."""

    def test_list_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(GatewayClient, "list_reminders", return_value=_stub_reminder_list()),
        ):
            resp = client.get("/houmao/agents/abc123/gateway/reminders")
        assert resp.status_code == 200

    def test_create_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        request_model = GatewayReminderCreateBatchV1(
            reminders=[
                GatewayReminderDefinitionV1(
                    mode="one_off",
                    title="Check inbox",
                    prompt="Review the inbox now.",
                    ranking=0,
                    start_after_seconds=60,
                )
            ]
        )
        with (
            client,
            patch.object(
                GatewayClient,
                "create_reminders",
                return_value=_stub_reminder_create_result(),
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/gateway/reminders",
                json=request_model.model_dump(mode="json"),
            )
        assert resp.status_code == 200

    def test_get_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client, patch.object(GatewayClient, "get_reminder", return_value=_stub_reminder()):
            resp = client.get("/houmao/agents/abc123/gateway/reminders/greminder-1")
        assert resp.status_code == 200

    def test_put_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        request_model = GatewayReminderPutV1(
            mode="one_off",
            title="Check inbox later",
            prompt="Review the inbox later.",
            ranking=1,
            deliver_at_utc="2026-04-09T12:00:00+00:00",
        )
        with client, patch.object(GatewayClient, "put_reminder", return_value=_stub_reminder()):
            resp = client.put(
                "/houmao/agents/abc123/gateway/reminders/greminder-1",
                json=request_model.model_dump(mode="json"),
            )
        assert resp.status_code == 200

    def test_delete_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "delete_reminder",
                return_value=_stub_reminder_delete_result(),
            ),
        ):
            resp = client.delete("/houmao/agents/abc123/gateway/reminders/greminder-1")
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/unknown/gateway/reminders")
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/gateway/reminders")
        assert resp.status_code == 502

    def test_gateway_error_status_is_preserved(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "put_reminder",
                side_effect=GatewayHttpError(
                    method="PUT",
                    url="http://127.0.0.1:9901/v1/reminders/greminder-1",
                    status_code=409,
                    detail="busy",
                ),
            ),
        ):
            resp = client.put(
                "/houmao/agents/abc123/gateway/reminders/greminder-1",
                json={
                    "schema_version": 1,
                    "mode": "one_off",
                    "title": "later",
                    "prompt": "later",
                    "ranking": 0,
                    "deliver_at_utc": "2026-04-09T12:00:00+00:00",
                },
            )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Mail status endpoint
# ---------------------------------------------------------------------------


class TestGatewayMailStatusEndpoint:
    """GET /houmao/agents/{agent_ref}/mail/status."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client, patch.object(GatewayClient, "mail_status", return_value=_stub_mail_status()):
            resp = client.get("/houmao/agents/abc123/mail/status")
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/unknown/mail/status")
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/mail/status")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Mail list endpoint
# ---------------------------------------------------------------------------


class TestGatewayMailListEndpoint:
    """POST /houmao/agents/{agent_ref}/mail/list."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(GatewayClient, "list_mail", return_value=_stub_mail_list_response()),
        ):
            resp = client.post(
                "/houmao/agents/abc123/mail/list",
                json={"schema_version": 1},
            )
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post(
                "/houmao/agents/unknown/mail/list",
                json={"schema_version": 1},
            )
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post(
                "/houmao/agents/abc123/mail/list",
                json={"schema_version": 1},
            )
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Mail send endpoint
# ---------------------------------------------------------------------------


class TestGatewayMailSendEndpoint:
    """POST /houmao/agents/{agent_ref}/mail/send."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient, "send_mail", return_value=_stub_mail_action_response("send")
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/mail/send",
                json={
                    "schema_version": 1,
                    "to": ["user@example.com"],
                    "subject": "Test",
                    "body_content": "Hello",
                },
            )
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post(
                "/houmao/agents/unknown/mail/send",
                json={
                    "schema_version": 1,
                    "to": ["user@example.com"],
                    "subject": "Test",
                    "body_content": "Hello",
                },
            )
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post(
                "/houmao/agents/abc123/mail/send",
                json={
                    "schema_version": 1,
                    "to": ["user@example.com"],
                    "subject": "Test",
                    "body_content": "Hello",
                },
            )
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Mail post endpoint
# ---------------------------------------------------------------------------


class TestGatewayMailPostEndpoint:
    """POST /houmao/agents/{agent_ref}/mail/post."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient, "post_mail", return_value=_stub_mail_action_response("post")
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/mail/post",
                json={
                    "schema_version": 1,
                    "subject": "Operator note",
                    "body_content": "Hello",
                },
            )
        assert resp.status_code == 200

    def test_gateway_http_status_is_preserved(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient,
                "post_mail",
                side_effect=GatewayHttpError(
                    method="POST",
                    url="http://gateway/v1/mail/post",
                    detail="unsupported for current transport",
                    status_code=422,
                ),
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/mail/post",
                json={
                    "schema_version": 1,
                    "subject": "Operator note",
                    "body_content": "Hello",
                },
            )
        assert resp.status_code == 422

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post(
                "/houmao/agents/abc123/mail/post",
                json={
                    "schema_version": 1,
                    "subject": "Operator note",
                    "body_content": "Hello",
                },
            )
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Mail reply endpoint
# ---------------------------------------------------------------------------


class TestGatewayMailReplyEndpoint:
    """POST /houmao/agents/{agent_ref}/mail/reply."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with (
            client,
            patch.object(
                GatewayClient, "reply_mail", return_value=_stub_mail_action_response("reply")
            ),
        ):
            resp = client.post(
                "/houmao/agents/abc123/mail/reply",
                json={
                    "schema_version": 1,
                    "message_ref": "msg-1",
                    "body_content": "Reply text",
                },
            )
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post(
                "/houmao/agents/unknown/mail/reply",
                json={
                    "schema_version": 1,
                    "message_ref": "msg-1",
                    "body_content": "Reply text",
                },
            )
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post(
                "/houmao/agents/abc123/mail/reply",
                json={
                    "schema_version": 1,
                    "message_ref": "msg-1",
                    "body_content": "Reply text",
                },
            )
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# TUI observation endpoint helpers
# ---------------------------------------------------------------------------


def _make_agent_client_with_observer(
    tmp_path: object,
    agents: list[DiscoveredAgent],
    *,
    reconcile: bool = True,
) -> TestClient:
    """Build a test client pre-populated with agents and reconciled observers."""

    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=Path(str(tmp_path)),
    )
    svc = PassiveServerService(config=config)
    svc.m_discovery.m_index.replace({a.record.agent_id: a for a in agents})
    if reconcile and agents:
        svc.m_observation._reconcile_observers(svc.m_discovery.index.list_all())
    app = create_app(config=config, service=svc)

    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    _orig_enter = app.router.lifespan_context

    @asynccontextmanager
    async def _patched_lifespan(a: object) -> AsyncIterator[None]:
        with (
            patch.object(svc.m_discovery, "start"),
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "start"),
            patch.object(svc.m_observation, "stop"),
            patch.object(svc.m_headless, "start"),
            patch.object(svc.m_headless, "stop"),
        ):
            async with _orig_enter(a) as val:
                yield val

    app.router.lifespan_context = _patched_lifespan  # type: ignore[assignment]
    return TestClient(app)


def _make_managed_headless_client(tmp_path: object) -> tuple[TestClient, str]:
    """Build a test client with one live passive-managed headless agent."""

    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=Path(str(tmp_path)),
    )
    svc = PassiveServerService(config=config)

    def _send_prompt(prompt: str, *, turn_artifact_dir_name: str | None) -> list[SessionEvent]:
        del prompt
        assert turn_artifact_dir_name is not None
        turn_dir = (
            svc.m_headless.m_store.agent_root(tracked_agent_id="tracked-alpha")
            / "artifacts"
            / turn_artifact_dir_name
        )
        turn_dir.mkdir(parents=True, exist_ok=True)
        (turn_dir / "stdout.jsonl").write_text(
            '{"type":"assistant","message":"hello from worker"}\n',
            encoding="utf-8",
        )
        (turn_dir / "stderr.log").write_text("warning line\n", encoding="utf-8")
        (turn_dir / "exitcode").write_text("0\n", encoding="utf-8")
        return [
            SessionEvent(
                kind="done",
                message="turn completed",
                turn_index=1,
                payload={"completion_source": "process_exit"},
            )
        ]

    controller = _FakeRuntimeController(
        manifest_path=Path(str(tmp_path)) / "runtime" / "tracked-alpha" / "manifest.json",
        backend_session=_FakeHeadlessBackendSession(send_prompt_callback=_send_prompt),
    )
    controller.launch_plan.mailbox = None
    _seed_managed_handle(
        svc,
        tracked_agent_id="tracked-alpha",
        agent_name="HOUMAO-alpha",
        agent_id="published-alpha",
        controller=controller,
    )
    accepted = svc.m_headless.submit_turn("tracked-alpha", "hello")
    assert not isinstance(accepted, tuple)
    _join_turn_worker(svc.m_headless, "tracked-alpha")

    app = create_app(config=config, service=svc)

    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    _orig_enter = app.router.lifespan_context

    @asynccontextmanager
    async def _patched_lifespan(a: object) -> AsyncIterator[None]:
        with (
            patch.object(svc.m_discovery, "start"),
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "start"),
            patch.object(svc.m_observation, "stop"),
            patch.object(svc.m_headless, "start"),
            patch.object(svc.m_headless, "stop"),
            patch("houmao.passive_server.headless.tmux_session_exists", return_value=True),
        ):
            async with _orig_enter(a) as val:
                yield val

    app.router.lifespan_context = _patched_lifespan  # type: ignore[assignment]
    return TestClient(app), accepted.turn_id


# ---------------------------------------------------------------------------
# Agent state endpoint
# ---------------------------------------------------------------------------


class TestAgentStateEndpoint:
    """GET /houmao/agents/{agent_ref}/state."""

    def test_returns_200_with_observer(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/state")
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == "abc123"
        assert "diagnostics" in body
        assert "surface" in body
        assert "turn" in body
        assert "last_turn" in body
        assert "stability" in body
        # Compact state should NOT include probe_snapshot or parsed_surface
        assert "probe_snapshot" not in body
        assert "parsed_surface" not in body

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/nonexistent/state")
        assert resp.status_code == 404

    def test_ambiguous_returns_409(self, tmp_path: object) -> None:
        a1 = _agent(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1")
        a2 = _agent(agent_id="a2", agent_name="HOUMAO-alpha", session_name="s2")
        client = _make_agent_client_with_observer(tmp_path, [a1, a2])
        with client:
            resp = client.get("/houmao/agents/alpha/state")
        assert resp.status_code == 409

    def test_no_observer_returns_503(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [_agent()], reconcile=False)
        with client:
            resp = client.get("/houmao/agents/abc123/state")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Agent state detail endpoint
# ---------------------------------------------------------------------------


class TestAgentStateDetailEndpoint:
    """GET /houmao/agents/{agent_ref}/state/detail."""

    def test_returns_200_with_observer(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/state/detail")
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == "abc123"
        assert "diagnostics" in body
        assert "surface" in body
        # Detail response includes probe_snapshot and parsed_surface keys
        assert "probe_snapshot" in body
        assert "parsed_surface" in body

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/nonexistent/state/detail")
        assert resp.status_code == 404

    def test_ambiguous_returns_409(self, tmp_path: object) -> None:
        a1 = _agent(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1")
        a2 = _agent(agent_id="a2", agent_name="HOUMAO-alpha", session_name="s2")
        client = _make_agent_client_with_observer(tmp_path, [a1, a2])
        with client:
            resp = client.get("/houmao/agents/alpha/state/detail")
        assert resp.status_code == 409

    def test_no_observer_returns_503(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [_agent()], reconcile=False)
        with client:
            resp = client.get("/houmao/agents/abc123/state/detail")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Agent history endpoint
# ---------------------------------------------------------------------------


class TestAgentHistoryEndpoint:
    """GET /houmao/agents/{agent_ref}/history."""

    def test_returns_200_with_observer(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == "abc123"
        assert "entries" in body
        assert isinstance(body["entries"], list)

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/nonexistent/history")
        assert resp.status_code == 404

    def test_ambiguous_returns_409(self, tmp_path: object) -> None:
        a1 = _agent(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1")
        a2 = _agent(agent_id="a2", agent_name="HOUMAO-alpha", session_name="s2")
        client = _make_agent_client_with_observer(tmp_path, [a1, a2])
        with client:
            resp = client.get("/houmao/agents/alpha/history")
        assert resp.status_code == 409

    def test_no_observer_returns_503(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [_agent()], reconcile=False)
        with client:
            resp = client.get("/houmao/agents/abc123/history")
        assert resp.status_code == 503

    def test_limit_query_parameter(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/history?limit=10")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Managed compatibility routes
# ---------------------------------------------------------------------------


class TestManagedCompatibilityRoutes:
    """Pair-facing managed-agent compatibility routes."""

    def test_managed_state_returns_tui_summary(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(
            tmp_path,
            [_agent(tool="codex", backend="codex_app_server")],
        )

        with client:
            resp = client.get("/houmao/agents/abc123/managed-state")

        assert resp.status_code == 200
        body = resp.json()
        assert body["tracked_agent_id"] == "abc123"
        assert body["identity"]["transport"] == "tui"
        assert "turn" in body

    def test_managed_state_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client_with_observer(tmp_path, [])

        with client:
            resp = client.get("/houmao/agents/nonexistent/managed-state")

        assert resp.status_code == 404

    def test_managed_state_ambiguous_returns_409(self, tmp_path: object) -> None:
        a1 = _agent(
            agent_id="a1",
            agent_name="HOUMAO-alpha",
            session_name="s1",
            tool="codex",
            backend="codex_app_server",
        )
        a2 = _agent(
            agent_id="a2",
            agent_name="HOUMAO-alpha",
            session_name="s2",
            tool="codex",
            backend="codex_app_server",
        )
        client = _make_agent_client_with_observer(tmp_path, [a1, a2])

        with client:
            resp = client.get("/houmao/agents/alpha/managed-state")

        assert resp.status_code == 409

    def test_managed_state_detail_returns_headless_view(self, tmp_path: object) -> None:
        client, turn_id = _make_managed_headless_client(tmp_path)

        with client:
            resp = client.get("/houmao/agents/published-alpha/managed-state/detail")

        assert resp.status_code == 200
        body = resp.json()
        assert body["identity"]["transport"] == "headless"
        assert body["detail"]["transport"] == "headless"
        assert body["detail"]["runtime_resumable"] is True
        assert body["detail"]["tmux_session_live"] is True
        assert body["detail"]["can_accept_prompt_now"] is True
        assert body["detail"]["interruptible"] is False
        assert body["detail"]["last_turn"]["turn_id"] == turn_id

    def test_managed_history_returns_headless_history(self, tmp_path: object) -> None:
        client, turn_id = _make_managed_headless_client(tmp_path)

        with client:
            resp = client.get("/houmao/agents/published-alpha/managed-history")

        assert resp.status_code == 200
        body = resp.json()
        assert body["tracked_agent_id"] == "tracked-alpha"
        assert len(body["entries"]) == 1
        assert body["entries"][0]["turn_id"] == turn_id

    def test_managed_headless_detail_returns_503_for_non_owned_headless(
        self,
        tmp_path: object,
    ) -> None:
        client = _make_agent_client(
            tmp_path, [_agent(agent_id="abc123", backend="claude_headless")]
        )

        with client:
            resp = client.get("/houmao/agents/abc123/managed-state/detail")

        assert resp.status_code == 503
        assert "not owned by the current passive server" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Gateway attach/detach stub endpoints (Tier 5)
# ---------------------------------------------------------------------------


class TestGatewayAttachStub:
    """POST /houmao/agents/{agent_ref}/gateway/attach → 501."""

    def test_returns_501(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post("/houmao/agents/abc123/gateway/attach")
        assert resp.status_code == 501

    def test_detail_mentions_houmao_mgr(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            body = client.post("/houmao/agents/abc123/gateway/attach").json()
        assert "houmao-mgr" in body["detail"]

    def test_detail_includes_agent_ref(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            body = client.post("/houmao/agents/abc123/gateway/attach").json()
        assert "abc123" in body["detail"]


class TestGatewayDetachStub:
    """POST /houmao/agents/{agent_ref}/gateway/detach → 501."""

    def test_returns_501(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post("/houmao/agents/abc123/gateway/detach")
        assert resp.status_code == 501

    def test_detail_mentions_houmao_mgr(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            body = client.post("/houmao/agents/abc123/gateway/detach").json()
        assert "houmao-mgr" in body["detail"]


# ---------------------------------------------------------------------------
# Request submission endpoint (Tier 6)
# ---------------------------------------------------------------------------


class TestSubmitRequestEndpoint:
    """POST /houmao/agents/{agent_ref}/requests."""

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post("/houmao/agents/nonexistent/requests", json={"prompt": "hello"})
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post("/houmao/agents/abc123/requests", json={"prompt": "hello"})
        assert resp.status_code == 502
        assert "gateway" in resp.json()["detail"].lower()

    def test_gateway_mediated_success(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        mock_result = GatewayAcceptedRequestV1(
            request_id="req-42",
            request_kind="submit_prompt",
            state="accepted",
            accepted_at_utc="2026-01-01T00:00:00Z",
            queue_depth=1,
            managed_agent_instance_epoch=1,
        )
        with client:
            with patch.object(GatewayClient, "create_request", return_value=mock_result):
                resp = client.post("/houmao/agents/abc123/requests", json={"prompt": "hello"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["request_id"] == "req-42"

    def test_gateway_error_returns_502(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client:
            with patch.object(
                GatewayClient,
                "create_request",
                side_effect=GatewayHttpError(
                    method="POST",
                    url="/v1/requests",
                    status_code=500,
                    detail="internal",
                ),
            ):
                resp = client.post("/houmao/agents/abc123/requests", json={"prompt": "hello"})
        assert resp.status_code == 502

    def test_empty_prompt_rejected(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post("/houmao/agents/abc123/requests", json={"prompt": "   "})
        assert resp.status_code == 422

    def test_ambiguous_agent_returns_409(self, tmp_path: object) -> None:
        a1 = _agent(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1")
        a2 = _agent(agent_id="a2", agent_name="HOUMAO-alpha", session_name="s2")
        client = _make_agent_client(tmp_path, [a1, a2])
        with client:
            resp = client.post("/houmao/agents/alpha/requests", json={"prompt": "hello"})
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Interrupt endpoint (Tier 6)
# ---------------------------------------------------------------------------


class TestInterruptEndpoint:
    """POST /houmao/agents/{agent_ref}/interrupt."""

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post("/houmao/agents/nonexistent/interrupt")
        assert resp.status_code == 404

    def test_no_gateway_not_managed_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post("/houmao/agents/abc123/interrupt")
        assert resp.status_code == 502

    def test_gateway_mediated_success(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        mock_result = GatewayAcceptedRequestV1(
            request_id="req-int-1",
            request_kind="submit_prompt",
            state="accepted",
            accepted_at_utc="2026-01-01T00:00:00Z",
            queue_depth=0,
            managed_agent_instance_epoch=1,
        )
        with client:
            with patch.object(GatewayClient, "create_request", return_value=mock_result):
                resp = client.post("/houmao/agents/abc123/interrupt")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["agent_id"] == "abc123"


# ---------------------------------------------------------------------------
# Stop endpoint (Tier 6)
# ---------------------------------------------------------------------------


class TestStopEndpoint:
    """POST /houmao/agents/{agent_ref}/stop."""

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post("/houmao/agents/nonexistent/stop")
        assert resp.status_code == 404

    def test_discovered_agent_stop(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            with (
                patch("houmao.passive_server.service.kill_tmux_session") as mock_kill,
                patch("houmao.passive_server.service.remove_live_agent_record") as mock_remove,
            ):
                resp = client.post("/houmao/agents/abc123/stop")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["agent_id"] == "abc123"
        mock_kill.assert_called_once_with(session_name="HOUMAO-alpha-abc123")
        mock_remove.assert_called_once()


# ---------------------------------------------------------------------------
# Headless launch endpoint (Tier 7)
# ---------------------------------------------------------------------------


class TestHeadlessLaunchEndpoint:
    """POST /houmao/agents/headless/launches."""

    def test_missing_working_directory_returns_422(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post(
                "/houmao/agents/headless/launches",
                json={
                    "tool": "claude",
                    "working_directory": "/nonexistent/dir",
                    "agent_def_dir": str(tmp_path),
                    "brain_manifest_path": "/nonexistent/manifest.json",
                },
            )
        assert resp.status_code == 422
        assert "working_directory" in resp.json()["detail"]

    def test_missing_manifest_returns_422(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post(
                "/houmao/agents/headless/launches",
                json={
                    "tool": "claude",
                    "working_directory": str(tmp_path),
                    "agent_def_dir": str(tmp_path),
                    "brain_manifest_path": "/nonexistent/manifest.json",
                },
            )
        assert resp.status_code == 422
        assert "brain_manifest_path" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Headless turn endpoints (Tier 7)
# ---------------------------------------------------------------------------


class TestHeadlessTurnEndpoints:
    """Turn submission, status, events, and artifacts for headless agents."""

    def test_turn_submit_non_managed_returns_400(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post("/houmao/agents/abc123/turns", json={"prompt": "hello"})
        assert resp.status_code == 400
        assert "not a managed headless" in resp.json()["detail"]

    def test_turn_status_non_managed_returns_400(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/turns/turn-1")
        assert resp.status_code == 400

    def test_turn_events_non_managed_returns_400(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/turns/turn-1/events")
        assert resp.status_code == 400

    def test_turn_artifact_non_managed_returns_400(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.get("/houmao/agents/abc123/turns/turn-1/artifacts/stdout")
        assert resp.status_code == 400

    def test_turn_submit_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post("/houmao/agents/nonexistent/turns", json={"prompt": "hello"})
        assert resp.status_code == 404
