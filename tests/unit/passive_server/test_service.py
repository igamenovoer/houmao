"""Tests for ``PassiveServerService`` lifecycle and methods."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.registry_models import RegistryGatewayV1
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import (
    DiscoveredAgent,
    _summary_from_record,
)
from houmao.passive_server.models import DiscoveredAgentConflictResponse
from houmao.passive_server.service import PassiveServerService
from houmao.server.models import (
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayPromptControlResponse,
)
from tests.unit.passive_server.test_discovery import _make_record


def _make_service(tmp_path: Path) -> PassiveServerService:
    """Build a service with an isolated runtime root and no real polling."""

    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=tmp_path,
    )
    svc = PassiveServerService(config=config)
    return svc


class TestStartup:
    """Service startup behaviour."""

    def test_creates_current_instance_file(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        with (
            patch.object(svc.m_discovery, "start"),
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "start"),
            patch.object(svc.m_observation, "stop"),
        ):
            svc.startup()
            assert svc.m_config.current_instance_path.exists()
            svc.shutdown()

    def test_current_instance_file_has_correct_pid(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        with (
            patch.object(svc.m_discovery, "start"),
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "start"),
            patch.object(svc.m_observation, "stop"),
        ):
            svc.startup()
            payload = json.loads(svc.m_config.current_instance_path.read_text())
            assert payload["pid"] == os.getpid()
            svc.shutdown()

    def test_current_instance_file_has_correct_url(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        with (
            patch.object(svc.m_discovery, "start"),
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "start"),
            patch.object(svc.m_observation, "stop"),
        ):
            svc.startup()
            payload = json.loads(svc.m_config.current_instance_path.read_text())
            assert payload["api_base_url"] == "http://127.0.0.1:19891"
            svc.shutdown()

    def test_run_dir_created(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        with (
            patch.object(svc.m_discovery, "start"),
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "start"),
            patch.object(svc.m_observation, "stop"),
        ):
            svc.startup()
            assert svc.m_config.run_dir.is_dir()
            svc.shutdown()


class TestShutdown:
    """Service shutdown behaviour."""

    def test_removes_current_instance_file(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        with (
            patch.object(svc.m_discovery, "start"),
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "start"),
            patch.object(svc.m_observation, "stop"),
        ):
            svc.startup()
            assert svc.m_config.current_instance_path.exists()
            svc.shutdown()
            assert not svc.m_config.current_instance_path.exists()

    def test_shutdown_without_startup_is_safe(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        with (
            patch.object(svc.m_discovery, "stop"),
            patch.object(svc.m_observation, "stop"),
        ):
            svc.shutdown()  # should not raise


class TestCurrentInstance:
    """current_instance() response builder."""

    def test_returns_correct_pid(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        resp = svc.current_instance()
        assert resp.pid == os.getpid()

    def test_returns_correct_url(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        resp = svc.current_instance()
        assert resp.api_base_url == "http://127.0.0.1:19891"

    def test_returns_server_root_string(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.startup()
        resp = svc.current_instance()
        assert resp.server_root == str(svc.m_config.server_root)


class TestHealth:
    """health() response builder."""

    def test_returns_passive_identity(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        resp = svc.health()
        assert resp.houmao_service == "houmao-passive-server"
        assert resp.status == "ok"


# ---------------------------------------------------------------------------
# Agent listing and resolution
# ---------------------------------------------------------------------------


def _populate_index(svc: PassiveServerService, agents: list[DiscoveredAgent]) -> None:
    """Inject agents into the service's discovery index directly."""

    svc.m_discovery.m_index.replace({a.record.agent_id: a for a in agents})


def _agent(
    agent_id: str = "abc123",
    agent_name: str = "HOUMAO-alpha",
    session_name: str = "HOUMAO-alpha-abc123",
) -> DiscoveredAgent:
    """Create a DiscoveredAgent for test injection."""

    record = _make_record(agent_id=agent_id, agent_name=agent_name, session_name=session_name)
    return DiscoveredAgent(record=record, summary=_summary_from_record(record))


