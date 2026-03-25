from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.srv_ctrl.commands.managed_agents import (
    list_managed_agents,
    resolve_managed_agent_target,
)


def test_resolve_managed_agent_target_prefers_shared_registry_for_local_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    record = SimpleNamespace(
        agent_name="AGENTSYS-gpu",
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
        agent_identity="AGENTSYS-gpu",
        launch_plan=SimpleNamespace(backend="codex_headless", tool="codex", mailbox=None),
        manifest_path=(tmp_path / "manifest.json").resolve(),
        tmux_session_name="gpu-session",
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_live_agent_record",
        lambda agent_identity: record,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resume_runtime_session",
        lambda **kwargs: controller,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("server fallback should not run")),
    )

    target = resolve_managed_agent_target(agent_ref="AGENTSYS-gpu", port=None)

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
        agent_name="AGENTSYS-gpu",
        agent_id="agent-1234",
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_live_agent_record",
        lambda agent_identity: None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: client,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_managed_agent_identity",
        lambda resolved_client, *, agent_ref: identity,
    )

    target = resolve_managed_agent_target(agent_ref="AGENTSYS-gpu", port=None)

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
        agent_name="AGENTSYS-local",
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
        agent_name="AGENTSYS-server",
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
        agent_name="AGENTSYS-local",
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
