from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from gig_agents.agents.brain_launch_runtime.backends.tmux_runtime import (
    TmuxCommandError,
    create_tmux_session,
    has_tmux_session,
    list_tmux_sessions,
    set_tmux_session_environment,
    show_tmux_environment,
)


def _completed(
    args: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_has_tmux_session_builds_expected_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def _fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool, timeout: float | None = None
    ) -> subprocess.CompletedProcess[str]:
        captured[:] = cmd
        return _completed(cmd)

    monkeypatch.setattr("subprocess.run", _fake_run)
    result = has_tmux_session(session_name="AGENTSYS-gpu")
    assert result.returncode == 0
    assert captured == ["tmux", "has-session", "-t", "AGENTSYS-gpu"]


def test_show_tmux_environment_builds_expected_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def _fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool, timeout: float | None = None
    ) -> subprocess.CompletedProcess[str]:
        captured[:] = cmd
        return _completed(cmd, stdout="AGENTSYS_MANIFEST_PATH=/tmp/x.json\n")

    monkeypatch.setattr("subprocess.run", _fake_run)
    result = show_tmux_environment(
        session_name="AGENTSYS-gpu",
        variable_name="AGENTSYS_MANIFEST_PATH",
    )
    assert result.returncode == 0
    assert captured == [
        "tmux",
        "show-environment",
        "-t",
        "AGENTSYS-gpu",
        "AGENTSYS_MANIFEST_PATH",
    ]


def test_list_tmux_sessions_normalizes_no_server(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool, timeout: float | None = None
    ) -> subprocess.CompletedProcess[str]:
        return _completed(cmd, returncode=1, stderr="no server running on /tmp/tmux")

    monkeypatch.setattr("subprocess.run", _fake_run)
    assert list_tmux_sessions() == set()


def test_create_tmux_session_surfaces_tmux_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool, timeout: float | None = None
    ) -> subprocess.CompletedProcess[str]:
        return _completed(cmd, returncode=1, stderr="duplicate session: AGENTSYS-gpu")

    monkeypatch.setattr("subprocess.run", _fake_run)
    with pytest.raises(TmuxCommandError, match="duplicate session"):
        create_tmux_session(
            session_name="AGENTSYS-gpu",
            working_directory=tmp_path,
        )


def test_set_tmux_session_environment_surfaces_key_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = {"count": 0}

    def _fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool, timeout: float | None = None
    ) -> subprocess.CompletedProcess[str]:
        call_count["count"] += 1
        if call_count["count"] == 1:
            return _completed(cmd)
        return _completed(cmd, returncode=1, stderr="unknown variable")

    monkeypatch.setattr("subprocess.run", _fake_run)
    with pytest.raises(TmuxCommandError, match="AGENTSYS_MANIFEST_PATH"):
        set_tmux_session_environment(
            session_name="AGENTSYS-gpu",
            env_vars={
                "AGENTSYS_TOOL": "codex",
                "AGENTSYS_MANIFEST_PATH": "/tmp/session.json",
            },
        )
