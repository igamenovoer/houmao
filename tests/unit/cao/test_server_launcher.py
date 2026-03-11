from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from gig_agents.cao.server_launcher import (
    CaoServerOwnership,
    CaoServerLauncherError,
    ProxyPolicy,
    _require_executable_on_path,
    build_cao_server_environment,
    load_cao_server_launcher_config,
    read_cao_server_ownership,
    read_cao_server_pid,
    resolve_cao_server_runtime_artifacts,
    start_cao_server,
    status_cao_server,
    stop_cao_server,
    write_cao_server_ownership,
    write_cao_server_pid,
)


class _FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _write_config(
    tmp_path: Path,
    *,
    base_url: str = "http://localhost:9889",
    runtime_root: str = "tmp/agents-runtime",
    home_dir: Path | None = None,
    proxy_policy: str = "clear",
    startup_timeout_seconds: float = 15.0,
    extras: str = "",
) -> Path:
    home = home_dir or tmp_path
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "launcher.toml"
    path.write_text(
        "\n".join(
            [
                f'base_url = "{base_url}"',
                f'runtime_root = "{runtime_root}"',
                f'home_dir = "{home}"',
                f'proxy_policy = "{proxy_policy}"',
                f"startup_timeout_seconds = {startup_timeout_seconds}",
                extras,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_build_cao_server_environment_clear_sanitizes_proxy_vars() -> None:
    env = build_cao_server_environment(
        base_env={
            "HTTP_PROXY": "http://proxy.internal:8080",
            "HTTPS_PROXY": "http://proxy.internal:8443",
            "ALL_PROXY": "socks5://proxy.internal:1080",
            "http_proxy": "http://proxy.lower:8080",
            "NO_PROXY": "example.com,localhost",
            "PATH": "/usr/bin",
        },
        proxy_policy=ProxyPolicy.CLEAR,
    )

    assert "HTTP_PROXY" not in env
    assert "HTTPS_PROXY" not in env
    assert "ALL_PROXY" not in env
    assert "http_proxy" not in env
    no_proxy_tokens = env["NO_PROXY"].split(",")
    assert "example.com" in no_proxy_tokens
    assert "localhost" in no_proxy_tokens
    assert "127.0.0.1" in no_proxy_tokens
    assert "::1" in no_proxy_tokens
    assert env["no_proxy"] == env["NO_PROXY"]


def test_build_cao_server_environment_inherit_preserves_proxy_vars() -> None:
    env = build_cao_server_environment(
        base_env={
            "HTTP_PROXY": "http://proxy.internal:8080",
            "NO_PROXY": "corp.internal",
            "no_proxy": "localhost",
        },
        proxy_policy=ProxyPolicy.INHERIT,
    )

    assert env["HTTP_PROXY"] == "http://proxy.internal:8080"
    no_proxy_tokens = env["NO_PROXY"].split(",")
    assert "corp.internal" in no_proxy_tokens
    assert "localhost" in no_proxy_tokens
    assert "127.0.0.1" in no_proxy_tokens
    assert "::1" in no_proxy_tokens
    assert env["no_proxy"] == env["NO_PROXY"]


def test_runtime_artifacts_are_partitioned_by_host_port(tmp_path: Path) -> None:
    localhost_config = load_cao_server_launcher_config(
        _write_config(tmp_path / "a", home_dir=tmp_path)
    )
    loopback_config = load_cao_server_launcher_config(
        _write_config(tmp_path / "b", base_url="http://127.0.0.1:9889", home_dir=tmp_path)
    )

    localhost_artifacts = resolve_cao_server_runtime_artifacts(localhost_config)
    loopback_artifacts = resolve_cao_server_runtime_artifacts(loopback_config)

    assert localhost_artifacts.artifact_dir.name == "localhost-9889"
    assert loopback_artifacts.artifact_dir.name == "127.0.0.1-9889"
    assert localhost_artifacts.pid_file.name == "cao-server.pid"
    assert localhost_artifacts.log_file.name == "cao-server.log"
    assert localhost_artifacts.ownership_file.name == "ownership.json"


def test_pidfile_read_write_roundtrip(tmp_path: Path) -> None:
    pid_file = tmp_path / "runtime" / "cao-server.pid"
    write_cao_server_pid(pid_file, 12345)
    assert read_cao_server_pid(pid_file) == 12345


def test_config_validation_rejects_unknown_keys(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, extras='unknown_key = "value"')
    with pytest.raises(CaoServerLauncherError, match=r"unknown_key"):
        load_cao_server_launcher_config(config_path)


def test_config_validation_rejects_invalid_proxy_policy(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, proxy_policy="invalid_policy")
    with pytest.raises(CaoServerLauncherError, match=r"proxy_policy"):
        load_cao_server_launcher_config(config_path)


def test_config_validation_rejects_unsupported_base_url(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, base_url="http://0.0.0.0:9889")
    with pytest.raises(CaoServerLauncherError, match=r"base_url"):
        load_cao_server_launcher_config(config_path)


def test_stop_refuses_to_kill_when_identity_verification_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = _write_config(tmp_path)
    config = load_cao_server_launcher_config(config_path)
    artifacts = resolve_cao_server_runtime_artifacts(config)
    write_cao_server_pid(artifacts.pid_file, 4242)

    kill_calls: list[tuple[int, int]] = []

    monkeypatch.setattr(
        "gig_agents.cao.server_launcher._is_process_running",
        lambda pid: True,
    )
    monkeypatch.setattr(
        "gig_agents.cao.server_launcher._read_process_cmdline",
        lambda pid: "python unrelated_service.py",
    )
    monkeypatch.setattr(
        "gig_agents.cao.server_launcher.os.kill",
        lambda pid, signum: kill_calls.append((pid, int(signum))),
    )

    result = stop_cao_server(config)

    assert result.stopped is False
    assert result.verification_passed is False
    assert result.already_stopped is False
    assert "Refusing to stop process" in result.message
    assert kill_calls == []


def test_start_records_detached_ownership_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = load_cao_server_launcher_config(_write_config(tmp_path))

    probe_results = iter([False, True])

    def fake_status(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        healthy = next(probe_results)
        return type(
            "_Status",
            (),
            {
                "operation": "status",
                "base_url": config.base_url,
                "healthy": healthy,
                "health_status": "ok" if healthy else None,
                "service": "cli-agent-orchestrator" if healthy else None,
                "error": None if healthy else "connection refused",
            },
        )()

    class FakeProcess:
        pid = 4242

        @staticmethod
        def poll() -> int | None:
            return None

    monkeypatch.setattr("gig_agents.cao.server_launcher.status_cao_server", fake_status)
    monkeypatch.setattr(
        "gig_agents.cao.server_launcher._require_executable_on_path",
        lambda *args, **kwargs: "/tmp/fake-bin/cao-server",
    )
    monkeypatch.setattr(
        "gig_agents.cao.server_launcher._launch_cao_server_detached",
        lambda **kwargs: FakeProcess(),
    )
    monkeypatch.setattr(
        "gig_agents.cao.server_launcher._process_group_id_for_pid",
        lambda pid: pid,
    )

    result = start_cao_server(config)

    ownership = read_cao_server_ownership(result.ownership_file)
    assert result.started_new_process is True
    assert result.reused_existing_process is False
    assert result.ownership is not None
    assert ownership.managed_by == "gig_agents.cao.server_launcher"
    assert ownership.launch_mode == "detached"
    assert ownership.base_url == config.base_url
    assert ownership.pid == 4242
    assert ownership.process_group_id == 4242
    assert ownership.executable_path == Path("/tmp/fake-bin/cao-server")


def test_stop_refuses_to_kill_when_ownership_metadata_disagrees_with_pidfile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = load_cao_server_launcher_config(_write_config(tmp_path))
    artifacts = resolve_cao_server_runtime_artifacts(config)
    write_cao_server_pid(artifacts.pid_file, 4242)
    write_cao_server_ownership(
        artifacts.ownership_file,
        CaoServerOwnership(
            managed_by="gig_agents.cao.server_launcher",
            launch_mode="detached",
            base_url=config.base_url,
            runtime_root=config.runtime_root,
            artifact_dir=artifacts.artifact_dir,
            home_dir=config.home_dir,
            config_path=config.config_path,
            proxy_policy=config.proxy_policy,
            pid=9999,
            process_group_id=9999,
            executable_path=Path("/usr/bin/cao-server"),
            started_at_utc="2026-03-11T05:00:00+00:00",
        ),
    )

    kill_calls: list[tuple[int, int]] = []

    monkeypatch.setattr("gig_agents.cao.server_launcher._is_process_running", lambda pid: True)
    monkeypatch.setattr(
        "gig_agents.cao.server_launcher._read_process_cmdline",
        lambda pid: "python /usr/bin/cao-server",
    )
    monkeypatch.setattr(
        "gig_agents.cao.server_launcher.os.kill",
        lambda pid, signum: kill_calls.append((pid, int(signum))),
    )

    result = stop_cao_server(config)

    assert result.stopped is False
    assert result.verification_passed is False
    assert "ownership metadata does not match the pidfile" in result.message
    assert kill_calls == []


def test_status_cao_server_injects_loopback_no_proxy_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = load_cao_server_launcher_config(_write_config(tmp_path))
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)

    captured_inside: dict[str, str | None] = {}

    def _fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        del req, timeout
        captured_inside["NO_PROXY"] = os.environ.get("NO_PROXY")
        captured_inside["no_proxy"] = os.environ.get("no_proxy")
        return _FakeResponse(
            status=200,
            payload={"status": "ok", "service": "cli-agent-orchestrator"},
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    result = status_cao_server(config)

    assert result.healthy is True
    assert result.health_status == "ok"
    assert result.error is None
    assert captured_inside["NO_PROXY"] is not None
    assert "corp.internal" in captured_inside["NO_PROXY"].split(",")
    assert "localhost" in captured_inside["NO_PROXY"].split(",")
    assert "127.0.0.1" in captured_inside["NO_PROXY"].split(",")
    assert "::1" in captured_inside["NO_PROXY"].split(",")
    assert captured_inside["no_proxy"] == captured_inside["NO_PROXY"]
    assert os.environ.get("NO_PROXY") == "corp.internal"
    assert os.environ.get("no_proxy") is None


def test_status_cao_server_preserve_mode_leaves_no_proxy_untouched(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = load_cao_server_launcher_config(_write_config(tmp_path))
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("AGENTSYS_PRESERVE_NO_PROXY_ENV", "1")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)

    captured_inside: dict[str, str | None] = {}

    def _fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        del req, timeout
        captured_inside["NO_PROXY"] = os.environ.get("NO_PROXY")
        captured_inside["no_proxy"] = os.environ.get("no_proxy")
        return _FakeResponse(
            status=200,
            payload={"status": "ok", "service": "cli-agent-orchestrator"},
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    result = status_cao_server(config)

    assert result.healthy is True
    assert captured_inside["NO_PROXY"] == "corp.internal"
    assert captured_inside["no_proxy"] is None
    assert os.environ.get("NO_PROXY") == "corp.internal"
    assert os.environ.get("no_proxy") is None


def test_launcher_preflight_reports_missing_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("gig_agents.cao.server_launcher.shutil.which", lambda _: None)
    with pytest.raises(CaoServerLauncherError, match="command -v cao-server"):
        _require_executable_on_path(
            "cao-server",
            install_hint="verify with `command -v cao-server`.",
        )


def test_launcher_preflight_accepts_present_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gig_agents.cao.server_launcher.shutil.which",
        lambda _: "/usr/bin/cao-server",
    )
    assert (
        _require_executable_on_path(
            "cao-server",
            install_hint="verify with `command -v cao-server`.",
        )
        == "/usr/bin/cao-server"
    )
