"""Controlled owned native Web Hosts with private credentials and scoped cleanup."""

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Any
from uuid import uuid4

import pytest

from houmao.agents.dsh_configuration import DshEffectiveToolParams, prepare_dsh_home
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient


def read_native_workspaces(client: DshWebClient) -> dict[str, dict[str, Any]]:
    """Read one native Workspace baseline from the owned API stream."""

    socket = client.m_socket
    assert socket is not None
    stream_id = str(uuid4())
    socket.send(
        json.dumps(
            {
                "type": "open",
                "streamId": stream_id,
                "endpoint": "workspace/follow",
                "payload": {"args": {}},
            }
        )
    )
    try:
        frame = json.loads(socket.recv(timeout=10))
        assert frame["streamId"] == stream_id and frame["type"] == "item"
        baseline = frame["value"]
        assert baseline["type"] == "baseline"
        rows = baseline["value"]["items"]
        by_path = {row["path"]: row for row in rows}
        assert len(by_path) == len(rows)
        return by_path
    finally:
        socket.send(json.dumps({"type": "cancel", "streamId": stream_id}))


def call_native_request(client: DshWebClient, method: str, args: dict[str, Any]) -> dict[str, Any]:
    """Use DSH's normal API to seed or read fixture-owned native records."""

    http = client.m_http
    assert http is not None
    rpc_id = str(uuid4())
    response = http.post(
        f"/api/{method}",
        json={
            "type": "client-request",
            "rpcId": rpc_id,
            "method": method,
            "payload": {"args": args},
        },
    )
    assert response.status_code == 200
    envelope = response.json()
    assert envelope["rpcId"] == rpc_id and envelope["result"]["ok"], envelope["result"]
    return envelope["result"]["value"]


def read_native_history(client: DshWebClient, session_id: str) -> str:
    """Read persisted conversation events without selecting or activating that session."""

    return json.dumps(
        call_native_request(
            client,
            "session/events",
            {"request": {"address": {"kind": "session", "sessionId": session_id}}},
        )
    )


def read_native_session_ids(client: DshWebClient) -> set[str]:
    """Count native conversations independently of Workspace membership."""

    items = call_native_request(client, "session/list", {"_request": {}})["items"]
    ids = {item["sessionId"] for item in items}
    assert len(ids) == len(items)
    return ids


@dataclass
class NativeWebGates:
    """Configure test-only native barriers without product control hooks."""

    directory: Path

    @property
    def plugin(self) -> dict[str, Any]:
        """Return the isolated native test-plugin contribution."""

        return {
            "id": "qualification-gates",
            "name": str(Path(__file__).with_name("native-gates.mjs")),
            "config": {"directory": str(self.directory)},
        }

    def hold(self, boundary: str, text: str = "") -> None:
        """Arm a named controlled barrier before dispatch."""

        (self.directory / f"{boundary}.entered").unlink(missing_ok=True)
        (self.directory / f"{boundary}.release").unlink(missing_ok=True)
        (self.directory / f"{boundary}.count").unlink(missing_ok=True)
        (self.directory / f"{boundary}.request").write_text(text)

    def wait(self, boundary: str) -> None:
        """Wait for proof that the native boundary was entered."""

        deadline = time.monotonic() + 10
        while not (self.directory / f"{boundary}.entered").exists():
            if time.monotonic() >= deadline:
                raise AssertionError(f"Native {boundary} gate was not entered")
            time.sleep(0.01)

    def release(self, boundary: str) -> None:
        """Release only the selected fixture barrier."""

        (self.directory / f"{boundary}.release").touch()


@pytest.fixture
def native_web_gates(tmp_path: Path) -> Iterator[NativeWebGates]:
    """Release every native test barrier during teardown even after assertion failure."""

    directory = tmp_path / "native-gates"
    directory.mkdir()
    gates = NativeWebGates(directory)
    try:
        yield gates
    finally:
        for boundary in ["prepare", "step", "maintenance", "settlement"]:
            gates.release(boundary)


