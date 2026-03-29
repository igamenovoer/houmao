from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.backends.local_interactive import LocalInteractiveSession
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxControlInputError,
    TmuxControlInputSegment,
    parse_tmux_control_input,
    send_tmux_control_input,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.runtime import RuntimeSessionController


def _sample_launch_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="claude_headless",
        tool="claude",
        executable="claude",
        args=[],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env={"ANTHROPIC_API_KEY": "secret"},
        env_var_names=["ANTHROPIC_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt",
            role_name="gpu-kernel-coder",
            prompt="role prompt",
        ),
        metadata={},
    )


def _sample_local_interactive_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="local_interactive",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="gpu-kernel-coder",
            prompt="role prompt",
        ),
        metadata={},
    )


def _make_local_interactive_session(tmp_path: Path) -> LocalInteractiveSession:
    session = object.__new__(LocalInteractiveSession)
    session.backend = "local_interactive"
    session._plan = _sample_local_interactive_plan(tmp_path)
    session._state = HeadlessSessionState(
        turn_index=0,
        role_bootstrap_applied=False,
        working_directory=str(tmp_path),
        tmux_session_name="AGENTSYS-local",
    )
    return session


def test_parse_tmux_control_input_mixes_literal_and_special_keys() -> None:
    segments = parse_tmux_control_input(
        sequence="/model<[Enter]><[Down]><[Enter]>",
    )

    assert segments == (
        TmuxControlInputSegment(kind="literal", value="/model"),
        TmuxControlInputSegment(kind="special", value="Enter"),
        TmuxControlInputSegment(kind="special", value="Down"),
        TmuxControlInputSegment(kind="special", value="Enter"),
    )


def test_parse_tmux_control_input_escape_mode_keeps_literal_text() -> None:
    segments = parse_tmux_control_input(
        sequence="/model<[Enter]>",
        escape_special_keys=True,
    )

    assert segments == (TmuxControlInputSegment(kind="literal", value="/model<[Enter]>"),)


def test_parse_tmux_control_input_preserves_marker_like_literal_text() -> None:
    segments = parse_tmux_control_input(sequence="<[<[Enter]>")

    assert segments == (
        TmuxControlInputSegment(kind="literal", value="<["),
        TmuxControlInputSegment(kind="special", value="Enter"),
    )


def test_parse_tmux_control_input_rejects_unsupported_exact_tokens() -> None:
    with pytest.raises(TmuxControlInputError, match=r"<\[escape\]>"):
        parse_tmux_control_input(sequence="<[escape]>")


