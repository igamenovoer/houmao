"""Cross-component accounting workflows using sanitized exact-client captures.

These tests exercise the shared collector, durable ledger, gateway HTTP route,
and maintained passive-server route together without contacting a provider.
Live provider qualification is recorded separately under ``tmp/usage-qualification``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
import pytest

from houmao.agents.realm_controller.gateway_service import (
    GatewayServiceRuntime,
    create_app as create_gateway_app,
)
from houmao.agents.realm_controller.usage_adapters import UsageAdapter
from houmao.agents.realm_controller.usage_models import UsagePage
from houmao.agents.realm_controller.usage_support import UsageService, persist_terminal_evidence
from houmao.passive_server.app import create_app as create_passive_app
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.service import PassiveServerService
from houmao.server.managed_agents import ManagedHeadlessAuthorityRecord

_CAPTURED_TOKEN_COUNTS = {
    "claude": [(4445, 32), (4502, 31)],
    "codex": [(11613, 40), (11675, 32)],
    "kimi": [(20114, 40), (20242, 24)],
}


def _fixture(provider: str) -> dict[str, Any]:
    """Load one sanitized capture with two completed, resumed client turns."""

    root = Path(__file__).parents[3] / "fixtures" / "agent-usage-records"
    return json.loads(next(root.glob(f"{provider}-*-qwen.json")).read_text(encoding="utf-8"))


def _native_turns(provider: str, fixture: dict[str, Any]) -> list[list[dict[str, Any]]]:
    """Split native records only at their qualified structured turn markers."""

    adapter = UsageAdapter.from_provider(provider, fixture["provider_session_id"])
    turns: list[list[dict[str, Any]]] = [[]]
    starts = 0
    for index, payload in enumerate(fixture["native_records"]):
        observations = adapter.parse(payload, source_ref=f"fixture-{index}")
        if any(item.lifecycle == "started" for item in observations):
            starts += 1
            if starts > 1:
                turns.append([])
        turns[-1].append(payload)
    assert len(turns) == 2
    return turns


def _append(path: Path, payloads: list[dict[str, Any]]) -> None:
    """Append complete provider records at their real JSONL byte boundaries."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(json.dumps(payload) + "\n")


def _manifest(tmp_path: Path, provider: str, *, headless: bool = True) -> Path:
    """Create the runtime-owned identity and isolated provider home."""

    path = tmp_path / "session" / "manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "tool": provider,
                "backend": f"{provider}_headless" if headless else "local_interactive",
                "agent_id": "agent-a",
                "agent_name": "usage-agent",
                "registry_generation_id": "generation-original",
                "runtime": {"session_id": "runtime-a"},
                "backend_state": {"session_id": "identity-1"},
                "launch_plan": {"home_selector": {"home_path": str(tmp_path / "home")}},
            }
        ),
        encoding="utf-8",
    )
    return path


def _source(tmp_path: Path, provider: str) -> Path:
    """Return a session-owned source in the provider's supported home layout."""

    if provider == "claude":
        return tmp_path / "home" / "projects" / "project" / "identity-1.jsonl"
    if provider == "kimi":
        return (
            tmp_path
            / "home"
            / "sessions"
            / "wd-project"
            / "identity-1"
            / "agents"
            / "main"
            / "wire.jsonl"
        )
    return tmp_path / "home" / "sessions" / "rollout.jsonl"


def _gateway_client(service: UsageService) -> TestClient:
    """Expose the production gateway route against the real shared usage service."""

    runtime = GatewayServiceRuntime.__new__(GatewayServiceRuntime)
    runtime.m_usage_service = service
    runtime.m_usage_error = None
    return TestClient(create_gateway_app(runtime=runtime))


def _passive_client(tmp_path: Path, manifest: Path) -> TestClient:
    """Publish a persisted authority without requiring a live execution controller."""

    config = PassiveServerConfig(
        runtime_root=tmp_path / "passive", registry_root=tmp_path / "registry"
    )
    service = PassiveServerService(config=config)
    service.m_headless.m_store.write_authority(
        ManagedHeadlessAuthorityRecord(
            tracked_agent_id="tracked-a",
            backend=json.loads(manifest.read_text())["backend"],
            tool=json.loads(manifest.read_text())["tool"],
            manifest_path=str(manifest),
            session_root=str(manifest.parent),
            tmux_session_name="no-live-controller",
            agent_def_dir=str(tmp_path / "agent-defs"),
            agent_id="agent-a",
            agent_name="usage-agent",
            created_at_utc="2026-11-13T00:00:00Z",
            updated_at_utc="2026-11-13T00:00:00Z",
        )
    )
    return TestClient(create_passive_app(service=service))


