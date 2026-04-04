from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    TmuxPaneRecord,
    attach_tmux_session,
    capture_tmux_pane,
    create_tmux_session,
    prepare_headless_agent_window,
    has_tmux_session,
    load_tmux_buffer,
    list_tmux_panes,
    list_tmux_sessions,
    paste_tmux_buffer,
    read_tmux_session_environment_value,
    resolve_tmux_pane,
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


class _FakeLibtmuxCmd:
    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: list[str] | None = None,
        stderr: list[str] | None = None,
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout or []
        self.stderr = stderr or []


class _FakeLibtmuxPane:
    def __init__(
        self,
        *,
        pane_id: str,
        session_name: str,
        window_id: str,
        window_index: str,
        window_name: str,
        pane_index: str,
        pane_active: str = "0",
        pane_pid: str | None = None,
        pane_dead: str | None = None,
        display_values: dict[str, str] | None = None,
        capture_lines: list[str] | None = None,
    ) -> None:
        self.pane_id = pane_id
        self.session_name = session_name
        self.window_id = window_id
        self.window_index = window_index
        self.window_name = window_name
        self.pane_index = pane_index
        self.pane_active = pane_active
        if pane_pid is not None:
            self.pane_pid = pane_pid
        if pane_dead is not None:
            self.pane_dead = pane_dead
        self.m_display_values = display_values or {}
        self.m_display_calls: list[tuple[str, bool]] = []
        self.m_capture_lines = capture_lines or []

    def display_message(self, expression: str, get_text: bool = False) -> list[str]:
        self.m_display_calls.append((expression, get_text))
        return [self.m_display_values.get(expression, "")]

    def capture_pane(
        self,
        start: str | int | None = None,
        end: str | int | None = None,
        *,
        escape_sequences: bool = False,
    ) -> list[str]:
        assert start == "-"
        assert end == "-"
        assert escape_sequences is True
        return list(self.m_capture_lines)


class _FakeLibtmuxSession:
    def __init__(
        self,
        *,
        session_name: str,
        panes: list[_FakeLibtmuxPane],
        client_cmd: _FakeLibtmuxCmd | None = None,
        attach_error: Exception | None = None,
    ) -> None:
        self.session_name = session_name
        self.panes = panes
        self.m_client_cmd = client_cmd or _FakeLibtmuxCmd(stdout=[])
        self.m_attach_calls = 0
        self.m_attach_error = attach_error

    def cmd(self, command: str, *args: str, target: str | int | None = None) -> _FakeLibtmuxCmd:
        assert command == "list-clients"
        assert args == ("-F", "#{client_tty}")
        del target
        return self.m_client_cmd

    def attach(self) -> None:
        self.m_attach_calls += 1
        if self.m_attach_error is not None:
            raise self.m_attach_error


class _FakeLibtmuxServer:
    def __init__(
        self,
        *,
        sessions: list[_FakeLibtmuxSession],
        capture_cmd: _FakeLibtmuxCmd | None = None,
    ) -> None:
        self.sessions = sessions
        self.m_capture_cmd = capture_cmd or _FakeLibtmuxCmd(stdout=[])

    def cmd(self, command: str, *args: str, target: str | int | None = None) -> _FakeLibtmuxCmd:
        assert command == "capture-pane"
        assert args == ("-p", "-e", "-S", "-")
        assert target is not None
        return self.m_capture_cmd


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
    result = has_tmux_session(session_name="HOUMAO-gpu")
    assert result.returncode == 0
    assert captured == ["tmux", "has-session", "-t", "HOUMAO-gpu"]


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
        return _completed(cmd, stdout="HOUMAO_MANIFEST_PATH=/tmp/x.json\n")

    monkeypatch.setattr("subprocess.run", _fake_run)
    result = show_tmux_environment(
        session_name="HOUMAO-gpu",
        variable_name="HOUMAO_MANIFEST_PATH",
    )
    assert result.returncode == 0
    assert captured == [
        "tmux",
        "show-environment",
        "-t",
        "HOUMAO-gpu",
        "HOUMAO_MANIFEST_PATH",
    ]


