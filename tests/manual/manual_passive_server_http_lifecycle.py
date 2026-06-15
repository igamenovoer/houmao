"""Manual smoke validation for passive-server HTTP lifecycle routes."""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from typing import Any
from urllib import error, request


def _repo_root() -> Path:
    """Return the repository root for this manual script."""

    return Path(__file__).resolve().parents[2]


def _free_port() -> int:
    """Return one currently free localhost TCP port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _manual_env(workdir: Path) -> dict[str, str]:
    """Return an isolated Houmao environment for subprocesses."""

    roots = {
        "HOUMAO_GLOBAL_RUNTIME_DIR": workdir / "runtime",
        "HOUMAO_GLOBAL_REGISTRY_DIR": workdir / "registry",
        "HOUMAO_GLOBAL_MAILBOX_DIR": workdir / "mailbox",
        "HOUMAO_LOCAL_JOBS_DIR": workdir / "jobs",
    }
    for root in roots.values():
        root.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    for key, value in roots.items():
        env[key] = str(value)
    env["HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE"] = "cwd_only"
    return env


def _request_json(
    *,
    method: str,
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 5.0,
) -> tuple[int, dict[str, Any]]:
    """Issue one JSON HTTP request and return status plus decoded object body."""

    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"accept": "application/json"}
    if body is not None:
        headers["content-type"] = "application/json"
    req = request.Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers=headers,
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
            return int(response.status), _decode_json_object(raw_body)
    except error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        return int(exc.code), _decode_json_object(raw_body)


def _decode_json_object(raw_body: str) -> dict[str, Any]:
    """Decode one JSON object response body."""

    if not raw_body:
        return {}
    decoded = json.loads(raw_body)
    if not isinstance(decoded, dict):
        raise RuntimeError(f"Expected JSON object response, got: {decoded!r}")
    return decoded


def _start_passive_server(
    *,
    repo_root: Path,
    env: dict[str, str],
    port: int,
) -> subprocess.Popen[str]:
    """Start the passive-server CLI subprocess."""

    return subprocess.Popen(
        [
            "pixi",
            "run",
            "houmao-passive-server",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_for_health(
    *,
    process: subprocess.Popen[str],
    base_url: str,
    timeout_seconds: float = 20.0,
) -> None:
    """Wait until the passive server answers `/health`."""

    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise RuntimeError(
                "Passive server exited before readiness.\n"
                f"exit={process.returncode}\nstdout:\n{stdout}\nstderr:\n{stderr}"
            )
        try:
            status, body = _request_json(method="GET", base_url=base_url, path="/health")
        except Exception as exc:
            last_error = exc
        else:
            if status == 200 and body.get("houmao_service") == "houmao-passive-server":
                return
        time.sleep(0.2)
    raise RuntimeError(f"Passive server did not become healthy: {last_error!r}")


def _terminate_process(process: subprocess.Popen[str]) -> None:
    """Terminate a subprocess if it is still running."""

    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _assert_status(status: int, expected: int, body: dict[str, Any]) -> None:
    """Raise a clear assertion error for an unexpected HTTP status."""

    if status != expected:
        raise AssertionError(f"Expected HTTP {expected}, got {status}: {body}")


def main() -> None:
    """Run the passive-server HTTP lifecycle smoke scenario."""

    repo_root = _repo_root()
    tmp_root = Path(tempfile.mkdtemp(prefix="houmao-passive-lifecycle-")).resolve()
    process: subprocess.Popen[str] | None = None
    try:
        env = _manual_env(tmp_root)
        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        process = _start_passive_server(repo_root=repo_root, env=env, port=port)
        _wait_for_health(process=process, base_url=base_url)

        status, health = _request_json(method="GET", base_url=base_url, path="/health")
        _assert_status(status, 200, health)
        assert health == {
            "status": "ok",
            "houmao_service": "houmao-passive-server",
        }, health

        status, current = _request_json(
            method="GET",
            base_url=base_url,
            path="/houmao/server/current-instance",
        )
        _assert_status(status, 200, current)
        assert current["status"] == "ok", current
        assert current["api_base_url"] == base_url, current
        assert isinstance(current["pid"], int) and current["pid"] > 0, current
        assert Path(str(current["server_root"])).is_dir(), current

        status, agents = _request_json(method="GET", base_url=base_url, path="/houmao/agents")
        _assert_status(status, 200, agents)
        assert agents == {"agents": []}, agents

        status, shutdown = _request_json(
            method="POST",
            base_url=base_url,
            path="/houmao/server/shutdown",
        )
        _assert_status(status, 200, shutdown)
        assert shutdown == {"status": "ok"}, shutdown

        process.wait(timeout=10)
        print("manual-passive-server-http-lifecycle=PASS")
        print(f"base_url={base_url}")
    finally:
        if process is not None:
            _terminate_process(process)
        try:
            import shutil

            shutil.rmtree(tmp_root, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
