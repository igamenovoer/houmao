"""Execution-scoped tmux selectors stay independent of enclosing sessions."""

from concurrent.futures import ThreadPoolExecutor
import logging
import os
from pathlib import Path
import subprocess
from threading import Barrier
from types import SimpleNamespace
from typing import Any

import libtmux
import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.boundary_models import SessionManifestTmuxSectionV1
from houmao.agents.realm_controller.registry_models import RegistryTerminalV2
from houmao.execution import tmux
from houmao.execution.tmux import (
    TmuxCommandError,
    TmuxInvalidObservation,
    TmuxObservationUnavailable,
    TmuxServer,
    capture_tmux_socket_path,
    current_tmux_socket_path,
    tmux_server_scope,
)


def test_scoped_commands_clear_inherited_tmux_without_mutating_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native launch and buffer paths use the bound socket and child environment."""

    monkeypatch.setenv("TMUX", "/operator/server.sock,123,0")
    monkeypatch.setenv("TMUX_PANE", "%operator")
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        """Capture the exact command environment without invoking tmux."""

        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(tmux.subprocess, "run", run)
    with tmux_server_scope("/owner/private.sock"):
        server = TmuxServer()
        server.start(["new-session", "-d", "-s", "shared-name"], environment=os.environ)
        server.load_buffer("fixture", "literal")
    assert len(calls) == 2
    for argv, kwargs in calls:
        assert argv[:3] == ["tmux", "-S", "/owner/private.sock"]
        assert "TMUX" not in kwargs["env"]
        assert "TMUX_PANE" not in kwargs["env"]
    assert calls[1][1]["input"] == "literal"
    assert "literal" not in calls[1][0]
    assert capture_tmux_socket_path() == "/operator/server.sock"
    assert os.environ["TMUX_PANE"] == "%operator"
    assert current_tmux_socket_path() is None


def test_libtmux_receives_explicit_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct library-based pane/session access selects the same server."""

    selected: list[tuple[str, str | None]] = []

    class Server:
        """Provide just the library surface used by session listing."""

        def __init__(self, *, socket_path: str, tmux_bin: str | None) -> None:
            selected.append((socket_path, tmux_bin))

        def cmd(self, command: str, *args: str) -> SimpleNamespace:
            """Return a checked observation through the pinned command interface."""

            assert [command, *args] == ["list-sessions", "-F", "#{session_name}"]
            return SimpleNamespace(returncode=0, stdout=["live"], stderr=[])

    monkeypatch.setattr(libtmux, "Server", Server)
    with tmux_server_scope("/owner/private.sock"):
        assert TmuxServer(executable="/caller/bin/tmux").list_sessions() == {"live"}
    assert selected == [("/owner/private.sock", "/caller/bin/tmux")]


def test_nested_and_concurrent_scopes_do_not_leak() -> None:
    """Each thread and nested operation restores its own selector."""

    callers = Barrier(2)

    def observed(path: str) -> tuple[str, str]:
        """Retain one server binding independently of a new nested selection."""

        with tmux_server_scope(path):
            server = TmuxServer()
            with tmux_server_scope(None):
                assert TmuxServer().socket_path == path
            with tmux_server_scope("/nested.sock"):
                assert TmuxServer().socket_path == "/nested.sock"
                assert server.socket_path == path
                callers.wait(timeout=5)
            return server.socket_path, TmuxServer().socket_path

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(observed, ["/first.sock", "/second.sock"]))
    assert results == [("/first.sock", "/first.sock"), ("/second.sock", "/second.sock")]
    assert current_tmux_socket_path() is None


@pytest.mark.parametrize(
    ("returncode", "stdout", "error_type"),
    [
        (0, ["malformed\tpane"], TmuxInvalidObservation),
        (2, [], TmuxObservationUnavailable),
    ],
)
def test_observation_failure_is_not_absence(
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: list[str],
    error_type: type[TmuxCommandError],
) -> None:
    """Invalid rows and silent nonzero status cannot establish missing panes."""

    calls: list[tuple[str, ...]] = []

    def cmd(_server: libtmux.Server, *args: str) -> SimpleNamespace:
        """Return malformed rows or a fixture-shim style silent refusal."""

        calls.append(args)
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=[])

    monkeypatch.setattr(libtmux.Server, "cmd", cmd)
    with pytest.raises(error_type) as caught:
        TmuxServer("/owner/private.sock").observe_session("agent")
    assert len(calls) == 1
    assert calls[0][:4] == ("list-panes", "-s", "-t", "=agent:")
    if returncode:
        assert caught.value.returncode == returncode


