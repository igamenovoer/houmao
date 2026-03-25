"""Tests for ``PassiveServerService`` lifecycle and methods."""

from __future__ import annotations

import json
import os
from pathlib import Path

from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.service import PassiveServerService


def _make_service(tmp_path: Path) -> PassiveServerService:
    """Build a service with an isolated runtime root."""

    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=tmp_path,
    )
    return PassiveServerService(config=config)


class TestStartup:
    """Service startup behaviour."""

    def test_creates_current_instance_file(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        assert svc.m_config.current_instance_path.exists()

    def test_current_instance_file_has_correct_pid(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        payload = json.loads(svc.m_config.current_instance_path.read_text())
        assert payload["pid"] == os.getpid()

    def test_current_instance_file_has_correct_url(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        payload = json.loads(svc.m_config.current_instance_path.read_text())
        assert payload["api_base_url"] == "http://127.0.0.1:19891"

    def test_run_dir_created(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        assert svc.m_config.run_dir.is_dir()


class TestShutdown:
    """Service shutdown behaviour."""

    def test_removes_current_instance_file(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        assert svc.m_config.current_instance_path.exists()
        svc.shutdown()
        assert not svc.m_config.current_instance_path.exists()

    def test_shutdown_without_startup_is_safe(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.shutdown()  # should not raise


class TestCurrentInstance:
    """current_instance() response builder."""

    def test_returns_correct_pid(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        resp = svc.current_instance()
        assert resp.pid == os.getpid()

    def test_returns_correct_url(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        resp = svc.current_instance()
        assert resp.api_base_url == "http://127.0.0.1:19891"

    def test_returns_server_root_string(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        resp = svc.current_instance()
        assert resp.server_root == str(svc.m_config.server_root)


class TestHealth:
    """health() response builder."""

    def test_returns_passive_identity(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        resp = svc.health()
        assert resp.houmao_service == "houmao-passive-server"
        assert resp.status == "ok"
