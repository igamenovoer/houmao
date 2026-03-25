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
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentMailCheckRequest,
    HoumaoManagedAgentMailReplyRequest,
    HoumaoManagedAgentMailSendRequest,
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
        self.m_list_managed_agents_calls = 0
        self.m_get_session_calls: list[str] = []
        self.m_create_session_calls: list[dict[str, object]] = []
        self.m_delete_session_calls: list[str] = []
        self.m_register_requests: list[HoumaoRegisterLaunchRequest] = []
        self.m_headless_launch_requests: list[HoumaoHeadlessLaunchRequest] = []
        self.m_get_managed_agent_calls: list[str] = []
        self.m_get_managed_agent_state_calls: list[str] = []
        self.m_get_managed_agent_state_detail_calls: list[str] = []
        self.m_get_managed_agent_history_calls: list[tuple[str, int | None]] = []
        self.m_submit_managed_agent_request_calls: list[tuple[str, object]] = []
        self.m_interrupt_managed_agent_calls: list[str] = []
        self.m_stop_managed_agent_calls: list[str] = []
        self.m_attach_managed_agent_gateway_calls: list[str] = []
        self.m_get_managed_agent_gateway_status_calls: list[str] = []
        self.m_detach_managed_agent_gateway_calls: list[str] = []
        self.m_submit_managed_agent_gateway_request_calls: list[tuple[str, object]] = []
        self.m_get_managed_agent_mail_status_calls: list[str] = []
        self.m_check_managed_agent_mail_calls: list[
            tuple[str, HoumaoManagedAgentMailCheckRequest]
        ] = []
        self.m_send_managed_agent_mail_calls: list[
            tuple[str, HoumaoManagedAgentMailSendRequest]
        ] = []
        self.m_reply_managed_agent_mail_calls: list[
            tuple[str, HoumaoManagedAgentMailReplyRequest]
        ] = []
        self.m_submit_headless_turn_calls: list[tuple[str, object]] = []
        self.m_get_headless_turn_status_calls: list[tuple[str, str]] = []
        self.m_get_headless_turn_events_calls: list[tuple[str, str]] = []
        self.m_get_headless_turn_artifact_text_calls: list[tuple[str, str, str]] = []

    def list_sessions(self) -> list[_FakeSession]:
        return list(self.m_list_sessions_payload)

    def list_managed_agents(self) -> dict[str, object]:
        self.m_list_managed_agents_calls += 1
        return {
            "agents": [
                self.get_managed_agent("cao-gpu").model_dump(mode="json"),
                self.get_managed_agent("headless-agent").model_dump(mode="json"),
            ]
        }

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
        if agent_ref in {"headless-agent", "claude-headless-1"}:
            return HoumaoManagedAgentIdentity(
                tracked_agent_id="claude-headless-1",
                transport="headless",
                tool="claude",
                session_name=None,
                terminal_id=None,
                runtime_session_id="claude-headless-1",
                tmux_session_name="AGENTSYS-headless",
                tmux_window_name="agent",
                manifest_path="/tmp/runtime/sessions/claude_headless/claude-headless-1/manifest.json",
                session_root="/tmp/runtime/sessions/claude_headless/claude-headless-1",
                agent_name="AGENTSYS-headless",
                agent_id="headless-agent-id",
            )
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

    def get_managed_agent_state(self, agent_ref: str) -> dict[str, object]:
        self.m_get_managed_agent_state_calls.append(agent_ref)
        identity = self.get_managed_agent(agent_ref)
        return {
            "tracked_agent_id": identity.tracked_agent_id,
            "identity": identity.model_dump(mode="json"),
            "availability": "available",
            "turn": {"phase": "ready", "active_turn_id": None},
            "last_turn": {
                "result": "none",
                "turn_id": None,
                "turn_index": None,
                "updated_at_utc": None,
            },
            "diagnostics": [],
            "mailbox": None,
            "gateway": None,
        }

    def get_managed_agent_state_detail(self, agent_ref: str) -> dict[str, object]:
        self.m_get_managed_agent_state_detail_calls.append(agent_ref)
        state = self.get_managed_agent_state(agent_ref)
        return {
            "tracked_agent_id": state["tracked_agent_id"],
            "identity": state["identity"],
            "summary_state": state,
            "detail": {
                "transport": state["identity"]["transport"],
                "runtime_resumable": True,
                "tmux_session_live": True,
                "can_accept_prompt_now": True,
                "interruptible": False,
                "turn": state["turn"],
                "last_turn": state["last_turn"],
                "active_turn_started_at_utc": None,
                "active_turn_interrupt_requested_at_utc": None,
                "last_turn_status": None,
                "last_turn_started_at_utc": None,
                "last_turn_completed_at_utc": None,
                "last_turn_completion_source": None,
                "last_turn_returncode": None,
                "last_turn_history_summary": None,
                "last_turn_error": None,
                "mailbox": None,
                "gateway": None,
                "diagnostics": [],
            },
        }

    def get_managed_agent_history(
        self,
        agent_ref: str,
        *,
        limit: int | None = None,
    ) -> dict[str, object]:
        self.m_get_managed_agent_history_calls.append((agent_ref, limit))
        return {
            "tracked_agent_id": self.get_managed_agent(agent_ref).tracked_agent_id,
            "entries": [
                {
                    "recorded_at_utc": "2026-03-24T16:00:00+00:00",
                    "summary": f"history-limit={limit}",
                    "availability": "available",
                    "turn_phase": "ready",
                    "last_turn_result": "none",
                    "turn_id": None,
                }
            ],
        }

    def submit_managed_agent_request(
        self, agent_ref: str, request_model: object
    ) -> dict[str, object]:
        self.m_submit_managed_agent_request_calls.append((agent_ref, request_model))
        return {
            "success": True,
            "tracked_agent_id": self.get_managed_agent(agent_ref).tracked_agent_id,
            "request_id": "mreq-123",
            "request_kind": getattr(request_model, "request_kind", "submit_prompt"),
            "disposition": "accepted",
            "detail": "accepted",
            "headless_turn_id": None,
            "headless_turn_index": None,
        }

    def interrupt_managed_agent(self, agent_ref: str) -> dict[str, object]:
        self.m_interrupt_managed_agent_calls.append(agent_ref)
        return {
            "success": True,
            "tracked_agent_id": self.get_managed_agent(agent_ref).tracked_agent_id,
            "detail": "interrupted",
            "turn_id": None,
        }

    def stop_managed_agent(self, agent_ref: str) -> dict[str, object]:
        self.m_stop_managed_agent_calls.append(agent_ref)
        return {
            "success": True,
            "tracked_agent_id": self.get_managed_agent(agent_ref).tracked_agent_id,
            "detail": "stopped",
            "turn_id": None,
        }

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

    def get_managed_agent_gateway_status(self, agent_ref: str) -> GatewayStatusV1:
        self.m_get_managed_agent_gateway_status_calls.append(agent_ref)
        return self.attach_managed_agent_gateway(agent_ref)

    def detach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        self.m_detach_managed_agent_gateway_calls.append(agent_ref)
        return self.attach_managed_agent_gateway(agent_ref)

    def submit_managed_agent_gateway_request(
        self, agent_ref: str, request_model: object
    ) -> dict[str, object]:
        self.m_submit_managed_agent_gateway_request_calls.append((agent_ref, request_model))
        return {
            "request_id": "greq-123",
            "request_kind": getattr(request_model, "kind", "submit_prompt"),
            "state": "accepted",
            "accepted_at_utc": "2026-03-24T16:00:00+00:00",
            "queue_depth": 1,
            "managed_agent_instance_epoch": 1,
        }

    def get_managed_agent_mail_status(self, agent_ref: str) -> dict[str, object]:
        self.m_get_managed_agent_mail_status_calls.append(agent_ref)
        return {
            "schema_version": 1,
            "transport": "filesystem",
            "principal_id": "agent-1234",
            "address": "agent@agents.localhost",
            "bindings_version": "v1",
        }

    def check_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailCheckRequest,
    ) -> dict[str, object]:
        self.m_check_managed_agent_mail_calls.append((agent_ref, request_model))
        return {
            "schema_version": 1,
            "transport": "filesystem",
            "principal_id": "agent-1234",
            "address": "agent@agents.localhost",
            "unread_only": request_model.unread_only,
            "message_count": 0,
            "unread_count": 0,
            "messages": [],
        }

    def send_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailSendRequest,
    ) -> dict[str, object]:
        self.m_send_managed_agent_mail_calls.append((agent_ref, request_model))
        return {
            "schema_version": 1,
            "operation": "send",
            "transport": "filesystem",
            "principal_id": "agent-1234",
            "address": "agent@agents.localhost",
            "message": {
                "message_ref": "msg-123",
                "thread_ref": "thread-1",
                "created_at_utc": "2026-03-24T16:00:00+00:00",
                "subject": request_model.subject,
                "unread": False,
                "body_preview": request_model.body_content,
                "body_text": request_model.body_content,
                "sender": {"address": "agent@agents.localhost"},
                "to": [{"address": request_model.to[0]}],
                "cc": [],
                "reply_to": [],
                "attachments": [],
            },
        }

    def reply_managed_agent_mail(
        self,
        agent_ref: str,
        request_model: HoumaoManagedAgentMailReplyRequest,
    ) -> dict[str, object]:
        self.m_reply_managed_agent_mail_calls.append((agent_ref, request_model))
        return {
            "schema_version": 1,
            "operation": "reply",
            "transport": "filesystem",
            "principal_id": "agent-1234",
            "address": "agent@agents.localhost",
            "message": {
                "message_ref": request_model.message_ref,
                "thread_ref": "thread-1",
                "created_at_utc": "2026-03-24T16:00:00+00:00",
                "subject": "reply",
                "unread": False,
                "body_preview": request_model.body_content,
                "body_text": request_model.body_content,
                "sender": {"address": "agent@agents.localhost"},
                "to": [{"address": "peer@agents.localhost"}],
                "cc": [],
                "reply_to": [],
                "attachments": [],
            },
        }

    def submit_headless_turn(self, agent_ref: str, request_model: object) -> dict[str, object]:
        self.m_submit_headless_turn_calls.append((agent_ref, request_model))
        return {
            "success": True,
            "tracked_agent_id": self.get_managed_agent(agent_ref).tracked_agent_id,
            "turn_id": "turn-123",
            "turn_index": 1,
            "status": "active",
            "detail": "accepted",
        }

    def get_headless_turn_status(self, agent_ref: str, turn_id: str) -> dict[str, object]:
        self.m_get_headless_turn_status_calls.append((agent_ref, turn_id))
        return {
            "tracked_agent_id": self.get_managed_agent(agent_ref).tracked_agent_id,
            "turn_id": turn_id,
            "turn_index": 1,
            "status": "completed",
            "detail": "done",
            "started_at_utc": "2026-03-24T16:00:00+00:00",
            "completed_at_utc": "2026-03-24T16:01:00+00:00",
            "completion_source": "tmux_wait_for",
            "returncode": 0,
        }

    def get_headless_turn_events(self, agent_ref: str, turn_id: str) -> dict[str, object]:
        self.m_get_headless_turn_events_calls.append((agent_ref, turn_id))
        return {
            "tracked_agent_id": self.get_managed_agent(agent_ref).tracked_agent_id,
            "turn_id": turn_id,
            "entries": [],
        }

    def get_headless_turn_artifact_text(
        self,
        agent_ref: str,
        turn_id: str,
        *,
        artifact_name: str,
    ) -> str:
        self.m_get_headless_turn_artifact_text_calls.append((agent_ref, turn_id, artifact_name))
        return f"{artifact_name}:{turn_id}\n"


