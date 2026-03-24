from __future__ import annotations

import ast
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.cao.models import (
    CaoSessionDetail,
    CaoSessionInfo,
    CaoSessionTerminalSummary,
    CaoTerminal,
)
from houmao.cao.rest_client import CaoApiError
from houmao.server.models import (
    HoumaoHeadlessLaunchRequest,
    HoumaoInstallAgentProfileRequest,
    HoumaoManagedAgentIdentity,
    HoumaoRegisterLaunchRequest,
)
from houmao.srv_ctrl.commands.main import cli


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _extract_upstream_cli_commands() -> set[str]:
    tree = ast.parse(
        (
            _repo_root()
            / "extern"
            / "tracked"
            / "cli-agent-orchestrator"
            / "src"
            / "cli_agent_orchestrator"
            / "cli"
            / "main.py"
        ).read_text(encoding="utf-8")
    )
    command_names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Attribute):
            continue
        if not isinstance(call.func.value, ast.Name) or call.func.value.id != "cli":
            continue
        if call.func.attr != "add_command" or not call.args:
            continue
        argument = call.args[0]
        if isinstance(argument, ast.Name):
            command_names.add(argument.id.replace("_", "-"))
    return command_names


@dataclass(frozen=True)
class _FakeSession:
    id: str


class _FakeHoumaoClient:
    def __init__(self) -> None:
        self.m_list_sessions_payload: list[_FakeSession] = [_FakeSession(id="cao-gpu")]
        self.m_get_session_calls: list[str] = []
        self.m_create_session_calls: list[dict[str, object]] = []
        self.m_delete_session_calls: list[str] = []
        self.m_install_requests: list[HoumaoInstallAgentProfileRequest] = []
        self.m_register_requests: list[HoumaoRegisterLaunchRequest] = []
        self.m_headless_launch_requests: list[HoumaoHeadlessLaunchRequest] = []
        self.m_get_managed_agent_calls: list[str] = []
        self.m_attach_managed_agent_gateway_calls: list[str] = []

    def list_sessions(self) -> list[_FakeSession]:
        return list(self.m_list_sessions_payload)

    def create_session(
        self,
        *,
        provider: str,
        agent_profile: str,
        session_name: str | None = None,
        working_directory: str | None = None,
    ) -> CaoTerminal:
        self.m_create_session_calls.append(
            {
                "provider": provider,
                "agent_profile": agent_profile,
                "session_name": session_name,
                "working_directory": working_directory,
            }
        )
        resolved_session_name = session_name or "gpu"
        if not resolved_session_name.startswith("cao-"):
            resolved_session_name = f"cao-{resolved_session_name}"
        return CaoTerminal(
            id="abcd1234",
            name="gpu",
            provider=provider,
            session_name=resolved_session_name,
            agent_profile=agent_profile,
            status="idle",
        )

    def get_session(self, session_name: str) -> CaoSessionDetail:
        self.m_get_session_calls.append(session_name)
        return CaoSessionDetail(
            session=CaoSessionInfo(id=session_name, name=session_name, status="attached"),
            terminals=[
                CaoSessionTerminalSummary(
                    id="abcd1234",
                    tmux_session=session_name,
                    tmux_window="developer-1",
                    provider="codex",
                    agent_profile="gpu-kernel-coder",
                )
            ],
        )

    def delete_session(self, session_name: str) -> object:
        self.m_delete_session_calls.append(session_name)
        return type("DeleteResponse", (), {"success": True})()

    def install_agent_profile(self, request_model: HoumaoInstallAgentProfileRequest) -> object:
        self.m_install_requests.append(request_model)
        return type(
            "InstallResponse",
            (),
            {
                "success": True,
                "detail": (
                    "Pair-owned install completed through the Houmao-managed compatibility "
                    f"profile store for provider `{request_model.provider}` and agent source "
                    f"`{request_model.agent_source}`."
                ),
            },
        )()

    def register_launch(self, request_model: HoumaoRegisterLaunchRequest) -> None:
        self.m_register_requests.append(request_model)

    def launch_headless_agent(self, request_model: HoumaoHeadlessLaunchRequest) -> object:
        self.m_headless_launch_requests.append(request_model)
        return type(
            "HeadlessLaunchResponse",
            (),
            {
                "success": True,
                "tracked_agent_id": "claude-headless-1",
                "manifest_path": "/tmp/runtime/sessions/claude_headless/claude-headless-1/manifest.json",
            },
        )()

    def get_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentIdentity:
        self.m_get_managed_agent_calls.append(agent_ref)
        return HoumaoManagedAgentIdentity(
            tracked_agent_id="tracked-cao-gpu",
            transport="tui",
            tool="codex",
            session_name="cao-gpu",
            terminal_id="abcd1234",
            runtime_session_id=None,
            tmux_session_name="cao-gpu",
            tmux_window_name="developer-1",
            manifest_path="/tmp/runtime/sessions/houmao_server_rest/cao-gpu/manifest.json",
            session_root="/tmp/runtime/sessions/houmao_server_rest/cao-gpu",
            agent_name="AGENTSYS-gpu",
            agent_id="agent-1234",
        )

    def attach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        self.m_attach_managed_agent_gateway_calls.append(agent_ref)
        return GatewayStatusV1(
            attach_identity="houmao-server-rest-1",
            backend="houmao_server_rest",
            tmux_session_name="cao-gpu",
            gateway_health="healthy",
            managed_agent_connectivity="connected",
            managed_agent_recovery="idle",
            request_admission="open",
            terminal_surface_eligibility="ready",
            active_execution="idle",
            queue_depth=0,
            gateway_host="127.0.0.1",
            gateway_port=43123,
            managed_agent_instance_epoch=1,
        )


