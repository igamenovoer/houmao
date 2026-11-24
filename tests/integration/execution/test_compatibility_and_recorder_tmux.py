"""Exercise compatibility and recording through their bound tmux sockets."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from houmao.execution.tmux import TmuxPaneRecord, TmuxServer, tmux_server_scope
from houmao.server.control_core.tmux_controller import CompatibilityTmuxController
from houmao.terminal_record.models import RecorderMode, load_manifest
from houmao.terminal_record.runtime_bridge import TERMINAL_RECORD_LIVE_STATE_ENV_VAR
from houmao.terminal_record.service import start_terminal_record, stop_terminal_record


@pytest.fixture
def isolated_servers(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TmuxServer, TmuxServer]]:
    """Start two fresh servers with the same first session and pane IDs."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is needed for live compatibility and recorder checks")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setenv("SHELL", "/bin/sh")
    with tempfile.TemporaryDirectory(prefix="hm-tmux-") as directory:
        owner = TmuxServer(Path(directory) / "owner")
        enclosing = TmuxServer(Path(directory) / "enclosing")
        try:
            for server in (owner, enclosing):
                server.start(
                    ["-f", "/dev/null", "new-session", "-d", "-s", "anchor"],
                    environment=server.native_environment(),
                ).require_success()
            monkeypatch.setenv("TMUX", f"{enclosing.socket_path},{os.getpid()},0")
            monkeypatch.setenv("TMUX_PANE", "%0")
            yield owner, enclosing
        finally:
            for server in (owner, enclosing):
                server.command(["kill-server"])


def _wait_for(check: Callable[[], bool]) -> None:
    """Allow a bounded interval for the isolated pane process to render."""

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.05)
    assert check(), "Timed out waiting for isolated tmux evidence"


def _pane(server: TmuxServer, session: str, window: str) -> TmuxPaneRecord:
    """Return the observed pane in one named test window."""

    panes = server.observe_session(session)
    assert panes is not None
    return next(pane for pane in panes if pane.window_name == window)


def test_compatibility_window_lifecycle_input_and_exact_capture(
    isolated_servers: tuple[TmuxServer, TmuxServer], tmp_path: Path
) -> None:
    """Address inactive windows and preserve the native capture output exactly."""

    owner, enclosing = isolated_servers
    controller = CompatibilityTmuxController()
    with tmux_server_scope(enclosing.socket_path):
        controller.create_session_with_window(
            session_name="compat",
            window_name="primary",
            working_directory=tmp_path,
        )
        enclosing_window = controller.create_window(
            session_name="compat", window_name="auxiliary", working_directory=tmp_path
        )

    with tmux_server_scope(owner.socket_path):
        assert not controller.session_exists(session_name="compat")
        primary = controller.create_session_with_window(
            session_name="compat", window_name="primary", working_directory=tmp_path
        )
        auxiliary = controller.create_window(
            session_name="compat", window_name="auxiliary", working_directory=tmp_path
        )
        assert auxiliary.window_id == enclosing_window.window_id
        assert controller.list_windows(session_name="compat") == [primary, auxiliary]
        assert controller.list_clients(session_name="compat") == ()
        assert controller.get_window_working_directory(window_id=auxiliary.window_id) == str(
            tmp_path
        )

        pane = _pane(owner, "compat", "auxiliary")
        controller.wait_for_shell(
            window_id=auxiliary.window_id, timeout_seconds=4, polling_interval_seconds=0.05
        )
        controller.send_command(window_id=auxiliary.window_id, command="stty -echo; cat")
        controller.send_text(
            window_id=auxiliary.window_id, text="literal Enter in an inactive window", enter_count=1
        )
        _wait_for(
            lambda: (
                "literal Enter in an inactive window"
                in controller.capture_window(window_id=auxiliary.window_id)
            )
        )
        native_capture = subprocess.check_output(
            [
                "tmux",
                "-S",
                owner.socket_path,
                "capture-pane",
                "-p",
                "-e",
                "-S",
                "-",
                "-t",
                pane.pane_id,
            ],
            env=owner.native_environment(),
            text=True,
        )
        assert native_capture.endswith("\n\n")
        assert controller.capture_window(window_id=auxiliary.window_id) == native_capture
        assert "literal Enter in an inactive window" not in owner.capture_pane(
            _pane(owner, "compat", "primary").pane_id
        )
        assert "literal Enter in an inactive window" not in enclosing.capture_pane(
            _pane(enclosing, "compat", "auxiliary").pane_id
        )

        controller.send_special_key(window_id=auxiliary.window_id, key_name="C-c")
        _wait_for(
            lambda: (
                owner.checked_command(
                    ["display-message", "-p", "-t", pane.pane_id, "#{pane_current_command}"]
                ).stdout.strip()
                != "cat"
            )
        )
        controller.kill_window(window_id=auxiliary.window_id)
        controller.kill_window(window_id=auxiliary.window_id)
        assert controller.list_windows(session_name="compat") == [primary]
        controller.kill_session(session_name="compat")
        assert not controller.session_exists(session_name="compat")
    assert "compat" in enclosing.list_sessions()


