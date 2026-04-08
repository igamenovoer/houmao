from __future__ import annotations

import click
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import houmao.srv_ctrl.commands.managed_agents as managed_agents_module
from houmao.agents.realm_controller.backends.headless_output import (
    CanonicalHeadlessEvent,
    canonical_headless_event_artifact_path,
)
from houmao.agents.realm_controller.backends.headless_base import HeadlessInteractiveSession
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputResultV1,
    GatewayMailActionResponseV1,
    GatewayMailNotifierStatusV1,
    GatewayMailStateResponseV1,
    GatewayMailStatusV1,
    GatewayMailboxMessageV1,
    GatewayMailboxParticipantV1,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionControlResult,
)
from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.realm_controller import runtime as runtime_module
from houmao.mailbox.managed import ManagedMailboxOperationError
from houmao.server.models import (
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayPromptControlResponse,
    HoumaoManagedAgentHeadlessDetailView,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
    HoumaoStabilityMetadata,
    HoumaoTerminalSnapshotHistoryEntry,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedDiagnostics,
    HoumaoTrackedLastTurn,
    HoumaoTrackedSessionIdentity,
    HoumaoTrackedSurface,
    HoumaoTrackedTurn,
)
from houmao.srv_ctrl.commands.managed_agents import (
    ManagedAgentTarget,
    attach_gateway,
    detach_gateway,
    gateway_mail_notifier_disable,
    gateway_mail_notifier_enable,
    gateway_mail_notifier_status,
    gateway_prompt,
    gateway_send_keys,
    gateway_tui_history,
    gateway_tui_note_prompt,
    gateway_tui_state,
    interrupt_managed_agent,
    list_managed_agents,
    mail_send,
    mail_mark_read,
    mail_resolve_live,
    mail_status,
    mailbox_status,
    managed_agent_detail_payload,
    managed_agent_state_payload,
    prompt_managed_agent,
    register_mailbox_binding,
    relaunch_managed_agent,
    resolve_managed_agent_mail_target,
    resolve_managed_agent_target,
    submit_headless_turn,
    unregister_mailbox_binding,
)
from houmao.srv_ctrl.commands import runtime_artifacts as runtime_artifacts_module


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
        "houmao.srv_ctrl.commands.managed_agents._resolve_local_managed_agent_record_with_miss_context",
        lambda **kwargs: (record, None),
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
        "houmao.srv_ctrl.commands.managed_agents._resolve_local_managed_agent_record_with_miss_context",
        lambda **kwargs: (None, None),
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


def test_resolve_managed_agent_target_rejects_prefixed_agent_name_selector() -> None:
    with pytest.raises(click.ClickException, match="raw creation-time name"):
        resolve_managed_agent_target(agent_id=None, agent_name="HOUMAO-gpu", port=None)


def test_resolve_managed_agent_mail_target_uses_current_session_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = ManagedAgentTarget(
        mode="local",
        agent_ref="current",
        identity=_managed_identity(transport="tui"),
        controller=SimpleNamespace(),
    )
    monkeypatch.setattr(
        managed_agents_module,
        "_gateway_command_helpers",
        lambda: SimpleNamespace(
            _try_current_tmux_session_name=lambda: "HOUMAO-gpu",
            _resolve_gateway_current_session_target=lambda session_name: (
                expected if session_name == "HOUMAO-gpu" else None
            ),
        ),
    )

    target = resolve_managed_agent_mail_target(agent_id=None, agent_name=None, port=None)

    assert target is expected


def test_resolve_managed_agent_mail_target_prefers_explicit_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = ManagedAgentTarget(
        mode="local",
        agent_ref="gpu",
        identity=_managed_identity(transport="headless"),
        controller=SimpleNamespace(),
    )
    monkeypatch.setattr(
        managed_agents_module,
        "resolve_managed_agent_target",
        lambda **kwargs: expected,
    )

    target = resolve_managed_agent_mail_target(agent_id=None, agent_name="gpu", port=None)

    assert target is expected


def test_resolve_managed_agent_mail_target_fails_outside_tmux_without_selectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        managed_agents_module,
        "_gateway_command_helpers",
        lambda: SimpleNamespace(_try_current_tmux_session_name=lambda: None),
    )

    with pytest.raises(click.ClickException, match="run inside the target tmux session"):
        resolve_managed_agent_mail_target(agent_id=None, agent_name=None, port=None)


def test_local_registry_resolution_does_not_fall_back_to_tmux_session_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = SimpleNamespace(
        terminal=SimpleNamespace(session_name="gpu-session"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_live_agent_records_by_name",
        lambda _agent_name: (),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._list_registry_records",
        lambda: [record],
    )

    assert (
        managed_agents_module._resolve_local_managed_agent_record(
            agent_id=None,
            agent_name="gpu-session",
        )
        is None
    )


def test_resolve_managed_agent_target_reports_local_name_miss_before_default_pair_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_live_agent_records_by_name",
        lambda _agent_name: (),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._list_registry_records",
        lambda: [],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: (_ for _ in ()).throw(
            click.ClickException(
                "Failed to reach a Houmao pair authority at http://127.0.0.1:9889: "
                "connection refused"
            )
        ),
    )

    with pytest.raises(click.ClickException) as exc_info:
        resolve_managed_agent_target(agent_id=None, agent_name="agent-test", port=None)

    message = str(exc_info.value)
    assert "No local managed agent matched friendly name `agent-test`." in message
    assert "Fallback lookup through the default pair authority also failed:" in message
    assert (
        "Failed to reach a Houmao pair authority at http://127.0.0.1:9889: connection refused"
    ) in message
    assert (
        "Retry with `houmao-mgr agents list`, the correct friendly managed-agent name, "
        "or `--agent-id <id>`."
    ) in message


