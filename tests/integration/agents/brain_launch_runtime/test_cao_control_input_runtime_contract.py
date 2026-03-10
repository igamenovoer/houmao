from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from gig_agents.agents.brain_launch_runtime.backends.cao_rest import (
    CaoRestSession,
    CaoSessionState,
)
from gig_agents.agents.brain_launch_runtime.models import LaunchPlan, RoleInjectionPlan
from gig_agents.cao.models import CaoTerminal


def _sample_launch_plan(tmp_path: Path) -> LaunchPlan:
    env_file = tmp_path / "codex-vars.env"
    env_file.write_text("OPENAI_API_KEY=from-profile\n", encoding="utf-8")
    return LaunchPlan(
        backend="cao_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="gpu-kernel-coder",
            prompt="Be precise",
        ),
        metadata={"env_source_file": str(env_file)},
    )


def _resume_state(tmp_path: Path, *, tmux_window_name: str | None) -> CaoSessionState:
    return CaoSessionState(
        api_base_url="http://localhost:9889",
        session_name="AGENTSYS-gpu",
        terminal_id="term-123",
        profile_name="runtime-profile",
        profile_path=str(tmp_path / "runtime-profile.md"),
        parsing_mode="shadow_only",
        tmux_window_name=tmux_window_name,
        turn_index=2,
    )


def test_cao_control_input_uses_persisted_tmux_window_without_live_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("persisted tmux_window_name should avoid CAO fallback")

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
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest._list_tmux_windows",
        lambda *, session_name: [
            SimpleNamespace(
                window_id="@2",
                window_index="1",
                window_name="developer-1",
            )
        ],
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.tmux_runtime.run_tmux",
        _fake_run_tmux,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        existing_state=_resume_state(tmp_path, tmux_window_name="developer-1"),
    )

    result = session.send_input_ex("/model<[Enter]><[Down]>")

    assert result.status == "ok"
    assert result.action == "control_input"
    assert commands == [
        ["send-keys", "-t", "@2", "-l", "/model"],
        ["send-keys", "-t", "@2", "Enter"],
        ["send-keys", "-t", "@2", "Down"],
    ]
    assert session.state.tmux_window_name == "developer-1"


def test_cao_control_input_falls_back_to_live_terminal_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []
    list_windows_call_count = {"count": 0}
    terminal_lookup_count = {"count": 0}

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            terminal_lookup_count["count"] += 1
            return CaoTerminal(
                id=terminal_id,
                name="developer-7",
                provider="codex",
                session_name="AGENTSYS-gpu",
                agent_profile="runtime-profile",
                status="idle",
            )

    def _fake_list_tmux_windows(*, session_name: str) -> list[object]:
        assert session_name == "AGENTSYS-gpu"
        list_windows_call_count["count"] += 1
        if list_windows_call_count["count"] == 1:
            return [
                SimpleNamespace(
                    window_id="@1",
                    window_index="0",
                    window_name="bootstrap",
                )
            ]
        return [
            SimpleNamespace(
                window_id="@7",
                window_index="1",
                window_name="developer-7",
            )
        ]

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
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest._list_tmux_windows",
        _fake_list_tmux_windows,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.tmux_runtime.run_tmux",
        _fake_run_tmux,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        existing_state=_resume_state(tmp_path, tmux_window_name="stale-window"),
    )

    result = session.send_input_ex("<[Escape]>")

    assert result.status == "ok"
    assert commands == [["send-keys", "-t", "@7", "Escape"]]
    assert terminal_lookup_count["count"] == 1
    assert session.state.tmux_window_name == "developer-7"


def test_cao_control_input_returns_explicit_error_when_target_is_unresolved(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            return CaoTerminal(
                id=terminal_id,
                name="developer-9",
                provider="codex",
                session_name="AGENTSYS-gpu",
                agent_profile="runtime-profile",
                status="idle",
            )

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.backends.cao_rest._list_tmux_windows",
        lambda *, session_name: [
            SimpleNamespace(
                window_id="@1",
                window_index="0",
                window_name="bootstrap",
            )
        ],
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        existing_state=_resume_state(tmp_path, tmux_window_name=None),
    )

    result = session.send_input_ex("<[Escape]>")

    assert result.status == "error"
    assert result.action == "control_input"
    assert "Unable to resolve live tmux target" in result.detail
