"""Manual smoke validation for passive-server registry discovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
from typing import Any
from urllib import error, request
import uuid

from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.agents.realm_controller.registry_storage import publish_live_agent_record


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


def _wait_for_agent(
    *,
    base_url: str,
    agent_id: str,
    timeout_seconds: float = 12.0,
) -> list[dict[str, Any]]:
    """Wait until a discovered agent appears in the passive-server list."""

    deadline = time.monotonic() + timeout_seconds
    last_body: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        status, body = _request_json(method="GET", base_url=base_url, path="/houmao/agents")
        if status == 200:
            last_body = body
            agents = body.get("agents")
            if isinstance(agents, list) and any(
                isinstance(agent, dict) and agent.get("agent_id") == agent_id for agent in agents
            ):
                return [agent for agent in agents if isinstance(agent, dict)]
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for discovered agent {agent_id}: {last_body}")


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


def _record(
    *,
    agent_name: str,
    session_name: str,
    generation_id: str,
    runtime_root: Path,
) -> ManagedAgentRegistryRecordV3:
    """Build one active managed-agent registry record."""

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
        gateway=None,
        mailbox=None,
    )


def _publish_record(record: ManagedAgentRegistryRecordV3, env: dict[str, str]) -> None:
    """Publish one registry record into the isolated manual registry."""

    publish_live_agent_record(record, env=env)


def main() -> None:
    """Run the passive-server registry discovery smoke scenario."""

    repo_root = _repo_root()
    token = uuid.uuid4().hex[:8]
    live_session = f"houmao-passive-live-{token}"
    dead_session = f"houmao-passive-dead-{token}"
    live_agent_name = f"HOUMAO-passive-live-{token}"
    dead_agent_name = f"HOUMAO-passive-dead-{token}"
    live_agent_id = derive_agent_id_from_name(live_agent_name)
    dead_agent_id = derive_agent_id_from_name(dead_agent_name)
    tmp_root = Path(tempfile.mkdtemp(prefix="houmao-passive-discovery-")).resolve()
    process: subprocess.Popen[str] | None = None
    try:
        env = _manual_env(tmp_root)
        _start_tmux_session(live_session)
        _publish_record(
            _record(
                agent_name=live_agent_name,
                session_name=live_session,
                generation_id=f"manual-live-{token}",
                runtime_root=Path(env["HOUMAO_GLOBAL_RUNTIME_DIR"]),
            ),
            env,
        )
        _publish_record(
            _record(
                agent_name=dead_agent_name,
                session_name=dead_session,
                generation_id=f"manual-dead-{token}",
                runtime_root=Path(env["HOUMAO_GLOBAL_RUNTIME_DIR"]),
            ),
            env,
        )

        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        process = _start_passive_server(repo_root=repo_root, env=env, port=port)
        _wait_for_health(process=process, base_url=base_url)

        agents = _wait_for_agent(base_url=base_url, agent_id=live_agent_id)
        agent_ids = {str(agent.get("agent_id")) for agent in agents}
        assert live_agent_id in agent_ids, agents
        assert dead_agent_id not in agent_ids, agents
        assert len(agents) == 1, agents

        summary = agents[0]
        for key in (
            "agent_id",
            "agent_name",
            "generation_id",
            "tool",
            "backend",
            "tmux_session_name",
            "manifest_path",
            "session_root",
            "has_gateway",
            "has_mailbox",
            "published_at",
            "lease_expires_at",
        ):
            assert key in summary, summary
        assert summary["agent_id"] == live_agent_id, summary
        assert summary["agent_name"] == live_agent_name, summary
        assert summary["has_gateway"] is False, summary
        assert summary["has_mailbox"] is False, summary

        status, by_id = _request_json(
            method="GET",
            base_url=base_url,
            path=f"/houmao/agents/{live_agent_id}",
        )
        _assert_status(status, 200, by_id)
        assert by_id["agent_id"] == live_agent_id, by_id

        status, by_name = _request_json(
            method="GET",
            base_url=base_url,
            path=f"/houmao/agents/{live_agent_name}",
        )
        _assert_status(status, 200, by_name)
        assert by_name["agent_id"] == live_agent_id, by_name

        status, missing = _request_json(
            method="GET",
            base_url=base_url,
            path="/houmao/agents/HOUMAO-passive-missing",
        )
        _assert_status(status, 404, missing)
        assert "Agent not found" in str(missing.get("detail")), missing

        print("manual-passive-server-registry-discovery=PASS")
        print(f"base_url={base_url}")
        print(f"agent_id={live_agent_id}")
    finally:
        if process is not None:
            _terminate_process(process)
        _kill_tmux_session(live_session)
        try:
            shutil.rmtree(tmp_root, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