@pytest.mark.parametrize("mode", ["passive", "active"])
def test_recorder_pins_inactive_pane_for_snapshots_and_pty_cast(
    isolated_servers: tuple[TmuxServer, TmuxServer], tmp_path: Path, mode: RecorderMode
) -> None:
    """Record an inactive pane while a foreign server has the same coordinates."""

    repo = Path(__file__).resolve().parents[3]
    asciinema = (
        repo / "extern" / "orphan" / "bin" / f"asciinema-{platform.machine()}-unknown-linux-gnu"
    )
    if shutil.which("pixi") is None or not asciinema.is_file():
        pytest.skip("the Pixi asciinema task and its local binary are needed")

    owner, enclosing = isolated_servers
    for server, marker in ((owner, "OWNER-RECORDING"), (enclosing, "ENCLOSING-RECORDING")):
        server.checked_command(["new-session", "-d", "-s", "capture", "-n", "primary"])
        server.checked_command(
            [
                "new-window",
                "-d",
                "-t",
                "=capture:",
                "-n",
                "recorded",
                f"printf '%s\\n' '{marker}'; exec sleep 30",
            ]
        )

    pane = _pane(owner, "capture", "recorded")
    assert pane.pane_id == _pane(enclosing, "capture", "recorded").pane_id
    assert pane.window_id == _pane(enclosing, "capture", "recorded").window_id
    run_root = tmp_path / "recorder"
    enclosing.checked_command(["new-session", "-d", "-s", "HMREC-recorder"])
    pointer_query = ["show-environment", "-t", "=capture", TERMINAL_RECORD_LIVE_STATE_ENV_VAR]
    enclosing.checked_command(
        ["set-environment", "-t", "=capture", TERMINAL_RECORD_LIVE_STATE_ENV_VAR, "foreign-pointer"]
    )
    with tmux_server_scope(owner.socket_path):
        result = start_terminal_record(
            mode=mode,
            target_session="capture",
            target_pane=pane.pane_id,
            tool=None,
            run_root=run_root,
            sample_interval_seconds=0.1,
            duration_seconds=8,
        )

    try:
        assert result["status"] == "running"
        manifest = load_manifest(run_root / "manifest.json")
        assert manifest.target.socket_path == owner.socket_path
        assert manifest.target.pane_id == pane.pane_id
        assert manifest.target.window_id == pane.window_id
        if mode == "active":
            assert str(run_root / "live_state.json") in owner.checked_command(pointer_query).stdout

        cast = run_root / "session.cast"
        _wait_for(lambda: cast.is_file() and "OWNER-RECORDING" in cast.read_text(encoding="utf-8"))
        assert "ENCLOSING-RECORDING" not in cast.read_text(encoding="utf-8")
    finally:
        stopped = stop_terminal_record(run_root=run_root)
    assert stopped["status"] == "stopped"

    snapshots = [
        json.loads(line)
        for line in (run_root / "pane_snapshots.ndjson").read_text(encoding="utf-8").splitlines()
    ]
    assert snapshots
    for snapshot in snapshots:
        assert snapshot["target_pane_id"] == pane.pane_id
        assert snapshot["target_pane_width"] > 0
        assert snapshot["target_pane_height"] > 0
        assert "OWNER-RECORDING" in snapshot["output_text"]
        assert "ENCLOSING-RECORDING" not in snapshot["output_text"]
    assert manifest.recorder_session_name not in owner.list_sessions()
    assert owner.list_sessions() == {"anchor", "capture"}
    assert owner.command(pointer_query).returncode != 0
    assert "foreign-pointer" in enclosing.checked_command(pointer_query).stdout
    assert enclosing.list_sessions() == {"anchor", "capture", "HMREC-recorder"}