def test_local_headless_turn_event_loader_prefers_canonical_artifact(tmp_path: Path) -> None:
    turn_dir = tmp_path / "turn-0001"
    turn_dir.mkdir(parents=True)
    stdout_path = turn_dir / "stdout.jsonl"
    stdout_path.write_text(
        '{"type":"assistant","message":"raw stdout should not win","session_id":"sess-local"}\n',
        encoding="utf-8",
    )
    canonical_path = canonical_headless_event_artifact_path(turn_dir=turn_dir)
    canonical_path.write_text(
        json.dumps(
            CanonicalHeadlessEvent(
                kind="assistant",
                message="canonical local event wins",
                turn_index=1,
                provider="claude",
                provider_event_type="assistant.text",
                session_id="sess-local",
                data={"text": "canonical local event wins"},
            ).to_artifact_record(),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    snapshot = managed_agents_module._LocalHeadlessTurnSnapshot(
        turn_id="turn-0001",
        turn_index=1,
        status="completed",
        started_at_utc="2026-03-20T09:01:00+00:00",
        completed_at_utc="2026-03-20T09:02:00+00:00",
        completion_source="process_exit",
        stdout_path=stdout_path,
        stderr_path=None,
        status_path=None,
        returncode=0,
        history_summary="turn-0001 completed",
        error=None,
    )

    events = managed_agents_module._load_turn_events(snapshot, provider="claude")

    assert [event.kind for event in events] == ["assistant"]
    assert events[0].message == "canonical local event wins"


def test_resolve_managed_agent_target_reports_exact_tmux_alias_hint_on_local_name_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alias_record = SimpleNamespace(
        agent_name="gpu",
        agent_id="agent-1234",
        terminal=SimpleNamespace(session_name="agent-test"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_live_agent_records_by_name",
        lambda _agent_name: (),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._list_registry_records",
        lambda: [alias_record],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: (_ for _ in ()).throw(
            click.ClickException(
                "Failed to reach a Houmao pair authority at http://127.0.0.1:9889: "
                "connection refused"
            )
        ),
    )

    with pytest.raises(click.ClickException) as exc_info:
        resolve_managed_agent_target(agent_id=None, agent_name="agent-test", port=None)

    message = str(exc_info.value)
    assert "No local managed agent matched friendly name `agent-test`." in message
    assert "`--agent-name` expects the published friendly managed-agent name." in message
    assert (
        "`agent-test` matches the live local tmux/session alias for agent_name `gpu` "
        "(agent_id `agent-1234`)."
    ) in message
    assert (
        "Retry with `--agent-name gpu`, `--agent-id agent-1234`, "
        "or inspect `houmao-mgr agents list`."
    ) in message


def test_resolve_managed_agent_target_omits_alias_hint_when_alias_match_is_not_unique(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_record = SimpleNamespace(
        agent_name="gpu-a",
        agent_id="agent-a",
        terminal=SimpleNamespace(session_name="agent-test"),
    )
    second_record = SimpleNamespace(
        agent_name="gpu-b",
        agent_id="agent-b",
        terminal=SimpleNamespace(session_name="agent-test"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_live_agent_records_by_name",
        lambda _agent_name: (),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._list_registry_records",
        lambda: [first_record, second_record],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: (_ for _ in ()).throw(
            click.ClickException(
                "Failed to reach a Houmao pair authority at http://127.0.0.1:9889: "
                "connection refused"
            )
        ),
    )

    with pytest.raises(click.ClickException) as exc_info:
        resolve_managed_agent_target(agent_id=None, agent_name="agent-test", port=None)

    message = str(exc_info.value)
    assert "No local managed agent matched friendly name `agent-test`." in message
    assert "tmux/session alias" not in message
    assert (
        "Retry with `houmao-mgr agents list`, the correct friendly managed-agent name, "
        "or `--agent-id <id>`."
    ) in message


def test_resolve_managed_agent_target_preserves_agent_id_fallback_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_live_agent_record_by_agent_id",
        lambda _agent_id: None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: (_ for _ in ()).throw(
            click.ClickException("Failed to reach a Houmao pair authority at http://127.0.0.1:9889")
        ),
    )

    with pytest.raises(click.ClickException) as exc_info:
        resolve_managed_agent_target(agent_id="agent-1234", agent_name=None, port=None)

    message = str(exc_info.value)
    assert message == "Failed to reach a Houmao pair authority at http://127.0.0.1:9889"
    assert "No local managed agent matched friendly name" not in message


def test_resolve_managed_agent_target_preserves_local_name_ambiguity_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_record = SimpleNamespace(
        agent_name="gpu",
        agent_id="agent-a",
        terminal=SimpleNamespace(session_name="gpu-a"),
    )
    second_record = SimpleNamespace(
        agent_name="gpu",
        agent_id="agent-b",
        terminal=SimpleNamespace(session_name="gpu-b"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resolve_live_agent_records_by_name",
        lambda _agent_name: (first_record, second_record),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("server fallback should not run")),
    )

    with pytest.raises(click.ClickException) as exc_info:
        resolve_managed_agent_target(agent_id=None, agent_name="gpu", port=None)

    message = str(exc_info.value)
    assert "Local managed-agent resolution is ambiguous for --agent-name `gpu`" in message
    assert "Retry with `--agent-id <id>`." in message


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


def test_late_mailbox_commands_reject_server_backed_targets() -> None:
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="gpu",
        identity=_managed_identity(),
        client=SimpleNamespace(),
    )

    with pytest.raises(click.ClickException, match="server-backed"):
        mailbox_status(target)
    with pytest.raises(click.ClickException, match="server-backed"):
        register_mailbox_binding(
            target,
            mailbox_root=None,
            principal_id=None,
            address=None,
            mode="safe",
        )
    with pytest.raises(click.ClickException, match="server-backed"):
        unregister_mailbox_binding(target, mode="deactivate")


def test_register_mailbox_binding_converts_runtime_errors_to_click() -> None:
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="local",
        identity=_managed_identity(transport="tui"),
        controller=SimpleNamespace(
            register_filesystem_mailbox=lambda **kwargs: (_ for _ in ()).throw(
                SessionManifestError("expected mailbox failure")
            )
        ),
    )

    with pytest.raises(click.ClickException, match="expected mailbox failure"):
        register_mailbox_binding(
            target,
            mailbox_root=None,
            principal_id=None,
            address=None,
            mode="safe",
        )


def test_register_mailbox_binding_converts_mailbox_operation_errors_to_click() -> None:
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="local",
        identity=_managed_identity(transport="tui"),
        controller=SimpleNamespace(
            register_filesystem_mailbox=lambda **kwargs: (_ for _ in ()).throw(
                ManagedMailboxOperationError("expected overwrite failure")
            )
        ),
    )

    with pytest.raises(click.ClickException, match="expected overwrite failure"):
        register_mailbox_binding(
            target,
            mailbox_root=None,
            principal_id=None,
            address=None,
            mode="safe",
        )


def test_register_mailbox_binding_forwards_confirmation_callback() -> None:
    observed: dict[str, object] = {}

    def _register_filesystem_mailbox(**kwargs: object) -> SimpleNamespace:
        observed.update(kwargs)
        return SimpleNamespace(
            mailbox=SimpleNamespace(
                transport="filesystem",
                principal_id="HOUMAO-alpha",
                address="HOUMAO-alpha@agents.localhost",
                filesystem_root=Path("/tmp/mailbox-root"),
                bindings_version="2026-03-30T00:00:00Z",
            ),
            activation_state="active",
            shared_lifecycle_result={"ok": True, "mode": "force"},
        )

    target = ManagedAgentTarget(
        mode="local",
        agent_ref="local",
        identity=_managed_identity(transport="tui"),
        controller=SimpleNamespace(
            agent_identity="alpha",
            agent_id="agent-123",
            register_filesystem_mailbox=_register_filesystem_mailbox,
        ),
    )
    confirm_calls: list[str] = []

    def _confirm(prompt: str) -> bool:
        confirm_calls.append(prompt)
        return True

    payload = register_mailbox_binding(
        target,
        mailbox_root=None,
        principal_id=None,
        address=None,
        mode="safe",
        confirm_destructive_replace=_confirm,
    )

    assert observed["confirm_destructive_replace"] is _confirm
    assert payload["activation_state"] == "active"
    assert payload["shared_registration"] == {"ok": True, "mode": "force"}
    assert confirm_calls == []


def test_mail_status_uses_live_mailbox_ready_path_for_joined_session() -> None:
    controller = SimpleNamespace(
        launch_plan=SimpleNamespace(mailbox=object()),
        tmux_session_name="test-agent-join",
    )
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="local",
        identity=_managed_identity(transport="tui"),
        controller=controller,
    )

    original = managed_agents_module._local_manager_mail_status
    managed_agents_module._local_manager_mail_status = lambda _controller: GatewayMailStatusV1(
        transport="filesystem",
        principal_id="HOUMAO-alpha",
        address="HOUMAO-alpha@agents.localhost",
        bindings_version="2026-03-27T00:00:00Z",
    )
    try:
        payload = mail_status(target)
    finally:
        managed_agents_module._local_manager_mail_status = original

    assert payload == {
        "schema_version": 1,
        "operation": "status",
        "authoritative": True,
        "status": "verified",
        "execution_path": "manager_direct",
        "transport": "filesystem",
        "principal_id": "HOUMAO-alpha",
        "address": "HOUMAO-alpha@agents.localhost",
        "bindings_version": "2026-03-27T00:00:00Z",
    }


