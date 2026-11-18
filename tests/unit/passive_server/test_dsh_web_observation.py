"""Native Web passive inspection uses verified sources and no terminal parser."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from tests.unit.passive_server.contract_client import AdmittedPassiveClient
import pytest

from houmao.agents.realm_controller.native_surface import WebNativeSurfaceV1
from houmao.agents.realm_controller.registry_models import (
    RegistryMailboxesV1,
    RegistryMailboxSlotV1,
)
from houmao.agents.realm_controller.web_observation import WebObservation
from houmao.passive_server.app import create_app
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent
from houmao.passive_server.models import DiscoveredAgentSummary
from houmao.passive_server.observation import TuiObservationService
from houmao.passive_server.service import PassiveServerService
from houmao.passive_server.web_observation import AgentWebObserver
from tests.unit.agents.realm_controller.test_dsh_web_observation import _metadata, _page, _state


def _agent(tmp_path: Path, *, gateway: bool = True) -> DiscoveredAgent:
    """Build discovered Web authority with an explicit supervisor handle."""

    record = SimpleNamespace(
        agent_id="owner",
        agent_name="web-agent",
        generation_id="generation",
        identity=SimpleNamespace(backend="dsh_web", tool="dsh"),
        runtime=SimpleNamespace(
            manifest_path=str(tmp_path / "manifest.json"),
            agent_def_dir=str(tmp_path / "agent-defs"),
        ),
        terminal=SimpleNamespace(session_name="supervisor"),
        gateway=SimpleNamespace(host="127.0.0.1", port=43123) if gateway else None,
        mailboxes=RegistryMailboxesV1(
            offline=RegistryMailboxSlotV1(revision="offline", binding=None),
            online=RegistryMailboxSlotV1(revision="online", binding=None),
        ),
        canonical_mail_identity=None,
    )
    summary = DiscoveredAgentSummary(
        agent_id="owner",
        agent_name="web-agent",
        generation_id="generation",
        tool="dsh",
        backend="dsh_web",
        tmux_session_name="supervisor",
        manifest_path=record.runtime.manifest_path,
        session_root=str(tmp_path),
        has_gateway=gateway,
        has_mailbox=False,
        published_at=datetime.now(UTC).isoformat(),
        lease_expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        native_surface_kind="web",
        native_surface=WebNativeSurfaceV1(origin=_metadata().origin, native_session_id="native"),
        browser_origin=_metadata().origin,
        native_session_id="native",
    )
    return DiscoveredAgent(record=record, summary=summary)


def _native() -> tuple[dict, WebObservation]:
    """Return a mutable controlled native snapshot and its validated projection."""

    payload = _state()
    observation = WebObservation(
        metadata=_metadata(), state=lambda: deepcopy(payload), history=lambda **_: _page(1)
    )
    observation.refresh()
    return payload, observation


def _observer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, gateway: bool = True
) -> AgentWebObserver:
    """Inject exact metadata without opening any real host, process, or tmux server."""

    observer = AgentWebObserver(agent=_agent(tmp_path, gateway=gateway))
    monkeypatch.setattr(observer, "_read_metadata", _metadata)
    return observer


def test_supervisor_tmux_never_creates_a_terminal_parser_for_web(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Web observer creation and disappearance stay independent of terminal observers."""

    service = TuiObservationService(
        discovery=Mock(),
        config=PassiveServerConfig(runtime_root=tmp_path, registry_root=tmp_path / "registry"),
    )
    terminal = Mock(side_effect=AssertionError("supervisor is not a human interface"))
    monkeypatch.setattr("houmao.passive_server.observation.AgentTuiObserver", terminal)
    agent = _agent(tmp_path)
    service._reconcile_observers([agent])
    observer = service.get_web_observer("owner")
    assert observer is not None and service.get_observer("owner") is None
    service._reconcile_observers([agent])
    assert service.get_web_observer("owner") is observer
    closed = Mock()
    monkeypatch.setattr(observer, "close", closed)
    service._reconcile_observers([])
    closed.assert_called_once()
    terminal.assert_not_called()


