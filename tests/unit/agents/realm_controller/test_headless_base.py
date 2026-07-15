from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
)
from houmao.agents.realm_controller.backends.kimi_headless import (
    KimiHeadlessSession,
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
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RelaunchChatSessionSelection,
    RoleInjectionPlan,
)
from houmao.agents.model_selection import ModelConfig, ModelReasoningConfig


def _fake_tool_executable(tmp_path: Path, name: str) -> Path:
    executable = tmp_path / "fake-bin" / name
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    return executable


def _sample_kimi_launch_plan(
    tmp_path: Path,
    *,
    executable: str | None = None,
    args: list[str] | None = None,
) -> LaunchPlan:
    resolved_executable = executable or str(_fake_tool_executable(tmp_path, "kimi"))
    return LaunchPlan(
        backend="kimi_headless",
        tool="kimi",
        executable=resolved_executable,
        args=list(args or []),
        working_directory=tmp_path,
        home_env_var="KIMI_CODE_HOME",
        home_path=tmp_path / "kimi-home",
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
    args: list[str] | None = None,
) -> LaunchPlan:
    return LaunchPlan(
        backend="claude_headless",
        tool="claude",
        executable="claude",
        args=list(args or []),
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


def test_kimi_headless_builds_new_turn_command_with_managed_skills_dir(
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    session = KimiHeadlessSession(
        launch_plan=_sample_kimi_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-kimi",
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
            **_kwargs,
        ) -> HeadlessRunResult:
            del env, cwd, turn_index, output_format, tmux_session_name, turn_artifacts_root
            captured["command"] = list(command)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="kimi-session-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    session.send_prompt("hello")

    assert captured["command"] == [
        str(tmp_path / "fake-bin" / "kimi"),
        "--skills-dir",
        str(tmp_path / "kimi-home" / "skills"),
        "-p",
        "bootstrap\n\nhello",
        "--output-format",
        "stream-json",
    ]
    assert "--auto" not in captured["command"]
    assert "--yolo" not in captured["command"]
    assert "--plan" not in captured["command"]


def test_kimi_headless_builds_exact_resume_turn_command(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    session = KimiHeadlessSession(
        launch_plan=_sample_kimi_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            session_id="kimi-session-1",
            turn_index=1,
            role_bootstrap_applied=True,
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-kimi",
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
            **_kwargs,
        ) -> HeadlessRunResult:
            del env, cwd, turn_index, output_format, tmux_session_name, turn_artifacts_root
            captured["command"] = list(command)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="kimi-session-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    session.send_prompt("hello")

    assert captured["command"] == [
        str(tmp_path / "fake-bin" / "kimi"),
        "--session",
        "kimi-session-1",
        "--skills-dir",
        str(tmp_path / "kimi-home" / "skills"),
        "-p",
        "hello",
        "--output-format",
        "stream-json",
    ]


def test_kimi_headless_builds_latest_resume_turn_command_from_selector(
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    session = KimiHeadlessSession(
        launch_plan=_sample_kimi_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-kimi",
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
            **_kwargs,
        ) -> HeadlessRunResult:
            del env, cwd, turn_index, output_format, tmux_session_name, turn_artifacts_root
            captured["command"] = list(command)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="kimi-session-latest",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    session.send_prompt(
        "hello",
        session_selection=HeadlessTurnSessionSelection(mode="tool_last_or_new"),
    )

    assert captured["command"] == [
        str(tmp_path / "fake-bin" / "kimi"),
        "--continue",
        "--skills-dir",
        str(tmp_path / "kimi-home" / "skills"),
        "-p",
        "hello",
        "--output-format",
        "stream-json",
    ]


def test_kimi_headless_execution_model_projects_model_arg_before_prompt(
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    session = KimiHeadlessSession(
        launch_plan=_sample_kimi_launch_plan(tmp_path, args=["--temperature", "0"]),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-kimi",
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
            **_kwargs,
        ) -> HeadlessRunResult:
            del env, cwd, turn_index, output_format, tmux_session_name, turn_artifacts_root
            captured["command"] = list(command)
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="kimi-session-model",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    session.send_prompt(
        "hello",
        execution_model=ModelConfig(name="kimi-code/kimi-for-coding"),
    )

    assert captured["command"] == [
        str(tmp_path / "fake-bin" / "kimi"),
        "--temperature",
        "0",
        "--model",
        "kimi-code/kimi-for-coding",
        "--skills-dir",
        str(tmp_path / "kimi-home" / "skills"),
        "-p",
        "bootstrap\n\nhello",
        "--output-format",
        "stream-json",
    ]


def test_headless_relaunch_selector_sets_next_prompt_resume_policy(tmp_path: Path) -> None:
    session = object.__new__(ClaudeHeadlessSession)
    session._state = HeadlessSessionState(  # type: ignore[attr-defined]
        session_id="old-session",
        role_bootstrap_applied=False,
        working_directory=str(tmp_path),
        tmux_session_name="HOUMAO-claude",
    )

    session._apply_relaunch_chat_session(  # noqa: SLF001
        RelaunchChatSessionSelection(mode="exact", session_id="provider-session-1")
    )

    assert session._state.session_id is None  # noqa: SLF001
    assert session._state.resume_selection_kind == "exact"  # noqa: SLF001
    assert session._state.resume_selection_value == "provider-session-1"  # noqa: SLF001
    assert session._state.role_bootstrap_applied is True  # noqa: SLF001

    session._apply_relaunch_chat_session(RelaunchChatSessionSelection(mode="new"))  # noqa: SLF001

    assert session._state.resume_selection_kind == "none"  # noqa: SLF001
    assert session._state.resume_selection_value is None  # noqa: SLF001
    assert session._state.role_bootstrap_applied is False  # noqa: SLF001


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
            **_kwargs,
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
            **_kwargs,
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


def test_claude_headless_includes_model_selection_args_from_launch_plan(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    session = ClaudeHeadlessSession(
        launch_plan=_sample_claude_launch_plan(
            tmp_path,
            args=["--model", "sonnet", "--effort", "high"],
        ),
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
            **_kwargs,
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
        "--model",
        "sonnet",
        "--effort",
        "high",
        "-p",
        "--verbose",
        "--append-system-prompt",
        "role prompt",
        "hello",
        "--output-format",
        "stream-json",
    ]


def test_claude_headless_uses_execution_model_args_for_one_prompt_only(
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

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
            **_kwargs,
        ) -> HeadlessRunResult:
            del env, cwd, turn_index, output_format, tmux_session_name, turn_artifacts_root
            commands.append(list(command))
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="sess-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]

    session.send_prompt(
        "hello",
        execution_model=ModelConfig(
            name="sonnet",
            reasoning=ModelReasoningConfig(level=3),
        ),
    )
    session.send_prompt("next")

    assert commands[0] == [
        "claude",
        "--model",
        "sonnet",
        "--effort",
        "high",
        "-p",
        "--verbose",
        "--append-system-prompt",
        "role prompt",
        "hello",
        "--output-format",
        "stream-json",
    ]
    assert commands[1] == [
        "claude",
        "-p",
        "--verbose",
        "--resume",
        "sess-1",
        "next",
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
            **_kwargs,
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
            **_kwargs,
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
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("EXAMPLE_TOKEN", "abc")
    monkeypatch.delenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", raising=False)

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

    KimiHeadlessSession(
        launch_plan=_sample_kimi_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        agent_def_dir=agent_def_dir,
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-kimi",
        ),
    )

    assert captured_tmux_env["session_name"] == "HOUMAO-kimi"
    assert prepared_sessions == ["HOUMAO-kimi"]
    env_vars = captured_tmux_env["env_vars"]
    assert isinstance(env_vars, dict)
    assert env_vars[AGENT_MANIFEST_PATH_ENV_VAR] == str((tmp_path / "session.json").resolve())
    assert env_vars[AGENT_DEF_DIR_ENV_VAR] == str(agent_def_dir.resolve())
    assert env_vars["TERM"] == "tmux-256color"
    assert env_vars["COLORTERM"] == "truecolor"
    assert "NO_COLOR" not in env_vars
    assert env_vars["EXAMPLE_TOKEN"] == "abc"


def test_headless_resume_preserves_color_env_when_tmux_injection_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_tmux_env: dict[str, object] = {}
    monkeypatch.setenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", "0")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("COLORTERM", "")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.set_tmux_session_environment_shared",
        lambda *, session_name, env_vars: captured_tmux_env.update(
            {"session_name": session_name, "env_vars": dict(env_vars)}
        ),
    )

    KimiHeadlessSession(
        launch_plan=_sample_kimi_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-kimi",
        ),
    )

    env_vars = captured_tmux_env["env_vars"]
    assert isinstance(env_vars, dict)
    assert env_vars["NO_COLOR"] == "1"
    assert env_vars["TERM"] == "dumb"
    assert env_vars["COLORTERM"] == ""


def test_headless_env_injects_loopback_no_proxy_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)
    session = KimiHeadlessSession(
        launch_plan=_sample_kimi_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-kimi",
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
            **_kwargs,
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
    session = KimiHeadlessSession(
        launch_plan=_sample_kimi_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-kimi",
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
            **_kwargs,
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
        lambda name: None if name == "kimi" else "/usr/bin/tmux",
    )

    with pytest.raises(BackendExecutionError, match="command -v kimi"):
        KimiHeadlessSession(
            launch_plan=_sample_kimi_launch_plan(tmp_path, executable="kimi"),
            role_name="gpu-kernel-coder",
            session_manifest_path=tmp_path / "session.json",
            state=HeadlessSessionState(
                working_directory=str(tmp_path),
                tmux_session_name="HOUMAO-kimi",
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
