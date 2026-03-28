"""Demo-owned `houmao-server` lifecycle helpers."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

from houmao.server.client import HoumaoServerClient

from .models import DemoPaths, ServerProcessState, utc_now_iso


class DemoServerError(RuntimeError):
    """Raised when demo-owned server lifecycle steps fail."""


def choose_free_loopback_port() -> int:
    """Select one currently-free loopback TCP port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def start_demo_server(
    *,
    api_base_url: str,
    paths: DemoPaths,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> ServerProcessState:
    """Start the demo-owned server and wait for health."""

    paths.server_logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = paths.server_logs_dir / "houmao-server.stdout.log"
    stderr_path = paths.server_logs_dir / "houmao-server.stderr.log"
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "houmao.server",
            "serve",
            "--api-base-url",
            api_base_url,
            "--runtime-root",
            str(paths.server_runtime_root),
            "--no-startup-child",
        ],
        cwd=str(_repo_root()),
        env=dict(env),
        stdout=stdout_handle,
        stderr=stderr_handle,
        start_new_session=True,
    )
    stdout_handle.close()
    stderr_handle.close()
    wait_for_server_health(api_base_url=api_base_url, timeout_seconds=timeout_seconds)
    return ServerProcessState(
        api_base_url=api_base_url,
        port=int(api_base_url.rsplit(":", 1)[-1]),
        runtime_root=paths.server_runtime_root,
        home_dir=paths.server_home_dir,
        pid=process.pid,
        started_at_utc=utc_now_iso(),
        started_by_demo=True,
        stdout_log_path=stdout_path,
        stderr_log_path=stderr_path,
    )


def wait_for_server_health(*, api_base_url: str, timeout_seconds: float) -> None:
    """Wait until the selected server reports healthy status."""

    client = HoumaoServerClient(api_base_url, timeout_seconds=1.0)
    deadline = time.monotonic() + timeout_seconds
    last_error = "server did not become healthy"
    while time.monotonic() < deadline:
        try:
            health = client.health_extended()
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
            continue
        if health.status == "ok" and health.houmao_service == "houmao-server":
            return
        last_error = health.model_dump_json()
        time.sleep(0.25)
    raise DemoServerError(
        f"timed out waiting for demo-owned houmao-server health at {api_base_url}: {last_error}"
    )


def stop_demo_server(server: ServerProcessState, *, timeout_seconds: float) -> None:
    """Best-effort stop for one previously-started server process."""

    pid = server.pid
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.2)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _repo_root() -> Path:
    """Return the repository root for subprocess launches."""

    return Path(__file__).resolve().parents[4]