def test_list_tmux_sessions_normalizes_no_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime._libtmux_server",
        lambda: (_ for _ in ()).throw(RuntimeError("no server running on /tmp/tmux")),
    )
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
        return _completed(cmd, returncode=1, stderr="duplicate session: HOUMAO-gpu")

    monkeypatch.setattr("subprocess.run", _fake_run)
    with pytest.raises(TmuxCommandError, match="duplicate session"):
        create_tmux_session(
            session_name="HOUMAO-gpu",
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

    prepare_headless_agent_window(session_name="HOUMAO-gpu")

    assert captured == [
        ["tmux", "rename-window", "-t", "HOUMAO-gpu:0", "agent"],
        ["tmux", "select-window", "-t", "HOUMAO-gpu:0"],
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
    with pytest.raises(TmuxCommandError, match="HOUMAO_MANIFEST_PATH"):
        set_tmux_session_environment(
            session_name="HOUMAO-gpu",
            env_vars={
                "HOUMAO_TOOL": "codex",
                "HOUMAO_MANIFEST_PATH": "/tmp/session.json",
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
            session_name="HOUMAO-gpu",
            variable_name="HOUMAO_TERMINAL_RECORD_LIVE_STATE",
        )
        is None
    )


def test_list_tmux_panes_parses_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    panes = [
        _FakeLibtmuxPane(
            pane_id="%1",
            session_name="HOUMAO-gpu",
            window_id="@2",
            window_index="1",
            window_name="developer-1",
            pane_index="0",
            pane_active="1",
            pane_pid="1234",
            display_values={"#{pane_dead}": "0"},
        ),
        _FakeLibtmuxPane(
            pane_id="%2",
            session_name="HOUMAO-gpu",
            window_id="@2",
            window_index="1",
            window_name="developer-1",
            pane_index="1",
            pane_active="0",
            pane_dead="1",
            pane_pid="4321",
        ),
    ]
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime._libtmux_server",
        lambda: _FakeLibtmuxServer(
            sessions=[_FakeLibtmuxSession(session_name="HOUMAO-gpu", panes=panes)]
        ),
    )

    assert list_tmux_panes(session_name="HOUMAO-gpu") == (
        TmuxPaneRecord(
            pane_id="%1",
            session_name="HOUMAO-gpu",
            window_id="@2",
            window_index="1",
            window_name="developer-1",
            pane_index="0",
            pane_active=True,
            pane_dead=False,
            pane_pid=1234,
        ),
        TmuxPaneRecord(
            pane_id="%2",
            session_name="HOUMAO-gpu",
            window_id="@2",
            window_index="1",
            window_name="developer-1",
            pane_index="1",
            pane_active=False,
            pane_dead=True,
            pane_pid=4321,
        ),
    )
    assert panes[0].m_display_calls == [("#{pane_dead}", True)]


def test_attach_tmux_session_uses_libtmux_session_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeLibtmuxSession(session_name="HOUMAO-gpu", panes=[])
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime._libtmux_server",
        lambda: _FakeLibtmuxServer(sessions=[session]),
    )

    attach_tmux_session(session_name="HOUMAO-gpu")

    assert session.m_attach_calls == 1


def test_resolve_tmux_pane_prefers_explicit_window_name_over_current_focus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    panes = [
        _FakeLibtmuxPane(
            pane_id="%1",
            session_name="HOUMAO-local",
            window_id="@1",
            window_index="0",
            window_name="agent",
            pane_index="0",
            pane_active="0",
            pane_dead="0",
            pane_pid="1111",
        ),
        _FakeLibtmuxPane(
            pane_id="%9",
            session_name="HOUMAO-local",
            window_id="@9",
            window_index="1",
            window_name="gateway",
            pane_index="0",
            pane_active="1",
            pane_dead="0",
            pane_pid="9999",
        ),
    ]
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime._libtmux_server",
        lambda: _FakeLibtmuxServer(
            sessions=[_FakeLibtmuxSession(session_name="HOUMAO-local", panes=panes)]
        ),
    )

    resolved = resolve_tmux_pane(session_name="HOUMAO-local", window_name="agent")

    assert resolved.pane_id == "%1"
    assert resolved.window_name == "agent"


def test_resolve_tmux_pane_rejects_ambiguous_session_without_explicit_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    panes = [
        _FakeLibtmuxPane(
            pane_id="%1",
            session_name="HOUMAO-local",
            window_id="@1",
            window_index="0",
            window_name="agent",
            pane_index="0",
            pane_active="0",
            pane_dead="0",
        ),
        _FakeLibtmuxPane(
            pane_id="%9",
            session_name="HOUMAO-local",
            window_id="@9",
            window_index="1",
            window_name="gateway",
            pane_index="0",
            pane_active="1",
            pane_dead="0",
        ),
    ]
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime._libtmux_server",
        lambda: _FakeLibtmuxServer(
            sessions=[_FakeLibtmuxSession(session_name="HOUMAO-local", panes=panes)]
        ),
    )

    with pytest.raises(TmuxCommandError, match="Ambiguous tmux pane target"):
        resolve_tmux_pane(session_name="HOUMAO-local")


def test_capture_tmux_pane_surfaces_tmux_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime._require_libtmux_pane",
        lambda *, pane_id: (_ for _ in ()).throw(TmuxCommandError(f"can't find pane: {pane_id}")),
    )

    with pytest.raises(TmuxCommandError, match="can't find pane"):
        capture_tmux_pane(target="%9")


def test_capture_tmux_pane_uses_pane_bound_capture_for_pane_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pane = _FakeLibtmuxPane(
        pane_id="%9",
        session_name="HOUMAO-local",
        window_id="@9",
        window_index="1",
        window_name="gateway",
        pane_index="0",
        pane_active="1",
        pane_dead="0",
        capture_lines=["line one", "line two"],
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime._require_libtmux_pane",
        lambda *, pane_id: pane,
    )

    assert capture_tmux_pane(target="%9") == "line one\nline two"


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
        target="HOUMAO-gpu:0.0",
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
        "HOUMAO-gpu:0.0",
    ]