def test_top_level_command_inventory_reserves_pair_namespace() -> None:
    assert set(cli.commands.keys()) == {"agent-gateway", "cao", "install", "launch"}


def test_cao_group_inventory_matches_pinned_upstream() -> None:
    cao_group = cli.commands["cao"]
    assert isinstance(cao_group, click.Group)
    assert set(cao_group.commands.keys()) == _extract_upstream_cli_commands()


def test_cao_flow_list_uses_local_compatibility_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("AGENTSYS_GLOBAL_RUNTIME_DIR", str((tmp_path / "runtime").resolve()))

    result = CliRunner().invoke(cli, ["cao", "flow", "list", "--all"])

    assert result.exit_code == 0
    assert "No flows found" in result.output


def test_cao_init_initializes_local_compatibility_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    monkeypatch.setenv("AGENTSYS_GLOBAL_RUNTIME_DIR", str(runtime_root))

    result = CliRunner().invoke(cli, ["cao", "init"])

    assert result.exit_code == 0
    assert "CLI Agent Orchestrator initialized successfully" in result.output
    assert (runtime_root / "cao_compat" / "flows.json").is_file()
    assert json.loads((runtime_root / "cao_compat" / "flows.json").read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "flows": [],
    }


def test_cao_mcp_server_reports_pair_owned_guidance() -> None:
    result = CliRunner().invoke(cli, ["cao", "mcp-server"])

    assert result.exit_code != 0
    assert "The standalone CAO MCP helper is not part of the supported Houmao pair" in result.output
    assert "houmao-server" in result.output


def test_top_level_install_routes_through_houmao_server_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pair_checks: list[str] = []
    client = _FakeHoumaoClient()
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.install.require_supported_houmao_pair",
        lambda *, base_url: pair_checks.append(base_url) or client,
    )

    result = CliRunner().invoke(cli, ["install", "projection-demo", "--provider", "codex"])

    assert result.exit_code == 0
    assert pair_checks == ["http://127.0.0.1:9889"]
    assert client.m_install_requests == [
        HoumaoInstallAgentProfileRequest(
            agent_source="projection-demo",
            provider="codex",
            working_directory=str(tmp_path.resolve()),
        )
    ]
    assert "Houmao-managed compatibility profile store" in result.output


