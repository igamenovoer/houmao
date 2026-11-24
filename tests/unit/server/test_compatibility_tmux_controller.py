"""Compatibility behavior at the shared terminal-operation boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from houmao.execution.tmux import TmuxCommandResult, TmuxServer
from houmao.server.control_core.tmux_controller import (
    CompatibilityTmuxController,
    CompatibilityTmuxError,
)


@pytest.fixture
def tmux_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Record the scoped controller operations without invoking tmux."""

    calls: list[list[str]] = []

    def _fake_start(
        self: TmuxServer, args: Sequence[str], *, environment: Mapping[str, str]
    ) -> TmuxCommandResult:
        assert "TMUX" not in environment
        assert "TMUX_PANE" not in environment
        calls.append(list(args))
        return TmuxCommandResult(tuple(args), 0, "$0\t@1\t0\tagent\n", "")

    def _fake_command(
        self: TmuxServer, args: Sequence[str], *, sensitive: bool = False, no_start: bool = False
    ) -> TmuxCommandResult:
        calls.append(list(args))
        return TmuxCommandResult(tuple(args), 0, "", "")

    monkeypatch.setattr(TmuxServer, "start", _fake_start)
    monkeypatch.setattr(TmuxServer, "command", _fake_command)
    return calls


def test_create_session_with_window_applies_default_config_injection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tmux_calls: list[list[str]]
) -> None:
    monkeypatch.delenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", raising=False)

    record = CompatibilityTmuxController().create_session_with_window(
        session_name="cao-gpu",
        window_name="agent",
        working_directory=tmp_path,
    )

    assert record.window_id == "@1"
    assert tmux_calls == [
        [
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
            "#{session_id}\t#{window_id}\t#{window_index}\t#{window_name}",
        ],
        ["set-option", "-t", "$0", "mouse", "on"],
        ["set-option", "-t", "$0", "default-terminal", "tmux-256color"],
        ["set-option", "-at", "$0", "terminal-overrides", ",*256col*:Tc"],
        ["set-environment", "-t", "$0", "TERM", "tmux-256color"],
        ["set-environment", "-t", "$0", "COLORTERM", "truecolor"],
        ["set-environment", "-t", "$0", "-u", "NO_COLOR"],
    ]


def test_create_session_with_window_skips_config_injection_when_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tmux_calls: list[list[str]]
) -> None:
    monkeypatch.setenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", "0")

    CompatibilityTmuxController().create_session_with_window(
        session_name="cao-gpu",
        window_name="agent",
        working_directory=tmp_path,
    )

    assert len(tmux_calls) == 1
    assert tmux_calls[0][0] == "new-session"


def test_create_session_with_window_cleans_up_and_guides_when_injection_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tmux_calls: list[list[str]]
) -> None:
    monkeypatch.delenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", raising=False)

    def _fail_option(
        self: TmuxServer, args: Sequence[str], *, sensitive: bool = False, no_start: bool = False
    ) -> TmuxCommandResult:
        tmux_calls.append(list(args))
        if args[0] == "set-option":
            return TmuxCommandResult(tuple(args), 1, "", "bad option")
        return TmuxCommandResult(tuple(args), 0, "", "")

    monkeypatch.setattr(TmuxServer, "command", _fail_option)

    with pytest.raises(
        CompatibilityTmuxError,
        match="tmux config injection.*HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0",
    ):
        CompatibilityTmuxController().create_session_with_window(
            session_name="cao-gpu",
            window_name="agent",
            working_directory=tmp_path,
        )

    assert tmux_calls[-1] == ["kill-session", "-t", "$0"]


def test_failed_compatibility_paste_cleans_its_buffer_and_does_not_submit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def _fake_command(
        self: TmuxServer, args: Sequence[str], *, sensitive: bool = False, no_start: bool = False
    ) -> TmuxCommandResult:
        calls.append(tuple(args))
        if args[0] == "display-message":
            return TmuxCommandResult(tuple(args), 0, "@1\t%3\t/work\n", "")
        if args[0] == "paste-buffer":
            return TmuxCommandResult(tuple(args), 1, "", "")
        return TmuxCommandResult(tuple(args), 0, "", "")

    def _fake_load(self: TmuxServer, name: str, text: str) -> None:
        assert text == "literal Enter"
        calls.append(("load-buffer", name))

    monkeypatch.setattr(TmuxServer, "command", _fake_command)
    monkeypatch.setattr(TmuxServer, "load_buffer", _fake_load)

    with pytest.raises(CompatibilityTmuxError, match="paste-buffer exited with status 1"):
        CompatibilityTmuxController().send_text(window_id="@1", text="literal Enter")

    assert [call[0] for call in calls] == [
        "display-message",
        "load-buffer",
        "paste-buffer",
        "delete-buffer",
    ]
    assert calls[-1][2] == calls[1][1]
    assert calls[-2][-1] == "%3"