class TestListAgents:
    """list_agents() method."""

    def test_empty_index(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        resp = svc.list_agents()
        assert resp.agents == []

    def test_returns_all_agents(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(
            svc,
            [
                _agent(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1"),
                _agent(agent_id="b1", agent_name="HOUMAO-beta", session_name="s2"),
            ],
        )
        resp = svc.list_agents()
        assert len(resp.agents) == 2
        assert resp.agents[0].agent_name == "HOUMAO-alpha"
        assert resp.agents[1].agent_name == "HOUMAO-beta"


class TestResolveAgent:
    """resolve_agent() method."""

    def test_resolve_by_id(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent(agent_id="abc123")])
        result = svc.resolve_agent("abc123")
        assert result is not None
        assert not isinstance(result, DiscoveredAgentConflictResponse)
        assert result.agent_id == "abc123"

    def test_resolve_by_name(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent(agent_id="abc123", agent_name="HOUMAO-alpha")])
        result = svc.resolve_agent("alpha")
        assert result is not None
        assert not isinstance(result, DiscoveredAgentConflictResponse)
        assert result.agent_id == "abc123"

    def test_resolve_by_canonical_name(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent(agent_id="abc123", agent_name="HOUMAO-alpha")])
        result = svc.resolve_agent("HOUMAO-alpha")
        assert result is not None
        assert not isinstance(result, DiscoveredAgentConflictResponse)
        assert result.agent_id == "abc123"

    def test_resolve_not_found(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        result = svc.resolve_agent("nonexistent")
        assert result is None

    def test_resolve_ambiguous(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(
            svc,
            [
                _agent(agent_id="abc123", agent_name="HOUMAO-alpha", session_name="s1"),
                _agent(agent_id="def456", agent_name="HOUMAO-alpha", session_name="s2"),
            ],
        )
        result = svc.resolve_agent("alpha")
        assert isinstance(result, DiscoveredAgentConflictResponse)
        assert set(result.agent_ids) == {"abc123", "def456"}


# ---------------------------------------------------------------------------
# Gateway proxy helpers
# ---------------------------------------------------------------------------


def _agent_with_gateway(
    agent_id: str = "abc123",
    agent_name: str = "HOUMAO-alpha",
    session_name: str = "HOUMAO-alpha-abc123",
    gateway_host: str = "127.0.0.1",
    gateway_port: int = 9901,
) -> DiscoveredAgent:
    """Create a DiscoveredAgent with live gateway coordinates."""

    record = _make_record(agent_id=agent_id, agent_name=agent_name, session_name=session_name)
    record.gateway = RegistryGatewayV1(
        host=gateway_host,  # type: ignore[arg-type]
        port=gateway_port,
        state_path="/tmp/gw/state.json",
        protocol_version="v1",
    )
    return DiscoveredAgent(record=record, summary=_summary_from_record(record))


def _control_input_result() -> GatewayControlInputResultV1:
    """Return a valid control-input response for passive gateway tests."""

    return GatewayControlInputResultV1(detail="delivered")


def _prompt_control_result() -> HoumaoManagedAgentGatewayPromptControlResponse:
    """Return a valid prompt-control response for passive gateway tests."""

    return HoumaoManagedAgentGatewayPromptControlResponse(
        sent=True,
        forced=False,
        detail="Prompt dispatched.",
    )


def _mail_notifier_status(
    *,
    enabled: bool,
    interval_seconds: int | None,
) -> GatewayMailNotifierStatusV1:
    """Return a valid notifier status for passive gateway tests."""

    return GatewayMailNotifierStatusV1(
        enabled=enabled,
        interval_seconds=interval_seconds,
        supported=True,
        support_error=None,
        last_poll_at_utc=None,
        last_notification_at_utc=None,
        last_error=None,
    )


# ---------------------------------------------------------------------------
# _gateway_client_for_agent tests
# ---------------------------------------------------------------------------


class TestGatewayClientForAgent:
    """_gateway_client_for_agent() helper."""

    def test_returns_client_for_live_gateway(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        agent = _agent_with_gateway()
        client = svc._gateway_client_for_agent(agent)
        assert isinstance(client, GatewayClient)

    def test_returns_none_when_no_gateway(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        agent = _agent()  # no gateway
        client = svc._gateway_client_for_agent(agent)
        assert client is None

    def test_returns_none_when_gateway_has_no_live_fields(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        record = _make_record()
        agent = DiscoveredAgent(record=record, summary=_summary_from_record(record))
        client = svc._gateway_client_for_agent(agent)
        assert client is None


# ---------------------------------------------------------------------------
# gateway_status() tests
# ---------------------------------------------------------------------------


class TestGatewayStatus:
    """gateway_status() service method."""

    def test_success_returns_status(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        agent = _agent_with_gateway()
        _populate_index(svc, [agent])

        mock_status = MagicMock(spec=GatewayStatusV1)
        with patch.object(GatewayClient, "status", return_value=mock_status):
            result = svc.gateway_status("abc123")
        assert result is mock_status

    def test_agent_not_found_returns_404(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        result = svc.gateway_status("nonexistent")
        assert isinstance(result, tuple)
        assert result[0] == 404

    def test_no_gateway_returns_502(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent()])  # no gateway
        result = svc.gateway_status("abc123")
        assert isinstance(result, tuple)
        assert result[0] == 502
        assert "No gateway" in result[1]["detail"]

    def test_gateway_error_returns_502(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent_with_gateway()])
        with patch.object(
            GatewayClient,
            "status",
            side_effect=GatewayHttpError(
                method="GET", url="http://127.0.0.1:9901/v1/status", detail="Connection refused"
            ),
        ):
            result = svc.gateway_status("abc123")
        assert isinstance(result, tuple)
        assert result[0] == 502
        assert "Connection refused" in result[1]["detail"]

    def test_ambiguous_returns_409(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(
            svc,
            [
                _agent_with_gateway(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1"),
                _agent_with_gateway(agent_id="a2", agent_name="HOUMAO-alpha", session_name="s2"),
            ],
        )
        result = svc.gateway_status("alpha")
        assert isinstance(result, tuple)
        assert result[0] == 409


class TestGatewayControlInput:
    """gateway_send_control_input() service method."""

    def test_success_returns_result(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent_with_gateway()])
        expected = _control_input_result()
        with patch.object(GatewayClient, "send_control_input", return_value=expected):
            result = svc.gateway_send_control_input(
                "abc123",
                GatewayControlInputRequestV1(sequence="<[Escape]>"),
            )
        assert result == expected

    def test_agent_not_found_returns_404(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        result = svc.gateway_send_control_input(
            "missing",
            GatewayControlInputRequestV1(sequence="<[Escape]>"),
        )
        assert isinstance(result, tuple)
        assert result[0] == 404

    def test_no_gateway_returns_502(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent()])
        result = svc.gateway_send_control_input(
            "abc123",
            GatewayControlInputRequestV1(sequence="<[Escape]>"),
        )
        assert isinstance(result, tuple)
        assert result[0] == 502
        assert "No gateway" in result[1]["detail"]

    def test_gateway_error_returns_502(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent_with_gateway()])
        with patch.object(
            GatewayClient,
            "send_control_input",
            side_effect=GatewayHttpError(
                method="POST",
                url="http://127.0.0.1:9901/v1/control/send-keys",
                detail="Connection refused",
            ),
        ):
            result = svc.gateway_send_control_input(
                "abc123",
                GatewayControlInputRequestV1(sequence="<[Escape]>"),
            )
        assert isinstance(result, tuple)
        assert result[0] == 502
        assert "Connection refused" in result[1]["detail"]


class TestGatewayPromptControl:
    """gateway_control_prompt() service method."""

    def test_success_returns_result(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent_with_gateway()])
        expected = _prompt_control_result()
        with patch.object(GatewayClient, "control_prompt", return_value=expected):
            result = svc.gateway_control_prompt(
                "abc123",
                HoumaoManagedAgentGatewayPromptControlRequest(prompt="hello"),
            )
        assert result == expected

    def test_agent_not_found_returns_404(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        result = svc.gateway_control_prompt(
            "missing",
            HoumaoManagedAgentGatewayPromptControlRequest(prompt="hello"),
        )
        assert isinstance(result, tuple)
        assert result[0] == 404

    def test_no_gateway_returns_502(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent()])
        result = svc.gateway_control_prompt(
            "abc123",
            HoumaoManagedAgentGatewayPromptControlRequest(prompt="hello"),
        )
        assert isinstance(result, tuple)
        assert result[0] == 502
        assert "No gateway" in result[1]["detail"]

    def test_gateway_error_preserves_status_and_structured_detail(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent_with_gateway()])
        with patch.object(
            GatewayClient,
            "control_prompt",
            side_effect=GatewayHttpError(
                method="POST",
                url="http://127.0.0.1:9901/v1/control/prompt",
                status_code=409,
                detail=json.dumps(
                    {
                        "action": "submit_prompt",
                        "detail": "not ready",
                        "error_code": "not_ready",
                        "forced": False,
                        "sent": False,
                        "status": "error",
                    },
                    sort_keys=True,
                ),
            ),
        ):
            result = svc.gateway_control_prompt(
                "abc123",
                HoumaoManagedAgentGatewayPromptControlRequest(prompt="hello"),
            )
        assert isinstance(result, tuple)
        assert result[0] == 409
        assert isinstance(result[1]["detail"], dict)
        assert result[1]["detail"]["error_code"] == "not_ready"


class TestGatewayMailNotifier:
    """gateway_mail_notifier_*() service methods."""

    def test_status_success_returns_status(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent_with_gateway()])
        expected = _mail_notifier_status(enabled=False, interval_seconds=None)
        with patch.object(GatewayClient, "get_mail_notifier", return_value=expected):
            result = svc.gateway_mail_notifier_status("abc123")
        assert result == expected

    def test_enable_success_returns_status(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent_with_gateway()])
        expected = _mail_notifier_status(enabled=True, interval_seconds=30)
        with patch.object(GatewayClient, "put_mail_notifier", return_value=expected):
            result = svc.gateway_mail_notifier_enable(
                "abc123",
                GatewayMailNotifierPutV1(interval_seconds=30),
            )
        assert result == expected

    def test_disable_success_returns_status(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent_with_gateway()])
        expected = _mail_notifier_status(enabled=False, interval_seconds=None)
        with patch.object(GatewayClient, "delete_mail_notifier", return_value=expected):
            result = svc.gateway_mail_notifier_disable("abc123")
        assert result == expected

    def test_no_gateway_returns_502(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(svc, [_agent()])
        result = svc.gateway_mail_notifier_status("abc123")
        assert isinstance(result, tuple)
        assert result[0] == 502
        assert "No gateway" in result[1]["detail"]

    def test_ambiguous_returns_409(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        _populate_index(
            svc,
            [
                _agent_with_gateway(agent_id="a1", agent_name="HOUMAO-alpha", session_name="s1"),
                _agent_with_gateway(agent_id="a2", agent_name="HOUMAO-alpha", session_name="s2"),
            ],
        )
        result = svc.gateway_mail_notifier_status("alpha")
        assert isinstance(result, tuple)
        assert result[0] == 409
