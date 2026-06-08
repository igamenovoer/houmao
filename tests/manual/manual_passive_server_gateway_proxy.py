"""Manual smoke validation for passive-server gateway proxy routes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from typing import Any
from urllib import error, parse, request
import uuid

from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryGatewayV1,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.agents.realm_controller.registry_storage import publish_live_agent_record


@dataclass
class _GatewayCapture:
    """Captured fake-gateway request state."""

    agent_id: str
    session_name: str
    port: int
    request_payloads: list[dict[str, Any]] = field(default_factory=list)


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
            "--runtime-root",
            env["HOUMAO_GLOBAL_RUNTIME_DIR"],
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


def _wait_for_gateway_agent(
    *,
    base_url: str,
    agent_id: str,
    timeout_seconds: float = 12.0,
) -> dict[str, Any]:
    """Wait until a discovered gateway-backed agent appears."""

    deadline = time.monotonic() + timeout_seconds
    last_body: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        status, body = _request_json(method="GET", base_url=base_url, path="/houmao/agents")
        if status == 200:
            last_body = body
            agents = body.get("agents")
            if isinstance(agents, list):
                for agent in agents:
                    if (
                        isinstance(agent, dict)
                        and agent.get("agent_id") == agent_id
                        and agent.get("has_gateway") is True
                    ):
                        return agent
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for gateway-backed agent {agent_id}: {last_body}")


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


def _start_tmux_session(session_name: str) -> None:
    """Start a detached tmux session used for discovery liveness."""

    if shutil.which("tmux") is None:
        raise RuntimeError("tmux not found on PATH")
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "sleep", "600"],
        check=True,
        capture_output=True,
        text=True,
    )


def _kill_tmux_session(session_name: str) -> None:
    """Kill a tmux session if it still exists."""

    if shutil.which("tmux") is None:
        return
    subprocess.run(
        ["tmux", "kill-session", "-t", session_name],
        check=False,
        capture_output=True,
        text=True,
    )


def _make_gateway_handler(capture: _GatewayCapture) -> type[BaseHTTPRequestHandler]:
    """Create a fake-gateway request handler bound to captured state."""

    class _FakeGatewayHandler(BaseHTTPRequestHandler):
        """Minimal fake gateway for passive-server proxy validation."""

        def do_GET(self) -> None:
            """Serve fake gateway status."""

            parsed = parse.urlsplit(self.path)
            if parsed.path != "/v1/status":
                self._send_json(404, {"detail": f"Unknown path: {parsed.path}"})
                return
            self._send_json(200, _gateway_status_payload(capture))

        def do_POST(self) -> None:
            """Serve fake gateway request creation."""

            parsed = parse.urlsplit(self.path)
            if parsed.path != "/v1/requests":
                self._send_json(404, {"detail": f"Unknown path: {parsed.path}"})
                return
            payload = self._read_json()
            capture.request_payloads.append(payload)
            self._send_json(
                200,
                {
                    "request_id": "manual-request-1",
                    "request_kind": payload.get("kind", "submit_prompt"),
                    "state": "accepted",
                    "accepted_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                    "queue_depth": 0,
                    "managed_agent_instance_epoch": 1,
                },
            )

        def log_message(self, format: str, *args: object) -> None:
            """Suppress default stderr logging in the manual smoke script."""

        def _read_json(self) -> dict[str, Any]:
            """Read one JSON request body."""

            length = int(self.headers.get("content-length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
            decoded = json.loads(raw_body)
            if not isinstance(decoded, dict):
                raise RuntimeError(f"Expected JSON object request, got: {decoded!r}")
            return decoded

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            """Write one JSON response."""

            raw_body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(raw_body)))
            self.end_headers()
            self.wfile.write(raw_body)

    return _FakeGatewayHandler


def _gateway_status_payload(capture: _GatewayCapture) -> dict[str, Any]:
    """Build a strict gateway status payload accepted by the gateway client."""

    return {
        "schema_version": 1,
        "protocol_version": "v1",
        "attach_identity": capture.agent_id,
        "backend": "claude_headless",
        "tmux_session_name": capture.session_name,
        "gateway_health": "healthy",
        "managed_agent_connectivity": "connected",
        "managed_agent_recovery": "idle",
        "request_admission": "open",
        "terminal_surface_eligibility": "ready",
        "active_execution": "idle",
        "execution_mode": "detached_process",
        "queue_depth": 0,
        "gateway_host": "127.0.0.1",
        "gateway_port": capture.port,
        "managed_agent_instance_epoch": 1,
        "managed_agent_instance_id": "manual-instance-1",
    }


def _start_fake_gateway(
    *,
    agent_id: str,
    session_name: str,
    port: int,
) -> tuple[ThreadingHTTPServer, threading.Thread, _GatewayCapture]:
    """Start the fake gateway HTTP server."""

    capture = _GatewayCapture(agent_id=agent_id, session_name=session_name, port=port)
    server = ThreadingHTTPServer(("127.0.0.1", port), _make_gateway_handler(capture))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, capture


def _stop_fake_gateway(server: ThreadingHTTPServer, thread: threading.Thread) -> None:
    """Stop the fake gateway HTTP server."""

    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _record(
    *,
    agent_name: str,
    session_name: str,
    generation_id: str,
    runtime_root: Path,
    gateway_port: int,
) -> ManagedAgentRegistryRecordV3:
    """Build one active gateway-backed managed-agent registry record."""

    now = datetime.now(UTC)
    agent_id = derive_agent_id_from_name(agent_name)
    session_root = runtime_root / "manual-sessions" / agent_id
    session_root.mkdir(parents=True, exist_ok=True)
    return ManagedAgentRegistryRecordV3(
        agent_name=agent_name,
        agent_id=agent_id,
        generation_id=generation_id,
        lifecycle=RegistryLifecycleV1(
            state="active",
            relaunchable=True,
            state_updated_at=now.isoformat(timespec="seconds"),
        ),
        identity=RegistryIdentityV1(backend="claude_headless", tool="claude"),
        runtime=RegistryRuntimeV1(
            manifest_path=str(session_root / "manifest.json"),
            session_root=str(session_root),
            agent_def_dir=str(_repo_root() / "tests" / "fixtures" / "plain-agent-def"),
        ),
        terminal=RegistryTerminalV2(
            current_session_name=session_name,
            last_session_name=session_name,
        ),
        liveness=RegistryLivenessV1(
            published_at=now.isoformat(timespec="seconds"),
            lease_expires_at=(now + timedelta(hours=1)).isoformat(timespec="seconds"),
        ),
        gateway=RegistryGatewayV1(
            host="127.0.0.1",
            port=gateway_port,
            state_path=str(session_root / "gateway-state.json"),
            protocol_version="v1",
        ),
        mailbox=None,
    )


def main() -> None:
    """Run the passive-server gateway proxy smoke scenario."""

    repo_root = _repo_root()
    token = uuid.uuid4().hex[:8]
    session_name = f"houmao-passive-gateway-{token}"
    agent_name = f"HOUMAO-passive-gateway-{token}"
    agent_id = derive_agent_id_from_name(agent_name)
    tmp_root = Path(tempfile.mkdtemp(prefix="houmao-passive-gateway-")).resolve()
    process: subprocess.Popen[str] | None = None
    fake_gateway: tuple[ThreadingHTTPServer, threading.Thread, _GatewayCapture] | None = None
    try:
        env = _manual_env(tmp_root)
        _start_tmux_session(session_name)
        gateway_port = _free_port()
        fake_gateway = _start_fake_gateway(
            agent_id=agent_id,
            session_name=session_name,
            port=gateway_port,
        )
        publish_live_agent_record(
            _record(
                agent_name=agent_name,
                session_name=session_name,
                generation_id=f"manual-gateway-{token}",
                runtime_root=Path(env["HOUMAO_GLOBAL_RUNTIME_DIR"]),
                gateway_port=gateway_port,
            ),
            env=env,
        )

        passive_port = _free_port()
        base_url = f"http://127.0.0.1:{passive_port}"
        process = _start_passive_server(repo_root=repo_root, env=env, port=passive_port)
        _wait_for_health(process=process, base_url=base_url)

        summary = _wait_for_gateway_agent(base_url=base_url, agent_id=agent_id)
        assert summary["has_gateway"] is True, summary

        status, gateway_status = _request_json(
            method="GET",
            base_url=base_url,
            path=f"/houmao/agents/{agent_id}/gateway",
        )
        _assert_status(status, 200, gateway_status)
        assert gateway_status["gateway_host"] == "127.0.0.1", gateway_status
        assert gateway_status["gateway_port"] == gateway_port, gateway_status
        assert gateway_status["gateway_health"] == "healthy", gateway_status

        prompt_payload = {
            "schema_version": 1,
            "kind": "submit_prompt",
            "payload": {"prompt": "manual passive-server gateway proxy smoke"},
        }
        status, accepted = _request_json(
            method="POST",
            base_url=base_url,
            path=f"/houmao/agents/{agent_id}/gateway/requests",
            payload=prompt_payload,
        )
        _assert_status(status, 200, accepted)
        assert accepted["request_id"] == "manual-request-1", accepted
        assert accepted["request_kind"] == "submit_prompt", accepted
        capture = fake_gateway[2]
        assert len(capture.request_payloads) == 1, capture.request_payloads
        forwarded = capture.request_payloads[0]
        assert forwarded["schema_version"] == 1, forwarded
        assert forwarded["kind"] == "submit_prompt", forwarded
        assert forwarded["payload"]["prompt"] == prompt_payload["payload"]["prompt"], forwarded

        print("manual-passive-server-gateway-proxy=PASS")
        print(f"base_url={base_url}")
        print(f"agent_id={agent_id}")
        print(f"fake_gateway_port={gateway_port}")
    finally:
        if process is not None:
            _terminate_process(process)
        if fake_gateway is not None:
            _stop_fake_gateway(fake_gateway[0], fake_gateway[1])
        _kill_tmux_session(session_name)
        try:
            shutil.rmtree(tmp_root, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