def test_gateway_to_direct_fallback_preserves_native_identity_and_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale gateway falls back to fresh native observation without activation or replay."""

    observer = _observer(tmp_path, monkeypatch)
    payload, native = _native()
    client = Mock()
    client.get_web_state.return_value = native.refresh()
    client.get_web_history.return_value = native.history()
    monkeypatch.setattr(
        "houmao.passive_server.web_observation.GatewayClient", Mock(return_value=client)
    )
    entry = native.history().entries[0]
    page = _page(1)
    page["entries"] = [{**entry.model_dump(exclude={"metadata"}), **entry.metadata}]
    backend = SimpleNamespace(
        observe_web_state=lambda: deepcopy(payload),
        observe_web_history=lambda **_: page,
        close_control_connection=Mock(),
    )
    reconnect = Mock(return_value=SimpleNamespace(backend_session=backend))
    monkeypatch.setattr("houmao.passive_server.web_observation.resume_runtime_session", reconnect)
    first = observer.current_state().web
    assert first.source == "gateway" and first.can_accept_prompt_now
    reconnect.assert_not_called()
    client.get_web_state.return_value = first.model_copy(
        update={"observed_at_utc": "2000-01-01T00:00:00+00:00"}
    )
    payload["interaction_waits"] = ["approval"]
    payload["admission"] = {
        "ready_only": False,
        "if_no_pending": False,
        "always": True,
        "reason": "approval",
    }
    second = observer.current_state().web
    assert second.source == "direct" and second.identity == first.identity
    assert second.interaction_waits == ["approval"] and not second.can_accept_prompt_now
    reconnect.assert_called_once()
    assert [entry.sequence for entry in observer.history().web.entries] == [1]
    assert "terminal" not in second.model_dump_json()
    observer.close()
    backend.close_control_connection.assert_called_once()


@pytest.mark.parametrize("loss", ["revoked", "wrong_identity", "cold_unavailable"])
def test_unavailable_web_sources_clear_stale_idle_without_cold_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, loss: str
) -> None:
    """Neither healthy supervision nor a stale ready sample becomes native availability."""

    observer = _observer(tmp_path, monkeypatch)
    _, native = _native()
    client = Mock()
    client.get_web_state.return_value = native.refresh()
    client.get_web_history.return_value = native.history()
    monkeypatch.setattr(
        "houmao.passive_server.web_observation.GatewayClient", Mock(return_value=client)
    )
    assert observer.current_state().web.can_accept_prompt_now
    if loss == "revoked":
        client.get_web_state.side_effect = RuntimeError("credential revoked")
    elif loss == "wrong_identity":
        client.get_web_state.return_value = native.refresh().model_copy(
            update={
                "identity": _metadata().identity.model_copy(
                    update={"agent_incarnation": "replacement"}
                )
            }
        )
    else:
        client.get_web_state.return_value = native.unavailable()
    reconnect = Mock(side_effect=RuntimeError("Native agent remains cold"))
    monkeypatch.setattr("houmao.passive_server.web_observation.resume_runtime_session", reconnect)
    state = observer.current_state().web
    assert state.availability == "unavailable"
    assert not state.can_accept_prompt_now and not state.admission.always
    assert state.active_turn is None
    assert "credential" not in state.model_dump_json()
    assert reconnect.call_count == 1
    history = observer.history().web
    assert not history.reconciled
    assert history.sequence == 1


def test_web_passive_routes_share_native_detail_without_terminal_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compact, canonical detail, and history routes work without a terminal observer."""

    config = PassiveServerConfig(
        runtime_root=tmp_path / "runtime", registry_root=tmp_path / "registry"
    )
    service = PassiveServerService(config)
    agent = _agent(tmp_path, gateway=False)
    service.m_discovery.index.replace({"owner": agent})
    observer = _observer(tmp_path, monkeypatch, gateway=False)
    _, native = _native()
    observer.m_metadata = _metadata()
    monkeypatch.setattr(
        observer, "poll_cycle", lambda: setattr(observer, "m_state", native.refresh())
    )
    observer.m_entries.extend(reversed(native.history().entries))
    observer.m_reconciled = True
    service.m_observation.m_web_observers["owner"] = observer
    monkeypatch.setattr(service, "_managed_gateway_summary", lambda _: None)
    monkeypatch.setattr(service.m_headless, "resolve_managed_matches", lambda _: [])
    client = AdmittedPassiveClient(create_app(service=service, config=config))
    compact = client.get("/houmao/agents/owner/state")
    assert compact.status_code == 200 and compact.json()["transport"] == "web"
    detail = client.get("/houmao/agents/owner/state/detail")
    assert detail.status_code == 200
    body = detail.json()
    assert body["identity"]["transport"] == "web"
    assert body["identity"]["runtime_session_id"] == "runtime"
    assert body["detail"]["transport"] == "web"
    assert body["detail"]["state"] == compact.json()["web"]
    assert "probe_snapshot" not in body["detail"] and "parsed_surface" not in body["detail"]
    assert "canonical_terminal_state_route" not in body["detail"]
    history = client.get("/houmao/agents/owner/history")
    assert history.status_code == 200
    assert history.json()["web"]["entries"][0]["identity"]["native_session_id"] == "native"
    gateway = Mock()
    gateway.get_web_state.return_value = native.refresh()
    gateway.get_web_history.return_value = native.history()
    monkeypatch.setattr(service, "_gateway_client_for_agent", lambda _: gateway)
    assert client.get("/houmao/agents/owner/gateway/web/state").status_code == 200
    proxied_history = client.get("/houmao/agents/owner/gateway/web/history?limit=7")
    assert proxied_history.status_code == 200
    gateway.get_web_history.assert_called_once_with(limit=7)
