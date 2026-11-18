"""Passive accounting authority, projection, and HTTP boundary tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from tests.unit.passive_server.contract_client import AdmittedPassiveClient
import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.backends.headless_base import HeadlessInteractiveSession
from houmao.agents.realm_controller.usage_models import (
    UsageCapability,
    UsageCollectionHealth,
    UsagePage,
    UsageRecord,
)
from houmao.agents.realm_controller.usage_store import UsageStore, UsageStoreError
from houmao.passive_server.app import create_app
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, _summary_from_record
from houmao.passive_server.service import PassiveServerService
from houmao.server.managed_agents import (
    ManagedHeadlessActiveTurnRecord,
    ManagedHeadlessAuthorityRecord,
    ManagedHeadlessTurnRecord,
)
from houmao.passive_server.headless import _ManagedHeadlessHandle
from tests.unit.passive_server.test_discovery import _make_record


def _service(tmp_path: Path) -> PassiveServerService:
    """Build a passive service without starting real collectors or discovery."""

    return PassiveServerService(
        config=PassiveServerConfig(runtime_root=tmp_path, registry_root=tmp_path / "registry")
    )


def _authority(
    service: PassiveServerService, *, tracked_id: str = "tracked-a"
) -> ManagedHeadlessAuthorityRecord:
    """Seed a durable authority without creating an in-memory controller."""

    root = service.m_config.runtime_root / "runtime" / tracked_id
    result = ManagedHeadlessAuthorityRecord(
        tracked_agent_id=tracked_id,
        backend="codex_headless",
        tool="codex",
        manifest_path=str(root / "manifest.json"),
        session_root=str(root),
        tmux_session_name="agent-a-tmux",
        agent_def_dir=str(service.m_config.runtime_root / "agent-defs"),
        agent_id=f"published-{tracked_id}",
        agent_name="agent-a",
        created_at_utc="2026-11-13T00:00:00+00:00",
        updated_at_utc="2026-11-13T00:00:00+00:00",
    )
    service.m_headless.m_store.write_authority(result)
    return result


def _page(*, records: bool = True) -> UsagePage:
    """Build native usage with degraded current collection and a pollable end cursor."""

    return UsagePage(
        runtime_session_id="runtime-a",
        stream_id="stream-a",
        capability=UsageCapability(
            status="partial",
            turn_recording=True,
            source_kinds=["native_session_log"],
            observed_scopes=["turn"],
            reasons=["source_unreadable"],
        ),
        collection=UsageCollectionHealth(status="degraded", diagnostics=["source_unreadable"]),
        records=[
            UsageRecord(
                agent_id="published-a",
                runtime_session_id="runtime-a",
                turn_id="native-a",
                backend="local_interactive",
                provider="codex",
                turn_origin="native_observed",
                outcome="completed",
            )
        ]
        if records
        else [],
        next_cursor="saved-position",
        has_more=False,
    )


def _discover(service: PassiveServerService, *, duplicate: bool = False) -> None:
    """Populate live discovery independently of server-managed authorities."""

    agents = {}
    for agent_id in ("gateway-a", "gateway-b") if duplicate else ("gateway-a",):
        record = _make_record(agent_id=agent_id, agent_name="gateway-agent")
        agents[agent_id] = DiscoveredAgent(record=record, summary=_summary_from_record(record))
    service.m_discovery.m_index.replace(agents)


@pytest.mark.parametrize("reference", ["tracked-a", "published-tracked-a", "agent-a"])
def test_usage_resolves_durable_authority_without_controller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reference: str
) -> None:
    """Finalized authority-owned history does not require a controller or gateway."""

    service = _service(tmp_path)
    authority = _authority(service)
    reader = Mock()
    reader.get_usage.return_value = _page()
    factory = Mock(return_value=reader)
    monkeypatch.setattr("houmao.passive_server.headless.UsageService.from_manifest", factory)
    assert service.get_usage(reference, after="old", limit=2) == _page()
    factory.assert_called_once_with(Path(authority.manifest_path))
    reader.get_usage.assert_called_once_with(after="old", limit=2)
    reader.start.assert_not_called()
    reader.reconcile.assert_not_called()


def test_usage_prefers_server_authority_over_discovery_gateway(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second live gateway projection cannot supersede server-managed accounting."""

    service = _service(tmp_path)
    _authority(service)
    reader = Mock()
    reader.get_usage.return_value = _page()
    monkeypatch.setattr(
        "houmao.passive_server.headless.UsageService.from_manifest", Mock(return_value=reader)
    )
    monkeypatch.setattr(
        service, "_resolve_agent_or_error", Mock(side_effect=AssertionError("gateway used"))
    )
    assert service.get_usage("agent-a") == _page()


