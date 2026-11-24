"""Qualify Web gateway and mailbox/plugin dispatch against owned controlled hosts."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import importlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from houmao.ag_ui.mapper import AgUiEventMapper
from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import mailboxes_resolved_config_from_payload
from houmao.agents.realm_controller.backends.dsh_web import DshWebSession, DshWebSessionState
from houmao.agents.realm_controller.gateway_access_runtime import save_gateway_deployment
from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataWebV1,
    GatewayMailNotifierPutV1,
    GatewayRequestCreateV1,
)
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    mutate_session_mailbox_binding,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.registry_storage import load_managed_agent_record_by_agent_id
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.agents.realm_controller.models import RelaunchChatSessionSelection
from houmao.gateway.plugins import PluginEvent
from houmao.gateway.deployment import GatewayDeployment
from houmao.passive_server.discovery import DiscoveredAgent, _summary_from_record
from houmao.passive_server.web_observation import AgentWebObserver
from tests.integration.agents.dsh.test_managed_acp import _launch_plan
from tests.integration.agents.dsh.test_gateway_passive import bind_fixture_gateway_owner
from tests.fixtures.gateway_access import (
    FixtureProofAuth,
    enroll_fixture_admin,
    fixture_admin_key,
    gateway_fixture_client,
    self_fixture_auth,
)
from tests.unit.agents.realm_controller.test_gateway_support import _deliver_unread_mailbox_message
from tests.unit.gateway_plugins.test_cccc_plugin import harness, offer


def _runtime(
    root: Path,
    executable: Path,
    endpoint: str,
    monkeypatch: pytest.MonkeyPatch,
    tmux_socket: Path,
    *,
    agent_id: str = "owner1",
    session_name: str = "HOUMAO-web-integration",
    managed_web_skills: bool = False,
) -> tuple[GatewayServiceRuntime, DshWebSession]:
    """Create owned native execution and reconstruct exact controllers without ambient accounts."""

    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(root / "registry"))
    plan, provisional = _launch_plan(root, executable, endpoint)
    if managed_web_skills:
        setup = Path(plan.metadata["dsh"]["setup_path"])
        setup.write_text(json.dumps({**json.loads(setup.read_text()), "managed_web_skills": True}))
    provisional.unlink()
    plan = bind_fixture_gateway_owner(
        plan,
        root=root,
        tmux_socket=tmux_socket,
        agent_id=agent_id,
        generation="web-integration-generation",
    )
    plan = replace(
        plan,
        backend="dsh_web",
        native_surface_kind="web",
        metadata={
            **plan.metadata,
            "managed_web_identity": {
                "agent_id": agent_id,
                "runtime_session_id": "runtime1",
                "generation": "web-integration-generation",
            },
        },
    )
    manifest = root / "runtime1/manifest.json"
    manifest.parent.mkdir()
    definitions = root / "agent-defs"
    definitions.mkdir()
    name = session_name
    backend = DshWebSession.from_launch_plan(
        launch_plan=plan,
        session_manifest_path=manifest,
        role_name="controlled",
        provider_start=True,
        tmux_session_name=name,
    )

    def controller_for(
        selected: DshWebSession, selected_plan=plan, generation: str = "web-integration-generation"
    ) -> RuntimeSessionController:
        """Use the actual semantic controller and its manifest-preserving Web helper."""

        return RuntimeSessionController(
            launch_plan=selected_plan,
            role_name="controlled",
            brain_manifest_path=root / "brain.yaml",
            manifest_path=manifest,
            backend_session=selected,
            agent_def_dir=definitions,
            agent_identity=name,
            agent_id=agent_id,
            tmux_session_name=name,
            registry_generation_id=generation,
        )

    controller = controller_for(backend)
    controller.persist_manifest()
    controller.ensure_gateway_capability()

    def reconstruct(**_kwargs: object) -> RuntimeSessionController:
        """Restore only the exact latest private binding without native lifecycle activation."""

        current = parse_session_manifest_payload(
            load_session_manifest(manifest).payload, source=str(manifest)
        )
        generation = current.registry_generation_id
        assert generation is not None
        current_plan = replace(
            plan,
            metadata={
                **plan.metadata,
                "managed_web_identity": {
                    "agent_id": agent_id,
                    "runtime_session_id": "runtime1",
                    "generation": generation,
                },
            },
            mailboxes=mailboxes_resolved_config_from_payload(
                current.launch_plan.mailboxes.model_dump(mode="json"),
                manifest_path=manifest,
            ),
        )
        restored = DshWebSession.from_launch_plan(
            launch_plan=current_plan,
            session_manifest_path=manifest,
            role_name="controlled",
            state=DshWebSessionState.from_payload(current.backend_state),
            provider_start=False,
        )
        return controller_for(restored, current_plan, generation)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session", reconstruct
    )
    monkeypatch.setattr("houmao.passive_server.web_observation.resume_runtime_session", reconstruct)
    assert controller.gateway_root is not None
    return GatewayServiceRuntime.from_gateway_root(
        gateway_root=controller.gateway_root, host="127.0.0.1", port=43123
    ), backend


def _wait(runtime: GatewayServiceRuntime) -> None:
    """Wait for actual native completion, independently of the insertion acknowledgement."""

    deadline = time.monotonic() + 30
    while (
        runtime.m_direct_prompt_thread is not None
        or not runtime.get_web_state().can_accept_prompt_now
    ):
        if time.monotonic() >= deadline:
            raise AssertionError("Controlled owned Web work did not settle")
        time.sleep(0.02)


def _stop(runtime: GatewayServiceRuntime, backend: DshWebSession) -> None:
    """Release only the fixture's isolated owned host and explicitly isolated tmux envelope."""

    runtime.shutdown()
    backend.configure_stop_force_cleanup(force_cleanup=True)
    assert backend.terminate().status == "ok"


