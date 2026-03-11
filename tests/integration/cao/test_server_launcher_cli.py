"""Integration coverage for detached CAO launcher lifecycle behavior."""

from __future__ import annotations

import json
import os
import socket
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


def _source_repo_root() -> Path:
    """Return the tracked repo root for subprocess PYTHONPATH wiring."""

    return Path(__file__).resolve().parents[3]


def _write_executable(path: Path, content: str) -> None:
    """Write an executable test helper script."""

    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _port_is_listening(port: int) -> bool:
    """Return whether a TCP listener is already bound on loopback for the port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _write_fake_cao_server(fake_bin_dir: Path) -> None:
    """Install a fake `cao-server` executable that serves `/health`."""

    _write_executable(
        fake_bin_dir / "cao-server",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            from __future__ import annotations

            import json
            from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


            class Handler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:  # noqa: N802
                    if self.path != "/health":
                        self.send_response(404)
                        self.end_headers()
                        return

                    payload = json.dumps(
                        {"status": "ok", "service": "cli-agent-orchestrator"}
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)

                def log_message(self, format: str, *args: object) -> None:  # noqa: A003
                    return


            server = ThreadingHTTPServer(("127.0.0.1", 9889), Handler)
            print("fake cao-server ready", flush=True)
            server.serve_forever()
            """
        ),
    )


def _write_config(tmp_path: Path) -> Path:
    """Write a launcher config that targets the fake loopback server."""

    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "cao-server-launcher.toml"
    config_path.write_text(
        "\n".join(
            [
                'base_url = "http://127.0.0.1:9889"',
                f'runtime_root = "{tmp_path / "runtime"}"',
                f'home_dir = "{home_dir}"',
                'proxy_policy = "clear"',
                "startup_timeout_seconds = 5",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _run_launcher_command(
    command_name: str,
    *,
    config_path: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run the launcher CLI through a separate Python process."""

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "gig_agents.cao.tools.cao_server_launcher",
            command_name,
            "--config",
            str(config_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=_source_repo_root(),
    )


def test_cli_start_remains_healthy_after_launcher_process_exits(tmp_path: Path) -> None:
    """Launcher start should leave a detached service reachable from later commands."""

    if _port_is_listening(9889):
        pytest.skip("loopback port 9889 is already in use")

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    _write_fake_cao_server(fake_bin_dir)

    config_path = _write_config(tmp_path)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env.get('PATH', '')}"
    env["PYTHONPATH"] = f"{_source_repo_root() / 'src'}:{env.get('PYTHONPATH', '')}"

    start_result = _run_launcher_command("start", config_path=config_path, env=env)
    try:
        assert start_result.returncode == 0, start_result.stderr
        start_payload = json.loads(start_result.stdout)
        assert start_payload["healthy"] is True
        assert start_payload["started_new_process"] is True
        assert start_payload["reused_existing_process"] is False

        status_result = _run_launcher_command("status", config_path=config_path, env=env)
        assert status_result.returncode == 0, status_result.stderr
        status_payload = json.loads(status_result.stdout)
        assert status_payload["healthy"] is True
        assert status_payload["service"] == "cli-agent-orchestrator"

        ownership_file = Path(start_payload["ownership_file"])
        ownership_payload = json.loads(ownership_file.read_text(encoding="utf-8"))
        assert ownership_file.exists()
        assert ownership_payload["launch_mode"] == "detached"
        assert ownership_payload["base_url"] == "http://127.0.0.1:9889"
    finally:
        stop_result = _run_launcher_command("stop", config_path=config_path, env=env)
        assert stop_result.returncode == 0, stop_result.stderr