def test_mail_send_local_tui_without_gateway_returns_submission_only_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="local",
        identity=_managed_identity(transport="tui"),
        controller=SimpleNamespace(),
    )
    expected = {
        "schema_version": 1,
        "operation": "send",
        "authoritative": False,
        "status": "submitted",
        "execution_path": "tui_submission",
        "request_id": "mailreq-1",
    }

    monkeypatch.setattr(
        managed_agents_module,
        "_live_gateway_client_for_controller",
        lambda _controller: None,
    )
    monkeypatch.setattr(
        managed_agents_module,
        "_run_local_mail_prompt",
        lambda **kwargs: expected,
    )

    payload = mail_send(
        target,
        to_recipients=["alpha@agents.localhost"],
        cc_recipients=[],
        subject="hello",
        body_content="world",
        attachments=[],
    )

    assert payload == expected


def test_mail_send_local_headless_uses_verified_manager_direct_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="local",
        identity=_managed_identity(transport="headless"),
        controller=SimpleNamespace(),
    )
    response = GatewayMailActionResponseV1(
        operation="send",
        transport="filesystem",
        principal_id="HOUMAO-alpha",
        address="HOUMAO-alpha@agents.localhost",
        message=GatewayMailboxMessageV1(
            message_ref="filesystem:msg-1",
            thread_ref="filesystem:msg-1",
            created_at_utc="2026-03-29T15:00:00Z",
            subject="hello",
            sender=GatewayMailboxParticipantV1(address="HOUMAO-alpha@agents.localhost"),
            to=[GatewayMailboxParticipantV1(address="beta@agents.localhost")],
        ),
    )
    monkeypatch.setattr(
        managed_agents_module,
        "_local_manager_mail_send",
        lambda controller, **kwargs: response,
    )

    payload = mail_send(
        target,
        to_recipients=["beta@agents.localhost"],
        cc_recipients=[],
        subject="hello",
        body_content="world",
        attachments=[],
    )

    assert payload["authoritative"] is True
    assert payload["status"] == "verified"
    assert payload["execution_path"] == "manager_direct"
    assert payload["message"]["message_ref"] == "filesystem:msg-1"