def test_owned_web_gateway_plugin_and_public_requests_share_native_state_without_replay_queue(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Actual semantic controllers confirm native insertion and preserve one browser conversation."""

    assert isolated_tmux.is_absolute()
    endpoint, requests = controlled_messages_server
    runtime, backend = _runtime(tmp_path, dsh_executable, endpoint, monkeypatch, isolated_tmux)
    native_id = backend.state.web_identity["native_session_id"]
    assert runtime.m_manifest_path is not None
    save_gateway_deployment(runtime.m_manifest_path, GatewayDeployment(public_input_enabled=True))
    runtime.start()
    try:
        client = gateway_fixture_client(runtime)
        assert (
            client.get("/v1/control/web/state").json()["identity"]["native_session_id"] == native_id
        )
        assert client.get("/v1/control/tui/state").status_code == 501
        assert client.post("/v1/control/send-keys", json={"sequence": "<[C-c]>"}).status_code == 501
        metadata = runtime.m_attach_contract.backend_metadata
        assert isinstance(metadata, GatewayAttachBackendMetadataWebV1)
        assert metadata.identity.native_session_id == native_id
        assert runtime.m_tui_tracking is None
        assert runtime.status().native_surface_kind == "web"
        result = runtime.dispatch_plugin_event(
            PluginEvent(source_event_id="web-notice", text="controlled Web notification"),
            instance_id="notifications",
            binding_id="owner-bound",
            timeout_seconds=20,
            is_active=lambda: True,
        )
        assert result.source_event_id == "web-notice"
        _wait(runtime)
        accepted = runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt", payload={"prompt": "ordinary Web public request"}
            )
        )
        assert accepted.queue_depth == 0
        _wait(runtime)
        state = runtime.ag_ui_request_state(accepted.request_id)
        assert state is not None and state.state == "completed"
        with sqlite3.connect(runtime.m_paths.queue_path) as connection:
            payload, request_state = connection.execute(
                "SELECT payload_json,state FROM gateway_requests WHERE request_id=?",
                (accepted.request_id,),
            ).fetchone()
        assert request_state == "completed" and "ordinary Web public request" not in payload
        assert len(requests) == 2
        shared = runtime.get_web_state()
        assert shared.identity.native_session_id == native_id
        assert shared.last_turn is not None and shared.last_turn.turn == 2
        assert shared.input_claims
        activity = AgUiEventMapper(
            thread_id="web-thread", run_id="run", parent_run_id=None
        ).map_web_observation(shared, sequence_index=0)
        assert activity[0].model_dump(mode="json")["activity_type"] == "houmao.web.state"
        assert native_id in activity[0].model_dump_json()
        record = load_managed_agent_record_by_agent_id("owner1")
        assert record is not None
        observer = AgentWebObserver(
            agent=DiscoveredAgent(record=record, summary=_summary_from_record(record))
        )
        manifest_before_observation = runtime.m_manifest_path.read_bytes()
        try:
            passive = observer.current_state().web
            assert passive.availability == "available"
            assert passive.identity == shared.identity
            assert passive.origin == shared.origin
            assert observer.history().web.entries
        finally:
            observer.close()
        assert runtime.m_manifest_path.read_bytes() == manifest_before_observation
        assert client.get("/v1/control/web/history").status_code == 200
        handoff = client.post(
            "/v1/public/prompt",
            json={"source_event_id": "web-public", "prompt": "public Web contact"},
        )
        assert handoff.json() == {"disposition": "dispatched", "source_event_id": "web-public"}
        _wait(runtime)
        assert len(requests) == 3
        assert "This request came through the public gateway" in json.dumps(requests[-1])
        with sqlite3.connect(runtime.m_paths.queue_path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM gateway_requests").fetchone()[0] == 1
        public = runtime.status().model_dump_json() + runtime.get_web_history().model_dump_json()
        assert "ordinary Web public request" not in public
        assert "launch_token" not in public and "parsed_surface" not in public
    finally:
        _stop(runtime, backend)


def test_owned_web_exact_relaunch_atomically_hands_registry_and_gateway_to_new_generation(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A live gateway reconnects to the exact retained conversation after explicit host replacement."""

    assert isolated_tmux.is_absolute()
    endpoint, requests = controlled_messages_server
    runtime, backend = _runtime(tmp_path, dsh_executable, endpoint, monkeypatch, isolated_tmux)
    runtime.start()
    controller = runtime.m_adapter._resume_controller()
    selected_backend = controller.backend_session
    assert isinstance(selected_backend, DshWebSession)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._build_provider_start_launch_plan_for_relaunch",
        lambda current: current.launch_plan,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._activate_hook_observation_for_controller",
        lambda **kwargs: kwargs["launch_plan"],
    )
    try:
        client = TestClient(create_app(runtime=runtime), base_url=runtime.owner_connect_url)
        admin_key, admin_signer = fixture_admin_key(tmp_path, "relaunch-admin")
        enroll_fixture_admin(client, admin_key, admin_signer)
        stale_self = self_fixture_auth(runtime)
        assert client.get("/v1/status", auth=stale_self).status_code == 200
        original = dict(backend.state.web_identity)
        runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt", payload={"prompt": "before gateway relaunch"}
            )
        )
        _wait(runtime)
        result = controller.relaunch(
            chat_session=RelaunchChatSessionSelection(
                mode="exact", session_id=original["native_session_id"]
            )
        )
        assert result.status == "ok", result.detail
        assert not controller.operation_warnings
        record = load_managed_agent_record_by_agent_id("owner1")
        assert record is not None
        changed = runtime.get_web_state()
        assert changed.availability == "available"
        assert changed.identity.native_session_id == original["native_session_id"]
        assert changed.identity.generation != original["generation"]
        assert record.generation_id == changed.identity.generation
        assert runtime.status().request_admission == "open"
        current = runtime._current_access()
        assert client.get("/v1/endpoint").json()["target"]["incarnation"] == record.generation_id
        assert client.get("/v1/status", auth=stale_self).status_code == 401
        fresh_self = FixtureProofAuth(
            current.self_store.self_signer_path(current.target.incarnation)
        )
        assert client.get("/v1/status", auth=fresh_self).status_code == 200
        runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt", payload={"prompt": "after gateway relaunch"}
            )
        )
        _wait(runtime)
        assert len(requests) == 2
        assert "before gateway relaunch" in json.dumps(requests[-1]["messages"])
    finally:
        _stop(runtime, selected_backend)