def test_cao_install_routes_through_houmao_server_pair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pair_checks: list[str] = []
    client = _FakeHoumaoClient()
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.install.require_supported_houmao_pair",
        lambda *, base_url: pair_checks.append(base_url) or client,
    )

    result = CliRunner().invoke(cli, ["cao", "install", "gpu-kernel-coder"])

    assert result.exit_code == 0
    assert pair_checks == ["http://127.0.0.1:9889"]
    assert client.m_install_requests == [
        HoumaoInstallAgentProfileRequest(
            agent_source="gpu-kernel-coder",
            provider="kiro_cli",
            working_directory=str(tmp_path.resolve()),
        )
    ]
    assert "Houmao-managed compatibility profile store" in result.output


def test_cao_info_reads_current_tmux_session_through_pair_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pair_checks: list[str] = []
    client = _FakeHoumaoClient()

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.cao.require_supported_houmao_pair",
        lambda *, base_url: pair_checks.append(base_url) or client,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.cao.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="cao-gpu\n",
            stderr="",
        ),
    )

    result = CliRunner().invoke(cli, ["cao", "info"])

    assert result.exit_code == 0
    assert pair_checks == ["http://127.0.0.1:9889"]
    assert client.m_get_session_calls == ["cao-gpu"]
    assert "Database path:" in result.output
    assert "Session ID: cao-gpu" in result.output
    assert "Active terminals: 1" in result.output


def test_cao_shutdown_all_uses_pair_client(monkeypatch: pytest.MonkeyPatch) -> None:
    pair_checks: list[str] = []
    client = _FakeHoumaoClient()
    client.m_list_sessions_payload = [_FakeSession(id="cao-a"), _FakeSession(id="cao-b")]

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.cao.require_supported_houmao_pair",
        lambda *, base_url: pair_checks.append(base_url) or client,
    )

    result = CliRunner().invoke(cli, ["cao", "shutdown", "--all"])

    assert result.exit_code == 0
    assert pair_checks == ["http://127.0.0.1:9889"]
    assert client.m_delete_session_calls == ["cao-a", "cao-b"]
    assert "✓ Shutdown session 'cao-a'" in result.output
    assert "✓ Shutdown session 'cao-b'" in result.output


def test_launch_registers_houmao_artifacts_and_attaches_tmux(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pair_checks: list[str] = []
    attach_calls: list[list[str]] = []
    materialized_launches: list[dict[str, object]] = []
    client = _FakeHoumaoClient()
    manifest_path = tmp_path / "manifest.json"
    session_root = tmp_path / "session-root"
    manifest_path.write_text("{}\n", encoding="utf-8")
    session_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.require_supported_houmao_pair",
        lambda *, base_url: pair_checks.append(base_url) or client,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.subprocess.run",
        lambda args, **kwargs: (
            attach_calls.append(list(args)) or subprocess.CompletedProcess(args=args, returncode=0)
        ),
    )

    def _fake_materialize_delegated_launch(**kwargs: object) -> tuple[Path, Path, str, str]:
        materialized_launches.append(kwargs)
        return manifest_path, session_root, "AGENTSYS-gpu", "agent-1234"

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.materialize_delegated_launch",
        _fake_materialize_delegated_launch,
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--provider",
            "codex",
            "--session-name",
            "gpu",
            "--yolo",
            "--port",
            "9999",
        ],
    )

    assert result.exit_code == 0
    assert result.output == ""
    assert pair_checks == ["http://127.0.0.1:9999"]
    assert client.m_create_session_calls == [
        {
            "provider": "codex",
            "agent_profile": "gpu-kernel-coder",
            "session_name": "gpu",
            "working_directory": str(tmp_path.resolve()),
        }
    ]
    assert client.m_get_session_calls == ["cao-gpu"]
    assert materialized_launches == [
        {
            "runtime_root": None,
            "api_base_url": "http://127.0.0.1:9999",
            "session_name": "cao-gpu",
            "terminal_id": "abcd1234",
            "tmux_window_name": "developer-1",
            "provider": "codex",
            "agent_profile": "gpu-kernel-coder",
            "working_directory": tmp_path.resolve(),
        }
    ]
    assert client.m_register_requests == [
        HoumaoRegisterLaunchRequest(
            session_name="cao-gpu",
            terminal_id="abcd1234",
            tool="codex",
            manifest_path=str(manifest_path),
            session_root=str(session_root),
            agent_name="AGENTSYS-gpu",
            agent_id="agent-1234",
            tmux_session_name="cao-gpu",
            tmux_window_name="developer-1",
        )
    ]
    assert attach_calls == [["tmux", "attach-session", "-t", "cao-gpu"]]