@pytest.mark.parametrize(
    ("error", "status"), [(ValueError("cursor"), 422), (UsageStoreError("private/path"), 503)]
)
def test_authority_usage_preserves_safe_validation_and_storage_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception, status: int
) -> None:
    """A failed read cannot masquerade as empty accounting history."""

    service = _service(tmp_path)
    _authority(service)
    reader = Mock()
    reader.get_usage.side_effect = error
    monkeypatch.setattr(
        "houmao.passive_server.headless.UsageService.from_manifest", Mock(return_value=reader)
    )
    result = service.get_usage("tracked-a")
    assert isinstance(result, tuple)
    assert result[0] == status
    assert "private/path" not in str(result[1])


def test_stopped_authority_with_ledger_survives_passive_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Controller cleanup retains the addressability of durable accounting history."""

    service = _service(tmp_path)
    authority = _authority(service)
    ledger_path = Path(authority.session_root) / "usage" / "records.sqlite3"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.touch()
    reader = Mock()
    reader.get_usage.return_value = _page()
    monkeypatch.setattr(
        "houmao.passive_server.headless.UsageService.from_manifest", Mock(return_value=reader)
    )
    monkeypatch.setattr("houmao.passive_server.headless.tmux_session_exists", lambda **_: False)
    service.m_headless.start()
    assert service.m_headless.m_store.read_authority(tracked_agent_id="tracked-a") == authority
    assert service.m_headless.m_handles["tracked-a"].controller is None
    reader.reconcile.assert_called_once()
    assert service.get_usage("agent-a") == _page()
    service.m_headless.stop()
    reader.stop.assert_called_once()


def test_explicit_stop_preserves_owned_usage_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stopping execution keeps existing accounting addressable without live control."""

    service = _service(tmp_path)
    authority = _authority(service)
    ledger_path = Path(authority.session_root) / "usage" / "records.sqlite3"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.touch()
    service.m_headless.m_handles["tracked-a"] = _ManagedHeadlessHandle(
        authority=authority, controller=None
    )
    reader = Mock()
    reader.get_usage.return_value = _page()
    monkeypatch.setattr(
        "houmao.passive_server.headless.UsageService.from_manifest", Mock(return_value=reader)
    )
    monkeypatch.setattr("houmao.passive_server.headless.kill_tmux_session", Mock())
    monkeypatch.setattr("houmao.passive_server.headless.remove_live_agent_record", Mock())
    result = service.m_headless.stop_managed("tracked-a")
    assert not isinstance(result, tuple)
    assert service.m_headless.m_store.read_authority(tracked_agent_id="tracked-a") == authority
    assert service.m_headless.m_handles["tracked-a"].controller is None
    assert service.get_usage("agent-a") == _page()
    reader.reconcile.assert_called_once()
    reader.stop.assert_called_once()


