"""Exercise private Web supervisor output and process-tree cleanup with owned children."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token


@pytest.mark.parametrize("escape_group", [False, True])
@pytest.mark.parametrize("stop_signal", [signal.SIGTERM, signal.SIGHUP])
def test_supervisor_keeps_native_output_private_and_reaps_captured_descendants(
    tmp_path: Path, escape_group: bool, stop_signal: signal.Signals
) -> None:
    """Retained native stdout and escaped children cannot outlive exact owned shutdown."""

    child_file = tmp_path / "child.json"
    script = "\n".join(
        [
            "import json, pathlib, subprocess, sys, time",
            f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session={escape_group!r})",
            f"pathlib.Path({str(child_file)!r}).write_text(json.dumps({{'pid': child.pid}}))",
            "print('http://127.0.0.1:12345/?token=synthetic-private-token', flush=True)",
            "time.sleep(60)",
        ]
    )
    invocation = tmp_path / "input.json"
    invocation.write_text(
        json.dumps(
            {
                "root": str(tmp_path),
                "working_directory": str(tmp_path),
                "environment": dict(os.environ),
                "command": [sys.executable, "-u", "-c", script],
            }
        )
    )
    invocation.chmod(0o600)
    supervisor = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "houmao.agents.realm_controller.backends.dsh_web_supervisor",
            "--input",
            str(invocation),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    supervisor_birth = _dispatch_origin_birth_token(supervisor.pid)
    child_pid: int | None = None
    child_birth: str | None = None
    native: dict[str, object] = {}
    try:
        deadline = time.monotonic() + 10
        while not child_file.exists() or not (tmp_path / "supervisor.json").exists():
            assert supervisor.poll() is None
            if time.monotonic() >= deadline:
                pytest.fail("Controlled Web supervisor did not establish its child")
            time.sleep(0.01)
        child_pid = json.loads(child_file.read_text())["pid"]
        child_birth = _dispatch_origin_birth_token(child_pid)
        native = json.loads((tmp_path / "supervisor.json").read_text())
        assert child_birth is not None and supervisor_birth is not None
        assert _dispatch_origin_birth_token(supervisor.pid) == supervisor_birth
        os.kill(supervisor.pid, stop_signal)
        output, _ = supervisor.communicate(timeout=25)
        assert "synthetic-private-token" not in output
        private_log = tmp_path / "native-private.log"
        assert private_log.stat().st_mode & 0o077 == 0
        assert "synthetic-private-token" in private_log.read_text()
        assert _dispatch_origin_birth_token(child_pid) != child_birth
        assert _dispatch_origin_birth_token(native["native_pid"]) != native["native_birth_token"]
        assert not invocation.exists()
    finally:
        # Only these captured children may be signalled; no tmux server is used.
        for pid, birth in [
            (supervisor.pid, supervisor_birth),
            (native.get("native_pid"), native.get("native_birth_token")),
            (child_pid, child_birth),
        ]:
            if (
                type(pid) is int
                and isinstance(birth, str)
                and _dispatch_origin_birth_token(pid) == birth
            ):
                os.kill(pid, signal.SIGKILL)
        supervisor.wait(timeout=5)
