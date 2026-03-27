from __future__ import annotations

import sys
from pathlib import Path

import pytest

from houmao.server.config import HoumaoServerConfig
from houmao.server.models import HoumaoCurrentInstance
from houmao.srv_ctrl import server_startup


class _FakeProcess:
    def __init__(self, *, pid: int, returncode: int | None) -> None:
        self.pid = pid
        self.m_returncode = returncode

    def poll(self) -> int | None:
        return self.m_returncode

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        return self.m_returncode or 0


def test_start_detached_server_reuses_existing_healthy_instance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = HoumaoServerConfig(
        api_base_url="http://127.0.0.1:9988",
        runtime_root=tmp_path,
    )
    current_instance = HoumaoCurrentInstance(
        pid=321,
        api_base_url=config.api_base_url,
        server_root=str(config.server_root),
    )

    monkeypatch.setattr(
        server_startup,
        "_probe_ready_server",
        lambda **kwargs: current_instance,
    )
    monkeypatch.setattr(
        server_startup,
        "_launch_detached_server",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("launch should not run")),
    )

    result = server_startup.start_detached_server(config)

    assert result.success is True
    assert result.running is True
    assert result.reused_existing is True
    assert result.pid == 321
    assert result.current_instance == current_instance
    assert result.server_root == str(config.server_root)
    assert result.log_paths is not None
    assert result.log_paths.stdout.endswith("houmao-server.stdout.log")
    assert result.log_paths.stderr.endswith("houmao-server.stderr.log")


def test_start_detached_server_reports_early_child_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = HoumaoServerConfig(
        api_base_url="http://127.0.0.1:9989",
        runtime_root=tmp_path,
    )

    monkeypatch.setattr(server_startup, "_probe_ready_server", lambda **kwargs: None)
    monkeypatch.setattr(
        server_startup,
        "_launch_detached_server",
        lambda **kwargs: _FakeProcess(pid=456, returncode=7),
    )
    monkeypatch.setattr(server_startup.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(server_startup.time, "sleep", lambda seconds: None)

    result = server_startup.start_detached_server(config)

    assert result.success is False
    assert result.running is False
    assert result.pid == 456
    assert result.exit_code == 7
    assert result.server_root == str(config.server_root)
    assert result.log_paths is not None
    assert "exited before becoming healthy" in result.detail


def test_background_server_command_replays_resolved_config_flags(tmp_path: Path) -> None:
    config = HoumaoServerConfig(
        api_base_url="http://127.0.0.1:9990",
        runtime_root=tmp_path,
        watch_poll_interval_seconds=1.5,
        recent_transition_limit=99,
        stability_threshold_seconds=2.0,
        completion_stability_seconds=3.0,
        unknown_to_stalled_timeout_seconds=4.0,
        supported_tui_processes={"codex": ("codex", "codex-beta"), "claude": ("claude",)},
        compat_shell_ready_timeout_seconds=5.0,
        compat_shell_ready_poll_interval_seconds=0.7,
        compat_provider_ready_timeout_seconds=8.0,
        compat_provider_ready_poll_interval_seconds=0.9,
        compat_codex_warmup_seconds=1.2,
        startup_child=False,
    )

    command = server_startup._background_server_command(config)

    assert command[:5] == [sys.executable, "-m", "houmao.srv_ctrl", "server", "start"]
    assert "--foreground" in command
    assert "--runtime-root" in command
    assert str(tmp_path.resolve()) in command
    assert "--supported-tui-process" in command
    assert "claude=claude" in command
    assert "codex=codex,codex-beta" in command
    assert command[-1] == "--no-startup-child"
