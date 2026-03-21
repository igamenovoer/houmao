from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from houmao.cao.models import CaoSessionDetail, CaoSessionInfo, CaoSessionTerminalSummary, CaoTerminal
from houmao.server.models import (
    HoumaoHeadlessLaunchRequest,
    HoumaoInstallAgentProfileRequest,
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
                    "Pair-owned install completed through managed child CAO state for "
                    f"provider `{request_model.provider}` and agent source "
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


def test_top_level_command_inventory_reserves_pair_namespace() -> None:
    assert set(cli.commands.keys()) == {"cao", "install", "launch"}


def test_cao_group_inventory_matches_pinned_upstream() -> None:
    cao_group = cli.commands["cao"]
    assert isinstance(cao_group, click.Group)
    assert set(cao_group.commands.keys()) == _extract_upstream_cli_commands()


@pytest.mark.parametrize(
    ("argv", "expected_command_name", "expected_extra_args"),
    [
        (["cao", "flow", "list", "--all"], "flow", ["list", "--all"]),
        (["cao", "init"], "init", []),
        (["cao", "mcp-server"], "mcp-server", []),
    ],
)
def test_cao_passthrough_commands_forward_arguments(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    expected_command_name: str,
    expected_extra_args: list[str],
) -> None:
    forwarded: list[tuple[str, list[str]]] = []

    def _fake_run_passthrough(
        *, command_name: str, extra_args: list[str]
    ) -> subprocess.CompletedProcess[bytes]:
        forwarded.append((command_name, list(extra_args)))
        return subprocess.CompletedProcess(args=[], returncode=0)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.passthrough.run_passthrough", _fake_run_passthrough
    )

    result = CliRunner().invoke(cli, argv)

    assert result.exit_code == 0
    assert forwarded == [(expected_command_name, expected_extra_args)]


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
    assert "Pair-owned install completed through managed child CAO state" in result.output


def test_cao_install_remains_local_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    forwarded: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.passthrough.run_passthrough",
        lambda *, command_name, extra_args: (
            forwarded.append((command_name, list(extra_args)))
            or subprocess.CompletedProcess(args=[], returncode=0)
        ),
    )

    result = CliRunner().invoke(cli, ["cao", "install", "gpu-kernel-coder"])

    assert result.exit_code == 0
    assert forwarded == [("install", ["gpu-kernel-coder"])]


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