def test_top_level_command_inventory_reserves_pair_namespace() -> None:
    assert set(cli.commands.keys()) == {"admin", "agents", "brains", "cao", "launch"}


def test_top_level_help_advertises_native_families_and_retires_agent_gateway() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Usage: houmao-mgr " in result.output
    assert "agents" in result.output
    assert "brains" in result.output
    assert "admin" in result.output
    assert "agent-gateway" not in result.output


def test_cao_group_inventory_matches_pinned_upstream() -> None:
    cao_group = cli.commands["cao"]
    assert isinstance(cao_group, click.Group)
    assert set(cao_group.commands.keys()) == (_extract_upstream_cli_commands() - {"install"})


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


def test_launch_session_backed_accepts_compat_timeout_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pair_checks: list[dict[str, object]] = []
    attach_calls: list[list[str]] = []
    client = _FakeHoumaoClient()
    manifest_path = tmp_path / "manifest.json"
    session_root = tmp_path / "session-root"
    manifest_path.write_text("{}\n", encoding="utf-8")
    session_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.require_supported_houmao_pair",
        lambda *, base_url, timeout_seconds=None, create_timeout_seconds=None: (
            pair_checks.append(
                {
                    "base_url": base_url,
                    "timeout_seconds": timeout_seconds,
                    "create_timeout_seconds": create_timeout_seconds,
                }
            )
            or client
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.subprocess.run",
        lambda args, **kwargs: (
            attach_calls.append(list(args)) or subprocess.CompletedProcess(args=args, returncode=0)
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.materialize_delegated_launch",
        lambda **kwargs: (manifest_path, session_root, "AGENTSYS-gpu", "agent-1234"),
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
            "--yolo",
            "--compat-http-timeout-seconds",
            "7",
            "--compat-create-timeout-seconds",
            "91",
        ],
    )

    assert result.exit_code == 0
    assert pair_checks == [
        {
            "base_url": "http://127.0.0.1:9889",
            "timeout_seconds": 7.0,
            "create_timeout_seconds": 91.0,
        }
    ]
    assert attach_calls == [["tmux", "attach-session", "-t", "cao-gpu"]]