def test_mail_mark_read_local_headless_uses_verified_manager_direct_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="local",
        identity=_managed_identity(transport="headless"),
        controller=SimpleNamespace(),
    )
    response = GatewayMailStateResponseV1(
        transport="filesystem",
        principal_id="HOUMAO-alpha",
        address="HOUMAO-alpha@agents.localhost",
        message_ref="filesystem:msg-1",
        read=True,
    )
    monkeypatch.setattr(
        managed_agents_module,
        "_local_manager_mail_mark_read",
        lambda controller, **kwargs: response,
    )

    payload = mail_mark_read(target, message_ref="filesystem:msg-1")

    assert payload["authoritative"] is True
    assert payload["status"] == "verified"
    assert payload["execution_path"] == "manager_direct"
    assert payload["read"] is True


def test_mail_mark_read_local_tui_without_gateway_returns_submission_only_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="local",
        identity=_managed_identity(transport="tui"),
        controller=SimpleNamespace(),
    )
    expected = {
        "schema_version": 1,
        "operation": "mark-read",
        "authoritative": False,
        "status": "submitted",
        "execution_path": "tui_submission",
        "request_id": "mailreq-3",
    }
    monkeypatch.setattr(
        managed_agents_module,
        "_live_gateway_client_for_controller",
        lambda _controller: None,
    )
    monkeypatch.setattr(
        managed_agents_module,
        "_run_local_mail_prompt",
        lambda **kwargs: expected,
    )

    payload = mail_mark_read(target, message_ref="filesystem:msg-1")

    assert payload == expected


def test_mail_resolve_live_local_returns_normalized_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resolution = SimpleNamespace(
        gateway=None,
        payload=lambda: {
            "source": "manifest_binding",
            "transport": "filesystem",
            "principal_id": "HOUMAO-alpha",
            "address": "HOUMAO-alpha@agents.localhost",
            "bindings_version": "2026-03-29T15:00:00Z",
            "mailbox": {
                "transport": "filesystem",
                "filesystem": {
                    "root": "/tmp/mailbox",
                },
            },
            "gateway": None,
        },
    )
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="local",
        identity=_managed_identity(transport="tui"),
        controller=SimpleNamespace(
            launch_plan=SimpleNamespace(mailbox=object()),
            manifest_path=tmp_path / "manifest.json",
        ),
    )
    monkeypatch.setattr(
        managed_agents_module,
        "resolve_live_mailbox_binding_from_manifest_path",
        lambda **kwargs: resolution,
    )

    payload = mail_resolve_live(target)

    assert payload["schema_version"] == 1
    assert payload["managed_agent"]["mode"] == "local"
    assert payload["transport"] == "filesystem"
    assert payload["gateway_available"] is False


def test_mail_resolve_live_server_returns_pair_authority_payload() -> None:
    client = SimpleNamespace(
        get_managed_agent_mail_resolve_live=lambda agent_ref: {
            "source": "manifest_binding",
            "transport": "filesystem",
            "principal_id": "HOUMAO-alpha",
            "address": "HOUMAO-alpha@agents.localhost",
            "bindings_version": "2026-03-29T15:00:00Z",
            "mailbox": {
                "transport": "filesystem",
                "filesystem": {
                    "root": "/tmp/mailbox",
                },
            },
            "gateway": {
                "source": "current_instance_record",
                "host": "127.0.0.1",
                "port": 43123,
                "base_url": "http://127.0.0.1:43123",
                "protocol_version": "v1",
                "state_path": "/tmp/state.json",
            },
        },
    )
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="remote",
        identity=_managed_identity(transport="tui"),
        client=client,
    )

    payload = mail_resolve_live(target)

    assert payload["source"] == "pair_authority"
    assert payload["managed_agent"]["mode"] == "server"
    assert payload["gateway_available"] is True
    assert payload["gateway"]["base_url"] == "http://127.0.0.1:43123"


def test_enrich_local_mail_prompt_args_resolves_filesystem_mailbox_principals(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="sender-principal",
        address="sender@agents.localhost",
        filesystem_root=tmp_path / "mailbox",
        bindings_version="2026-03-29T15:00:00Z",
    )

    def _fake_load_active_mailbox_registration(
        mailbox_root: Path, *, address: str
    ) -> SimpleNamespace:
        assert mailbox_root == mailbox.filesystem_root
        if address == "alpha@agents.localhost":
            return SimpleNamespace(
                owner_principal_id="alpha-principal",
                address=address,
                display_name="Alpha",
                manifest_path_hint="/tmp/alpha.json",
                role="alpha-role",
            )
        if address == "cc@agents.localhost":
            return SimpleNamespace(
                owner_principal_id="cc-principal",
                address=address,
                display_name=None,
                manifest_path_hint=None,
                role=None,
            )
        raise FileNotFoundError(address)

    monkeypatch.setattr(
        managed_agents_module,
        "load_active_mailbox_registration",
        _fake_load_active_mailbox_registration,
    )

    enriched = managed_agents_module._enrich_local_mail_prompt_args(
        mailbox=mailbox,
        operation="send",
        args={
            "to": ["alpha@agents.localhost", "alpha@agents.localhost"],
            "cc": ["cc@agents.localhost"],
            "subject": "hello",
            "body_content": "world",
            "attachments": [],
        },
    )

    assert enriched["resolved_sender"] == {
        "principal_id": "sender-principal",
        "address": "sender@agents.localhost",
    }
    assert enriched["resolved_to"] == [
        {
            "principal_id": "alpha-principal",
            "address": "alpha@agents.localhost",
            "display_name": "Alpha",
            "manifest_path_hint": "/tmp/alpha.json",
            "role": "alpha-role",
        }
    ]
    assert enriched["resolved_cc"] == [
        {
            "principal_id": "cc-principal",
            "address": "cc@agents.localhost",
        }
    ]


