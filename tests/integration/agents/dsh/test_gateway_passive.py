"""Qualify DSH semantic integrations with a real isolated ACP execution body."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import fcntl
import importlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any

import pytest

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.realm_controller.backends.dsh_acp import DshAcpSession
from houmao.agents.realm_controller.errors import GatewayError
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime
from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataHeadlessV1,
    GatewayMailNotifierPutV1,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    load_session_manifest,
    mutate_session_mailbox_binding,
    write_session_manifest,
)
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.gateway.plugins import PluginDispatchError, PluginEvent
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.headless import HeadlessAgentService
from houmao.server.managed_agents import (
    ManagedHeadlessActiveTurnRecord,
    ManagedHeadlessAuthorityRecord,
    ManagedHeadlessTurnRecord,
)
from tests.integration.agents.dsh.test_managed_acp import _launch_plan
from tests.unit.gateway_plugins.test_cccc_plugin import harness, offer
from tests.unit.agents.realm_controller.test_gateway_support import _deliver_unread_mailbox_message


def _gateway_runtime(
    root: Path, executable: Path, endpoint: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[GatewayServiceRuntime, DshAcpSession]:
    """Bind real native execution to the ordinary gateway using synthetic credentials."""

    plan, manifest = _launch_plan(root, executable, endpoint)
    plan = replace(plan, metadata={**plan.metadata, "headless_output_format": "dsh-acp"})
    definitions = root / "agent-defs"
    definitions.mkdir()
    name = "HOUMAO-dsh-integration"
    manifest.unlink()
    manifest = root / "runtime1/manifest.json"
    manifest.parent.mkdir()
    write_session_manifest(
        manifest,
        build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=plan,
                role_name="controlled",
                brain_manifest_path=root / "brain.yaml",
                backend_state={},
                agent_name=name,
                agent_id="owner1",
                tmux_session_name=name,
                session_id="runtime1",
                registry_generation_id="native-integration-generation",
                agent_def_dir=definitions,
            )
        ),
    )
    backend = DshAcpSession(
        launch_plan=plan,
        role_name="controlled",
        session_manifest_path=manifest,
        tmux_session_name=name,
    )
    controller = RuntimeSessionController(
        launch_plan=plan,
        role_name="controlled",
        brain_manifest_path=root / "brain.yaml",
        manifest_path=manifest,
        backend_session=backend,
        agent_def_dir=definitions,
        agent_identity=name,
        agent_id="owner1",
        tmux_session_name=name,
        registry_generation_id="native-integration-generation",
    )
    controller.persist_manifest(refresh_registry=False)
    controller.ensure_gateway_capability()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_kwargs: controller,
    )
    assert controller.gateway_root is not None
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=controller.gateway_root, host="127.0.0.1", port=43123
    )
    return runtime, backend


def _wait_for_completion(runtime: GatewayServiceRuntime) -> None:
    """Wait only for this controlled gateway turn to settle."""

    deadline = time.monotonic() + 30
    while runtime.m_direct_prompt_thread is not None:
        if time.monotonic() >= deadline:
            raise AssertionError("Controlled DSH turn did not settle")
        time.sleep(0.02)


def test_native_dsh_gateway_continues_exact_session_and_keeps_debug_frames(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An idle envelope accepts semantic delivery without a persistent native worker."""

    assert isolated_tmux.is_absolute()
    endpoint, requests = controlled_messages_server
    runtime, backend = _gateway_runtime(tmp_path, dsh_executable, endpoint, monkeypatch)
    runtime.start()
    try:
        assert runtime.status().managed_agent_connectivity == "connected"
        metadata = runtime.m_attach_contract.backend_metadata
        assert isinstance(metadata, GatewayAttachBackendMetadataHeadlessV1)
        assert metadata.native_capabilities is not None
        assert "exact_resume" in metadata.native_capabilities.supported_operations
        assert "raw_keys" in metadata.native_capabilities.unsupported_operations
        assert metadata.native_capabilities.resource_activation == "startup-only"
        assert metadata.native_capabilities.accounting_source == "dsh-journal-v4"
        with pytest.raises(GatewayError, match="unsupported"):
            runtime.m_adapter.send_control_input(sequence="C-c")
        with (backend._plan.home_path / "houmao-invocation.lock").open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            assert runtime.status().terminal_surface_eligibility == "not_ready"
            with pytest.raises(PluginDispatchError) as refusal:
                runtime.dispatch_plugin_event(
                    PluginEvent(source_event_id="busy", text="must not enter native inbox"),
                    instance_id="notifications",
                    binding_id="owner-bound",
                    timeout_seconds=20,
                    is_active=lambda: True,
                )
            assert refusal.value.status_code == 409
            assert refusal.value.dispatch_outcome == "not_sent"
            assert requests == []
        for index in (1, 2):
            result = runtime.dispatch_plugin_event(
                PluginEvent(
                    source_event_id=f"event-{index}", text=f"controlled notification {index}"
                ),
                instance_id="notifications",
                binding_id="owner-bound",
                timeout_seconds=20,
                is_active=lambda: True,
            )
            assert result.source_event_id == f"event-{index}"
            _wait_for_completion(runtime)
            assert runtime.status().queue_depth == 0
            if index == 1:
                native_id = backend.state.session_id
            else:
                assert backend.state.session_id == native_id
        assert len(requests) == 2
        assert "controlled notification 1" in json.dumps(requests[1]["messages"])
        for directory in backend._turn_artifacts_root.iterdir():
            raw = [
                json.loads(line)
                for line in (directory / "provider-stdout.jsonl").read_text().splitlines()
            ]
            assert any(frame.get("jsonrpc") == "2.0" for frame in raw)
            assert (directory / "canonical-events.jsonl").is_file()
        assert runtime.m_manifest_path is not None
        authority = ManagedHeadlessAuthorityRecord(
            tracked_agent_id="tracked-native-dsh",
            backend="dsh_acp",
            tool="dsh",
            manifest_path=str(runtime.m_manifest_path),
            session_root=str(runtime.m_manifest_path.parent),
            tmux_session_name=backend.state.tmux_session_name,
            agent_def_dir=str(tmp_path / "agent-defs"),
            agent_name="HOUMAO-dsh-integration",
            agent_id="owner1",
            created_at_utc="2026-11-16T00:00:00+00:00",
            updated_at_utc="2026-11-16T00:00:00+00:00",
        )
        passive = HeadlessAgentService(
            PassiveServerConfig(
                runtime_root=tmp_path / "passive", registry_root=tmp_path / "registry"
            )
        )
        turn_directory = next(backend._turn_artifacts_root.iterdir())
        common = {
            "tracked_agent_id": authority.tracked_agent_id,
            "turn_id": turn_directory.name,
            "turn_index": 1,
            "turn_artifact_dir": str(turn_directory),
            "started_at_utc": "2026-11-16T00:00:00+00:00",
            "tmux_session_name": authority.tmux_session_name,
        }
        passive.m_store.write_authority(authority)
        passive.m_store.write_turn_record(ManagedHeadlessTurnRecord(**common))
        passive.m_store.write_active_turn(ManagedHeadlessActiveTurnRecord(**common))
        monkeypatch.setattr(
            "houmao.passive_server.headless.resume_runtime_session",
            lambda **_kwargs: runtime.m_adapter._resume_controller(),
        )
        passive.start()
        try:
            status = passive.turn_status(authority.tracked_agent_id, turn_directory.name)
            assert status.status == "completed"
            assert (
                passive.m_store.read_active_turn(tracked_agent_id=authority.tracked_agent_id)
                is None
            )
            events = passive.turn_events(authority.tracked_agent_id, turn_directory.name)
            assert any(event.kind == "assistant" for event in events.entries)
            raw = passive.turn_artifact_text(
                authority.tracked_agent_id, turn_directory.name, "stdout"
            )
            assert any(json.loads(line).get("jsonrpc") == "2.0" for line in raw.splitlines())
            page = passive.get_usage(authority.tracked_agent_id)
            assert len(page.records) == 2
            assert len(requests) == 2
            accepted = passive.submit_turn(
                authority.tracked_agent_id, "explicit passive continuation"
            )
            assert not isinstance(accepted, tuple)
            handle = passive._require_handle(authority.tracked_agent_id)
            assert handle is not None and handle.turn_worker is not None
            handle.turn_worker.join(30)
            assert not handle.turn_worker.is_alive()
            assert (
                passive.turn_status(authority.tracked_agent_id, accepted.turn_id).status
                == "completed"
            )
            assert len(requests) == 3
            stored = load_session_manifest(runtime.m_manifest_path).payload
            assert stored["backend_state"]["session_id"] == native_id
            assert stored["headless"]["turn_index"] == 3
        finally:
            passive.stop()
    finally:
        runtime.shutdown()
        backend.configure_stop_force_cleanup(force_cleanup=True)
        backend.terminate()