def test_cao_launch_uses_env_compat_timeout_defaults_when_flags_are_omitted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pair_checks: list[dict[str, object]] = []
    client = _FakeHoumaoClient()
    manifest_path = tmp_path / "manifest.json"
    session_root = tmp_path / "session-root"
    manifest_path.write_text("{}\n", encoding="utf-8")
    session_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HOUMAO_COMPAT_HTTP_TIMEOUT_SECONDS", "6")
    monkeypatch.setenv("HOUMAO_COMPAT_CREATE_TIMEOUT_SECONDS", "93")
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.require_supported_houmao_pair",
        lambda *, base_url, timeout_seconds=None, create_timeout_seconds=None: (
            pair_checks.append(
                {
                    "base_url": base_url,
                    "timeout_seconds": timeout_seconds,
                    "create_timeout_seconds": create_timeout_seconds,
                }
            )
            or client
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.launch.materialize_delegated_launch",
        lambda **kwargs: (manifest_path, session_root, "AGENTSYS-gpu", "agent-1234"),
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
            "--headless",
            "--yolo",
        ],
    )

    assert result.exit_code == 0
    assert pair_checks == [
        {
            "base_url": "http://127.0.0.1:9889",
            "timeout_seconds": 6.0,
            "create_timeout_seconds": 93.0,
        }
    ]


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