def test_enrich_local_mail_prompt_args_fails_when_recipient_is_unregistered(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="sender-principal",
        address="sender@agents.localhost",
        filesystem_root=tmp_path / "mailbox",
        bindings_version="2026-03-29T15:00:00Z",
    )
    monkeypatch.setattr(
        managed_agents_module,
        "load_active_mailbox_registration",
        lambda mailbox_root, *, address: (_ for _ in ()).throw(FileNotFoundError(address)),
    )

    with pytest.raises(click.ClickException, match="missing@agents.localhost"):
        managed_agents_module._enrich_local_mail_prompt_args(
            mailbox=mailbox,
            operation="send",
            args={
                "to": ["missing@agents.localhost"],
                "cc": [],
                "subject": "hello",
                "body_content": "world",
                "attachments": [],
            },
        )


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
        tmux_session_name="HOUMAO-alpha",
        tmux_window_name="agent",
        manifest_path="/tmp/manifest.json",
        session_root="/tmp/session-root",
        agent_name="HOUMAO-alpha",
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


def _gateway_tui_state_response() -> HoumaoTerminalStateResponse:
    return HoumaoTerminalStateResponse(
        terminal_id="headless123",
        tracked_session=HoumaoTrackedSessionIdentity(
            tracked_session_id="tracked-alpha",
            session_name="HOUMAO-alpha",
            tool="claude",
            tmux_session_name="HOUMAO-alpha",
            terminal_aliases=["headless123"],
        ),
        diagnostics=HoumaoTrackedDiagnostics(
            availability="available",
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status="parsed",
            probe_error=None,
            parse_error=None,
        ),
        probe_snapshot=None,
        parsed_surface=None,
        surface=HoumaoTrackedSurface(
            accepting_input="yes",
            editing_input="no",
            ready_posture="yes",
        ),
        turn=HoumaoTrackedTurn(phase="ready"),
        last_turn=HoumaoTrackedLastTurn(result="none", source="none", updated_at_utc=None),
        stability=HoumaoStabilityMetadata(
            signature="ready",
            stable=True,
            stable_for_seconds=3.0,
            stable_since_utc="2026-01-01T00:00:00+00:00",
        ),
        recent_transitions=[],
    )


def _sample_launch_plan(
    *,
    tmp_path: Path,
    backend: str,
    tool: str = "codex",
) -> LaunchPlan:
    return LaunchPlan(
        backend=backend,
        tool=tool,
        executable=tool,
        args=[],
        working_directory=tmp_path.resolve(),
        home_env_var=f"{tool.upper()}_HOME",
        home_path=(tmp_path / f"{tool}-home").resolve(),
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="r",
            prompt="role prompt",
        ),
        metadata={"session_origin": "joined_tmux"},
    )


def _write_manifest(
    *,
    tmp_path: Path,
    launch_plan: LaunchPlan,
    tmux_window_name: str,
) -> Path:
    manifest_path = (tmp_path / "session-root" / "manifest.json").resolve()
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=(tmp_path / "brain_manifest.json").resolve(),
            backend_state={
                "turn_index": 0,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path.resolve()),
            },
            agent_name="joined-agent",
            agent_id="agent-joined",
            tmux_session_name="join-sess",
            session_id="joined-session",
            agent_def_dir=(tmp_path / "agent-def").resolve(),
            job_dir=(tmp_path / ".houmao" / "jobs" / "joined-session").resolve(),
        )
    )
    assert payload["tmux"] is not None
    payload["tmux"]["primary_window_name"] = tmux_window_name
    write_session_manifest(manifest_path, payload)
    return manifest_path


def _sample_local_tui_state(
    *, manifest_path: Path, tmux_window_name: str
) -> HoumaoTerminalStateResponse:
    identity = HoumaoTrackedSessionIdentity(
        tracked_session_id="agent-joined",
        session_name="join-sess",
        tool="codex",
        tmux_session_name="join-sess",
        tmux_window_name=tmux_window_name,
        agent_name="joined-agent",
        agent_id="agent-joined",
        manifest_path=str(manifest_path),
        session_root=str(manifest_path.parent),
    )
    return HoumaoTerminalStateResponse(
        terminal_id="term-1",
        tracked_session=identity,
        diagnostics=HoumaoTrackedDiagnostics(
            availability="available",
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status="parsed",
        ),
        probe_snapshot=None,
        parsed_surface=None,
        surface=HoumaoTrackedSurface(
            accepting_input="yes",
            editing_input="no",
            ready_posture="yes",
        ),
        turn=HoumaoTrackedTurn(phase="ready"),
        last_turn=HoumaoTrackedLastTurn(
            result="none",
            source="none",
            updated_at_utc="2026-01-01T00:00:00+00:00",
        ),
        stability=HoumaoStabilityMetadata(
            signature="ready",
            stable=True,
            stable_for_seconds=2.0,
            stable_since_utc="2026-01-01T00:00:00+00:00",
        ),
        recent_transitions=[],
    )


