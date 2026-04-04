from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.codex_headless import (
    CodexHeadlessSession,
)
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessSessionState,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessRunResult,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
)


def _sample_codex_launch_plan(tmp_path: Path, *, prompt: str = "role prompt") -> LaunchPlan:
    return LaunchPlan(
        backend="codex_headless",
        tool="codex",
        executable="codex",
        args=["--x"],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "sk-secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="gpu-kernel-coder",
            prompt=prompt,
        ),
        metadata={"codex_headless_cli_mode": "exec_json_resume"},
    )


@pytest.fixture(autouse=True)
def _stub_tmux_and_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.ensure_codex_home_bootstrap",
        lambda *, home_path, env, working_directory: None,
    )


def test_codex_headless_builds_new_turn_command(tmp_path: Path) -> None:
    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-codex",
        ),
    )
    captured: dict[str, object] = {}

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
            captured["command"] = command
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="thread-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    events = session.send_prompt("hello world")

    assert captured["command"] == [
        "codex",
        "--x",
        "-c",
        "developer_instructions=role prompt",
        "exec",
        "--json",
        "hello world",
    ]
    assert session.state.turn_index == 1
    assert session.state.session_id == "thread-1"
    assert events[-1].payload == {
        "session_id": "thread-1",
        "tmux_session_name": "HOUMAO-codex",
        "stdout_path": None,
        "stderr_path": None,
        "canonical_path": None,
        "completion_source": "direct_process",
    }


def test_codex_headless_builds_resume_turn_command(tmp_path: Path) -> None:
    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            session_id="thread-1",
            turn_index=1,
            role_bootstrap_applied=True,
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-codex",
        ),
    )
    captured: dict[str, object] = {}

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
            captured["command"] = command
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="thread-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    session.send_prompt("next turn")

    assert captured["command"] == [
        "codex",
        "--x",
        "-c",
        "developer_instructions=role prompt",
        "exec",
        "--json",
        "resume",
        "thread-1",
        "next turn",
    ]


def test_codex_headless_skips_empty_developer_instructions(tmp_path: Path) -> None:
    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path, prompt=""),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-codex",
        ),
    )
    captured: dict[str, object] = {}

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
            captured["command"] = command
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="thread-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    session.send_prompt("hello world")

    assert captured["command"] == ["codex", "--x", "exec", "--json", "hello world"]