@dataclass
class NativeWebHost:
    """Hold private fixture authority independently of public browser locations."""

    root: Path
    process: subprocess.Popen[bytes] = field(repr=False)
    birth_token: str | None = field(repr=False)
    client: DshWebClient = field(repr=False)
    identity: dict[str, Any]
    bootstrap_path: Path

    @property
    def origin(self) -> str:
        """Return the verified token-free native listener origin."""

        return str(json.loads(self.bootstrap_path.read_text())["origin"])

    @property
    def launch_token(self) -> str:
        """Read the private token only when another deliberately separate client signs in."""

        return str(json.loads(self.bootstrap_path.read_text())["launch_token"])

    def browser_connection_file(self) -> Path:
        """Create a private browser-only handoff for the exact selected native session."""

        path = self.root / "browser-connection.json"
        path.write_text(
            json.dumps(
                {
                    "origin": self.origin,
                    "launch_token": self.launch_token,
                    "native_session_id": self.identity["native_session_id"],
                }
            )
        )
        path.chmod(0o600)
        return path

    def kill(self) -> None:
        """Kill only this captured process group while its birth identity still matches."""

        if self.process.poll() is None:
            assert self.birth_token is not None
            assert _dispatch_origin_birth_token(self.process.pid) == self.birth_token
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=10)
        self.client.close()

    def close(self) -> None:
        """Release API credentials and reap only the fixture's captured native process."""

        self.client.close()
        if self.process.poll() is None:
            assert self.birth_token is not None
            assert _dispatch_origin_birth_token(self.process.pid) == self.birth_token
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.kill()


