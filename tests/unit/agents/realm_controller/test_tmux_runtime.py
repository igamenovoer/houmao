from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    TmuxPaneRecord,
    capture_tmux_pane,
    create_tmux_session,
    prepare_headless_agent_window,
    has_tmux_session,
    load_tmux_buffer,
    list_tmux_panes,
    list_tmux_sessions,
    paste_tmux_buffer,
    read_tmux_session_environment_value,
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
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
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
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
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
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return _completed(cmd, returncode=1, stderr="no server running on /tmp/tmux")

    monkeypatch.setattr("subprocess.run", _fake_run)
    assert list_tmux_sessions() == set()


def test_create_tmux_session_surfaces_tmux_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return _completed(cmd, returncode=1, stderr="duplicate session: AGENTSYS-gpu")

    monkeypatch.setattr("subprocess.run", _fake_run)
    with pytest.raises(TmuxCommandError, match="duplicate session"):
        create_tmux_session(
            session_name="AGENTSYS-gpu",
            working_directory=tmp_path,
        )


def test_prepare_headless_agent_window_renames_and_selects_window_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        captured.append(cmd)
        return _completed(cmd)

    monkeypatch.setattr("subprocess.run", _fake_run)

    prepare_headless_agent_window(session_name="AGENTSYS-gpu")

    assert captured == [
        ["tmux", "rename-window", "-t", "AGENTSYS-gpu:0", "agent"],
        ["tmux", "select-window", "-t", "AGENTSYS-gpu:0"],
    ]


def test_set_tmux_session_environment_surfaces_key_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = {"count": 0}

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
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


def test_read_tmux_session_environment_value_returns_none_for_unknown_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        return _completed(cmd, returncode=1, stderr="unknown variable: HOUMAO")

    monkeypatch.setattr("subprocess.run", _fake_run)

    assert (
        read_tmux_session_environment_value(
            session_name="AGENTSYS-gpu",
            variable_name="HOUMAO_TERMINAL_RECORD_LIVE_STATE",
        )
        is None
    )


def test_list_tmux_panes_parses_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        return _completed(
            cmd,
            stdout=(
                "%1\tAGENTSYS-gpu\t@2\t1\tdeveloper-1\t0\t1\t0\n"
                "%2\tAGENTSYS-gpu\t@2\t1\tdeveloper-1\t1\t0\t0\n"
            ),
        )

    monkeypatch.setattr("subprocess.run", _fake_run)

    assert list_tmux_panes(session_name="AGENTSYS-gpu") == (
        TmuxPaneRecord(
            pane_id="%1",
            session_name="AGENTSYS-gpu",
            window_id="@2",
            window_index="1",
            window_name="developer-1",
            pane_index="0",
            pane_active=True,
            pane_dead=False,
        ),
        TmuxPaneRecord(
            pane_id="%2",
            session_name="AGENTSYS-gpu",
            window_id="@2",
            window_index="1",
            window_name="developer-1",
            pane_index="1",
            pane_active=False,
            pane_dead=False,
        ),
    )


def test_capture_tmux_pane_surfaces_tmux_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        return _completed(cmd, returncode=1, stderr="can't find pane: %9")

    monkeypatch.setattr("subprocess.run", _fake_run)

    with pytest.raises(TmuxCommandError, match="can't find pane"):
        capture_tmux_pane(target="%9")


def test_load_tmux_buffer_builds_expected_command(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        input: str,
    ) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        captured["check"] = check
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["input"] = input
        return _completed(cmd)

    monkeypatch.setattr("subprocess.run", _fake_run)

    load_tmux_buffer(buffer_name="houmao-buffer", text="hello\nworld")

    assert captured == {
        "cmd": ["tmux", "load-buffer", "-b", "houmao-buffer", "-"],
        "check": False,
        "capture_output": True,
        "text": True,
        "input": "hello\nworld",
    }


def test_paste_tmux_buffer_requests_bracketed_paste(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text, timeout
        captured[:] = cmd
        return _completed(cmd)

    monkeypatch.setattr("subprocess.run", _fake_run)

    paste_tmux_buffer(
        target="AGENTSYS-gpu:0.0",
        buffer_name="houmao-buffer",
        bracketed_paste=True,
    )

    assert captured == [
        "tmux",
        "paste-buffer",
        "-p",
        "-b",
        "houmao-buffer",
        "-t",
        "AGENTSYS-gpu:0.0",
    ]
