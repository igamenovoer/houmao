from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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