def test_silent_mutation_is_not_replayed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing paste stays on the checked socket and is sent only once."""

    calls: list[tuple[str, ...]] = []

    def cmd(server: libtmux.Server, *args: str) -> SimpleNamespace:
        """Record one refused mutation on the expected socket."""

        assert server.socket_path == "/owner/private.sock"
        calls.append(args)
        return SimpleNamespace(returncode=2, stdout=[], stderr=[])

    monkeypatch.setattr(libtmux.Server, "cmd", cmd)
    with pytest.raises(TmuxCommandError, match="status 2") as caught:
        TmuxServer("/owner/private.sock").paste_buffer("private", "%3", delete_after=True)
    assert caught.value.returncode == 2
    assert calls == [("paste-buffer", "-p", "-d", "-b", "private", "-t", "%3")]


def test_sensitive_values_stay_out_of_diagnostics(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Neither a native stdin failure nor libtmux logging exposes payload text."""

    secret = "fixture-private-payload"
    log = logging.getLogger("libtmux.common")

    def native(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        """Simulate a child that prints the failed stdin payload in both streams."""

        assert argv == ["tmux", "-S", "/owner/private.sock", "load-buffer", "-b", "prompt", "-"]
        assert kwargs["input"] == secret
        return subprocess.CompletedProcess(argv, 2, secret, secret)

    def command(_server: libtmux.Server, *args: str) -> SimpleNamespace:
        """Simulate libtmux attaching argument and output data to its log record."""

        assert args == ("send-keys", "-t", "%3", "-l", "--", secret)
        log.error("libtmux subprocess failed", extra={"tmux_cmd": args, "tmux_stdout": secret})
        return SimpleNamespace(returncode=2, stdout=[secret], stderr=[secret])

    monkeypatch.setattr(tmux.subprocess, "run", native)
    monkeypatch.setattr(libtmux.Server, "cmd", command)
    server = TmuxServer("/owner/private.sock")
    with caplog.at_level(logging.DEBUG, logger=log.name):
        with pytest.raises(TmuxCommandError, match="load-buffer.*status 2") as load_failure:
            server.load_buffer("prompt", secret)
        with pytest.raises(TmuxCommandError, match="send-keys.*status 2") as key_failure:
            server.send_keys("%3", secret, literal=True)
        log.debug("ordinary log message")
    assert secret not in str(load_failure.value)
    assert secret not in str(key_failure.value)
    assert [record.getMessage() for record in caplog.records] == ["ordinary log message"]


def test_capture_enclosing_socket_preserves_commas() -> None:
    """Native trailing fields delimit the socket without local filesystem access."""

    assert capture_tmux_socket_path({"TMUX": "/owner/path,comma/server,123,4"}) == (
        "/owner/path,comma/server"
    )
    with pytest.raises(ValueError, match="malformed"):
        capture_tmux_socket_path({"TMUX": "unusable"})


@pytest.mark.parametrize("value", ["relative.sock", "", "/tmp/invalid\x00.sock"])
def test_persisted_socket_rejects_invalid_paths(value: str) -> None:
    """Owner authority never accepts relative or invalid native socket locators."""

    with pytest.raises(ValidationError):
        SessionManifestTmuxSectionV1(session_name="agent", socket_path=value)
    with pytest.raises(ValidationError):
        RegistryTerminalV2(current_session_name="agent", socket_path=value)


def test_persisted_socket_does_not_resolve_foreign_path(tmp_path: Path) -> None:
    """A valid absolute socket remains an opaque owner-local locator."""

    target = tmp_path / "not-created" / "server.sock"
    record = SessionManifestTmuxSectionV1(session_name="agent", socket_path=str(target))
    assert record.socket_path == str(target)
    assert not target.parent.exists()
