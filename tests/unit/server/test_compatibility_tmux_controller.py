from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from houmao.server.control_core.tmux_controller import (
    CompatibilityTmuxController,
    CompatibilityTmuxError,
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


def test_create_session_with_window_applies_default_config_injection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.delenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", raising=False)

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        calls.append(cmd)
        if cmd[1] == "new-session":
            return _completed(cmd, stdout="@1\t0\tagent\n")
        return _completed(cmd)

    monkeypatch.setattr("subprocess.run", _fake_run)

    record = CompatibilityTmuxController().create_session_with_window(
        session_name="cao-gpu",
        window_name="agent",
        working_directory=tmp_path,
    )

    assert record.window_id == "@1"
    assert calls == [
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            "cao-gpu",
            "-n",
            "agent",
            "-c",
            str(tmp_path),
            "-P",
            "-F",
            "#{window_id}\t#{window_index}\t#{window_name}",
        ],
        ["tmux", "set-option", "-t", "cao-gpu", "mouse", "on"],
        ["tmux", "set-option", "-t", "cao-gpu", "default-terminal", "tmux-256color"],
        ["tmux", "set-option", "-at", "cao-gpu", "terminal-overrides", ",*256col*:Tc"],
        ["tmux", "set-environment", "-t", "cao-gpu", "TERM", "tmux-256color"],
        ["tmux", "set-environment", "-t", "cao-gpu", "COLORTERM", "truecolor"],
        ["tmux", "set-environment", "-t", "cao-gpu", "-u", "NO_COLOR"],
    ]


def test_create_session_with_window_skips_config_injection_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", "0")

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        calls.append(cmd)
        return _completed(cmd, stdout="@1\t0\tagent\n")

    monkeypatch.setattr("subprocess.run", _fake_run)

    CompatibilityTmuxController().create_session_with_window(
        session_name="cao-gpu",
        window_name="agent",
        working_directory=tmp_path,
    )

    assert len(calls) == 1
    assert calls[0][1] == "new-session"


def test_create_session_with_window_cleans_up_and_guides_when_injection_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.delenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", raising=False)

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        calls.append(cmd)
        if cmd[1] == "new-session":
            return _completed(cmd, stdout="@1\t0\tagent\n")
        if cmd[1:4] == ["set-option", "-t", "cao-gpu"]:
            return _completed(cmd, returncode=1, stderr="bad option")
        return _completed(cmd)

    monkeypatch.setattr("subprocess.run", _fake_run)

    with pytest.raises(
        CompatibilityTmuxError,
        match="tmux config injection.*HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0",
    ):
        CompatibilityTmuxController().create_session_with_window(
            session_name="cao-gpu",
            window_name="agent",
            working_directory=tmp_path,
        )

    assert calls[-1] == ["tmux", "kill-session", "-t", "cao-gpu"]
