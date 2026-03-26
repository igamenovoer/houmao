from __future__ import annotations

import click
from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.server.models import (
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentHeadlessDetailView,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
)
from houmao.srv_ctrl.commands.managed_agents import (
    ManagedAgentTarget,
    attach_gateway,
    detach_gateway,
    list_managed_agents,
    managed_agent_detail_payload,
    managed_agent_state_payload,
    relaunch_managed_agent,
    resolve_managed_agent_target,
    submit_headless_turn,
)


def test_resolve_managed_agent_target_prefers_shared_registry_for_local_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    record = SimpleNamespace(
        agent_name="gpu",
        agent_id="agent-1234",
        identity=SimpleNamespace(backend="codex_headless", tool="codex"),
        runtime=SimpleNamespace(
            agent_def_dir=str((tmp_path / "agent-def").resolve()),
            manifest_path=str((tmp_path / "manifest.json").resolve()),
            session_root=str((tmp_path / "session-root").resolve()),
        ),
        terminal=SimpleNamespace(session_name="gpu-session"),
    )
    controller = SimpleNamespace(
        agent_id="agent-1234",
        agent_identity="gpu",
        launch_plan=SimpleNamespace(backend="codex_headless", tool="codex", mailbox=None),
        manifest_path=(tmp_path / "manifest.json").resolve(),
        tmux_session_name="gpu-session",
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._resolve_local_managed_agent_record",
        lambda **kwargs: record,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resume_runtime_session",
        lambda **kwargs: controller,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("server fallback should not run")),
    )

    target = resolve_managed_agent_target(agent_id=None, agent_name="gpu", port=None)

    assert target.mode == "local"
    assert target.controller is controller
    assert target.identity.transport == "headless"
    assert target.identity.agent_id == "agent-1234"


def test_resolve_managed_agent_target_falls_back_to_server_when_registry_misses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = SimpleNamespace()
    identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-1",
        transport="tui",
        tool="codex",
        session_name="sess-a",
        terminal_id="abcd1234",
        runtime_session_id=None,
        tmux_session_name="sess-a",
        tmux_window_name="agent",
        manifest_path="/tmp/manifest.json",
        session_root="/tmp/session-root",
        agent_name="gpu",
        agent_id="agent-1234",
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._resolve_local_managed_agent_record",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: client,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_managed_agent_identity",
        lambda resolved_client, *, agent_ref: identity,
    )

    target = resolve_managed_agent_target(agent_id=None, agent_name="gpu", port=None)

    assert target.mode == "server"
    assert target.client is client
    assert target.identity == identity


def test_list_managed_agents_merges_registry_and_server_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-local",
        transport="headless",
        tool="codex",
        session_name=None,
        terminal_id=None,
        runtime_session_id="tracked-local",
        tmux_session_name="gpu-session",
        tmux_window_name=None,
        manifest_path="/tmp/local-manifest.json",
        session_root="/tmp/local-session",
        agent_name="local",
        agent_id="local-agent-id",
    )
    server_identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-server",
        transport="tui",
        tool="codex",
        session_name="sess-a",
        terminal_id="abcd1234",
        runtime_session_id=None,
        tmux_session_name="sess-a",
        tmux_window_name="agent",
        manifest_path="/tmp/server-manifest.json",
        session_root="/tmp/server-session",
        agent_name="server",
        agent_id="server-agent-id",
    )
    duplicate_server_identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-local-overridden",
        transport="headless",
        tool="codex",
        session_name=None,
        terminal_id=None,
        runtime_session_id="tracked-local-overridden",
        tmux_session_name="gpu-session",
        tmux_window_name=None,
        manifest_path="/tmp/other.json",
        session_root="/tmp/other-session",
        agent_name="local",
        agent_id="local-agent-id",
    )
    client = SimpleNamespace(
        list_managed_agents=lambda: SimpleNamespace(
            agents=[server_identity, duplicate_server_identity]
        )
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._list_registry_identities",
        lambda: [registry_identity],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._optional_pair_client",
        lambda **kwargs: client,
    )

    response = list_managed_agents(port=None)

    assert [agent.agent_id for agent in response.agents] == ["local-agent-id", "server-agent-id"]


