from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
)
from houmao.agents.realm_controller.backends.gemini_headless import (
    GeminiHeadlessSession,
)
from houmao.agents.realm_controller.backends.claude_headless import (
    ClaudeHeadlessSession,
)
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessSessionState,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessRunResult,
)
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
)


def _sample_gemini_launch_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="gemini_headless",
        tool="gemini",
        executable="gemini",
        args=[],
        working_directory=tmp_path,
        home_env_var="GEMINI_CLI_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="bootstrap_message",
            role_name="gpu-kernel-coder",
            prompt="role prompt",
            bootstrap_message="bootstrap",
        ),
        metadata={},
    )


def _sample_claude_launch_plan(
    tmp_path: Path,
    *,
    prompt: str = "role prompt",
    bootstrap_message: str = "bootstrap",
) -> LaunchPlan:
    return LaunchPlan(
        backend="claude_headless",
        tool="claude",
        executable="claude",
        args=[],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env={"ANTHROPIC_API_KEY": "sk-secret"},
        env_var_names=["ANTHROPIC_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt",
            role_name="gpu-kernel-coder",
            prompt=prompt,
            bootstrap_message=bootstrap_message,
        ),
        metadata={},
    )


def test_gemini_headless_surfaces_stderr_on_failure(tmp_path: Path) -> None:
    session = GeminiHeadlessSession(
        launch_plan=_sample_gemini_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-gemini",
        ),
    )

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
        ) -> HeadlessRunResult:
            return HeadlessRunResult(
                events=[],
                stderr="Please set an Auth method",
                returncode=41,
                session_id=None,
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    with pytest.raises(BackendExecutionError, match=r"Please set an Auth method"):
        session.send_prompt("hello")


def test_claude_headless_uses_launch_plan_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    session = ClaudeHeadlessSession(
        launch_plan=_sample_claude_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-claude",
        ),
    )

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
        ) -> HeadlessRunResult:
            captured["env"] = dict(env)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="sess-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    session.send_prompt("hello")
    assert isinstance(captured["env"], dict)
    assert captured["env"]["CLAUDE_CONFIG_DIR"] == str(tmp_path / "home")
    assert captured["env"]["ANTHROPIC_API_KEY"] == "sk-secret"


def test_claude_headless_adds_verbose_for_stream_json_output(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    session = ClaudeHeadlessSession(
        launch_plan=_sample_claude_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-claude",
        ),
    )

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
        ) -> HeadlessRunResult:
            del env, cwd, turn_index, output_format, tmux_session_name, turn_artifacts_root
            captured["command"] = list(command)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="sess-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    session.send_prompt("hello")

    assert captured["command"] == [
        "claude",
        "-p",
        "--verbose",
        "--append-system-prompt",
        "role prompt",
        "hello",
        "--output-format",
        "stream-json",
    ]


def test_claude_headless_skips_verbose_for_json_output(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    session = ClaudeHeadlessSession(
        launch_plan=_sample_claude_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-claude",
        ),
        output_format="json",
    )

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
        ) -> HeadlessRunResult:
            del env, cwd, turn_index, output_format, tmux_session_name, turn_artifacts_root
            captured["command"] = list(command)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="sess-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    session.send_prompt("hello")

    assert "--verbose" not in captured["command"]
    assert captured["command"] == [
        "claude",
        "-p",
        "--append-system-prompt",
        "role prompt",
        "hello",
        "--output-format",
        "json",
    ]


def test_claude_headless_omits_empty_appended_system_prompt(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    session = ClaudeHeadlessSession(
        launch_plan=_sample_claude_launch_plan(tmp_path, prompt="", bootstrap_message=""),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-claude",
        ),
    )

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
        ) -> HeadlessRunResult:
            del env, cwd, turn_index, output_format, tmux_session_name, turn_artifacts_root
            captured["command"] = list(command)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="sess-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    session.send_prompt("hello")

    assert captured["command"] == [
        "claude",
        "-p",
        "--verbose",
        "hello",
        "--output-format",
        "stream-json",
    ]


def test_headless_resume_republishes_manifest_and_agent_def_dir_to_tmux_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    agent_def_dir = tmp_path / "agents"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    captured_tmux_env: dict[str, object] = {}
    prepared_sessions: list[str] = []

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.set_tmux_session_environment_shared",
        lambda *, session_name, env_vars: captured_tmux_env.update(
            {"session_name": session_name, "env_vars": dict(env_vars)}
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.prepare_headless_agent_window_shared",
        lambda *, session_name: prepared_sessions.append(session_name),
    )

    GeminiHeadlessSession(
        launch_plan=_sample_gemini_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        agent_def_dir=agent_def_dir,
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-gemini",
        ),
    )

    assert captured_tmux_env["session_name"] == "HOUMAO-gemini"
    assert prepared_sessions == ["HOUMAO-gemini"]
    env_vars = captured_tmux_env["env_vars"]
    assert isinstance(env_vars, dict)
    assert env_vars[AGENT_MANIFEST_PATH_ENV_VAR] == str((tmp_path / "session.json").resolve())
    assert env_vars[AGENT_DEF_DIR_ENV_VAR] == str(agent_def_dir.resolve())


def test_headless_env_injects_loopback_no_proxy_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)
    session = GeminiHeadlessSession(
        launch_plan=_sample_gemini_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-gemini",
        ),
    )
    captured_env: dict[str, str] = {}

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
        ) -> HeadlessRunResult:
            del command, cwd, turn_index, output_format
            captured_env.update(env)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="sess-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    session.send_prompt("hello")

    assert captured_env["HTTP_PROXY"] == "http://proxy.internal:8080"
    no_proxy_tokens = captured_env["NO_PROXY"].split(",")
    assert "corp.internal" in no_proxy_tokens
    assert "localhost" in no_proxy_tokens
    assert "127.0.0.1" in no_proxy_tokens
    assert "::1" in no_proxy_tokens
    assert captured_env["no_proxy"] == captured_env["NO_PROXY"]


def test_headless_env_preserve_mode_leaves_no_proxy_untouched(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("HOUMAO_PRESERVE_NO_PROXY_ENV", "1")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)
    session = GeminiHeadlessSession(
        launch_plan=_sample_gemini_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-gemini",
        ),
    )
    captured_env: dict[str, str] = {}

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
        ) -> HeadlessRunResult:
            del command, cwd, turn_index, output_format
            captured_env.update(env)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="sess-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    session.send_prompt("hello")

    assert captured_env["HTTP_PROXY"] == "http://proxy.internal:8080"
    assert captured_env["NO_PROXY"] == "corp.internal"
    assert "no_proxy" not in captured_env


def test_headless_preflight_fails_when_tool_executable_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.shutil.which",
        lambda name: None if name == "gemini" else "/usr/bin/tmux",
    )

    with pytest.raises(BackendExecutionError, match="command -v gemini"):
        GeminiHeadlessSession(
            launch_plan=_sample_gemini_launch_plan(tmp_path),
            role_name="gpu-kernel-coder",
            session_manifest_path=tmp_path / "session.json",
            state=HeadlessSessionState(
                working_directory=str(tmp_path),
                tmux_session_name="HOUMAO-gemini",
            ),
        )


@pytest.fixture(autouse=True)
def _stub_tmux_for_headless_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.ensure_tmux_available_shared",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.has_tmux_session_shared",
        lambda *, session_name: subprocess.CompletedProcess(
            args=["tmux", "has-session", "-t", session_name],
            returncode=0,
            stdout="",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.set_tmux_session_environment_shared",
        lambda *, session_name, env_vars: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.prepare_headless_agent_window_shared",
        lambda *, session_name: None,
    )