def _gateway_status() -> GatewayStatusV1:
    return GatewayStatusV1(
        attach_identity="published-alpha",
        backend="claude_headless",
        tmux_session_name="HOUMAO-alpha",
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
        self.gateway_control_calls: list[tuple[str, str, bool]] = []
        self.gateway_prompt_calls: list[tuple[str, str, bool]] = []
        self.gateway_tui_state_calls: list[str] = []
        self.gateway_tui_history_calls: list[str] = []
        self.gateway_tui_note_prompt_calls: list[tuple[str, str]] = []
        self.gateway_notifier_get_calls: list[str] = []
        self.gateway_notifier_put_calls: list[tuple[str, int]] = []
        self.gateway_notifier_delete_calls: list[str] = []
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

    def attach_managed_agent_gateway(
        self,
        agent_ref: str,
        request_model: object | None = None,
    ) -> GatewayStatusV1:
        del request_model
        raise AssertionError(f"remote passive gateway attach should stay local for {agent_ref}")

    def detach_managed_agent_gateway(self, agent_ref: str) -> GatewayStatusV1:
        raise AssertionError(f"remote passive gateway detach should stay local for {agent_ref}")

    def send_managed_agent_gateway_control_input(
        self,
        agent_ref: str,
        request_model: object,
    ) -> GatewayControlInputResultV1:
        self.gateway_control_calls.append(
            (
                agent_ref,
                getattr(request_model, "sequence"),
                getattr(request_model, "escape_special_keys"),
            )
        )
        return GatewayControlInputResultV1(detail="delivered")

    def control_managed_agent_gateway_prompt(
        self,
        agent_ref: str,
        request_model: object,
    ) -> HoumaoManagedAgentGatewayPromptControlResponse:
        self.gateway_prompt_calls.append(
            (
                agent_ref,
                getattr(request_model, "prompt"),
                getattr(request_model, "force"),
            )
        )
        return HoumaoManagedAgentGatewayPromptControlResponse(
            sent=True,
            forced=getattr(request_model, "force"),
            detail="Prompt dispatched.",
        )

    def get_managed_agent_gateway_tui_state(self, agent_ref: str) -> HoumaoTerminalStateResponse:
        self.gateway_tui_state_calls.append(agent_ref)
        return _gateway_tui_state_response()

    def get_managed_agent_gateway_tui_history(
        self,
        agent_ref: str,
        *,
        limit: int = 100,
    ) -> HoumaoTerminalSnapshotHistoryResponse:
        self.gateway_tui_history_calls.append(agent_ref)
        state = _gateway_tui_state_response()
        return HoumaoTerminalSnapshotHistoryResponse(
            terminal_id=state.terminal_id,
            tracked_session_id=state.tracked_session.tracked_session_id,
            entries=[
                HoumaoTerminalSnapshotHistoryEntry(
                    recorded_at_utc="2026-01-01T00:00:00+00:00",
                    diagnostics=state.diagnostics,
                    probe_snapshot=state.probe_snapshot,
                    parsed_surface=state.parsed_surface,
                    surface=state.surface,
                    turn=state.turn,
                    last_turn=state.last_turn,
                    stability=state.stability.model_copy(update={"signature": f"limit-{limit}"}),
                )
            ],
        )

    def note_managed_agent_gateway_tui_prompt(
        self,
        agent_ref: str,
        *,
        prompt: str,
    ) -> HoumaoTerminalStateResponse:
        self.gateway_tui_note_prompt_calls.append((agent_ref, prompt))
        return _gateway_tui_state_response()

    def get_managed_agent_gateway_mail_notifier(
        self, agent_ref: str
    ) -> GatewayMailNotifierStatusV1:
        self.gateway_notifier_get_calls.append(agent_ref)
        return GatewayMailNotifierStatusV1(
            enabled=False,
            interval_seconds=None,
            supported=True,
            support_error=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_error=None,
        )

    def put_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
        request_model: object,
    ) -> GatewayMailNotifierStatusV1:
        self.gateway_notifier_put_calls.append(
            (agent_ref, getattr(request_model, "interval_seconds"))
        )
        return GatewayMailNotifierStatusV1(
            enabled=True,
            interval_seconds=getattr(request_model, "interval_seconds"),
            supported=True,
            support_error=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_error=None,
        )

    def delete_managed_agent_gateway_mail_notifier(
        self,
        agent_ref: str,
    ) -> GatewayMailNotifierStatusV1:
        self.gateway_notifier_delete_calls.append(agent_ref)
        return GatewayMailNotifierStatusV1(
            enabled=False,
            interval_seconds=None,
            supported=True,
            support_error=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_error=None,
        )


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


def test_gateway_send_keys_uses_passive_pair_client() -> None:
    client = _FakePassivePairClient()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=client.m_state.identity,
        client=client,
    )

    response = gateway_send_keys(target, sequence="<[Escape]>", escape_special_keys=True)

    assert response.action == "control_input"
    assert client.gateway_control_calls == [("published-alpha", "<[Escape]>", True)]


def test_gateway_prompt_uses_passive_pair_client() -> None:
    client = _FakePassivePairClient()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=client.m_state.identity,
        client=client,
    )

    response = gateway_prompt(target, prompt="hello", force=True)

    assert response.sent is True
    assert response.forced is True
    assert client.gateway_prompt_calls == [("published-alpha", "hello", True)]


def test_gateway_tui_commands_use_passive_pair_client() -> None:
    client = _FakePassivePairClient()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=client.m_state.identity,
        client=client,
    )

    state = gateway_tui_state(target)
    history = gateway_tui_history(target)
    noted = gateway_tui_note_prompt(target, prompt="hello")

    assert state.terminal_id == "headless123"
    assert history.entries[0].stability.signature == "limit-100"
    assert noted.terminal_id == "headless123"
    assert client.gateway_tui_state_calls == ["published-alpha"]
    assert client.gateway_tui_history_calls == ["published-alpha"]
    assert client.gateway_tui_note_prompt_calls == [("published-alpha", "hello")]


def test_gateway_mail_notifier_commands_use_passive_pair_client() -> None:
    client = _FakePassivePairClient()
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=client.m_state.identity,
        client=client,
    )

    status = gateway_mail_notifier_status(target)
    enabled = gateway_mail_notifier_enable(target, interval_seconds=60)
    disabled = gateway_mail_notifier_disable(target)

    assert status.enabled is False
    assert enabled.interval_seconds == 60
    assert disabled.enabled is False
    assert client.gateway_notifier_get_calls == ["published-alpha"]
    assert client.gateway_notifier_put_calls == [("published-alpha", 60)]
    assert client.gateway_notifier_delete_calls == ["published-alpha"]