def test_headless_launch_rejects_compat_timeout_flags() -> None:
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
            "--compat-http-timeout-seconds",
            "7",
        ],
    )

    assert result.exit_code != 0
    assert "Compatibility timeout flags only apply to session-backed launch." in result.output


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


def test_agents_gateway_attach_explicit_resolves_alias_before_attach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pair_checks: list[str] = []
    client = _FakeHoumaoClient()

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_pair_client",
        lambda *, port=None: pair_checks.append(f"http://127.0.0.1:{port or 9889}") or client,
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "gateway", "attach", "AGENTSYS gpu/1", "--port", "9999"],
    )

    assert result.exit_code == 0
    assert pair_checks == ["http://127.0.0.1:9999"]
    assert client.m_get_managed_agent_calls == ["AGENTSYS gpu/1"]
    assert client.m_attach_managed_agent_gateway_calls == ["tracked-cao-gpu"]
    assert json.loads(result.output)["gateway_port"] == 43123


def test_agents_gateway_attach_current_session_uses_persisted_server_and_session_alias(
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
        "houmao.srv_ctrl.commands.agents.gateway.require_supported_houmao_pair",
        lambda *, base_url: client if base_url == "http://127.0.0.1:9988" else None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="cao-gpu\n",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: {
            ("cao-gpu", "AGENTSYS_GATEWAY_ATTACH_PATH"): str(attach_path.resolve()),
            ("cao-gpu", "AGENTSYS_GATEWAY_ROOT"): str(gateway_root.resolve()),
        }.get((session_name, variable_name)),
    )

    result = CliRunner().invoke(cli, ["agents", "gateway", "attach"])

    assert result.exit_code == 0
    assert client.m_get_managed_agent_calls == ["cao-gpu"]
    assert client.m_attach_managed_agent_gateway_calls == ["cao-gpu"]
    assert json.loads(result.output)["gateway_host"] == "127.0.0.1"


