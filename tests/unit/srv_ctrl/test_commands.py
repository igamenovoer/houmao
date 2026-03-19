from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from houmao.server.models import HoumaoRegisterLaunchRequest
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
        self.m_list_calls = 0
        self.m_get_session_calls: list[str] = []
        self.m_register_requests: list[HoumaoRegisterLaunchRequest] = []

    def list_sessions(self) -> list[_FakeSession]:
        self.m_list_calls += 1
        if self.m_list_calls == 1:
            return []
        return [_FakeSession(id="cao-gpu")]

    def get_session(self, session_name: str) -> dict[str, object]:
        self.m_get_session_calls.append(session_name)
        return {"terminals": [{"id": "abcd1234"}]}

    def register_launch(self, request_model: HoumaoRegisterLaunchRequest) -> None:
        self.m_register_requests.append(request_model)


def test_command_inventory_matches_pinned_upstream() -> None:
    assert set(cli.commands.keys()) == _extract_upstream_cli_commands()


@pytest.mark.parametrize(
    ("argv", "expected_command_name", "expected_extra_args"),
    [
        (["flow", "list", "--all"], "flow", ["list", "--all"]),
        (["init"], "init", []),
        (["install", "gpu-kernel-coder"], "install", ["gpu-kernel-coder"]),
        (["mcp-server"], "mcp-server", []),
    ],
)
def test_passthrough_commands_forward_arguments(
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

    monkeypatch.setattr("houmao.srv_ctrl.commands.passthrough.run_passthrough", _fake_run_passthrough)

    result = CliRunner().invoke(cli, argv)

    assert result.exit_code == 0
    assert forwarded == [(expected_command_name, expected_extra_args)]


@pytest.mark.parametrize(
    ("argv", "expected_base_url"),
    [
        (["info"], "http://127.0.0.1:9889"),
        (["shutdown", "--all"], "http://127.0.0.1:9889"),
    ],
)
def test_pair_required_commands_check_supported_houmao_pair_before_forwarding(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    expected_base_url: str,
) -> None:
    pair_checks: list[str] = []
    forwarded: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.passthrough.require_supported_houmao_pair",
        lambda *, base_url: pair_checks.append(base_url) or object(),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.passthrough.run_passthrough",
        lambda *, command_name, extra_args: forwarded.append((command_name, list(extra_args)))
        or subprocess.CompletedProcess(args=[], returncode=0),
    )

    result = CliRunner().invoke(cli, argv)

    assert result.exit_code == 0
    assert pair_checks == [expected_base_url]
    assert forwarded == [(argv[0], argv[1:])]


def test_pair_required_command_stops_when_pair_check_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded: list[tuple[str, list[str]]] = []

    def _raise_pair_error(*, base_url: str) -> object:
        del base_url
        raise click.ClickException("unsupported pair")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.passthrough.require_supported_houmao_pair",
        _raise_pair_error,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.passthrough.run_passthrough",
        lambda *, command_name, extra_args: forwarded.append((command_name, list(extra_args)))
        or subprocess.CompletedProcess(args=[], returncode=0),
    )

    result = CliRunner().invoke(cli, ["info"])

    assert result.exit_code != 0
    assert "unsupported pair" in result.output
    assert forwarded == []


def test_launch_forwards_args_and_registers_houmao_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pair_checks: list[str] = []
    delegated_args: list[list[str]] = []
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
        "houmao.srv_ctrl.commands.launch.run_passthrough",
        lambda *, command_name, extra_args: delegated_args.append([command_name, *list(extra_args)])
        or subprocess.CompletedProcess(args=[], returncode=0),
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
            "--headless",
            "--yolo",
            "--port",
            "9999",
        ],
    )

    assert result.exit_code == 0
    assert pair_checks == ["http://127.0.0.1:9999"]
    assert delegated_args == [
        [
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
        ]
    ]
    assert materialized_launches == [
        {
            "runtime_root": None,
            "api_base_url": "http://127.0.0.1:9999",
            "session_name": "cao-gpu",
            "terminal_id": "abcd1234",
            "provider": "codex",
            "agent_profile": "gpu-kernel-coder",
            "working_directory": tmp_path.resolve(),
        }
    ]
    assert client.m_get_session_calls == ["cao-gpu"]
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
        )
    ]
    assert "Houmao launch registration complete: session=cao-gpu terminal=abcd1234" in result.output


def test_launch_returns_delegated_exit_code_without_houmao_follow_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeHoumaoClient()
    materialized_launches: list[dict[str, object]] = []

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.require_supported_houmao_pair",
        lambda *, base_url: client,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.run_passthrough",
        lambda *, command_name, extra_args: subprocess.CompletedProcess(args=[], returncode=7),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.materialize_delegated_launch",
        lambda **kwargs: materialized_launches.append(kwargs)
        or (Path("/tmp/manifest.json"), Path("/tmp/session-root"), "AGENTSYS-gpu", "agent-1234"),
    )

    result = CliRunner().invoke(cli, ["launch", "--agents", "gpu-kernel-coder", "--headless"])

    assert result.exit_code == 7
    assert client.m_list_calls == 1
    assert client.m_register_requests == []
    assert materialized_launches == []


def test_launch_rejects_unsupported_pair_before_delegating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated: list[tuple[str, list[str]]] = []

    def _raise_pair_error(*, base_url: str) -> object:
        del base_url
        raise click.ClickException("unsupported pair")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.require_supported_houmao_pair",
        _raise_pair_error,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.run_passthrough",
        lambda *, command_name, extra_args: delegated.append((command_name, list(extra_args)))
        or subprocess.CompletedProcess(args=[], returncode=0),
    )

    result = CliRunner().invoke(cli, ["launch", "--agents", "gpu-kernel-coder", "--headless"])

    assert result.exit_code != 0
    assert "unsupported pair" in result.output
    assert delegated == []