def test_gateway_mail_notifier_commands_allow_joined_session_without_relaunch_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = SimpleNamespace(
        get_mail_notifier=lambda: GatewayMailNotifierStatusV1(
            enabled=False,
            interval_seconds=None,
            supported=True,
            support_error=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_error=None,
        ),
        put_mail_notifier=lambda request_model: GatewayMailNotifierStatusV1(
            enabled=True,
            interval_seconds=request_model.interval_seconds,
            supported=True,
            support_error=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_error=None,
        ),
        delete_mail_notifier=lambda: GatewayMailNotifierStatusV1(
            enabled=False,
            interval_seconds=None,
            supported=True,
            support_error=None,
            last_poll_at_utc=None,
            last_notification_at_utc=None,
            last_error=None,
        ),
    )
    controller = SimpleNamespace(
        agent_launch_authority=SimpleNamespace(
            session_origin="joined_tmux", posture_kind="unavailable"
        )
    )
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="published-alpha",
        identity=_managed_identity(transport="tui"),
        controller=controller,
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._require_live_gateway_client_for_controller",
        lambda resolved_controller: client,
    )

    status = gateway_mail_notifier_status(target)
    enabled = gateway_mail_notifier_enable(target, interval_seconds=60)
    disabled = gateway_mail_notifier_disable(target)

    assert status.supported is True
    assert enabled.enabled is True
    assert enabled.interval_seconds == 60
    assert disabled.enabled is False


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

    response = attach_gateway(target)

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


def test_identity_from_record_uses_persisted_tmux_window_name(
    tmp_path: Path,
) -> None:
    manifest_path = _write_manifest(
        tmp_path=tmp_path,
        launch_plan=_sample_launch_plan(tmp_path=tmp_path, backend="local_interactive"),
        tmux_window_name="manual",
    )
    record = SimpleNamespace(
        agent_name="joined-agent",
        agent_id="agent-joined",
        identity=SimpleNamespace(backend="local_interactive", tool="codex"),
        runtime=SimpleNamespace(
            agent_def_dir=str((tmp_path / "agent-def").resolve()),
            manifest_path=str(manifest_path),
            session_root=str(manifest_path.parent),
        ),
        terminal=SimpleNamespace(session_name="join-sess"),
    )

    identity = managed_agents_module._identity_from_record(record)

    assert identity.transport == "tui"
    assert identity.tmux_window_name == "manual"
    assert identity.tmux_session_name == "join-sess"


def test_identity_from_record_falls_back_to_join_launch_metadata_tmux_window_name(
    tmp_path: Path,
) -> None:
    manifest_path = _write_manifest(
        tmp_path=tmp_path,
        launch_plan=_sample_launch_plan(tmp_path=tmp_path, backend="local_interactive"),
        tmux_window_name="manual",
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["tmux"] is not None
    payload["tmux"]["primary_window_name"] = None
    assert payload["interactive"] is not None
    payload["interactive"]["tmux_window_name"] = None
    payload["backend_state"].pop("tmux_window_name", None)
    payload["launch_plan"]["metadata"]["tmux_window_name"] = "manual"
    payload["agent_launch_authority"]["session_origin"] = "joined_tmux"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    record = SimpleNamespace(
        agent_name="joined-agent",
        agent_id="agent-joined",
        identity=SimpleNamespace(backend="local_interactive", tool="codex"),
        runtime=SimpleNamespace(
            agent_def_dir=str((tmp_path / "agent-def").resolve()),
            manifest_path=str(manifest_path),
            session_root=str(manifest_path.parent),
        ),
        terminal=SimpleNamespace(session_name="join-sess"),
    )

    identity = managed_agents_module._identity_from_record(record)

    assert identity.tmux_window_name == "manual"


def test_local_tui_state_and_detail_payloads_use_joined_window_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch_plan = _sample_launch_plan(tmp_path=tmp_path, backend="local_interactive")
    manifest_path = _write_manifest(
        tmp_path=tmp_path,
        launch_plan=launch_plan,
        tmux_window_name="manual",
    )
    controller = SimpleNamespace(
        manifest_path=manifest_path,
        tmux_session_name="join-sess",
        launch_plan=launch_plan,
        agent_identity="joined-agent",
        agent_id="agent-joined",
    )
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="agent-joined",
        identity=managed_agents_module._identity_from_controller(controller),
        controller=controller,
    )

    monkeypatch.setattr(
        managed_agents_module,
        "_refresh_local_tui_state",
        lambda *, controller: _sample_local_tui_state(
            manifest_path=manifest_path,
            tmux_window_name="manual",
        ),
    )

    state = managed_agent_state_payload(target)
    detail = managed_agent_detail_payload(target)

    assert state.identity.tmux_window_name == "manual"
    assert detail.identity.tmux_window_name == "manual"
    assert detail.detail.transport == "tui"


def test_joined_tui_state_and_detail_after_resume_keep_adopted_window_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime_artifacts_module,
        "ensure_gateway_capability",
        lambda publication: None,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "set_tmux_session_environment",
        lambda *, session_name, env_vars: None,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "publish_live_agent_record",
        lambda record: record,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "read_tmux_session_environment_value",
        lambda *, session_name, variable_name: None,
    )
    joined = runtime_artifacts_module.materialize_joined_launch(
        runtime_root=tmp_path,
        agent_name="tester",
        agent_id=None,
        provider="claude_code",
        headless=False,
        tmux_session_name="join-sess",
        tmux_window_name="manual",
        working_directory=tmp_path,
        launch_args=(),
        launch_env=(),
        resume_selection=None,
    )

    class _FakeLocalInteractiveSession(HeadlessInteractiveSession):
        def __init__(self, **kwargs: object) -> None:
            self.backend = "local_interactive"
            self._state = kwargs["state"]

    monkeypatch.setattr(runtime_module, "LocalInteractiveSession", _FakeLocalInteractiveSession)
    monkeypatch.setattr(
        runtime_module.RuntimeSessionController,
        "ensure_gateway_capability",
        lambda self: self.persist_manifest(refresh_registry=False),
    )

    controller = runtime_module.resume_runtime_session(
        agent_def_dir=(joined.session_root / "agent_def").resolve(),
        session_manifest_path=joined.manifest_path,
    )
    persisted_payload = json.loads(joined.manifest_path.read_text(encoding="utf-8"))
    target = ManagedAgentTarget(
        mode="local",
        agent_ref=joined.agent_id,
        identity=managed_agents_module._identity_from_controller(controller),
        controller=controller,
    )

    monkeypatch.setattr(
        managed_agents_module,
        "_refresh_local_tui_state",
        lambda *, controller: _sample_local_tui_state(
            manifest_path=joined.manifest_path,
            tmux_window_name="manual",
        ),
    )

    state = managed_agent_state_payload(target)
    detail = managed_agent_detail_payload(target)

    assert persisted_payload["tmux"]["primary_window_name"] == "manual"
    assert persisted_payload["interactive"]["tmux_window_name"] == "manual"
    assert persisted_payload["backend_state"]["tmux_window_name"] == "manual"
    assert managed_agents_module._tracked_tui_identity_for_controller(
        controller
    ).tmux_window_name == ("manual")
    assert state.identity.tmux_window_name == "manual"
    assert detail.identity.tmux_window_name == "manual"
    assert detail.detail.transport == "tui"