def _page(client: TestClient, route: str, after: str | None = None) -> UsagePage:
    """Read one strictly typed public page, retaining the returned end cursor."""

    response = client.get(route, params={"after": after} if after else None)
    assert response.status_code == 200, response.text
    return UsagePage.model_validate(response.json())


@pytest.mark.parametrize("provider", ["claude", "codex", "kimi"])
def test_resumed_headless_captures_have_one_record_per_turn_across_http_surfaces(
    tmp_path: Path, provider: str
) -> None:
    """Resumed native/stdout copies keep stable managed IDs and per-turn counters."""

    fixture = _fixture(provider)
    native_turns = _native_turns(provider, fixture)
    manifest = _manifest(tmp_path, provider)
    service = UsageService.from_manifest(manifest)
    source = _source(tmp_path, provider)
    gateway = _gateway_client(service)
    passive = _passive_client(tmp_path, manifest)
    initial = _page(gateway, "/v1/usage")
    assert initial.records == [] and initial.next_cursor is not None
    cursor = initial.next_cursor
    records = []
    for index in range(2):
        turn_id = f"managed-{index + 1}"
        turn_dir = manifest.parent / "manifest.turn-artifacts" / turn_id
        service.begin_headless_turn(
            turn_id=turn_id, turn_dir=turn_dir, turn_index=index + 1, new_session=index == 0
        )
        _append(source, native_turns[index])
        _append(turn_dir / "stdout.jsonl", fixture["headless_turns"][index])
        persist_terminal_evidence(
            turn_dir,
            returncode=0,
            completed_at_utc=f"2026-11-13T06:0{index}:03Z",
            wall_time_ms=1000.0 + index,
        )
        record = service.finalize_headless_turn(turn_dir, provider_session_id="identity-1")
        assert record is not None
        records.append(record)
        service.collect()
        page = _page(gateway, "/v1/usage", cursor)
        assert page.records == [record]
        assert record.turn_id == turn_id and record.turn_origin == "managed"
        assert record.provider_turn_id is not None
        expected_input, expected_output = _CAPTURED_TOKEN_COUNTS[provider][index]
        assert record.token_usage.input_tokens.value == expected_input
        assert record.token_usage.output_tokens.value == expected_output
        assert record.wall_time_ms.value == 1000.0 + index
        cursor = page.next_cursor
        empty = _page(gateway, "/v1/usage", cursor)
        assert empty.records == [] and empty.next_cursor == cursor
        mirrored = _page(passive, "/houmao/agents/usage-agent/usage")
        assert mirrored.records == records and mirrored.stream_id == initial.stream_id
    restarted = UsageService.from_manifest(manifest)
    restarted.reconcile()
    assert restarted.get_usage().records == records
    assert restarted.get_usage(after=cursor).records == []
    assert len({item.record_id for item in records}) == 2
    gateway.close()
    passive.close()


def test_headless_provider_reset_keeps_stream_and_original_generation(tmp_path: Path) -> None:
    """A new provider session cannot inherit the previous session's counters."""

    fixture = _fixture("codex")
    native_turn = _native_turns("codex", fixture)[0]
    manifest = _manifest(tmp_path, "codex")
    service = UsageService.from_manifest(manifest)
    records = []
    cursor = service.get_usage().next_cursor
    for index, session in enumerate(("identity-1", "identity-reset")):
        if index:
            payload = json.loads(manifest.read_text())
            payload["registry_generation_id"] = "generation-relaunch"
            payload["backend_state"]["session_id"] = None
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            service = UsageService.from_manifest(manifest)
        turn_id = f"reset-{index}"
        turn_dir = manifest.parent / "manifest.turn-artifacts" / turn_id
        service.begin_headless_turn(
            turn_id=turn_id, turn_dir=turn_dir, turn_index=index + 1, new_session=True
        )
        native = json.loads(json.dumps(native_turn).replace("identity-1", session))
        stdout = json.loads(json.dumps(fixture["headless_turns"][0]).replace("identity-1", session))
        _append(tmp_path / "home" / "sessions" / f"{session}.jsonl", native)
        _append(turn_dir / "stdout.jsonl", stdout)
        persist_terminal_evidence(
            turn_dir, returncode=0, completed_at_utc="2026-11-13T06:00:03Z", wall_time_ms=125.0
        )
        record = service.finalize_headless_turn(turn_dir, provider_session_id=session)
        assert record is not None
        records.append(record)
        page = service.get_usage(after=cursor)
        assert page.records == [record]
        assert record.provider_session_id == session
        assert record.token_usage.input_tokens.value == 11613
        assert record.token_usage.output_tokens.value == 40
        cursor = page.next_cursor
    assert records[0].generation_id == "generation-original"
    assert records[1].generation_id == "generation-relaunch"
    service.reconcile()
    assert service.get_usage().records == records


