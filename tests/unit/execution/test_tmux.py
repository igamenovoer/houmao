"""Execution-scoped tmux selectors stay independent of enclosing sessions."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
from typing import Any

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.backends import tmux_runtime
from houmao.agents.realm_controller.boundary_models import SessionManifestTmuxSectionV1
from houmao.agents.realm_controller.registry_models import RegistryTerminalV2
from houmao.execution.tmux import (
    capture_tmux_socket_path,
    current_tmux_socket_path,
    tmux_argv,
    tmux_server_scope,
)


def test_scoped_commands_clear_inherited_tmux_without_mutating_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both command and buffer paths honor an explicit runtime selector."""

    monkeypatch.setenv("TMUX", "/operator/server.sock,123,0")
    monkeypatch.setenv("TMUX_PANE", "%operator")
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        """Capture the exact command environment without invoking tmux."""

        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(tmux_runtime.subprocess, "run", run)
    with tmux_server_scope("/owner/private.sock"):
        tmux_runtime.has_tmux_session(session_name="shared-name")
        tmux_runtime.load_tmux_buffer(buffer_name="fixture", text="literal")
    assert len(calls) == 2
    for argv, kwargs in calls:
        assert argv[:3] == ["tmux", "-S", "/owner/private.sock"]
        assert "TMUX" not in kwargs["env"]
        assert "TMUX_PANE" not in kwargs["env"]
    assert calls[1][1]["input"] == "literal"
    assert capture_tmux_socket_path() == "/operator/server.sock"
    assert current_tmux_socket_path() is None


def test_libtmux_receives_explicit_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct library-based pane/session access selects the same server."""

    import libtmux

    selected: list[str | None] = []

    class Server:
        """Provide just the library surface used by session listing."""

        def __init__(self, *, socket_path: str | None = None) -> None:
            selected.append(socket_path)
            self.sessions: list[Any] = []

    monkeypatch.setattr(libtmux, "Server", Server)
    with tmux_server_scope("/owner/private.sock"):
        assert tmux_runtime.list_tmux_sessions() == set()
    assert selected == ["/owner/private.sock"]


def test_nested_and_concurrent_scopes_do_not_leak() -> None:
    """Each thread and nested operation restores its own selector."""

    def observed(path: str) -> list[str]:
        """Build argv under one independent caller's explicit binding."""

        with tmux_server_scope(path):
            with tmux_server_scope(None):
                assert current_tmux_socket_path() == path
            with tmux_server_scope("/nested.sock"):
                assert current_tmux_socket_path() == "/nested.sock"
            return tmux_argv(["has-session", "-t", "same-name"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(observed, ["/first.sock", "/second.sock"]))
    assert [argv[2] for argv in results] == ["/first.sock", "/second.sock"]
    assert current_tmux_socket_path() is None


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