def _managed_identity(*, transport: str = "headless") -> HoumaoManagedAgentIdentity:
    session_name = "sess-a" if transport == "tui" else None
    terminal_id = "terminal-a" if transport == "tui" else None
    runtime_session_id = None if transport == "tui" else "tracked-alpha"
    return HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-alpha",
        transport=transport,
        tool="claude",
        session_name=session_name,
        terminal_id=terminal_id,
        runtime_session_id=runtime_session_id,
        tmux_session_name="AGENTSYS-alpha",
        tmux_window_name="agent",
        manifest_path="/tmp/manifest.json",
        session_root="/tmp/session-root",
        agent_name="AGENTSYS-alpha",
        agent_id="published-alpha",
    )


def _managed_state(identity: HoumaoManagedAgentIdentity) -> HoumaoManagedAgentStateResponse:
    return HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability="available",
        turn=HoumaoManagedAgentTurnView(phase="ready", active_turn_id=None),
        last_turn=HoumaoManagedAgentLastTurnView(result="none", turn_id=None, turn_index=None),
        diagnostics=[],
        mailbox=None,
        gateway=None,
    )


def _managed_detail(state: HoumaoManagedAgentStateResponse) -> HoumaoManagedAgentDetailResponse:
    return HoumaoManagedAgentDetailResponse(
        tracked_agent_id=state.tracked_agent_id,
        identity=state.identity,
        summary_state=state,
        detail=HoumaoManagedAgentHeadlessDetailView(
            runtime_resumable=True,
            tmux_session_live=True,
            can_accept_prompt_now=True,
            interruptible=False,
            turn=state.turn,
            last_turn=state.last_turn,
            mailbox=None,
            gateway=None,
            diagnostics=[],
        ),
    )


def _gateway_status() -> GatewayStatusV1:
    return GatewayStatusV1(
        attach_identity="published-alpha",
        backend="claude_headless",
        tmux_session_name="AGENTSYS-alpha",
        gateway_health="healthy",
        managed_agent_connectivity="connected",
        managed_agent_recovery="idle",
        request_admission="open",
        terminal_surface_eligibility="ready",
        active_execution="idle",
        queue_depth=0,
        gateway_host="127.0.0.1",
        gateway_port=9901,
        managed_agent_instance_epoch=1,
    )


class _FakePassivePairClient:
    def __init__(self) -> None:
        self.pair_authority_kind = "houmao-passive-server"
        self.state_calls: list[str] = []
        self.detail_calls: list[str] = []
        self.turn_calls: list[tuple[str, str]] = []
        self.m_state = _managed_state(_managed_identity())
        self.m_detail = _managed_detail(self.m_state)
        self.m_turn = HoumaoHeadlessTurnAcceptedResponse(
            success=True,
            tracked_agent_id="tracked-alpha",
            turn_id="turn-0001",
            turn_index=1,
            status="completed",
            detail="accepted",
        )

    def get_managed_agent_state(self, agent_ref: str) -> HoumaoManagedAgentStateResponse:
        self.state_calls.append(agent_ref)
        return self.m_state

    def get_managed_agent_state_detail(self, agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        self.detail_calls.append(agent_ref)
        return self.m_detail

    def submit_headless_turn(
        self,
        agent_ref: str,
        request_model: object,
    ) -> HoumaoHeadlessTurnAcceptedResponse:
        self.turn_calls.append((agent_ref, getattr(request_model, "prompt")))
        return self.m_turn

    def attach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        raise AssertionError(f"remote passive gateway attach should stay local for {agent_ref}")

    def detach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        raise AssertionError(f"remote passive gateway detach should stay local for {agent_ref}")


class _FakeGatewayController:
    def __init__(self) -> None:
        self.attach_calls: list[str | None] = []

    def attach_gateway(self, *, execution_mode_override: str | None = None) -> SimpleNamespace:
        self.attach_calls.append(execution_mode_override)
        return SimpleNamespace(status="ok", detail="attached")


def test_managed_agent_state_payload_uses_passive_pair_client() -> None:
    client = _FakePassivePairClient()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=client.m_state.identity,
        client=client,
    )

    response = managed_agent_state_payload(target)

    assert response.tracked_agent_id == "tracked-alpha"
    assert client.state_calls == ["published-alpha"]