def test_send_tmux_control_input_uses_literal_mode_without_auto_enter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def _fake_run_tmux(
        args: list[str],
        *,
        timeout_seconds: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        commands.append(args)
        return subprocess.CompletedProcess(
            args=["tmux", *args],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime.run_tmux",
        _fake_run_tmux,
    )

    send_tmux_control_input(
        target="@2",
        segments=(
            TmuxControlInputSegment(kind="literal", value="/model"),
            TmuxControlInputSegment(kind="special", value="Enter"),
            TmuxControlInputSegment(kind="special", value="Down"),
        ),
    )

    assert commands == [
        ["send-keys", "-t", "@2", "-l", "/model"],
        ["send-keys", "-t", "@2", "Enter"],
        ["send-keys", "-t", "@2", "Down"],
    ]


def test_local_interactive_send_prompt_uses_paste_buffer_and_separate_submit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_local_interactive_session(tmp_path)
    loaded_buffers: list[tuple[str, str]] = []
    pasted_buffers: list[tuple[str, str, bool]] = []
    parse_calls: list[tuple[str, bool]] = []
    sent_segments: list[tuple[str, tuple[TmuxControlInputSegment, ...]]] = []
    enter_segments = (TmuxControlInputSegment(kind="special", value="Enter"),)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.local_interactive.load_tmux_buffer_shared",
        lambda *, buffer_name, text: loaded_buffers.append((buffer_name, text)),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.local_interactive.paste_tmux_buffer_shared",
        lambda *, target, buffer_name, bracketed_paste: pasted_buffers.append(
            (target, buffer_name, bracketed_paste)
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.local_interactive.parse_tmux_control_input_shared",
        lambda *, sequence, escape_special_keys=False: (
            parse_calls.append((sequence, escape_special_keys)) or enter_segments
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.local_interactive.send_tmux_control_input_shared",
        lambda *, target, segments: sent_segments.append((target, segments)),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.local_interactive.time.sleep",
        lambda _seconds: None,
    )

    events = session.send_prompt("reply with <[Enter]> literally")

    assert len(loaded_buffers) == 1
    buffer_name, prompt_text = loaded_buffers[0]
    assert buffer_name.startswith("houmao-submit-prompt-")
    assert prompt_text == "reply with <[Enter]> literally"
    assert pasted_buffers == [("AGENTSYS-local:0.0", buffer_name, True)]
    assert parse_calls == [("<[Enter]>", False)]
    assert sent_segments == [("AGENTSYS-local:0.0", enter_segments)]
    assert session.state.turn_index == 1
    assert events[0].kind == "submitted"
    assert events[0].payload == {"tmux_session_name": "AGENTSYS-local"}


def test_local_interactive_send_input_ex_keeps_raw_sequence_unmodified(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_local_interactive_session(tmp_path)
    parse_calls: list[tuple[str, bool]] = []
    sent_segments: list[tuple[str, tuple[TmuxControlInputSegment, ...]]] = []
    raw_segments = (TmuxControlInputSegment(kind="literal", value="hello world"),)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.local_interactive.parse_tmux_control_input_shared",
        lambda *, sequence, escape_special_keys=False: (
            parse_calls.append((sequence, escape_special_keys)) or raw_segments
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.local_interactive.send_tmux_control_input_shared",
        lambda *, target, segments: sent_segments.append((target, segments)),
    )

    result = session.send_input_ex("hello world")

    assert parse_calls == [("hello world", False)]
    assert sent_segments == [("AGENTSYS-local:0.0", raw_segments)]
    assert result.status == "ok"
    assert result.action == "control_input"


def test_local_interactive_build_launch_command_skips_empty_developer_instructions(
    tmp_path: Path,
) -> None:
    session = object.__new__(LocalInteractiveSession)
    session._plan = LaunchPlan(
        backend="local_interactive",
        tool="codex",
        executable="codex",
        args=["exec"],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="gpu-kernel-coder",
            prompt="",
        ),
        metadata={},
    )

    assert session._build_launch_command() == ["codex", "exec"]  # noqa: SLF001


def test_local_interactive_build_launch_command_skips_empty_append_prompt(tmp_path: Path) -> None:
    session = object.__new__(LocalInteractiveSession)
    session._plan = LaunchPlan(
        backend="local_interactive",
        tool="claude",
        executable="claude",
        args=["-p"],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt",
            role_name="gpu-kernel-coder",
            prompt="",
        ),
        metadata={},
    )

    assert session._build_launch_command() == ["claude", "-p"]  # noqa: SLF001


def test_runtime_session_controller_rejects_non_cao_control_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _FakeHeadlessSession:
        backend = "claude_headless"

        def send_prompt(self, prompt: str) -> list[object]:
            del prompt
            return []

        def interrupt(self) -> object:
            raise AssertionError("interrupt should not be called")

        def terminate(self) -> object:
            raise AssertionError("terminate should not be called")

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        RuntimeSessionController,
        "persist_manifest",
        lambda self: None,
    )

    controller = RuntimeSessionController(
        launch_plan=_sample_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=tmp_path / "session.json",
        backend_session=_FakeHeadlessSession(),  # type: ignore[arg-type]
    )

    result = controller.send_input_ex("<[Escape]>")

    assert result.status == "error"
    assert result.action == "control_input"
    assert "backend='claude_headless'" in result.detail
