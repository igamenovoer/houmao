"""Hermes terminal inspection through a verified native runtime."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.native_surface import TerminalNativeSurfaceV1
from houmao.agents.realm_controller.registry_models import (
    RegistryMailboxesV1,
    RegistryMailboxSlotV1,
)
from houmao.passive_server.app import create_app
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent
from houmao.passive_server.models import DiscoveredAgentSummary
from houmao.passive_server.service import PassiveServerService
from tests.unit.passive_server.contract_client import AdmittedPassiveClient


def _agent(tmp_path: Path) -> DiscoveredAgent:
    """Build a discovered structured terminal with a saved handoff pane."""

    terminal = TerminalNativeSurfaceV1(tmux_session_name="HOUMAO-hermes", pane_id="%2")
    manifest_path = str(tmp_path / "manifest.json")
    summary = DiscoveredAgentSummary(
        agent_id="agent",
        agent_name="agent",
        generation_id="generation",
        tool="hermes",
        backend="hermes_tui",
        mode="tui",
        tmux_session_name=terminal.tmux_session_name,
        manifest_path=manifest_path,
        session_root=str(tmp_path),
        has_gateway=False,
        has_mailbox=False,
        published_at=datetime.now(UTC).isoformat(),
        lease_expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        native_surface_kind="terminal",
        native_surface=terminal,
    )
    record = SimpleNamespace(
        agent_id=summary.agent_id,
        generation_id=summary.generation_id,
        mode=summary.mode,
        identity=SimpleNamespace(backend=summary.backend),
        execution_binding=None,
        native_surface=terminal,
        runtime=SimpleNamespace(manifest_path=manifest_path),
        mailboxes=RegistryMailboxesV1(
            offline=RegistryMailboxSlotV1(revision="offline", binding=None),
            online=RegistryMailboxSlotV1(revision="online", binding=None),
        ),
        canonical_mail_identity=None,
        gateway=None,
    )
    return DiscoveredAgent(record=record, summary=summary)


def test_hermes_aliases_present_native_state_and_keep_pane_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Report a detached queued prompt and degrade conservatively on authority loss."""

    config = PassiveServerConfig(runtime_root=tmp_path, registry_root=tmp_path / "registry")
    service = PassiveServerService(config)
    agent = _agent(tmp_path)
    service.m_discovery.index.replace({"agent": agent})
    tracker = Mock(side_effect=AssertionError("Native TUI must bypass terminal parsing"))
    monkeypatch.setattr("houmao.passive_server.observation.AgentTuiObserver", tracker)
    service.m_observation._reconcile_observers([agent])
    assert service.m_observation.get_observer("agent") is None
    tracker.assert_not_called()
    monkeypatch.setattr(service.m_headless, "resolve_managed_matches", lambda _: [])
    monkeypatch.setattr("houmao.passive_server.service.require_registry_mode_authority", Mock())
    native = ManagedControlObservationV1(
        source="tui_native",
        freshness="current",
        owner_available=True,
        connection_ready=True,
        can_accept_prompt_now=False,
        native_session_id="logical-session",
        native_admission_id="native-admission",
        native_admission_state="queued",
        terminal_attachment="detached",
    )
    manifest = SimpleNamespace(
        agent_id="agent",
        registry_generation_id="generation",
        runtime=SimpleNamespace(execution_binding=None, session_id="runtime-session"),
    )
    runtime = Mock(
        return_value=SimpleNamespace(
            execution_scope=nullcontext,
            require_managed_control_owner=lambda: manifest,
            observe_managed_tui=lambda: native,
        )
    )
    monkeypatch.setattr("houmao.passive_server.service.resume_runtime_session", runtime)
    client = AdmittedPassiveClient(create_app(service=service, config=config))
    base = "/houmao/agents/agent"
    for route in ("state", "managed-state"):
        compact = client.get(f"{base}/{route}")
        assert compact.status_code == 200
        assert compact.json()["availability"] == "available"
        assert compact.json()["turn"]["phase"] == "unknown"
        assert compact.json()["control"]["native_admission_state"] == "queued"
    for route in ("state/detail", "managed-state/detail"):
        response = client.get(f"{base}/{route}")
        assert response.status_code == 200
        detail = response.json()
        assert detail["identity"]["mode"] == "tui"
        assert detail["identity"]["native_surface"]["pane_id"] == "%2"
        assert detail["identity"]["runtime_session_id"] == "runtime-session"
        assert detail["detail"] == {"transport": "native_tui", "state": native.model_dump()}
    assert runtime.call_args.kwargs["read_only"] is True
    for route in ("history", "managed-history", "gateway/tui/state", "gateway/tui/history"):
        assert client.get(f"{base}/{route}").status_code == 501
    assert client.post(f"{base}/gateway/tui/note-prompt", json={"prompt": "hi"}).status_code == 501

    manifest.registry_generation_id = "unexpected-generation"
    unavailable = client.get(f"{base}/state/detail").json()
    assert unavailable["summary_state"]["availability"] == "unavailable"
    assert unavailable["identity"]["runtime_session_id"] is None
    assert unavailable["identity"]["native_surface"]["pane_id"] == "%2"
    state = unavailable["detail"]["state"]
    assert state["native_admission_id"] is None
    assert state["terminal_attachment"] == "unverified"
    assert state["can_accept_prompt_now"] is False
