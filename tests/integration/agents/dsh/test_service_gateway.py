"""Qualify authenticated service observation and dispatch against native DSH ACP."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import time
from typing import Any

import pytest

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_models import (
    GatewayMailNotifierPutV1,
    GatewayPromptControlRequestV1,
)
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime
from houmao.agents.realm_controller.manifest import mutate_session_mailbox_binding
from houmao.agents.realm_controller.owner_admission import reserve_owner_prompt
from houmao.gateway.plugins import PluginDispatchError, PluginEvent
from tests.integration.agents.dsh.conftest import ControlledModelGate
from tests.integration.agents.dsh.test_current_home import _prepare_fixture
from tests.unit.agents.realm_controller.test_gateway_support import _deliver_unread_mailbox_message


def test_gateway_reconnects_to_exact_active_service_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    controlled_model_gate: ControlledModelGate,
) -> None:
    """A signed gateway restart preserves the original request, journal and connection."""

    endpoint, requests = controlled_messages_server
    run, prepare, launch = _prepare_fixture(
        tmp_path,
        monkeypatch,
        dsh_executable,
        endpoint=endpoint,
        surface="manager",
        mode="service",
    )
    root = Path(run["run_dir"])
    try:
        launch.launch_run(root, timeout=45)
        run = launch.load_run(root)
        env = launch.run_environment(run)
        scope = ["agents", "single", "--agent-id", run["identity"]["agent_id"]]
        client = launch.manager_gateway(run)
        service = client.get_service_state()
        assert service.can_accept_prompt_now is True
        assert service.native_session_id and service.service_incarnation
        status = client.status()
        assert status.mode == "service" and status.backend == "dsh_acp"
        assert status.native_surface is None
        assert status.terminal_surface_eligibility == "unknown"
        assert status.capabilities is not None and "send_keys" not in status.capabilities.operations

        controlled_model_gate.armed = True
        result = client.control_prompt(GatewayPromptControlRequestV1(prompt="managed service turn"))
        assert result.operation_id and result.outcome == "queued" and not result.sent
        assert controlled_model_gate.entered.wait(timeout=20)
        native = client.get_service_request(result.operation_id)
        assert native.state == "handed_off"
        assert native.native_session_id == service.native_session_id
        assert native.service_incarnation == service.service_incarnation
        busy = client.get_service_state()
        assert busy.active_request_id == result.operation_id and busy.can_accept_prompt_now is False
        with pytest.raises(GatewayHttpError) as refused:
            client.control_prompt(GatewayPromptControlRequestV1(prompt="overlap must be refused"))
        assert refused.value.status_code == 409

        prepare.manager_root_call([*scope, "gateway", "detach"], env=env)
        attached = prepare.manager_root_call([*scope, "gateway", "attach", "--background"], env=env)
        run["identity"]["gateway_port"] = attached["gateway_port"]
        prepare.write_json(root / "run.json", run)
        client = launch.manager_gateway(run)
        reattached = client.get_service_state()
        assert reattached.service_incarnation == service.service_incarnation
        assert reattached.active_request_id == result.operation_id
        assert client.get_service_request(result.operation_id) == native
        controlled_model_gate.release.set()

        deadline = time.monotonic() + 30
        while native.state != "completed" and time.monotonic() < deadline:
            time.sleep(0.1)
            native = client.get_service_request(result.operation_id)
        assert native.state == "completed" and native.native_turn_id
        assert any(event.kind == "assistant" and event.message for event in native.events)
        usage = next(
            row for row in client.get_usage().records if row.turn_id == result.operation_id
        )
        assert usage.provider_session_id == service.native_session_id
        assert usage.token_usage.total_tokens.value == 16
        assert len(requests) == 1

        requested_run = "ag-ui-native-service"
        path = "/v1/ag-ui/runs"
        payload = json.dumps(
            {
                "threadId": "fixture-native-service",
                "runId": requested_run,
                "messages": [{"id": "user", "role": "user", "content": "second service turn"}],
                "tools": [],
                "context": [],
                "state": {},
                "forwardedProps": {
                    "houmao": {"chatSession": {"mode": "exact", "id": service.native_session_id}}
                },
            }
        ).encode()
        request = client._prepare_request(
            "POST",
            path,
            payload,
            {"Content-Type": "application/json", "Accept": "text/event-stream"},
        )
        response = client._open_request(
            request_obj=request, method="POST", url=client._build_url(path)
        )
        events = [
            json.loads(line[6:])
            for line in response.decode().splitlines()
            if line.startswith("data: ")
        ]
        assert events[-1]["type"] == "RUN_FINISHED"
        assert "native result" in "".join(
            event["delta"] for event in events if event["type"] == "TEXT_MESSAGE_CONTENT"
        )
        assert (
            client.get_service_request(requested_run).native_session_id == service.native_session_id
        )
        assert len(requests) == 2
    finally:
        controlled_model_gate.release.set()
        launch.stop_run(root)


def test_service_plugin_and_periodic_mail_use_the_same_owner_slot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Ordinary wakeups share native readiness, reservation, and request ownership."""

    endpoint, requests = controlled_messages_server
    run, prepare, launch = _prepare_fixture(
        tmp_path, monkeypatch, dsh_executable, endpoint=endpoint, surface="manager", mode="service"
    )
    root = Path(run["run_dir"])
    try:
        launch.launch_run(root, timeout=45)
        run = launch.load_run(root)
        identity = run["identity"]
        env = launch.run_environment(run)
        agent_id = identity["agent_id"]
        manifest_path = Path(identity["manifest_path"])
        prepare.manager_root_call(
            ["agents", "single", "--agent-id", agent_id, "gateway", "detach"], env=env
        )
        address = "native-service@agents.localhost"
        _deliver_unread_mailbox_message(
            tmp_path, recipient_principal_id=agent_id, recipient_address=address
        )
        with sqlite3.connect(tmp_path / "mailbox/index.sqlite") as database:
            registration = database.execute(
                "SELECT registration_id FROM mailbox_registrations WHERE address=? AND status='active'",
                (address,),
            ).fetchone()
        assert registration is not None
        manifest = json.loads(manifest_path.read_text())
        mutate_session_mailbox_binding(
            manifest_path,
            channel="offline",
            expected_revision=manifest["launch_plan"]["mailboxes"]["offline"]["revision"],
            binding=FilesystemMailboxResolvedConfig(
                transport="filesystem",
                principal_id=agent_id,
                address=address,
                filesystem_root=tmp_path / "mailbox",
                bindings_version="controlled-mail-revision",
                agent_id=agent_id,
                binding_id=registration[0],
            ),
            agent_id=agent_id,
            session_id=manifest["runtime"]["session_id"],
        )
        with prepare.command_environment(env):
            runtime = GatewayServiceRuntime(
                gateway_root=manifest_path.parent / "gateway",
                host="127.0.0.1",
                port=identity["gateway_port"],
            )
            runtime.start()
            try:
                before = runtime.get_service_state()
                claim = reserve_owner_prompt(
                    manifest_path, manifest["registry_generation_id"], origin="manager"
                )
                try:
                    with pytest.raises(PluginDispatchError) as blocked:
                        runtime.dispatch_plugin_event(
                            PluginEvent(source_event_id="busy", text="no delayed plugin input"),
                            instance_id="notifications",
                            binding_id="owner-bound",
                            timeout_seconds=20,
                            is_active=lambda: True,
                        )
                    assert blocked.value.status_code == 409
                    assert blocked.value.dispatch_outcome == "not_sent"
                    assert runtime.status().queue_depth == 0 and not requests
                finally:
                    claim.finish("failed", evidence="test_released_before_native_dispatch")

                delivered = runtime.dispatch_plugin_event(
                    PluginEvent(source_event_id="eligible", text="controlled service notification"),
                    instance_id="notifications",
                    binding_id="owner-bound",
                    timeout_seconds=20,
                    is_active=lambda: True,
                )
                assert delivered.source_event_id == "eligible"
                deadline = time.monotonic() + 25
                while runtime.get_service_state().can_accept_prompt_now is not True:
                    assert time.monotonic() < deadline
                    time.sleep(0.1)
                assert len(requests) == 1
                assert "controlled service notification" in json.dumps(requests[0]["messages"])

                runtime.put_mail_notifier(
                    GatewayMailNotifierPutV1(interval_seconds=1), channel="offline"
                )
                while len(requests) < 3:
                    assert time.monotonic() < deadline, "Unchanged unread mail did not repeat"
                    time.sleep(0.1)
                runtime.delete_mail_notifier(channel="offline")
                while runtime.get_service_state().can_accept_prompt_now is not True:
                    assert time.monotonic() < deadline
                    time.sleep(0.1)
                assert all(
                    "Mail channel: offline." in json.dumps(row["messages"]) for row in requests[1:]
                )
                after = runtime.get_service_state()
                assert after.service_incarnation == before.service_incarnation
                assert after.native_session_id == before.native_session_id
                assert runtime.status().queue_depth == 0
            finally:
                runtime.shutdown()
    finally:
        launch.stop_run(root)
