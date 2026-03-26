"""Tests for passive-server HTTP route contracts."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayMailActionResponseV1,
    GatewayMailCheckResponseV1,
    GatewayMailStatusV1,
    GatewayMailboxMessageV1,
    GatewayMailboxParticipantV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.registry_models import RegistryGatewayV1
from houmao.passive_server.app import create_app
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, _summary_from_record
from houmao.passive_server.service import PassiveServerService
from tests.unit.passive_server.test_discovery import _make_record


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
        with patch.object(svc.m_discovery, "start"), patch.object(svc.m_discovery, "stop"):
            async with _orig_enter(a) as val:
                yield val

    app.router.lifespan_context = _patched_lifespan  # type: ignore[assignment]
    return TestClient(app)


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
        with patch.object(svc.m_discovery, "start"), patch.object(svc.m_discovery, "stop"):
            async with _orig_enter(a) as val:
                yield val

    app.router.lifespan_context = _patched_lifespan  # type: ignore[assignment]
    return TestClient(app)


def _agent(
    agent_id: str = "abc123",
    agent_name: str = "AGENTSYS-alpha",
    session_name: str = "AGENTSYS-alpha-abc123",
) -> DiscoveredAgent:
    record = _make_record(
        agent_id=agent_id, agent_name=agent_name, session_name=session_name
    )
    return DiscoveredAgent(record=record, summary=_summary_from_record(record))


# ---------------------------------------------------------------------------
# Agent listing endpoint
# ---------------------------------------------------------------------------


class TestListAgentsEndpoint:
    """GET /houmao/agents."""

    def test_returns_200_with_agents(self, tmp_path: object) -> None:
        a1 = _agent(agent_id="a1", agent_name="AGENTSYS-alpha", session_name="s1")
        a2 = _agent(agent_id="b1", agent_name="AGENTSYS-beta", session_name="s2")
        client = _make_agent_client(tmp_path, [a1, a2])
        with client:
            resp = client.get("/houmao/agents")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["agents"]) == 2
        assert body["agents"][0]["agent_name"] == "AGENTSYS-alpha"
        assert body["agents"][1]["agent_name"] == "AGENTSYS-beta"

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
            "agent_id", "agent_name", "generation_id", "tool", "backend",
            "tmux_session_name", "manifest_path", "session_root",
            "has_gateway", "has_mailbox", "published_at", "lease_expires_at",
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
        client = _make_agent_client(tmp_path, [_agent(agent_name="AGENTSYS-alpha")])
        with client:
            resp = client.get("/houmao/agents/alpha")
        assert resp.status_code == 200
        assert resp.json()["agent_name"] == "AGENTSYS-alpha"

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/nonexistent")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    def test_ambiguous_returns_409(self, tmp_path: object) -> None:
        a1 = _agent(agent_id="abc123", agent_name="AGENTSYS-alpha", session_name="s1")
        a2 = _agent(agent_id="def456", agent_name="AGENTSYS-alpha", session_name="s2")
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
    agent_name: str = "AGENTSYS-alpha",
    session_name: str = "AGENTSYS-alpha-abc123",
    gateway_host: str = "127.0.0.1",
    gateway_port: int = 9901,
) -> DiscoveredAgent:
    """Create a DiscoveredAgent with live gateway coordinates."""

    record = _make_record(
        agent_id=agent_id, agent_name=agent_name, session_name=session_name
    )
    record.gateway = RegistryGatewayV1(
        gateway_root="/tmp/gw",
        attach_path="/tmp/gw/attach.json",
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


def _stub_mail_status() -> GatewayMailStatusV1:
    """Create a minimal valid GatewayMailStatusV1 for mocking."""

    return GatewayMailStatusV1(
        transport="filesystem",
        principal_id="p1",
        address="agent@local",
        bindings_version="v1",
    )


def _stub_mail_check_response() -> GatewayMailCheckResponseV1:
    """Create a minimal valid GatewayMailCheckResponseV1 for mocking."""

    return GatewayMailCheckResponseV1(
        transport="filesystem",
        principal_id="p1",
        address="agent@local",
        unread_only=False,
        message_count=0,
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


# ---------------------------------------------------------------------------
# Gateway status endpoint
# ---------------------------------------------------------------------------


class TestGatewayStatusEndpoint:
    """GET /houmao/agents/{agent_ref}/gateway."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client, patch.object(
            GatewayClient, "status", return_value=_stub_gateway_status()
        ):
            resp = client.get("/houmao/agents/abc123/gateway")
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.get("/houmao/agents/nonexistent/gateway")
        assert resp.status_code == 404

    def test_ambiguous_returns_409(self, tmp_path: object) -> None:
        a1 = _agent_with_gateway(
            agent_id="a1", agent_name="AGENTSYS-alpha", session_name="s1"
        )
        a2 = _agent_with_gateway(
            agent_id="a2", agent_name="AGENTSYS-alpha", session_name="s2"
        )
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
        with client, patch.object(
            GatewayClient,
            "status",
            side_effect=GatewayHttpError(
                method="GET", url="http://127.0.0.1:9901/v1/status", detail="refused"
            ),
        ):
            resp = client.get("/houmao/agents/abc123/gateway")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Gateway request submission endpoint
# ---------------------------------------------------------------------------


class TestGatewayCreateRequestEndpoint:
    """POST /houmao/agents/{agent_ref}/gateway/requests."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client, patch.object(
            GatewayClient, "create_request", return_value=_stub_accepted_request()
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
# Mail status endpoint
# ---------------------------------------------------------------------------


class TestGatewayMailStatusEndpoint:
    """GET /houmao/agents/{agent_ref}/mail/status."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client, patch.object(
            GatewayClient, "mail_status", return_value=_stub_mail_status()
        ):
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
# Mail check endpoint
# ---------------------------------------------------------------------------


class TestGatewayMailCheckEndpoint:
    """POST /houmao/agents/{agent_ref}/mail/check."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client, patch.object(
            GatewayClient, "check_mail", return_value=_stub_mail_check_response()
        ):
            resp = client.post(
                "/houmao/agents/abc123/mail/check",
                json={"schema_version": 1},
            )
        assert resp.status_code == 200

    def test_not_found_returns_404(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [])
        with client:
            resp = client.post(
                "/houmao/agents/unknown/mail/check",
                json={"schema_version": 1},
            )
        assert resp.status_code == 404

    def test_no_gateway_returns_502(self, tmp_path: object) -> None:
        client = _make_agent_client(tmp_path, [_agent()])
        with client:
            resp = client.post(
                "/houmao/agents/abc123/mail/check",
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
        with client, patch.object(
            GatewayClient, "send_mail", return_value=_stub_mail_action_response("send")
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
# Mail reply endpoint
# ---------------------------------------------------------------------------


class TestGatewayMailReplyEndpoint:
    """POST /houmao/agents/{agent_ref}/mail/reply."""

    def test_returns_200_with_mocked_client(self, tmp_path: object) -> None:
        agent = _agent_with_gateway()
        client = _make_agent_client(tmp_path, [agent])
        with client, patch.object(
            GatewayClient, "reply_mail", return_value=_stub_mail_action_response("reply")
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
