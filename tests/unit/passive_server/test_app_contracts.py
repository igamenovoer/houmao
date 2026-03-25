"""Tests for passive-server HTTP route contracts."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from houmao.passive_server.app import create_app
from houmao.passive_server.config import PassiveServerConfig


def _make_client(tmp_path: object) -> TestClient:
    """Build a test client with an isolated runtime root."""

    from pathlib import Path

    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=Path(str(tmp_path)),
    )
    app = create_app(config=config)
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