def test_agents_gateway_attach_current_session_fails_before_registration(
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
        "houmao.srv_ctrl.commands.agents.gateway.require_supported_houmao_pair",
        lambda *, base_url: client if base_url == "http://127.0.0.1:9988" else None,
    )
    monkeypatch.setattr(client, "get_managed_agent", _raise_not_found)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="cao-gpu\n",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: {
            ("cao-gpu", "AGENTSYS_GATEWAY_ATTACH_PATH"): str(attach_path.resolve()),
            ("cao-gpu", "AGENTSYS_GATEWAY_ROOT"): str(gateway_root.resolve()),
        }.get((session_name, variable_name)),
    )

    result = CliRunner().invoke(cli, ["agents", "gateway", "attach"])

    assert result.exit_code != 0
    assert "Unknown managed agent `cao-gpu`." in result.output


def test_agent_gateway_command_is_retired() -> None:
    result = CliRunner().invoke(cli, ["agent-gateway", "attach"])

    assert result.exit_code != 0
    assert "No such command 'agent-gateway'" in result.output


def test_agents_list_show_and_prompt_route_through_pair_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeHoumaoClient()
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_pair_client",
        lambda *, port=None: client,
    )

    list_result = CliRunner().invoke(cli, ["agents", "list"])
    show_result = CliRunner().invoke(cli, ["agents", "show", "cao-gpu"])
    prompt_result = CliRunner().invoke(cli, ["agents", "prompt", "cao-gpu", "--prompt", "hello"])
    interrupt_result = CliRunner().invoke(cli, ["agents", "interrupt", "cao-gpu"])

    assert list_result.exit_code == 0
    assert show_result.exit_code == 0
    assert prompt_result.exit_code == 0
    assert interrupt_result.exit_code == 0
    assert client.m_list_managed_agents_calls == 1
    assert client.m_get_managed_agent_state_detail_calls == ["cao-gpu"]
    assert client.m_submit_managed_agent_request_calls[0][0] == "cao-gpu"
    assert client.m_submit_managed_agent_request_calls[1][0] == "cao-gpu"
    assert getattr(client.m_submit_managed_agent_request_calls[1][1], "request_kind") == "interrupt"
    assert json.loads(prompt_result.output)["request_id"] == "mreq-123"