@pytest.fixture
def native_web_factory(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> Iterator[Callable[..., NativeWebHost]]:
    """Launch only explicitly selected native builds against a local synthetic provider."""

    hosts: list[NativeWebHost] = []
    default_endpoint, _requests = controlled_messages_server

    def launch(
        *,
        root: Path | None = None,
        extra_plugins: list[dict[str, Any]] | None = None,
        start: bool = True,
        mode: str = "new",
        session_id: str | None = None,
        abandoned_operation_ids: Sequence[str] = (),
        endpoint: str | None = None,
        operator_prompt_mode: str = "unattended",
        permissions: dict[str, str] | None = None,
        models: list[dict[str, Any]] | None = None,
        generation: str = "web-generation",
        skill_projection: Path | None = None,
        mcp_projection: Path | None = None,
        mcp_connectors: dict[str, dict[str, Any]] | None = None,
    ) -> NativeWebHost:
        """Create isolated private state or explicitly reuse a captured fixture home."""

        selected_root = root or tmp_path / f"host-{len(hosts)}"
        selected_root.mkdir(exist_ok=True, mode=0o700)
        (selected_root / "user-home").mkdir(exist_ok=True)
        setup = DshEffectiveToolParams.from_mapping(
            {
                "permissions": permissions or {},
                "provider": {
                    "adapter": "deepseek",
                    "protocol": "messages",
                    "route": "deepseek-official",
                    "base_url_env": "DSH_SYNTHETIC_ENDPOINT",
                    "api_key_env": "DSH_SYNTHETIC_KEY",
                },
                "models": models
                or [
                    {
                        "id": "controlled",
                        "context_window": 8192,
                        "max_output_tokens": 128,
                        "reasoning_efforts": False,
                    }
                ],
            }
        )
        prepared = prepare_dsh_home(
            selected_root / "dsh-home",
            setup,
            {
                "PATH": os.environ["PATH"],
                "HOME": str(selected_root / "user-home"),
                "DSH_SYNTHETIC_ENDPOINT": endpoint or default_endpoint,
                "DSH_SYNTHETIC_KEY": "synthetic-controlled-only",
            },
            "Literal Web role {{kept}} $HOME",
            selected_model="controlled",
            operator_prompt_mode=operator_prompt_mode,
        )
        bootstrap = selected_root / "bootstrap.json"
        bootstrap.unlink(missing_ok=True)
        control_path = selected_root / "control.json"
        control_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "mode": "web",
                    "agent_id": "web-agent",
                    "runtime_session_id": "web-runtime",
                    "generation": generation,
                    "working_directory": str(selected_root),
                    "expected_native_session_id": session_id,
                    "state_path": str(selected_root / "receipt-state.json"),
                    "evidence_path": str(selected_root / "evidence.jsonl"),
                    "bootstrap_path": str(bootstrap),
                    "roleFile": str(prepared.role_path),
                    "provider": "deepseek-official",
                    "model": "controlled",
                    "permission_preset": prepared.metadata["permission_preset"],
                    "native_version": subprocess.check_output(
                        [str(dsh_executable), "--version"], text=True
                    ).strip(),
                    **(
                        {
                            "skill_mount": {
                                "mount_id": (skill_projection / "mount-id").read_text().strip(),
                                "projection_root": str(skill_projection),
                            }
                        }
                        if skill_projection is not None
                        else {}
                    ),
                    **(
                        {
                            "mcp_mount": {
                                "mount_id": (mcp_projection / "mount-id").read_text().strip(),
                                "projection_root": str(mcp_projection),
                                "connectors": mcp_connectors or {},
                            }
                        }
                        if mcp_projection is not None
                        else {}
                    ),
                }
            )
        )
        control_path.chmod(0o600)
        asset = Path(__file__).resolve().parents[5] / "src/houmao/agents/assets/dsh/managed-web.mjs"
        patch = [
            entry
            for entry in json.loads(prepared.patch_path.read_text())
            if entry.get("id") != "acp"
        ]
        patch.extend(
            [
                {
                    "id": "agent-default-model",
                    "config": {"provider": "deepseek-official", "model": "controlled"},
                },
                {"id": "session-title-llm", "disabled": True},
                {
                    "insert": [
                        {
                            "id": "houmao-managed-web",
                            "name": str(asset),
                            "config": {"controlFile": str(control_path)},
                        }
                    ]
                },
            ]
        )
        if extra_plugins:
            patch.append({"insert": extra_plugins})
        patch_path = selected_root / "web.patch.json"
        patch_path.write_text(json.dumps(patch))
        patch_path.chmod(0o600)
        log_path = selected_root / f"native-{len(hosts)}.log"
        log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(log_fd, "wb") as output:
            process = subprocess.Popen(
                [
                    str(dsh_executable),
                    "--profile",
                    "web",
                    "--patch",
                    str(patch_path),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "0",
                    "--no-open",
                ],
                cwd=selected_root,
                env=prepared.environment,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        birth = _dispatch_origin_birth_token(process.pid)
        deadline = time.monotonic() + 45
        try:
            while not bootstrap.exists():
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise AssertionError(f"Native Web startup failed; private log: {log_path}")
                time.sleep(0.05)
            boot = json.loads(bootstrap.read_text())
            client = DshWebClient.from_connection(
                boot["origin"],
                launch_token=boot["launch_token"],
                cookie_file=selected_root / "api-credential.json",
            )
            host = NativeWebHost(selected_root, process, birth, client, {}, bootstrap)
            hosts.append(host)
            if start:
                host.identity = client.lifecycle_start(
                    mode=mode,
                    session_id=session_id,
                    abandoned_operation_ids=abandoned_operation_ids,
                )
            return host
        except BaseException:
            if (
                process.poll() is None
                and birth is not None
                and _dispatch_origin_birth_token(process.pid) == birth
            ):
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
            raise

    try:
        yield launch
    finally:
        for host in reversed(hosts):
            host.close()


@pytest.fixture
def native_web_host(native_web_factory: Callable[..., NativeWebHost]) -> NativeWebHost:
    """Return one explicitly created native conversation on an isolated Web Host."""

    return native_web_factory()