def test_managed_agent_detail_payload_uses_passive_pair_client() -> None:
    client = _FakePassivePairClient()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=client.m_detail.identity,
        client=client,
    )

    response = managed_agent_detail_payload(target)

    assert response.detail.transport == "headless"
    assert client.detail_calls == ["published-alpha"]


def test_submit_headless_turn_uses_passive_pair_client() -> None:
    client = _FakePassivePairClient()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=client.m_state.identity,
        client=client,
    )

    response = submit_headless_turn(target, prompt="hello")

    assert response.turn_id == "turn-0001"
    assert client.turn_calls == [("published-alpha", "hello")]


def test_attach_gateway_prefers_local_authority_for_passive_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakePassivePairClient()
    identity = client.m_state.identity
    controller = _FakeGatewayController()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=identity,
        client=client,
    )
    gateway_status = _gateway_status()
    record = SimpleNamespace(identity=SimpleNamespace(backend="claude_headless"))

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._resolve_local_gateway_record_for_passive_pair",
        lambda resolved_target: record,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._resume_controller_from_record",
        lambda resolved_record: controller,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._identity_from_controller",
        lambda resolved_controller: identity,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._gateway_status_for_controller",
        lambda resolved_controller: gateway_status,
    )

    response = attach_gateway(target, foreground=True)

    assert response.gateway_port == 9901
    assert controller.attach_calls == ["tmux_auxiliary_window"]


def test_detach_gateway_requires_local_authority_for_passive_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakePassivePairClient()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=client.m_state.identity,
        client=client,
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._resolve_local_gateway_record_for_passive_pair",
        lambda resolved_target: None,
    )

    with pytest.raises(click.ClickException, match="requires local authority on the owning host"):
        detach_gateway(target)


def test_relaunch_managed_agent_uses_local_controller() -> None:
    calls: list[str] = []
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="published-alpha",
        identity=_managed_identity(),
        controller=SimpleNamespace(
            relaunch=lambda: (
                calls.append("relaunch")
                or SimpleNamespace(status="ok", detail="Runtime relaunched.")
            )
        ),
    )

    response = relaunch_managed_agent(target)

    assert response.success is True
    assert response.tracked_agent_id == "tracked-alpha"
    assert response.detail == "Runtime relaunched."
    assert calls == ["relaunch"]


def test_relaunch_managed_agent_prefers_local_authority_for_passive_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakePassivePairClient()
    identity = client.m_state.identity
    record = SimpleNamespace(identity=SimpleNamespace(backend="houmao_server_rest"))
    calls: list[object] = []
    controller = SimpleNamespace(
        relaunch=lambda: (
            calls.append("relaunch")
            or SimpleNamespace(status="ok", detail="Pair runtime relaunched.")
        )
    )
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=identity,
        client=client,
        record=record,
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._resume_controller_from_record",
        lambda resolved_record: (calls.append(resolved_record), controller)[1],
    )

    response = relaunch_managed_agent(target)

    assert response.success is True
    assert response.tracked_agent_id == "tracked-alpha"
    assert response.detail == "Pair runtime relaunched."
    assert calls == [record, "relaunch"]


def test_relaunch_managed_agent_requires_local_authority_for_passive_pair() -> None:
    client = _FakePassivePairClient()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=client.m_state.identity,
        client=client,
    )

    with pytest.raises(click.ClickException, match="requires local manifest authority"):
        relaunch_managed_agent(target)
