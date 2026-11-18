"""Qualify public gateway refresh projection through an actual managed DSH host."""

import json
from collections.abc import Iterator
from contextlib import contextmanager, ExitStack
from pathlib import Path
import shutil
import socket
import threading
import time
from typing import Any

from click.testing import CliRunner
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import uvicorn

from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_service import create_app
from houmao.agents.realm_controller.native_refresh_models import NativeRefreshRequestV1
from houmao.agents.realm_controller.registry_models import RegistryGatewayV1
from houmao.agents.realm_controller.registry_storage import load_managed_agent_record_by_agent_id
from houmao.passive_server.app import create_app as create_passive_app
from houmao.passive_server.client import PassiveServerClient
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, _summary_from_record
from houmao.passive_server.service import PassiveServerService
from houmao.srv_ctrl.commands.main import cli
from tests.integration.agents.dsh.web.test_gateway_native import _runtime, _stop
from tests.integration.agents.dsh.web.test_refresh import MCP_SERVER, _skill


@contextmanager
def _serve(app: FastAPI) -> Iterator[tuple[str, int]]:
    """Serve one test-owned ASGI app on an already-reserved loopback socket."""

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    try:
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        yield f"http://127.0.0.1:{port}", port
    finally:
        server.should_exit = True
        thread.join(5)
        listener.close()
        assert not thread.is_alive()


