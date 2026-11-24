"""Exercise project birth and revival on explicitly isolated tmux servers."""

from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from typing import Any

from click.testing import CliRunner, Result
import pytest

from houmao.execution import tmux_selection
from houmao.execution.tmux import TmuxServer, tmux_server_scope
from houmao.srv_ctrl.commands.main import cli


def _invoke(*args: str) -> dict[str, Any]:
    """Run a manager command and decode its JSON object."""

    result = CliRunner().invoke(cli, ["--print-json", *args])
    assert result.exit_code == 0, (result.output, result.exception)
    payload, _ = json.JSONDecoder().raw_decode(result.output.lstrip())
    assert isinstance(payload, dict)
    return payload


def _launch(*args: str) -> Result:
    """Invoke the selected profile for error-path assertions."""

    return CliRunner().invoke(cli, ["project", "agents", "launch", "--profile", "review", *args])


def _wait_for_server_exit(socket: Path) -> None:
    """Allow the explicitly addressed tmux process to exit after its final session."""

    server = TmuxServer(socket, allow_start=False)
    deadline = monotonic() + 4
    while monotonic() < deadline:
        result = server.command(["list-sessions"])
        if result.returncode and (
            "no server running" in result.stderr or "No such file or directory" in result.stderr
        ):
            return
        sleep(0.05)
    raise AssertionError(f"Expected the isolated server at {socket} to exit: {result}")


@pytest.fixture
def socket_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Initialize a synthetic Codex project and a short, private tmux namespace."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required")
    for name in ("TMUX", "TMUX_PANE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("HOUMAO_GLOBAL_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.chdir(tmp_path)
    executable = tmp_path / "codex"
    executable.write_text("#!/bin/sh\nprintf '%s\\n' 'codex-cli 0.167.2'\n", encoding="utf-8")
    executable.chmod(0o700)
    auth = tmp_path / "auth.json"
    auth.write_text('{"logged_in": true}\n', encoding="utf-8")
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    _invoke("project", "init")
    _invoke(
        "project",
        "specialist",
        "create",
        "--name",
        "researcher",
        "--tool",
        "codex",
        "--api-key",
        "synthetic-key",
        "--codex-auth-json",
        str(auth),
        "--system-prompt",
        "Review the supplied inputs.",
    )
    _invoke(
        "project",
        "profile",
        "create",
        "--name",
        "review",
        "--specialist",
        "researcher",
        "--agent-name",
        "reviewer",
        "--mode",
        "headless",
        "--no-gateway",
        "--tmux-server",
        "new",
    )
    with TemporaryDirectory(prefix="hm-prof-") as directory:
        base = Path(directory)
        monkeypatch.setattr(tmux_selection, "_managed_socket_directory", lambda _uid: base)
        monkeypatch.setenv("TMUX_TMPDIR", str(base))
        try:
            yield base
        finally:
            for socket in base.rglob("*"):
                if socket.is_socket():
                    TmuxServer(socket).command(["kill-server"], no_start=True)


def _start_sibling(socket: Path, name: str) -> TmuxServer:
    """Create a test-owned session on an explicitly addressed socket."""

    server = TmuxServer(socket)
    server.start(
        ["-f", "/dev/null", "new-session", "-d", "-s", name], environment=os.environ
    ).require_success()
    return server


def test_stopped_relaunch_reuses_new_socket_after_profile_edit(socket_root: Path) -> None:
    """Saved socket routing survives a change in profile and the enclosing scope."""

    session_name = "overlapping-session"
    sibling = _start_sibling(socket_root / "sibling.sock", session_name)
    with tmux_server_scope(sibling.socket_path):
        launch = _invoke(
            "project", "agents", "launch", "--profile", "review", "--session-name", session_name
        )
        manifest = Path(launch["manifest_path"])
        binding = json.loads(manifest.read_text())["tmux"]
        socket_path = Path(binding["socket_path"])
        assert socket_path.is_relative_to(socket_root)
        assert str(socket_path) != sibling.socket_path
        assert binding["server_allow_start"] is True
        selector = ("agents", "single", "--agent-id", launch["agent_id"])
        result = _launch(
            "--agent-id",
            launch["agent_id"],
            "--force",
            "clean",
            "--tmux-server",
            "socket",
            "--tmux-socket-path",
            str(socket_root / "missing.sock"),
        )
        assert result.exit_code != 0
        assert "missing.sock" in result.output
        assert TmuxServer(socket_path).list_sessions() == {session_name}
        TmuxServer(socket_path).checked_command(["set-option", "-s", "exit-empty", "on"])
        assert _invoke(*selector, "stop")["success"]
        _wait_for_server_exit(socket_path)
        assert sibling.list_sessions() == {session_name}
        _invoke(
            "project",
            "profile",
            "set",
            "--name",
            "review",
            "--tmux-server",
            "socket",
            "--tmux-socket-path",
            sibling.socket_path,
        )
        assert _invoke(*selector, "relaunch")["success"]
        relaunched_binding = json.loads(manifest.read_text())["tmux"]
        assert relaunched_binding["socket_path"] == str(socket_path)
        assert TmuxServer(socket_path).list_sessions() == {relaunched_binding["session_name"]}
        assert sibling.list_sessions() == {session_name}


def test_existing_only_wins_one_birth_and_cannot_restart_server(socket_root: Path) -> None:
    """Precedence and force safety hold on an existing-only server."""

    socket = socket_root / "existing.sock"
    server = _start_sibling(socket, "keeper")
    launch = _invoke(
        "project",
        "agents",
        "launch",
        "--profile",
        "review",
        "--session-name",
        "owned",
        "--tmux-server",
        "socket",
        "--tmux-socket-path",
        str(socket),
    )
    manifest = Path(launch["manifest_path"])
    binding = json.loads(manifest.read_text())["tmux"]
    assert binding["socket_path"] == str(socket)
    assert binding["server_allow_start"] is False
    profile = _invoke("project", "profile", "get", "--name", "review")
    assert profile["defaults"]["posture"]["tmux"]["server"] == "new"
    server.checked_command(["kill-session", "-t", "=keeper"])
    result = _launch(
        "--agent-id",
        launch["agent_id"],
        "--force",
        "clean",
        "--tmux-server",
        "socket",
        "--tmux-socket-path",
        str(socket),
    )
    assert result.exit_code != 0
    assert "would stop the existing-only tmux server" in result.output
    assert server.list_sessions() == {"owned"}

    selector = ("agents", "single", "--agent-id", launch["agent_id"])
    assert _invoke(*selector, "stop")["success"]
    _wait_for_server_exit(socket)
    revived = CliRunner().invoke(cli, ["--print-json", *selector, "relaunch"])
    assert "startup" in revived.output or "unavailable" in revived.output
    _wait_for_server_exit(socket)
    persisted = json.loads(manifest.read_text())["tmux"]
    assert persisted["socket_path"] == str(socket)
    assert persisted["server_allow_start"] is False