def test_cao_launch_emits_compat_messages_and_registers_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pair_checks: list[str] = []
    materialized_launches: list[dict[str, object]] = []
    client = _FakeHoumaoClient()
    manifest_path = tmp_path / "manifest.json"
    session_root = tmp_path / "session-root"
    manifest_path.write_text("{}\n", encoding="utf-8")
    session_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.require_supported_houmao_pair",
        lambda *, base_url: pair_checks.append(base_url) or client,
    )

    def _fake_materialize_delegated_launch(**kwargs: object) -> tuple[Path, Path, str, str]:
        materialized_launches.append(kwargs)
        return manifest_path, session_root, "AGENTSYS-gpu", "agent-1234"

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.materialize_delegated_launch",
        _fake_materialize_delegated_launch,
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "cao",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--provider",
            "codex",
            "--session-name",
            "gpu",
            "--headless",
            "--yolo",
            "--port",
            "9999",
        ],
    )

    assert result.exit_code == 0
    assert pair_checks == ["http://127.0.0.1:9999"]
    assert client.m_get_session_calls == ["cao-gpu"]
    assert materialized_launches == [
        {
            "runtime_root": None,
            "api_base_url": "http://127.0.0.1:9999",
            "session_name": "cao-gpu",
            "terminal_id": "abcd1234",
            "tmux_window_name": "developer-1",
            "provider": "codex",
            "agent_profile": "gpu-kernel-coder",
            "working_directory": tmp_path.resolve(),
        }
    ]
    assert "Session created: cao-gpu" in result.output
    assert "Terminal created: gpu" in result.output


def test_headless_launch_targets_native_houmao_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pair_checks: list[str] = []
    client = _FakeHoumaoClient()
    request_model = HoumaoHeadlessLaunchRequest(
        tool="claude",
        working_directory=str(tmp_path.resolve()),
        agent_def_dir=str((tmp_path / "agents").resolve()),
        brain_manifest_path=str((tmp_path / "brain.yaml").resolve()),
        role_name="gpu-kernel-coder",
        agent_name="AGENTSYS-gpu",
        agent_id=None,
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.require_supported_houmao_pair",
        lambda *, base_url: pair_checks.append(base_url) or client,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.materialize_headless_launch_request",
        lambda **kwargs: request_model,
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--provider",
            "claude_code",
            "--headless",
            "--yolo",
            "--port",
            "9999",
        ],
    )

    assert result.exit_code == 0
    assert pair_checks == ["http://127.0.0.1:9999"]
    assert client.m_headless_launch_requests == [request_model]
    assert "Houmao native headless launch complete: agent=claude-headless-1" in result.output


def test_launch_rejects_unsupported_pair_before_session_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_pair_error(*, base_url: str) -> object:
        del base_url
        raise click.ClickException("unsupported pair")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.require_supported_houmao_pair",
        _raise_pair_error,
    )

    result = CliRunner().invoke(
        cli,
        ["launch", "--agents", "gpu-kernel-coder", "--yolo"],
    )

    assert result.exit_code != 0
    assert "unsupported pair" in result.output


def test_agent_gateway_attach_explicit_resolves_alias_before_attach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pair_checks: list[str] = []
    client = _FakeHoumaoClient()

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agent_gateway.require_supported_houmao_pair",
        lambda *, base_url: pair_checks.append(base_url) or client,
    )

    result = CliRunner().invoke(
        cli,
        ["agent-gateway", "attach", "--agent", "AGENTSYS gpu/1", "--port", "9999"],
    )

    assert result.exit_code == 0
    assert pair_checks == ["http://127.0.0.1:9999"]
    assert client.m_get_managed_agent_calls == ["AGENTSYS gpu/1"]
    assert client.m_attach_managed_agent_gateway_calls == ["tracked-cao-gpu"]
    assert json.loads(result.output)["gateway_port"] == 43123


