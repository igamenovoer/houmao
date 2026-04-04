from __future__ import annotations

from click.testing import CliRunner

from houmao.passive_server.cli import serve_command as passive_serve_command
from houmao.server.commands.serve import serve_command
from houmao.server.config import HoumaoServerConfig


def test_serve_command_accepts_compatibility_timing_options(
    monkeypatch,
    tmp_path,
) -> None:
    captured: dict[str, object] = {}
    config = HoumaoServerConfig(api_base_url="http://127.0.0.1:9991", runtime_root=tmp_path)

    def _build_config(**kwargs):
        captured["build_config_kwargs"] = kwargs
        return config

    monkeypatch.setattr("houmao.server.commands.serve.build_config", _build_config)
    monkeypatch.setattr(
        "houmao.server.commands.serve.create_app", lambda *, config: {"config": config}
    )
    monkeypatch.setattr(
        "houmao.server.commands.serve.uvicorn.run",
        lambda app, host, port, log_level: captured.update(
            {
                "uvicorn_app": app,
                "uvicorn_host": host,
                "uvicorn_port": port,
                "uvicorn_log_level": log_level,
            }
        ),
    )

    result = CliRunner().invoke(
        serve_command,
        [
            "--runtime-root",
            str(tmp_path),
            "--compat-shell-ready-timeout-seconds",
            "20",
            "--compat-shell-ready-poll-interval-seconds",
            "0.25",
            "--compat-provider-ready-timeout-seconds",
            "90",
            "--compat-provider-ready-poll-interval-seconds",
            "0.75",
            "--compat-codex-warmup-seconds",
            "0",
        ],
    )

    assert result.exit_code == 0
    assert captured["build_config_kwargs"] == {
        "api_base_url": "http://127.0.0.1:9889",
        "runtime_root": str(tmp_path),
        "watch_poll_interval_seconds": 0.5,
        "recent_transition_limit": 24,
        "stability_threshold_seconds": 1.0,
        "completion_stability_seconds": 1.0,
        "unknown_to_stalled_timeout_seconds": 30.0,
        "supported_tui_processes": (),
        "compat_shell_ready_timeout_seconds": 20.0,
        "compat_shell_ready_poll_interval_seconds": 0.25,
        "compat_provider_ready_timeout_seconds": 90.0,
        "compat_provider_ready_poll_interval_seconds": 0.75,
        "compat_codex_warmup_seconds": 0.0,
        "startup_child": True,
    }
    assert captured["uvicorn_host"] == "127.0.0.1"
    assert captured["uvicorn_port"] == 9991
    assert captured["uvicorn_log_level"] == "info"


def test_houmao_server_serve_help_mentions_project_aware_runtime_root() -> None:
    result = CliRunner().invoke(serve_command, ["--help"])

    assert result.exit_code == 0
    assert "this command uses the active project runtime" in result.output
    assert "HOUMAO_GLOBAL_RUNTIME_DIR" in result.output


def test_passive_server_serve_help_mentions_project_aware_runtime_root() -> None:
    result = CliRunner().invoke(passive_serve_command, ["--help"])

    assert result.exit_code == 0
    assert "active project runtime root when project" in result.output
    assert "HOUMAO_GLOBAL_RUNTIME_DIR" in result.output