def test_runner_timeout_does_not_finalize_live_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing completion marker remains pending while its identified child is live."""

    service = _service(tmp_path)
    authority = _authority(service)
    turn = ManagedHeadlessTurnRecord(
        tracked_agent_id="tracked-a",
        turn_id="turn-a",
        turn_index=1,
        status="active",
        started_at_utc="2026-11-13T00:00:00+00:00",
        turn_artifact_dir=str(tmp_path / "turn-a"),
        tmux_session_name=authority.tmux_session_name,
        interrupt_requested_at_utc="2026-11-13T00:01:00+00:00",
    )
    service.m_headless.m_store.write_turn_record(turn)
    monkeypatch.setattr(
        "houmao.passive_server.headless.headless_artifact_process_alive", lambda _: True
    )
    result = service.m_headless._refresh_turn_record(
        tracked_agent_id="tracked-a",
        turn_id="turn-a",
        completion_events=None,
        error_detail="Controller timed out",
    )
    assert result == turn
    assert (
        service.m_headless.m_store.read_turn_record(
            tracked_agent_id="tracked-a", turn_id="turn-a"
        ).status
        == "active"
    )


def test_managed_interrupt_persists_request_before_fast_process_exit(tmp_path: Path) -> None:
    """A fast signal exit cannot race the interrupted outcome into a failure."""

    service = _service(tmp_path)
    authority = _authority(service)
    turn_dir = tmp_path / "turn-a"
    turn_dir.mkdir()
    active = ManagedHeadlessActiveTurnRecord(
        tracked_agent_id="tracked-a",
        turn_id="turn-a",
        turn_index=1,
        started_at_utc="2026-11-13T00:00:00Z",
        turn_artifact_dir=str(turn_dir),
        tmux_session_name=authority.tmux_session_name,
    )
    record = ManagedHeadlessTurnRecord(
        tracked_agent_id=active.tracked_agent_id,
        turn_id=active.turn_id,
        turn_index=active.turn_index,
        started_at_utc=active.started_at_utc,
        turn_artifact_dir=active.turn_artifact_dir,
        tmux_session_name=active.tmux_session_name,
        status="active",
    )
    service.m_headless.m_store.write_active_turn(active)
    service.m_headless.m_store.write_turn_record(record)
    backend = Mock(spec=HeadlessInteractiveSession)
    service.m_headless.m_handles["tracked-a"] = _ManagedHeadlessHandle(
        authority=authority, controller=Mock(backend_session=backend)
    )

    def exit_immediately() -> Mock:
        """Finalize during the signal call, after durable interrupt intent exists."""

        persisted = service.m_headless.m_store.read_active_turn(tracked_agent_id="tracked-a")
        assert persisted is not None and persisted.interrupt_requested_at_utc is not None
        (turn_dir / "exitcode").write_text("-15\n", encoding="utf-8")
        finalized = service.m_headless._refresh_turn_record(
            tracked_agent_id="tracked-a",
            turn_id="turn-a",
            completion_events=None,
            error_detail="Process terminated",
        )
        assert finalized is not None and finalized.status == "interrupted"
        return Mock(detail="sent")

    backend.interrupt.side_effect = exit_immediately
    response = service.m_headless.interrupt_managed("tracked-a")
    assert not isinstance(response, tuple)
    finalized = service.m_headless.m_store.read_turn_record(
        tracked_agent_id="tracked-a", turn_id="turn-a"
    )
    assert finalized is not None and finalized.status == "interrupted"
    assert finalized.interrupt_requested_at_utc is not None


@pytest.mark.parametrize("page", [_page(), _page(records=False), UsagePage()])
def test_usage_proxy_preserves_tui_capability_records_health_and_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, page: UsagePage
) -> None:
    """Qualified, degraded, empty, and unavailable pages pass through unchanged."""

    service = _service(tmp_path)
    _discover(service)
    gateway = Mock()
    gateway.get_usage.return_value = page
    monkeypatch.setattr(service, "_gateway_client_for_agent", lambda _: gateway)
    assert service.get_usage("gateway-agent", after="position", limit=3) == page
    gateway.get_usage.assert_called_once_with(after="position", limit=3)


@pytest.mark.parametrize("status", [422, 503, None])
def test_usage_proxy_sanitizes_upstream_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int | None
) -> None:
    """The proxy omits upstream failure details from the public response."""

    service = _service(tmp_path)
    _discover(service)
    gateway = Mock()
    gateway.get_usage.side_effect = GatewayHttpError(
        method="GET", url="http://127.0.0.1:1/v1/usage", detail="safe error", status_code=status
    )
    monkeypatch.setattr(service, "_gateway_client_for_agent", lambda _: gateway)
    assert service.get_usage("gateway-a") == (502, {"detail": "Agent gateway request failed"})


def test_usage_resolution_unknown_ambiguous_and_missing_gateway(
    tmp_path: Path,
) -> None:
    """Usage reuses managed-agent resolution and requires a gateway for attached agents."""

    service = _service(tmp_path)
    assert service.get_usage("unknown")[0] == 404
    _discover(service)
    assert service.get_usage("gateway-agent")[0] == 502
    _discover(service, duplicate=True)
    assert service.get_usage("gateway-agent")[0] == 409
    _authority(service)
    _authority(service, tracked_id="tracked-b")
    assert service.get_usage("agent-a")[0] == 409


def test_usage_rejects_alias_collision_between_authority_and_gateway(tmp_path: Path) -> None:
    """Authority precedence does not authorize selecting an unrelated ambiguous name."""

    service = _service(tmp_path)
    _authority(service)
    record = _make_record(agent_id="other-agent", agent_name="agent-a")
    service.m_discovery.m_index.replace(
        {"other-agent": DiscoveredAgent(record=record, summary=_summary_from_record(record))}
    )
    assert service.get_usage("agent-a") == (409, {"detail": "Ambiguous managed agent reference"})


def test_passive_usage_http_page_and_query_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The maintained HTTP route uses the shared page and bounded query contract."""

    service = _service(tmp_path)
    query = Mock(return_value=_page(records=False))
    monkeypatch.setattr(service, "get_usage", query)
    client = AdmittedPassiveClient(
        create_app(config=service.m_config, service=service), extra_refs=["agent-a"]
    )
    response = client.get("/houmao/agents/agent-a/usage", params={"after": "position", "limit": 2})
    assert response.status_code == 200
    assert response.json() == _page(records=False).model_dump(mode="json")
    query.assert_called_once_with("agent-a", after="position", limit=2)
    for params in ({"limit": 0}, {"limit": 501}, {"after": ""}):
        assert client.get("/houmao/agents/agent-a/usage", params=params).status_code == 422
    assert query.call_count == 1