def test_public_gateway_native_refresh_preserves_real_common_evidence(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Map actual pending/apply/current/no-op and MCP evidence through public HTTP."""

    assert isolated_tmux.is_absolute()
    endpoint, requests = controlled_messages_server
    runtime, backend = _runtime(tmp_path, dsh_executable, endpoint, monkeypatch, isolated_tmux)
    identity = dict(backend.state.web_identity)
    runtime.start()
    try:
        client = TestClient(create_app(runtime=runtime))
        home = client.get("/v1/native-home")
        assert home.status_code == 200, home.text
        assert Path(home.json()["home_dir"]) == tmp_path / "dsh-home"
        assert home.json()["home_env_var"] == "DSH_HOME"
        root = tmp_path / "external-skills"
        root.mkdir()
        _skill(root, "alpha", "public native refresh")
        rows = [
            {
                "insert": [
                    {
                        "id": "public-skills",
                        "name": str(
                            dsh_executable.parents[2] / "dsh-skill-filesystem/lib/index.js"
                        ),
                        "config": {
                            "providerName": "public-refresh",
                            "includeDefaultRoots": False,
                            "customSkillDirs": [str(root)],
                            "watch": False,
                        },
                    }
                ]
            }
        ]
        patch = tmp_path / "dsh-home/cordis.patch.yml"
        patch.write_text(json.dumps(rows))
        before = patch.read_bytes()
        pending = client.get("/v1/control/refresh")
        assert pending.status_code == 200, pending.text
        assert pending.json()["freshness"] == "pending", pending.text
        assert patch.read_bytes() == before
        applied = client.post("/v1/control/refresh", json={"timeout_seconds": 5.0})
        assert applied.status_code == 200, applied.text
        result = applied.json()
        assert result["outcome"] == "refreshed", result
        assert result["method"] == "native_reload"
        assert result["observation"]["freshness"] == "current"
        assert any(
            "alpha" in resource["inventory"]
            for resource in result["observation"]["resources"]
            if resource["kind"] == "skills"
        )
        no_op = client.post("/v1/control/refresh", json={})
        assert no_op.status_code == 200, no_op.text
        assert no_op.json()["outcome"] == "already_current"
        assert no_op.json()["method"] == "noop"
        server = tmp_path / "controlled-server.cjs"
        server.write_text(MCP_SERVER)
        node = shutil.which("node")
        assert node
        rows.append(
            {
                "id": "mcp-manager",
                "config": {
                    "servers": {
                        "probe": {
                            "transport": "stdio",
                            "command": node,
                            "args": [str(server), "public"],
                            "startupTimeoutMs": 2000,
                            "reconnect": {"enabled": False},
                        }
                    }
                },
            }
        )
        patch.write_text(json.dumps(rows))
        mcp = client.post("/v1/control/refresh", json={"timeout_seconds": 5.0})
        assert mcp.status_code == 200, mcp.text
        resources = mcp.json()["observation"]["resources"]
        tools = next(
            row for row in resources if row["kind"] == "mcp" and row["component"] == "tools"
        )
        assert tools["freshness"] == "current" and tools["inventory"] == ["probe"]
        assert tools["evidence"] == ["native_connection_generation_and_tools_confirmed"]
        implementation = next(row for row in resources if row["component"] == "implementation")
        assert implementation["freshness"] == "unknown" and not implementation["required"]
        assert backend.observe_web_state()["identity"] == identity
        assert requests == []
        assert patch.read_bytes() == json.dumps(rows).encode()
        # A still-running supervisor is not active native Agent authority.
        assert backend._client().stop(identity)["stopped"]
        stopped_home = client.get("/v1/native-home")
        assert stopped_home.status_code == 503, stopped_home.text
    finally:
        _stop(runtime, backend)


def test_two_native_agents_share_cli_gateway_and_passive_refresh_contract(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise real HTTP and scoped CLI across distinct native homes and identities."""

    assert isolated_tmux.is_absolute()
    endpoint, requests = controlled_messages_server
    executions = []
    records = []
    identities = []
    for number in (1, 2):
        root = tmp_path / f"agent-{number}"
        root.mkdir()
        runtime, backend = _runtime(
            root,
            dsh_executable,
            endpoint,
            monkeypatch,
            isolated_tmux,
            agent_id=f"owner{number}",
            session_name=f"HOUMAO-refresh-{number}",
        )
        # Cache each exact controller before the fixture installs another
        # reconstruction callback for the next independently launched host.
        runtime.m_adapter._resume_controller()
        runtime.start()
        record = load_managed_agent_record_by_agent_id(f"owner{number}")
        assert record is not None
        executions.append((runtime, backend, root))
        records.append(record)
        identities.append(dict(backend.state.web_identity))
    service = PassiveServerService(
        PassiveServerConfig(runtime_root=tmp_path / "passive", registry_root=tmp_path / "registry")
    )
    try:
        with ExitStack() as stack:
            for (runtime, _backend, _root), record in zip(executions, records, strict=True):
                _base, port = stack.enter_context(_serve(create_app(runtime=runtime)))
                record.gateway = RegistryGatewayV1(
                    host="127.0.0.1",
                    port=port,
                    state_path=str(runtime.m_paths.state_path),
                    protocol_version="v1",
                )
            agents = [
                DiscoveredAgent(record=record, summary=_summary_from_record(record))
                for record in records
            ]
            service.m_discovery.m_index.replace({agent.record.agent_id: agent for agent in agents})
            base, port = stack.enter_context(_serve(create_passive_app(service=service)))
            passive = PassiveServerClient(base_url=base)
            runner = CliRunner()

            def command(agent: str, *arguments: str):
                """Invoke the real scoped CLI and its actual passive HTTP client."""

                return runner.invoke(
                    cli,
                    [
                        "--print-json",
                        "agents",
                        "single",
                        "--agent-id",
                        agent,
                        *arguments,
                        "--port",
                        str(port),
                    ],
                )

            rows_by_agent = []
            for number, (_runtime_value, _backend, root) in enumerate(executions, 1):
                skills = root / "external-skills"
                skills.mkdir()
                _skill(skills, f"only-{number}", "initial")
                rows = [
                    {
                        "insert": [
                            {
                                "id": "cross-surface-skills",
                                "name": str(
                                    dsh_executable.parents[2] / "dsh-skill-filesystem/lib/index.js"
                                ),
                                "config": {
                                    "providerName": f"external-{number}",
                                    "includeDefaultRoots": False,
                                    "customSkillDirs": [str(skills)],
                                    "watch": number == 1,
                                    "watchUsePolling": True,
                                    "watchStabilityThresholdMs": 20,
                                    "watchPollIntervalMs": 10,
                                },
                            }
                        ]
                    }
                ]
                (root / "dsh-home/cordis.patch.yml").write_text(json.dumps(rows))
                rows_by_agent.append(rows)
                home = command(f"owner{number}", "home")
                assert home.exit_code == 0, home.output
                assert Path(json.loads(home.output)["home_dir"]) == root / "dsh-home"
                pending = command(f"owner{number}", "refresh", "--check")
                assert pending.exit_code == 1, pending.output
                assert json.loads(pending.output)["freshness"] == "pending"
            applied = command("owner1", "refresh", "--timeout-seconds", "5")
            assert applied.exit_code == 0, applied.output
            assert json.loads(applied.output)["outcome"] == "refreshed"
            assert (
                passive.get_managed_agent_gateway_common_plugin_state("owner2").freshness
                == "pending"
            )
            second = passive.refresh_managed_agent_gateway_native(
                "owner2", NativeRefreshRequestV1(timeout_seconds=5.0)
            )
            assert second.outcome == "refreshed"
            time.sleep(0.2)
            _skill(executions[0][2] / "external-skills", "automatic", "outside Houmao")
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                observed = passive.get_managed_agent_gateway_common_plugin_state("owner1")
                if observed.freshness == "current" and any(
                    "automatic" in row.inventory for row in observed.resources
                ):
                    break
                time.sleep(0.03)
            assert observed.freshness == "current"
            redundant = command("owner1", "refresh")
            assert redundant.exit_code == 0, redundant.output
            assert json.loads(redundant.output)["outcome"] == "already_current"
            second_root = executions[1][2]
            failing = second_root / "failing.mjs"
            failing.write_text(
                "export function apply(){throw new Error('synthetic native failure')}\n"
            )
            rows_by_agent[1][0]["insert"][0]["config"]["providerName"] = "replacement"
            rows_by_agent[1].append(
                {"insert": [{"id": "native-special-failing", "name": str(failing)}]}
            )
            (second_root / "dsh-home/cordis.patch.yml").write_text(json.dumps(rows_by_agent[1]))
            partial = passive.refresh_managed_agent_gateway_native(
                "owner2", NativeRefreshRequestV1(timeout_seconds=5.0)
            )
            assert partial.outcome == "refreshed" and partial.effects == "partial"
            assert "native_activation_failed" in partial.diagnostics
            for number, ((runtime, backend, _root), record) in enumerate(
                zip(executions, records, strict=True), 1
            ):
                assert backend.observe_web_state()["identity"] == identities[number - 1]
                gateway = GatewayClient(
                    endpoint=GatewayEndpoint(host="127.0.0.1", port=record.gateway.port)
                )
                current = gateway.get_common_plugin_state()
                assert current.freshness == "current"
                assert any(f"only-{number}" in row.inventory for row in current.resources)
                assert not any(f"only-{3 - number}" in row.inventory for row in current.resources)
            assert requests == []
    finally:
        service.shutdown()
        for runtime, backend, _root in reversed(executions):
            _stop(runtime, backend)