def test_cccc_owner_bound_offer_reaches_the_same_native_dsh_agent(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real CCCC plugin uses ordinary native admission without changing agent identity."""

    assert isolated_tmux.is_absolute()
    endpoint, requests = controlled_messages_server
    runtime, backend = _gateway_runtime(tmp_path, dsh_executable, endpoint, monkeypatch)
    source = Path(__file__).resolve().parents[4] / "packages/houmao-cccc/src"
    monkeypatch.syspath_prepend(str(source))
    implementation = importlib.import_module("houmao_cccc.plugin")
    plugin_root = tmp_path / "cccc-state"
    plugin_root.mkdir()

    async def exercise() -> None:
        """Pass the plugin's admitted event through the actual gateway dispatch port."""

        async with harness(implementation, monkeypatch, plugin_root) as fixture:

            async def dispatch(event: PluginEvent) -> object:
                """Use the live owner's identity and this connection's liveness fence."""

                assert fixture.context.owner.agent_id == "owner1"
                assert fixture.context.owner.runtime_session_id == "runtime1"
                return await asyncio.to_thread(
                    runtime.dispatch_plugin_event,
                    event,
                    instance_id=fixture.context.instance_id,
                    binding_id=fixture.context.binding_id,
                    timeout_seconds=20,
                    is_active=lambda: fixture.plugin.m_phase == "connected",
                )

            fixture.context.events.dispatch.side_effect = dispatch
            await fixture.service.m_offers.put(
                offer(text="controlled CCCC notification", remaining_seconds=30.0)
            )
            async with asyncio.timeout(30):
                while not fixture.service.m_outcomes:
                    await asyncio.sleep(0.01)
            assert fixture.service.m_outcomes[0]["outcome"] == "accepted"
            assert fixture.context.events.dispatch.await_count == 1
            reference = fixture.context.events.dispatch.call_args.args[0].metadata["event_ref"]
            assert fixture.plugin._references().decode(reference, "event") == {"event_id": "event1"}

    runtime.start()
    try:
        asyncio.run(exercise())
        _wait_for_completion(runtime)
        assert len(requests) == 1
        assert "controlled CCCC notification" in json.dumps(requests[0]["messages"])
        assert runtime.status().queue_depth == 0
        stored = json.loads(runtime.m_manifest_path.read_text())
        assert stored["agent_id"] == "owner1"
        assert stored["runtime"]["session_id"] == "runtime1"
        assert stored["backend_state"]["session_id"] == backend.state.session_id
    finally:
        runtime.shutdown()
        backend.configure_stop_force_cleanup(force_cleanup=True)
        backend.terminate()


def test_native_dsh_mailbox_reminders_repeat_without_changing_mail_transport(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unchanged unread filesystem mail keeps periodic semantic wakeups on one DSH session."""

    assert isolated_tmux.is_absolute()
    endpoint, requests = controlled_messages_server
    runtime, backend = _gateway_runtime(tmp_path, dsh_executable, endpoint, monkeypatch)
    address = "controlled-dsh@agents.localhost"
    _deliver_unread_mailbox_message(
        tmp_path, recipient_principal_id="owner1", recipient_address=address
    )
    with sqlite3.connect(tmp_path / "mailbox/index.sqlite") as connection:
        registration = connection.execute(
            "SELECT registration_id FROM mailbox_registrations WHERE address=? AND status='active'",
            (address,),
        ).fetchone()
    assert registration is not None
    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="owner1",
        address=address,
        filesystem_root=tmp_path / "mailbox",
        bindings_version="controlled-mail-revision",
        agent_id="owner1",
        binding_id=registration[0],
    )
    assert runtime.m_manifest_path is not None
    current = load_session_manifest(runtime.m_manifest_path).payload
    mutate_session_mailbox_binding(
        runtime.m_manifest_path,
        channel="offline",
        expected_revision=current["launch_plan"]["mailboxes"]["offline"]["revision"],
        binding=mailbox,
        agent_id="owner1",
        session_id="runtime1",
    )
    runtime.start()
    try:
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1), channel="offline")
        deadline = time.monotonic() + 30
        while len(requests) < 2:
            if backend.m_last_run_result is not None and backend.m_last_run_result.returncode != 0:
                raise AssertionError(backend.m_last_run_result.stderr)
            if time.monotonic() >= deadline:
                raise AssertionError("Unchanged unread mail did not produce a second DSH reminder")
            time.sleep(0.02)
        runtime.delete_mail_notifier(channel="offline")
        while runtime.status().active_execution != "idle":
            if time.monotonic() >= deadline:
                raise AssertionError("Native DSH mailbox notification did not settle")
            time.sleep(0.02)
        assert runtime.status().queue_depth == 0
        assert backend.state.session_id is not None
        saved = json.loads(runtime.m_manifest_path.read_text())
        binding = saved["launch_plan"]["mailboxes"]["offline"]["binding"]
        assert binding["transport"] == "filesystem"
        assert binding["agent_id"] == "owner1"
        assert binding["address"] == address
        assert saved["launch_plan"]["mailboxes"]["online"]["binding"] is None
        assert all(
            "Mail channel: offline." in json.dumps(request["messages"]) for request in requests
        )
        assert all(registration[0] in json.dumps(request["messages"]) for request in requests)
    finally:
        runtime.shutdown()
        backend.configure_stop_force_cleanup(force_cleanup=True)
        backend.terminate()