def test_agent_gateway_attach_current_session_uses_persisted_server_and_session_alias(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = _FakeHoumaoClient()
    session_root = tmp_path / "runtime" / "sessions" / "houmao_server_rest" / "cao-gpu"
    gateway_root = session_root / "gateway"
    attach_path = gateway_root / "attach.json"
    gateway_root.mkdir(parents=True, exist_ok=True)
    attach_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "attach_identity": "houmao-server-rest-1",
                "backend": "houmao_server_rest",
                "tmux_session_name": "cao-gpu",
                "working_directory": str(tmp_path.resolve()),
                "backend_metadata": {
                    "api_base_url": "http://127.0.0.1:9988",
                    "session_name": "cao-gpu",
                    "terminal_id": "abcd1234",
                    "parsing_mode": "shadow_only",
                    "tmux_window_name": "developer-1",
                },
                "manifest_path": str((session_root / "manifest.json").resolve()),
                "agent_def_dir": str((session_root / "agent_def").resolve()),
                "runtime_session_id": "houmao-server-rest-1",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (session_root / "manifest.json").write_text("{}\n", encoding="utf-8")
    (session_root / "agent_def").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agent_gateway.require_supported_houmao_pair",
        lambda *, base_url: client if base_url == "http://127.0.0.1:9988" else None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agent_gateway.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="cao-gpu\n",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agent_gateway.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: {
            ("cao-gpu", "AGENTSYS_GATEWAY_ATTACH_PATH"): str(attach_path.resolve()),
            ("cao-gpu", "AGENTSYS_GATEWAY_ROOT"): str(gateway_root.resolve()),
        }.get((session_name, variable_name)),
    )

    result = CliRunner().invoke(cli, ["agent-gateway", "attach"])

    assert result.exit_code == 0
    assert client.m_get_managed_agent_calls == ["cao-gpu"]
    assert client.m_attach_managed_agent_gateway_calls == ["cao-gpu"]
    assert json.loads(result.output)["gateway_host"] == "127.0.0.1"


def test_agent_gateway_attach_current_session_fails_before_registration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = _FakeHoumaoClient()
    session_root = tmp_path / "runtime" / "sessions" / "houmao_server_rest" / "cao-gpu"
    gateway_root = session_root / "gateway"
    attach_path = gateway_root / "attach.json"
    gateway_root.mkdir(parents=True, exist_ok=True)
    (session_root / "manifest.json").write_text("{}\n", encoding="utf-8")
    (session_root / "agent_def").mkdir(parents=True, exist_ok=True)
    attach_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "attach_identity": "houmao-server-rest-1",
                "backend": "houmao_server_rest",
                "tmux_session_name": "cao-gpu",
                "working_directory": str(tmp_path.resolve()),
                "backend_metadata": {
                    "api_base_url": "http://127.0.0.1:9988",
                    "session_name": "cao-gpu",
                    "terminal_id": "abcd1234",
                    "parsing_mode": "shadow_only",
                },
                "manifest_path": str((session_root / "manifest.json").resolve()),
                "agent_def_dir": str((session_root / "agent_def").resolve()),
                "runtime_session_id": "houmao-server-rest-1",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    def _raise_not_found(agent_ref: str) -> object:
        del agent_ref
        raise CaoApiError(
            method="GET",
            url="http://127.0.0.1:9988/houmao/agents/cao-gpu",
            status_code=404,
            detail="Unknown managed agent `cao-gpu`.",
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agent_gateway.require_supported_houmao_pair",
        lambda *, base_url: client if base_url == "http://127.0.0.1:9988" else None,
    )
    monkeypatch.setattr(client, "get_managed_agent", _raise_not_found)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agent_gateway.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="cao-gpu\n",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agent_gateway.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: {
            ("cao-gpu", "AGENTSYS_GATEWAY_ATTACH_PATH"): str(attach_path.resolve()),
            ("cao-gpu", "AGENTSYS_GATEWAY_ROOT"): str(gateway_root.resolve()),
        }.get((session_name, variable_name)),
    )

    result = CliRunner().invoke(cli, ["agent-gateway", "attach"])

    assert result.exit_code != 0
    assert "Unknown managed agent `cao-gpu`." in result.output