def test_local_prompt_and_interrupt_use_runtime_controller() -> None:
    calls: list[str] = []
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="agent-joined",
        identity=_managed_identity(),
        controller=SimpleNamespace(
            send_prompt=lambda prompt: calls.append(prompt),
            interrupt=lambda: SessionControlResult(status="ok", action="interrupt", detail="done"),
        ),
    )

    prompt_response = prompt_managed_agent(target, prompt="hello")
    interrupt_response = interrupt_managed_agent(target)

    assert prompt_response.success is True
    assert prompt_response.request_kind == "submit_prompt"
    assert interrupt_response.success is True
    assert interrupt_response.detail == "done"
    assert calls == ["hello"]


def test_headless_detail_uses_exit_artifact_even_when_tmux_session_is_live(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch_plan = _sample_launch_plan(tmp_path=tmp_path, backend="gemini_headless", tool="gemini")
    manifest_path = _write_manifest(
        tmp_path=tmp_path,
        launch_plan=launch_plan,
        tmux_window_name="agent",
    )
    turn_dir = manifest_path.parent / "manifest.turn-artifacts" / "turn-0001"
    turn_dir.mkdir(parents=True)
    (turn_dir / "exitcode").write_text("0\n", encoding="utf-8")
    controller = SimpleNamespace(
        manifest_path=manifest_path,
        tmux_session_name="join-sess",
        launch_plan=launch_plan,
        agent_identity="joined-agent",
        agent_id="agent-joined",
    )
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="agent-joined",
        identity=managed_agents_module._identity_from_controller(controller),
        controller=controller,
    )

    monkeypatch.setattr(managed_agents_module, "_local_gateway_summary", lambda _controller: None)
    monkeypatch.setattr(managed_agents_module, "_local_mailbox_summary", lambda _controller: None)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.tmux_session_exists",
        lambda *, session_name: session_name == "join-sess",
    )

    detail = managed_agent_detail_payload(target)

    assert detail.detail.transport == "headless"
    assert detail.detail.tmux_session_live is True
    assert detail.detail.can_accept_prompt_now is True
    assert detail.detail.interruptible is False
    assert detail.detail.last_turn_status == "completed"
    assert detail.summary_state.turn.phase == "ready"


def test_attach_gateway_uses_local_runtime_controller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _FakeGatewayController()
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="published-alpha",
        identity=_managed_identity(),
        controller=controller,
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._gateway_status_for_controller",
        lambda resolved_controller: _gateway_status(),
    )

    response = attach_gateway(target)

    assert response.gateway_port == 9901
    assert controller.attach_calls == ["tmux_auxiliary_window"]


def test_attach_gateway_can_request_background_execution_for_local_controller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _FakeGatewayController()
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="published-alpha",
        identity=_managed_identity(),
        controller=controller,
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._gateway_status_for_controller",
        lambda resolved_controller: _gateway_status(),
    )

    response = attach_gateway(target, background=True)

    assert response.gateway_port == 9901
    assert controller.attach_calls == ["detached_process"]


def test_attach_gateway_sends_execution_mode_to_pair_client() -> None:
    captured: list[tuple[str, object]] = []
    target = ManagedAgentTarget(
        mode="server",
        agent_ref="published-alpha",
        identity=_managed_identity(),
        client=SimpleNamespace(
            pair_authority_kind="houmao-server",
            attach_managed_agent_gateway=lambda agent_ref, request_model=None: (
                captured.append((agent_ref, request_model)) or _gateway_status()
            ),
        ),
    )

    response = attach_gateway(target, background=True)

    assert response.gateway_port == 9901
    assert len(captured) == 1
    assert captured[0][0] == "published-alpha"
    assert getattr(captured[0][1], "execution_mode") == "detached_process"


def test_submit_headless_turn_uses_local_runtime_controller(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch_plan = _sample_launch_plan(tmp_path=tmp_path, backend="codex_headless")
    calls: list[str] = []
    controller = SimpleNamespace(
        send_prompt=lambda prompt: calls.append(prompt),
        launch_plan=launch_plan,
        manifest_path=(tmp_path / "session-root" / "manifest.json").resolve(),
    )
    target = ManagedAgentTarget(
        mode="local",
        agent_ref="agent-joined",
        identity=_managed_identity(),
        controller=controller,
    )

    monkeypatch.setattr(managed_agents_module, "_next_turn_index", lambda resolved_controller: 1)
    monkeypatch.setattr(
        managed_agents_module,
        "_turn_snapshot_from_id",
        lambda *, controller, turn_id: managed_agents_module._LocalHeadlessTurnSnapshot(
            turn_id=turn_id,
            turn_index=1,
            status="completed",
            started_at_utc="2026-01-01T00:00:00+00:00",
            completed_at_utc="2026-01-01T00:00:02+00:00",
            completion_source="process_exit",
            stdout_path=None,
            stderr_path=None,
            status_path=None,
            returncode=0,
            history_summary=None,
            error=None,
        ),
    )

    response = submit_headless_turn(target, prompt="summarize")

    assert response.success is True
    assert response.turn_id == "turn-0001"
    assert calls == ["summarize"]
