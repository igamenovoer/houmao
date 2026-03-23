from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.codex_app_server import (
    CodexAppServerSession,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
)


def _sample_launch_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="codex_app_server",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path / "workspace",
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "sk-secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="gpu-kernel-coder",
            prompt="role prompt",
        ),
        metadata={},
    )


def test_codex_app_server_uses_launch_plan_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = _sample_launch_plan(tmp_path)
    plan.working_directory.mkdir(parents=True)
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)
    captured_process: dict[str, object] = {}

    class _FakeProcess:
        pid = 1234
        stdin = None
        stdout = None
        stderr = None

        def poll(self) -> int | None:
            return None

    def _fake_popen(command: list[str], **kwargs: object) -> _FakeProcess:
        captured_process["command"] = command
        captured_process["cwd"] = kwargs.get("cwd")
        captured_process["env"] = kwargs.get("env")
        return _FakeProcess()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.codex_app_server.subprocess.Popen",
        _fake_popen,
    )

    session = CodexAppServerSession(launch_plan=plan)
    session._ensure_started()  # noqa: SLF001

    assert captured_process["command"] == ["codex", "app-server"]
    assert captured_process["cwd"] == str(plan.working_directory)
    assert isinstance(captured_process["env"], dict)
    assert captured_process["env"]["OPENAI_API_KEY"] == "sk-secret"
    assert captured_process["env"]["CODEX_HOME"] == str(plan.home_path)
    assert captured_process["env"]["HTTP_PROXY"] == "http://proxy.internal:8080"
    no_proxy_tokens = captured_process["env"]["NO_PROXY"].split(",")
    assert "corp.internal" in no_proxy_tokens
    assert "localhost" in no_proxy_tokens
    assert "127.0.0.1" in no_proxy_tokens
    assert "::1" in no_proxy_tokens
    assert captured_process["env"]["no_proxy"] == captured_process["env"]["NO_PROXY"]


def test_codex_app_server_preserve_mode_leaves_no_proxy_untouched(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plan = _sample_launch_plan(tmp_path)
    plan.working_directory.mkdir(parents=True)
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("AGENTSYS_PRESERVE_NO_PROXY_ENV", "1")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)
    captured_process: dict[str, object] = {}

    class _FakeProcess:
        pid = 1234
        stdin = None
        stdout = None
        stderr = None

        def poll(self) -> int | None:
            return None

    def _fake_popen(command: list[str], **kwargs: object) -> _FakeProcess:
        del command
        captured_process["env"] = kwargs.get("env")
        return _FakeProcess()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.codex_app_server.subprocess.Popen",
        _fake_popen,
    )

    session = CodexAppServerSession(launch_plan=plan)
    session._ensure_started()  # noqa: SLF001

    assert isinstance(captured_process["env"], dict)
    assert captured_process["env"]["HTTP_PROXY"] == "http://proxy.internal:8080"
    assert captured_process["env"]["NO_PROXY"] == "corp.internal"
    assert "no_proxy" not in captured_process["env"]