def test_owned_web_cccc_offer_uses_the_same_owner_bound_native_conversation(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The actual optional plugin confirms ordinary Web admission under its owner lifetime."""

    assert isolated_tmux.is_absolute()
    endpoint, requests = controlled_messages_server
    runtime, backend = _runtime(tmp_path, dsh_executable, endpoint, monkeypatch, isolated_tmux)
    native_id = backend.state.web_identity["native_session_id"]
    monkeypatch.syspath_prepend(
        str(Path(__file__).resolve().parents[5] / "packages/houmao-cccc/src")
    )
    implementation = importlib.import_module("houmao_cccc.plugin")
    plugin_root = tmp_path / "cccc-state"
    plugin_root.mkdir()

    async def exercise() -> None:
        """Route one offered service message through the real native Web execution adapter."""

        async with harness(implementation, monkeypatch, plugin_root) as fixture:

            async def dispatch(event: PluginEvent) -> object:
                """Bind delivery to the actual plugin owner and active connection."""

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
                offer(text="controlled CCCC Web notice", remaining_seconds=30.0)
            )
            async with asyncio.timeout(30):
                while not fixture.service.m_outcomes:
                    await asyncio.sleep(0.01)
            assert fixture.service.m_outcomes[0]["outcome"] == "accepted"
            assert fixture.context.events.dispatch.await_count == 1

    runtime.start()
    try:
        asyncio.run(exercise())
        _wait(runtime)
        assert len(requests) == 1
        assert "controlled CCCC Web notice" in json.dumps(requests[0]["messages"])
        assert runtime.status().queue_depth == 0
        assert runtime.get_web_state().identity.native_session_id == native_id
    finally:
        _stop(runtime, backend)


def test_owned_web_mailbox_reminders_repeat_without_executable_gateway_queue_or_transport_change(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unread filesystem mail retains periodic owner-bound native wakeups on the Web surface."""

    assert isolated_tmux.is_absolute()
    endpoint, requests = controlled_messages_server
    runtime, backend = _runtime(tmp_path, dsh_executable, endpoint, monkeypatch, isolated_tmux)
    address = "controlled-web@agents.localhost"
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
        bindings_version="controlled-web-mail-revision",
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
            if time.monotonic() >= deadline:
                raise AssertionError(
                    "Unread mail did not produce repeated controlled Web reminders"
                )
            time.sleep(0.02)
        runtime.delete_mail_notifier(channel="offline")
        _wait(runtime)
        with sqlite3.connect(runtime.m_paths.queue_path) as connection:
            rows = connection.execute(
                "SELECT payload_json,state FROM gateway_requests WHERE request_kind='mail_notifier_prompt'"
            ).fetchall()
        assert len(rows) >= 2
        assert all(
            "prompt" not in payload and "Mail channel" not in payload for payload, _state in rows
        )
        assert all(state in {"observing", "completed"} for _payload, state in rows)
        assert runtime.status().queue_depth == 0
        saved = load_session_manifest(runtime.m_manifest_path).payload
        binding = saved["launch_plan"]["mailboxes"]["offline"]["binding"]
        assert binding["transport"] == "filesystem" and binding["agent_id"] == "owner1"
        assert binding["binding_id"] == registration[0] and binding["address"] == address
        assert saved["launch_plan"]["mailboxes"]["online"]["binding"] is None
        assert all(
            "Mail channel: offline." in json.dumps(request["messages"]) for request in requests
        )
        assert all(registration[0] in json.dumps(request["messages"]) for request in requests)
    finally:
        _stop(runtime, backend)