def test_agents_gateway_prompt_routes_through_gateway_request_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeHoumaoClient()
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_pair_client",
        lambda *, port=None: client,
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "gateway", "prompt", "cao-gpu", "--prompt", "hello"],
    )

    assert result.exit_code == 0
    assert client.m_get_managed_agent_calls == ["cao-gpu"]
    agent_ref, request_model = client.m_submit_managed_agent_gateway_request_calls[0]
    assert agent_ref == "tracked-cao-gpu"
    assert request_model.kind == "submit_prompt"
    assert json.loads(result.output)["request_id"] == "greq-123"


def test_agents_mail_send_routes_through_pair_mail_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = _FakeHoumaoClient()
    attachment = tmp_path / "note.txt"
    attachment.write_text("hello\n", encoding="utf-8")
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mail.resolve_pair_client",
        lambda *, port=None: client,
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "mail",
            "send",
            "cao-gpu",
            "--to",
            "peer@agents.localhost",
            "--subject",
            "status",
            "--body-content",
            "hello",
            "--attach",
            str(attachment),
        ],
    )

    assert result.exit_code == 0
    agent_ref, request_model = client.m_send_managed_agent_mail_calls[0]
    assert agent_ref == "tracked-cao-gpu"
    assert request_model.attachments[0].path == str(attachment.resolve())
    assert json.loads(result.output)["operation"] == "send"


def test_agents_turn_submit_routes_for_headless_and_rejects_tui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeHoumaoClient()
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.turn.resolve_pair_client",
        lambda *, port=None: client,
    )

    success = CliRunner().invoke(
        cli,
        ["agents", "turn", "submit", "headless-agent", "--prompt", "hello"],
    )
    failure = CliRunner().invoke(
        cli,
        ["agents", "turn", "submit", "cao-gpu", "--prompt", "hello"],
    )

    assert success.exit_code == 0
    assert client.m_submit_headless_turn_calls[0][0] == "claude-headless-1"
    assert json.loads(success.output)["turn_id"] == "turn-123"
    assert failure.exit_code != 0
    assert "TUI-backed agents" in failure.output


def test_brains_build_routes_to_local_build_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recorded: list[object] = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.brains.build_brain_home",
        lambda request: (
            recorded.append(request)
            or type(
                "BuildResult",
                (),
                {
                    "home_id": "brain-1",
                    "home_path": tmp_path / "brain-home",
                    "manifest_path": tmp_path / "brain-home" / "manifest.json",
                    "launch_helper_path": tmp_path / "brain-home" / "launch.sh",
                },
            )()
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "brains",
            "build",
            "--agent-def-dir",
            "agents",
            "--tool",
            "codex",
            "--skill",
            "skills/mailbox",
            "--config-profile",
            "dev",
            "--cred-profile",
            "openai",
        ],
    )

    assert result.exit_code == 0
    request = recorded[0]
    assert request.tool == "codex"
    assert request.skills == ["skills/mailbox"]
    assert request.config_profile == "dev"
    assert request.credential_profile == "openai"
    assert json.loads(result.output)["home_id"] == "brain-1"


def test_admin_cleanup_registry_routes_to_local_maintenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.admin.cleanup_stale_live_agent_records",
        lambda grace_period: type(
            "CleanupResult",
            (),
            {
                "registry_root": Path("/tmp/runtime/live_agents"),
                "removed_agent_ids": ("stale-agent",),
                "preserved_agent_ids": ("live-agent",),
                "failed_agent_ids": (),
            },
        )(),
    )

    result = CliRunner().invoke(cli, ["admin", "cleanup-registry", "--grace-seconds", "0"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "failed_agent_ids": [],
        "failed_count": 0,
        "grace_seconds": 0,
        "preserved_agent_ids": ["live-agent"],
        "preserved_count": 1,
        "registry_root": "/tmp/runtime/live_agents",
        "removed_agent_ids": ["stale-agent"],
        "removed_count": 1,
    }