@pytest.mark.parametrize("outcome", ["failed", "interrupted", "completed"])
def test_headless_recorder_outage_recovers_original_terminal_facts(
    tmp_path: Path, outcome: str
) -> None:
    """Terminal sidecars recover once even after the generation changes."""

    manifest = _manifest(tmp_path, "codex")
    service = UsageService.from_manifest(manifest)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "turn-original"
    service.begin_headless_turn(
        turn_id="turn-original", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    initial = service.get_usage()
    assert initial.records == []
    persist_terminal_evidence(
        turn_dir,
        returncode=0 if outcome == "completed" else 130 if outcome == "interrupted" else 7,
        completed_at_utc="2026-11-13T00:00:03Z",
        wall_time_ms=321.5,
        interrupted=outcome == "interrupted",
    )
    payload = json.loads(manifest.read_text())
    payload["registry_generation_id"] = "generation-after-restart"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    restarted = UsageService.from_manifest(manifest)
    restarted.reconcile()
    page = restarted.get_usage(after=initial.next_cursor)
    assert len(page.records) == 1
    record = page.records[0]
    assert record.outcome == outcome
    assert record.generation_id == "generation-original"
    assert record.completed_at_utc == "2026-11-13T00:00:03Z"
    assert record.wall_time_ms.value == 321.5
    assert record.token_usage.input_tokens.value is None
    restarted.reconcile()
    assert restarted.get_usage().records == [record]
    passive = _passive_client(tmp_path, manifest)
    assert _page(passive, "/houmao/agents/tracked-a/usage").records == [record]
    passive.close()


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_tui_attachment_restart_and_pending_managed_association(
    tmp_path: Path, provider: str
) -> None:
    """Earlier native history stays excluded and unverified managed turns wait."""

    fixture = _fixture(provider)
    native_turns = _native_turns(provider, fixture)
    manifest = _manifest(tmp_path, provider, headless=False)
    source = _source(tmp_path, provider)
    _append(source, native_turns[0])
    service = UsageService.from_manifest(manifest)
    service.collect()
    attached = service.get_usage()
    assert attached.records == [] and attached.next_cursor is not None
    service.register_managed_turn(turn_id="managed-resume")
    _append(source, native_turns[1])
    restarted = UsageService.from_manifest(manifest)
    restarted.collect()
    pending = restarted.get_usage(after=attached.next_cursor)
    assert pending.records == []
    assert "managed_native_association_pending" in pending.collection.diagnostics
    adapter = UsageAdapter.from_provider(provider, fixture["provider_session_id"])
    observations = [
        item
        for index, payload in enumerate(fixture["native_records"])
        for item in adapter.parse(payload, source_ref=f"capture-{index}")
    ]
    marker = [item for item in observations if item.lifecycle == "started"][-1]
    assert marker.provider_turn_id is not None
    restarted.note_provider_turn(
        "managed-resume",
        provider_turn_id=marker.provider_turn_id,
        provider_session_id=fixture["provider_session_id"],
    )
    restarted.collect()
    page = restarted.get_usage(after=attached.next_cursor)
    assert len(page.records) == 1
    assert page.records[0].turn_id == "managed-resume"
    assert page.records[0].turn_origin == "managed"
    assert page.records[0].provider_turn_id == marker.provider_turn_id
    restarted.collect()
    assert restarted.get_usage(after=page.next_cursor).records == []


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_direct_tui_turns_survive_source_rotation_and_gateway_restart(
    tmp_path: Path, provider: str
) -> None:
    """A replacement native file replays known requests without adding charges."""

    fixture = _fixture(provider)
    native_turns = _native_turns(provider, fixture)
    manifest = _manifest(tmp_path, provider, headless=False)
    source = _source(tmp_path, provider)
    metadata = (
        {"type": "session_meta", "payload": {"id": "identity-1"}}
        if provider == "codex"
        else {"type": "progress", "sessionId": "identity-1"}
    )
    _append(source, [metadata])
    service = UsageService.from_manifest(manifest)
    service.collect()
    initial = service.get_usage()
    _append(source, native_turns[0])
    service.collect()
    first = service.get_usage(after=initial.next_cursor)
    assert len(first.records) == 1
    assert first.records[0].turn_origin == "native_observed"
    replacement = source.with_suffix(".replacement")
    _append(replacement, fixture["native_records"])
    replacement.replace(source)
    restarted = UsageService.from_manifest(manifest)
    restarted.collect()
    client = _gateway_client(restarted)
    second = _page(client, "/v1/usage", first.next_cursor)
    assert len(second.records) == 1
    assert second.records[0].provider_turn_id != first.records[0].provider_turn_id
    all_records = _page(client, "/v1/usage").records
    assert all_records == [*first.records, *second.records]
    restarted.collect()
    assert _page(client, "/v1/usage", second.next_cursor).records == []
    client.close()


@pytest.mark.parametrize("provider", ["claude", "codex"])
def test_tui_attachment_during_active_turn_marks_observed_usage_partial(
    tmp_path: Path, provider: str
) -> None:
    """An attached collector retains later request evidence without complete coverage."""

    fixture = _fixture(provider)
    native_turn = _native_turns(provider, fixture)[0]
    adapter = UsageAdapter.from_provider(provider, fixture["provider_session_id"])
    boundary = next(
        index + 1
        for index, payload in enumerate(native_turn)
        if any(
            item.lifecycle == "started"
            for item in adapter.parse(payload, source_ref=f"capture-{index}")
        )
    )
    manifest = _manifest(tmp_path, provider, headless=False)
    source = _source(tmp_path, provider)
    _append(source, native_turn[:boundary])
    service = UsageService.from_manifest(manifest)
    service.collect()
    initial = service.get_usage()
    assert initial.records == []
    _append(source, native_turn[boundary:])
    service.collect()
    client = _gateway_client(service)
    page = _page(client, "/v1/usage", initial.next_cursor)
    assert len(page.records) == 1
    record = page.records[0]
    assert record.turn_origin == "native_observed"
    expected_input, expected_output = _CAPTURED_TOKEN_COUNTS[provider][0]
    assert record.token_usage.input_tokens.value == expected_input
    assert record.token_usage.output_tokens.value == expected_output
    assert record.token_usage.input_tokens.availability == "partial"
    client.close()


def test_codex_fork_replay_waits_for_new_native_turn(tmp_path: Path) -> None:
    """Inherited fork accounting cannot become a new native charge through HTTP."""

    fixture = _fixture("codex")
    native_turn = _native_turns("codex", fixture)[0]
    manifest = _manifest(tmp_path, "codex", headless=False)
    source = _source(tmp_path, "codex")
    header = json.loads(json.dumps(native_turn[0]))
    header["payload"]["forked_from_id"] = "parent-session"
    _append(source, [header])
    service = UsageService.from_manifest(manifest)
    service.collect()
    client = _gateway_client(service)
    initial = _page(client, "/v1/usage")
    inherited = [
        payload
        for payload in native_turn
        if payload["type"] == "token_usage_record"
        or payload.get("payload", {}).get("type") == "token_count"
    ]
    _append(source, inherited)
    service.collect()
    replay = _page(client, "/v1/usage", initial.next_cursor)
    assert replay.records == [] and replay.next_cursor == initial.next_cursor
    _append(source, native_turn[1:])
    service.collect()
    completed = _page(client, "/v1/usage", replay.next_cursor)
    assert len(completed.records) == 1
    record = completed.records[0]
    assert record.turn_origin == "native_observed"
    assert record.token_usage.input_tokens.value == _CAPTURED_TOKEN_COUNTS["codex"][0][0]
    assert record.subagent_accounting == "unknown"
    restarted = UsageService.from_manifest(manifest)
    restarted.collect()
    assert restarted.get_usage().records == completed.records
    assert restarted.get_usage(after=completed.next_cursor).records == []
    client.close()


def test_claude_sidechain_parent_copies_do_not_add_charges(tmp_path: Path) -> None:
    """A sidechain copy of parent history preserves one native accounting record."""

    fixture = _fixture("claude")
    native_turn = _native_turns("claude", fixture)[0]
    manifest = _manifest(tmp_path, "claude", headless=False)
    source = _source(tmp_path, "claude")
    sidechain = source.parent / "subagents" / "agent-child.jsonl"
    metadata = {"type": "progress", "sessionId": "identity-1"}
    for path in (source, sidechain):
        _append(path, [metadata])
    service = UsageService.from_manifest(manifest)
    service.collect()
    initial = service.get_usage()
    _append(source, native_turn)
    _append(sidechain, [{**payload, "isSidechain": True} for payload in native_turn])
    service.collect()
    client = _gateway_client(service)
    page = _page(client, "/v1/usage", initial.next_cursor)
    assert len(page.records) == 1
    record = page.records[0]
    assert record.token_usage.input_tokens.value == _CAPTURED_TOKEN_COUNTS["claude"][0][0]
    assert record.token_usage.output_tokens.value == _CAPTURED_TOKEN_COUNTS["claude"][0][1]
    assert record.subagent_accounting == "unknown"
    _append(sidechain, [{**payload, "isSidechain": True} for payload in native_turn])
    restarted = UsageService.from_manifest(manifest)
    restarted.collect()
    assert restarted.get_usage().records == page.records
    assert restarted.get_usage(after=page.next_cursor).records == []
    client.close()
