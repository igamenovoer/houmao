"""Tests for passive-server HTTP route contracts."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

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