def test_passive_usage_http_preserves_service_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Storage failures propagate through the HTTP route as explicit errors."""

    service = _service(tmp_path)
    monkeypatch.setattr(
        service, "get_usage", Mock(return_value=(503, {"detail": "Usage history is unavailable"}))
    )
    response = AdmittedPassiveClient(create_app(service=service), extra_refs=["agent-a"]).get(
        "/houmao/agents/agent-a/usage"
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Usage history is unavailable"}


def test_passive_usage_reads_real_ledger_and_polls_after_empty_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real durable accounting survives controller absence and resumes after the current end."""

    service = _service(tmp_path)
    authority = _authority(service)
    manifest_path = Path(authority.manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "tool": "codex",
                "backend": "codex_headless",
                "agent_id": "published-tracked-a",
                "runtime": {"session_id": "runtime-a"},
                "launch_plan": {},
            }
        ),
        encoding="utf-8",
    )
    ledger = UsageStore.from_path(manifest_path.parent / "usage" / "records.sqlite3", "runtime-a")
    first = UsageRecord(
        agent_id="published-tracked-a",
        runtime_session_id="runtime-a",
        turn_id="turn-a",
        backend="codex_headless",
        provider="codex",
        outcome="completed",
    )
    ledger.finalize(first)
    monkeypatch.setattr(
        "houmao.passive_server.headless.UsageService.collect",
        Mock(side_effect=AssertionError("GET scanned provider sources")),
    )
    monkeypatch.setattr(
        "houmao.passive_server.headless.UsageService.reconcile",
        Mock(side_effect=AssertionError("GET reconciled provider artifacts")),
    )
    client = AdmittedPassiveClient(create_app(service=service))
    response = client.get("/houmao/agents/agent-a/usage", params={"limit": 1})
    assert response.status_code == 200
    first_page = response.json()
    assert first_page["records"][0]["record_id"] == first.record_id
    assert first_page["next_cursor"]
    assert first_page["has_more"] is False

    end = client.get(
        "/houmao/agents/agent-a/usage", params={"after": first_page["next_cursor"]}
    ).json()
    assert end["records"] == []
    assert end["next_cursor"] == first_page["next_cursor"]

    later = first.model_copy(update={"turn_id": "turn-b", "record_id": "usage-v1:runtime-a:turn-b"})
    ledger.finalize(later)
    next_response = client.get("/houmao/agents/agent-a/usage", params={"after": end["next_cursor"]})
    assert next_response.status_code == 200
    assert [record["turn_id"] for record in next_response.json()["records"]] == ["turn-b"]

    other = UsageStore.from_path(tmp_path / "other" / "records.sqlite3", "other-runtime")
    wrong = client.get(
        "/houmao/agents/agent-a/usage", params={"after": other.read_page().next_cursor}
    )
    assert wrong.status_code == 422

    ledger.path.write_bytes(b"corrupt sqlite storage")
    unreadable = client.get("/houmao/agents/agent-a/usage")
    assert unreadable.status_code == 503
