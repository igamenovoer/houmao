from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from houmao.project.overlay import bootstrap_project_overlay
from houmao.server.config import HoumaoServerConfig


def test_houmao_server_config_derives_public_listener_and_roots(tmp_path: Path) -> None:
    config = HoumaoServerConfig(
        api_base_url="http://127.0.0.1:9889",
        runtime_root=tmp_path,
    )

    assert config.public_host == "127.0.0.1"
    assert config.public_port == 9889
    assert config.server_root == tmp_path / "houmao_servers" / "127.0.0.1-9889"
    assert config.current_instance_path == config.server_root / "run" / "current-instance.json"
    assert config.terminal_state_root == config.server_root / "state" / "terminals"
    assert config.terminal_history_root == config.server_root / "history" / "terminals"
    assert config.compat_shell_ready_timeout_seconds == 10.0
    assert config.compat_shell_ready_poll_interval_seconds == 0.5
    assert config.compat_provider_ready_timeout_seconds == 45.0
    assert config.compat_provider_ready_poll_interval_seconds == 1.0
    assert config.compat_codex_warmup_seconds == 2.0


def test_houmao_server_config_validates_compatibility_timing_fields(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="compat_shell_ready_timeout_seconds"):
        HoumaoServerConfig(
            api_base_url="http://127.0.0.1:9889",
            runtime_root=tmp_path,
            compat_shell_ready_timeout_seconds=0.0,
        )

    with pytest.raises(ValidationError, match="compat_codex_warmup_seconds"):
        HoumaoServerConfig(
            api_base_url="http://127.0.0.1:9889",
            runtime_root=tmp_path,
            compat_codex_warmup_seconds=-0.1,
        )


def test_houmao_server_config_defaults_runtime_root_project_aware(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    monkeypatch.chdir(repo_root)

    config = HoumaoServerConfig(api_base_url="http://127.0.0.1:9889")

    assert config.runtime_root == (repo_root / ".houmao" / "runtime").resolve()
