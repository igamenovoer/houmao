"""Tests for the ``houmao-passive-server`` CLI."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import pytest

from houmao.owned_paths import (
    HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
)
from houmao.passive_server.cli import cli
from houmao.passive_server.config import PassiveServerConfig


def _capture_serve(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    """Patch app creation and uvicorn startup, returning captured call state."""

    captured: dict[str, object] = {}

    def fake_create_app(*, config: PassiveServerConfig) -> object:
        captured["config"] = config
        return object()

    def fake_uvicorn_run(
        app: object,
        *,
        host: str,
        port: int,
        log_level: str,
    ) -> None:
        captured["app"] = app
        captured["host"] = host
        captured["port"] = port
        captured["log_level"] = log_level

    monkeypatch.setattr("houmao.passive_server.cli.create_app", fake_create_app)
    monkeypatch.setattr("houmao.passive_server.cli.uvicorn.run", fake_uvicorn_run)
    return captured


def test_serve_without_project_overlay_uses_global_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The CLI starts from a plain directory without project-overlay bootstrap."""

    fake_config_path = tmp_path / "config" / "houmao"
    monkeypatch.delenv(HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR, raising=False)
    monkeypatch.delenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(
        "houmao.owned_paths.platformdirs.user_config_path",
        lambda **_kwargs: fake_config_path,
    )
    captured = _capture_serve(monkeypatch)

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["serve"])

    assert result.exit_code == 0, result.output
    config = captured["config"]
    assert isinstance(config, PassiveServerConfig)
    assert config.runtime_root == (fake_config_path / "runtime").resolve()
    assert config.registry_root == (fake_config_path / "registry").resolve()
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9891


def test_serve_accepts_registry_root_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The CLI forwards ``--registry-root`` into ``PassiveServerConfig``."""

    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    captured = _capture_serve(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "serve",
            "--host",
            "0.0.0.0",
            "--port",
            "9895",
            "--runtime-root",
            str(runtime_root),
            "--registry-root",
            str(registry_root),
        ],
    )

    assert result.exit_code == 0, result.output
    config = captured["config"]
    assert isinstance(config, PassiveServerConfig)
    assert config.api_base_url == "http://0.0.0.0:9895"
    assert config.runtime_root == runtime_root.resolve()
    assert config.registry_root == registry_root.resolve()
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9895
