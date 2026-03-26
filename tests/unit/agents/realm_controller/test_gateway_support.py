from __future__ import annotations

import json
import sqlite3
import subprocess
import threading
import time
from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    StalwartMailboxResolvedConfig,
)
from houmao.agents.mailbox_runtime_support import mailbox_env_bindings
from houmao.agents.realm_controller.errors import GatewayHttpError, LaunchPlanError
from houmao.agents.realm_controller.gateway_models import (
    BlueprintGatewayDefaults,
    GatewayCurrentInstanceV1,
    GatewayControlInputRequestV1,
    GatewayMailCheckRequestV1,
    GatewayMailNotifierPutV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStateRequestV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
)
from houmao.agents.realm_controller.gateway_service import (
    GatewayServiceRuntime,
    create_app,
)
from houmao.agents.realm_controller.gateway_storage import (
    AGENT_GATEWAY_HOST_ENV_VAR,
    AGENT_GATEWAY_PORT_ENV_VAR,
    AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
    AGENT_GATEWAY_STATE_PATH_ENV_VAR,
    GatewayCapabilityPublication,
    ensure_gateway_capability,
    gateway_paths_from_manifest_path,
    read_gateway_notifier_audit_records,
    write_gateway_current_instance,
)
from houmao.agents.realm_controller.loaders import load_blueprint
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionControlResult,
)
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.cao.models import CaoSuccessResponse, CaoTerminal
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.filesystem import resolve_active_mailbox_local_sqlite_path
from houmao.mailbox.managed import DeliveryRequest, deliver_message
from houmao.mailbox.protocol import MailboxMessage, serialize_message_document
from houmao.mailbox.stalwart import (
    StalwartError,
    build_stalwart_credential_ref,
    runtime_stalwart_credential_path,
)
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.server.models import (
    HoumaoRecentTransition,
    HoumaoStabilityMetadata,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedDiagnostics,
    HoumaoTrackedLastTurn,
    HoumaoTrackedSessionIdentity,
    HoumaoTrackedSurface,
    HoumaoTrackedTurn,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sample_headless_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="claude_headless",
        tool="claude",
        executable="claude",
        args=["-p"],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt",
            role_name="role",
            prompt="role prompt",
        ),
        metadata={},
    )


def _sample_local_interactive_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="local_interactive",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="role",
            prompt="role prompt",
        ),
        metadata={},
    )


def _sample_cao_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="cao_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="role",
            prompt="role prompt",
        ),
        metadata={},
    )


def _sample_houmao_server_plan(tmp_path: Path) -> LaunchPlan:
    return LaunchPlan(
        backend="houmao_server_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="role",
            prompt="role prompt",
        ),
        metadata={},
    )


def _sample_cao_plan_with_mailbox(tmp_path: Path) -> LaunchPlan:
    mailbox_root = tmp_path / "mailbox"
    principal_id = "AGENTSYS-gpu"
    address = "AGENTSYS-gpu@agents.localhost"
    bootstrap_filesystem_mailbox(
        mailbox_root,
        principal=MailboxPrincipal(principal_id=principal_id, address=address),
    )
    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id=principal_id,
        address=address,
        filesystem_root=mailbox_root.resolve(),
        bindings_version="2026-03-16T08:00:00.000001Z",
    )
    return LaunchPlan(
        backend="cao_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env=mailbox_env_bindings(mailbox),
        env_var_names=sorted(mailbox_env_bindings(mailbox).keys()),
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="role",
            prompt="role prompt",
        ),
        metadata={},
        mailbox=mailbox,
    )


def _sample_cao_plan_with_stalwart_mailbox(tmp_path: Path) -> LaunchPlan:
    principal_id = "AGENTSYS-gpu"
    address = "AGENTSYS-gpu@agents.localhost"
    jmap_url = "http://stalwart.local/jmap"
    management_url = "http://stalwart.local/api"
    mailbox = StalwartMailboxResolvedConfig(
        transport="stalwart",
        principal_id=principal_id,
        address=address,
        jmap_url=jmap_url,
        management_url=management_url,
        login_identity=address,
        credential_ref=build_stalwart_credential_ref(address=address, jmap_url=jmap_url),
        bindings_version="2026-03-19T08:00:00.000001Z",
        credential_file=None,
    )
    return LaunchPlan(
        backend="cao_rest",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="role",
            prompt="role prompt",
        ),
        metadata={},
        mailbox=mailbox,
    )


def _write_canonical_staged_message(
    staged_message: Path,
    request: DeliveryRequest,
    *,
    body_markdown: str = "Body\n",
) -> None:
    message = MailboxMessage(
        message_id=request.message_id,
        thread_id=request.thread_id,
        in_reply_to=request.in_reply_to,
        references=list(request.references),
        created_at_utc=request.created_at_utc,
        sender=request.sender.to_mailbox_principal(),
        to=[principal.to_mailbox_principal() for principal in request.to],
        cc=[principal.to_mailbox_principal() for principal in request.cc],
        reply_to=[principal.to_mailbox_principal() for principal in request.reply_to],
        subject=request.subject,
        body_markdown=body_markdown,
        attachments=[attachment.to_mailbox_attachment() for attachment in request.attachments],
        headers=dict(request.headers),
    )
    staged_message.write_text(serialize_message_document(message), encoding="utf-8")


class _FakeInteractiveSession:
    def __init__(self) -> None:
        self.backend = "claude_headless"
        self.terminated = False

    def send_prompt(self, prompt: str):  # type: ignore[no-untyped-def]
        del prompt
        return []

    def interrupt(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
        self.terminated = True
        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def close(self) -> None:
        self.terminated = True


def test_load_blueprint_accepts_strict_gateway_defaults(tmp_path: Path) -> None:
    blueprint_path = tmp_path / "gpu-blueprint.yaml"
    blueprint_path.write_text(
        (
            "schema_version: 1\n"
            "name: gpu\n"
            "role: researcher\n"
            "brain_recipe: recipes/gpu.yaml\n"
            "gateway:\n"
            "  host: 127.0.0.1\n"
            "  port: 43123\n"
        ),
        encoding="utf-8",
    )

    blueprint = load_blueprint(blueprint_path)

    assert blueprint.gateway == BlueprintGatewayDefaults(host="127.0.0.1", port=43123)


def test_load_blueprint_rejects_unknown_top_level_and_nested_gateway_fields(
    tmp_path: Path,
) -> None:
    top_level_path = tmp_path / "invalid-top-level.yaml"
    top_level_path.write_text(
        (
            "schema_version: 1\n"
            "name: gpu\n"
            "role: researcher\n"
            "brain_recipe: recipes/gpu.yaml\n"
            "unexpected: true\n"
        ),
        encoding="utf-8",
    )
    with pytest.raises(LaunchPlanError, match="unexpected"):
        load_blueprint(top_level_path)

    nested_path = tmp_path / "invalid-gateway.yaml"
    nested_path.write_text(
        (
            "schema_version: 1\n"
            "name: gpu\n"
            "role: researcher\n"
            "brain_recipe: recipes/gpu.yaml\n"
            "gateway:\n"
            "  host: 127.0.0.1\n"
            "  port: 43123\n"
            "  token: nope\n"
        ),
        encoding="utf-8",
    )
    with pytest.raises(LaunchPlanError, match="token"):
        load_blueprint(nested_path)


def test_ensure_gateway_capability_bootstraps_nested_gateway_root(tmp_path: Path) -> None:
    manifest_path = default_manifest_path(
        tmp_path,
        "cao_rest",
        "cao_rest-20260312-120000Z-abcd1234",
    )
    _write(manifest_path, "{}\n")

    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="cao_rest",
            tool="codex",
            session_id="cao_rest-20260312-120000Z-abcd1234",
            tmux_session_name="AGENTSYS-gpu",
            working_directory=tmp_path,
            backend_state={
                "api_base_url": "http://localhost:9889",
                "terminal_id": "term-123",
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
            },
            agent_def_dir=tmp_path / "agents",
            blueprint_gateway_defaults=BlueprintGatewayDefaults(
                host="127.0.0.1",
                port=43123,
            ),
        )
    )

    assert paths.gateway_root == manifest_path.parent / "gateway"
    assert paths.attach_path.is_file()
    assert paths.state_path.is_file()
    assert paths.queue_path.is_file()
    assert paths.protocol_version_path.read_text(encoding="utf-8").strip() == "v1"
    attach_payload = json.loads(paths.attach_path.read_text(encoding="utf-8"))
    assert attach_payload["attach_identity"] == "cao_rest-20260312-120000Z-abcd1234"
    assert attach_payload["desired_host"] == "127.0.0.1"
    assert attach_payload["desired_port"] == 43123
    state_payload = json.loads(paths.state_path.read_text(encoding="utf-8"))
    assert state_payload["gateway_health"] == "not_attached"
    assert gateway_paths_from_manifest_path(manifest_path) == paths
    with sqlite3.connect(paths.queue_path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='gateway_requests'"
        ).fetchone()
    assert row == (1,)


def test_legacy_tmux_session_stop_skips_gateway_teardown(tmp_path: Path) -> None:
    controller = RuntimeSessionController(
        launch_plan=_sample_headless_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=(tmp_path / "legacy-session.json").resolve(),
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="AGENTSYS-gpu",
    )

    result = controller.stop()

    assert result.status == "ok"
    assert result.action == "terminate"


def test_attach_gateway_supports_runtime_owned_headless_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = default_manifest_path(tmp_path, "claude_headless", "claude-headless-1")
    _write(manifest_path, "{}\n")
    controller = RuntimeSessionController(
        launch_plan=_sample_headless_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="AGENTSYS-gpu",
        tmux_session_name="AGENTSYS-gpu",
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    captured_attach: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._start_gateway_process",
        lambda *, controller, paths, host, port: (
            captured_attach.update(
                {
                    "controller": controller,
                    "paths": paths,
                    "host": host,
                    "port": port,
                }
            )
            or 43123
        ),
    )

    controller.ensure_gateway_capability()
    result = controller.attach_gateway()

    assert result.status == "ok"
    assert result.action == "gateway_attach"
    assert result.gateway_host == "127.0.0.1"
    assert result.gateway_port == 43123
    assert captured_attach["controller"] is controller
    assert captured_attach["host"] == "127.0.0.1"
    assert captured_attach["port"] == 0


def test_attach_gateway_supports_runtime_owned_local_interactive_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    _write(manifest_path, "{}\n")
    controller = RuntimeSessionController(
        launch_plan=_sample_local_interactive_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="AGENTSYS-local",
        tmux_session_name="AGENTSYS-local",
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    captured_attach: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._start_gateway_process",
        lambda *, controller, paths, host, port: (
            captured_attach.update(
                {
                    "controller": controller,
                    "paths": paths,
                    "host": host,
                    "port": port,
                }
            )
            or 43123
        ),
    )

    controller.ensure_gateway_capability()
    result = controller.attach_gateway()

    assert result.status == "ok"
    assert result.action == "gateway_attach"
    assert result.gateway_host == "127.0.0.1"
    assert result.gateway_port == 43123
    assert captured_attach["controller"] is controller
    assert captured_attach["host"] == "127.0.0.1"
    assert captured_attach["port"] == 0


def test_gateway_service_routes_local_interactive_prompts_through_runtime_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="AGENTSYS-local",
        session_id=None,
        backend="local_interactive",
    )
    fake_controller = _FakeGatewayHeadlessController(fake_session)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.HeadlessInteractiveSession",
        _FakeGatewayHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_kwargs: fake_controller,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.tmux_session_exists",
        lambda *, session_name: session_name == "AGENTSYS-local",
    )
    _FakeGatewayTrackingRuntime.reset()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.SingleSessionTrackingRuntime",
        _FakeGatewayTrackingRuntime,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    runtime.start()
    try:
        status = runtime.status()
        assert status.managed_agent_connectivity == "connected"
        assert status.terminal_surface_eligibility == "ready"
        assert status.request_admission == "open"

        accepted = runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(
                    prompt="hello",
                    turn_id="turn-local-123",
                ),
            )
        )
        assert accepted.request_kind == "submit_prompt"
        assert fake_session.started_event.wait(timeout=2.0)
        for _ in range(40):
            if _FakeGatewayTrackingRuntime.m_prompt_notes == ["hello"]:
                break
            time.sleep(0.05)
        assert _FakeGatewayTrackingRuntime.m_started_session_ids == ["local-interactive-1"]
        assert _FakeGatewayTrackingRuntime.m_prompt_notes == ["hello"]
    finally:
        fake_session.release_event.set()
        runtime.shutdown()

    assert fake_session.prompt_calls == [("hello", "turn-local-123")]
    assert fake_controller.persist_manifest_calls == [False]
    assert _FakeGatewayTrackingRuntime.m_stopped_session_ids == ["local-interactive-1"]


def test_gateway_service_routes_local_interactive_interrupts_through_runtime_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="AGENTSYS-local",
        session_id=None,
        backend="local_interactive",
    )
    fake_controller = _FakeGatewayHeadlessController(fake_session)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.HeadlessInteractiveSession",
        _FakeGatewayHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_kwargs: fake_controller,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.tmux_session_exists",
        lambda *, session_name: session_name == "AGENTSYS-local",
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    runtime.start()
    try:
        status = runtime.status()
        assert status.managed_agent_connectivity == "connected"
        assert status.request_admission == "open"

        accepted = runtime.create_request(
            GatewayRequestCreateV1(
                kind="interrupt",
                payload=GatewayRequestPayloadInterruptV1(),
            )
        )
        assert accepted.request_kind == "interrupt"
        assert fake_controller.interrupted_event.wait(timeout=2.0)
    finally:
        runtime.shutdown()

    assert fake_controller.interrupt_calls == 1


def test_gateway_service_routes_local_interactive_raw_send_keys_through_control_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="AGENTSYS-local",
        session_id=None,
        backend="local_interactive",
    )
    fake_controller = _FakeGatewayHeadlessController(fake_session)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.HeadlessInteractiveSession",
        _FakeGatewayHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_kwargs: fake_controller,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.tmux_session_exists",
        lambda *, session_name: session_name == "AGENTSYS-local",
    )
    _FakeGatewayTrackingRuntime.reset()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.SingleSessionTrackingRuntime",
        _FakeGatewayTrackingRuntime,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    runtime.start()
    try:
        response = client.post(
            "/v1/control/send-keys",
            json=GatewayControlInputRequestV1(
                sequence="hello world",
                escape_special_keys=False,
            ).model_dump(mode="json"),
        )
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "action": "control_input",
            "detail": "Delivered control input to the local interactive session.",
        }
        assert fake_controller.send_input_event.wait(timeout=2.0)
        assert runtime.status().queue_depth == 0
    finally:
        runtime.shutdown()

    assert fake_controller.send_input_calls == [("hello world", False)]
    assert fake_session.prompt_calls == []
    assert _FakeGatewayTrackingRuntime.m_prompt_notes == []


def test_gateway_service_builds_local_interactive_tui_tracking_identity_without_manifest_enrichment(
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    manifest_path.unlink()

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    identity = runtime._tui_tracking_identity_locked()

    assert identity is not None
    assert identity.tracked_session_id == "local-interactive-1"
    assert identity.session_name == "local-interactive-1"
    assert identity.tool == "codex"
    assert identity.tmux_session_name == "AGENTSYS-local"
    assert identity.tmux_window_name is None
    assert identity.terminal_aliases == []
    assert identity.agent_name is None
    assert identity.agent_id is None
    assert identity.manifest_path == str(manifest_path)


def test_gateway_service_exposes_local_interactive_state_and_prompt_note_routes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="AGENTSYS-local",
        session_id=None,
        backend="local_interactive",
    )
    fake_controller = _FakeGatewayHeadlessController(fake_session)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.HeadlessInteractiveSession",
        _FakeGatewayHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_kwargs: fake_controller,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.tmux_session_exists",
        lambda *, session_name: session_name == "AGENTSYS-local",
    )
    _FakeGatewayTrackingRuntime.reset()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.SingleSessionTrackingRuntime",
        _FakeGatewayTrackingRuntime,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    runtime.start()
    try:
        assert _FakeGatewayTrackingRuntime.m_started_session_ids == ["local-interactive-1"]
        identity = _FakeGatewayTrackingRuntime.m_identities[0]
        assert identity.tracked_session_id == "local-interactive-1"
        assert identity.session_name == "local-interactive-1"
        assert identity.tmux_session_name == "AGENTSYS-local"
        assert identity.tmux_window_name is None
        assert identity.terminal_aliases == []
        assert identity.agent_name == "AGENTSYS-local"
        assert identity.agent_id == derive_agent_id_from_name("AGENTSYS-local")

        state_response = client.get("/v1/control/tui/state")
        assert state_response.status_code == 200
        assert state_response.json()["terminal_id"] == "local-interactive-1"
        assert (
            state_response.json()["tracked_session"]["tracked_session_id"] == "local-interactive-1"
        )
        assert state_response.json()["tracked_session"]["terminal_aliases"] == []

        note_response = client.post(
            "/v1/control/tui/note-prompt",
            json=GatewayRequestPayloadSubmitPromptV1(
                prompt="route-note",
                turn_id="turn-route",
            ).model_dump(mode="json"),
        )
        assert note_response.status_code == 200
        assert note_response.json()["terminal_id"] == "local-interactive-1"
        assert (
            note_response.json()["tracked_session"]["tracked_session_id"] == "local-interactive-1"
        )
        assert _FakeGatewayTrackingRuntime.m_prompt_notes == ["route-note"]
    finally:
        runtime.shutdown()

    assert _FakeGatewayTrackingRuntime.m_stopped_session_ids == ["local-interactive-1"]


def test_gateway_service_routes_server_managed_headless_prompts_through_houmao_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_headless_gateway_root(
        tmp_path,
        managed_api_base_url="http://127.0.0.1:9889",
        managed_agent_ref="claude-headless-1",
    )
    fake_session = _FakeGatewayHeadlessSession()
    fake_controller = _FakeGatewayHeadlessController(fake_session)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.HeadlessInteractiveSession",
        _FakeGatewayHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_kwargs: fake_controller,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.tmux_session_exists",
        lambda *, session_name: session_name == "AGENTSYS-headless",
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    runtime.start()
    try:
        status = runtime.status()
        assert status.managed_agent_connectivity == "connected"
        assert status.request_admission == "open"

        accepted = runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(
                    prompt="hello",
                    turn_id="turn-server-123",
                ),
            )
        )
        assert accepted.request_kind == "submit_prompt"
        assert fake_session.started_event.wait(timeout=2.0)
    finally:
        fake_session.release_event.set()
        runtime.shutdown()

    assert fake_session.prompt_calls == [("hello", "turn-server-123")]
    assert fake_controller.persist_manifest_calls == [False]


def test_gateway_service_blocks_server_managed_headless_when_prompt_admission_is_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_headless_gateway_root(
        tmp_path,
        managed_api_base_url="http://127.0.0.1:9889",
        managed_agent_ref="claude-headless-1",
    )
    fake_session = _FakeGatewayHeadlessSession(block_prompt=True)
    fake_controller = _FakeGatewayHeadlessController(fake_session)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.HeadlessInteractiveSession",
        _FakeGatewayHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_kwargs: fake_controller,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.tmux_session_exists",
        lambda *, session_name: session_name == "AGENTSYS-headless",
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    runtime.start()
    try:
        status = runtime.status()
        assert status.managed_agent_connectivity == "connected"
        assert status.terminal_surface_eligibility == "ready"
        assert status.request_admission == "open"

        runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(
                    prompt="hello",
                    turn_id="turn-live",
                ),
            )
        )
        assert fake_session.started_event.wait(timeout=2.0)

        status = runtime.status()
        assert status.active_execution == "running"

        with pytest.raises(HTTPException, match="already active"):
            runtime.create_request(
                GatewayRequestCreateV1(
                    kind="submit_prompt",
                    payload=GatewayRequestPayloadSubmitPromptV1(
                        prompt="second",
                        turn_id="turn-next",
                    ),
                )
            )
    finally:
        fake_session.release_event.set()
        runtime.shutdown()


def test_ensure_gateway_capability_supports_houmao_server_backend(tmp_path: Path) -> None:
    manifest_path = default_manifest_path(
        tmp_path,
        "houmao_server_rest",
        "houmao-server-rest-20260319-120000Z-abcd1234",
    )
    _write(manifest_path, "{}\n")

    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="houmao_server_rest",
            tool="codex",
            session_id="houmao-server-rest-20260319-120000Z-abcd1234",
            tmux_session_name="AGENTSYS-gpu",
            working_directory=tmp_path,
            backend_state={
                "api_base_url": "http://127.0.0.1:9889",
                "session_name": "cao-gpu",
                "terminal_id": "term-123",
                "parsing_mode": "shadow_only",
                "tmux_window_name": "developer-1",
            },
            agent_def_dir=tmp_path / "agents",
        )
    )

    attach_payload = json.loads(paths.attach_path.read_text(encoding="utf-8"))
    metadata = attach_payload["backend_metadata"]

    assert attach_payload["backend"] == "houmao_server_rest"
    assert metadata["api_base_url"] == "http://127.0.0.1:9889"
    assert metadata["session_name"] == "cao-gpu"
    assert metadata["terminal_id"] == "term-123"
    assert metadata["tmux_window_name"] == "developer-1"
    assert "profile_name" not in metadata


def test_gateway_status_invalidates_stale_live_bindings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = default_manifest_path(tmp_path, "claude_headless", "claude-headless-1")
    _write(manifest_path, "{}\n")
    controller = RuntimeSessionController(
        launch_plan=_sample_headless_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="AGENTSYS-gpu",
        tmux_session_name="AGENTSYS-gpu",
    )

    captured_unset: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        lambda *, session_name, variable_names: captured_unset.update(
            {"session_name": session_name, "variable_names": tuple(variable_names)}
        ),
    )

    controller.ensure_gateway_capability()
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None

    def _fake_show_tmux_environment(
        *, session_name: str, variable_name: str
    ) -> subprocess.CompletedProcess[str]:
        mapping = {
            AGENT_GATEWAY_HOST_ENV_VAR: "127.0.0.1",
            AGENT_GATEWAY_PORT_ENV_VAR: "43123",
            AGENT_GATEWAY_STATE_PATH_ENV_VAR: str(paths.state_path),
            AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR: "v1",
        }
        value = mapping.get(variable_name)
        if value is None:
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="unknown variable"
            )
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=f"{variable_name}={value}\n",
            stderr="",
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.show_tmux_environment_shared",
        _fake_show_tmux_environment,
    )

    class _FailingGatewayClient:
        def __init__(self, *, endpoint, timeout_seconds: float = 5.0) -> None:
            del endpoint, timeout_seconds

        def health(self):  # type: ignore[no-untyped-def]
            raise GatewayHttpError(
                method="GET",
                url="http://127.0.0.1:43123/health",
                detail="connection refused",
            )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.GatewayClient",
        _FailingGatewayClient,
    )

    status = controller.gateway_status()

    assert status.gateway_health == "not_attached"
    assert captured_unset["session_name"] == "AGENTSYS-gpu"
    assert AGENT_GATEWAY_HOST_ENV_VAR in captured_unset["variable_names"]


def test_houmao_server_gateway_attach_persists_tmux_execution_handle_and_recreates_aux_window(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = default_manifest_path(tmp_path, "houmao_server_rest", "houmao-server-rest-1")
    _write(manifest_path, "{}\n")
    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="houmao_server_rest",
            tool="codex",
            session_id="houmao-server-rest-1",
            tmux_session_name="AGENTSYS-gpu",
            working_directory=tmp_path,
            backend_state={
                "api_base_url": "http://127.0.0.1:9889",
                "session_name": "cao-gpu",
                "terminal_id": "term-123",
                "parsing_mode": "shadow_only",
                "tmux_window_name": "developer-1",
            },
            agent_def_dir=tmp_path / "agents",
        )
    )
    controller = RuntimeSessionController(
        launch_plan=_sample_houmao_server_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="AGENTSYS-gpu",
        tmux_session_name="AGENTSYS-gpu",
    )

    tmux_state = {
        "handles": [("@9", "1", "%9"), ("@10", "2", "%10")],
        "alive": {"%9": True, "%10": True},
        "current": None,
        "kill_calls": [],
    }

    def _fake_run_tmux(
        args: list[str], *, timeout_seconds: float | None = None
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        if args[:1] == ["new-window"]:
            window_id, window_index, pane_id = tmux_state["handles"].pop(0)
            tmux_state["current"] = (window_id, window_index, pane_id)
            write_gateway_current_instance(
                paths.current_instance_path,
                GatewayCurrentInstanceV1(
                    pid=4242,
                    host="127.0.0.1",
                    port=43123,
                    execution_mode="tmux_auxiliary_window",
                    tmux_window_id=window_id,
                    tmux_window_index=window_index,
                    tmux_pane_id=pane_id,
                    managed_agent_instance_epoch=1,
                ),
            )
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=f"{window_id}\t{window_index}\t{pane_id}\n",
                stderr="",
            )
        if args[:1] == ["kill-window"]:
            tmux_state["kill_calls"].append(list(args))
            target = args[-1]
            current = tmux_state["current"]
            if current is not None and current[0] == target:
                if not tmux_state["alive"].get(current[2], False):
                    return subprocess.CompletedProcess(
                        args=args,
                        returncode=1,
                        stdout="",
                        stderr="can't find window",
                    )
                tmux_state["alive"][current[2]] = False
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="can't find window",
            )
        raise AssertionError(f"Unexpected tmux call: {args}")

    def _fake_list_tmux_panes(*, session_name: str):  # type: ignore[no-untyped-def]
        assert session_name == "AGENTSYS-gpu"
        current = tmux_state["current"]
        if current is None:
            return ()
        window_id, window_index, pane_id = current
        if not tmux_state["alive"].get(pane_id, False):
            return ()
        return (
            type(
                "Pane",
                (),
                {
                    "pane_id": pane_id,
                    "session_name": session_name,
                    "window_id": window_id,
                    "window_index": window_index,
                    "window_name": "gateway",
                    "pane_index": "0",
                    "pane_active": True,
                    "pane_dead": False,
                    "pane_pid": 4242,
                },
            )(),
        )

    class _HealthyGatewayClient:
        def __init__(self, *, endpoint, timeout_seconds: float = 5.0) -> None:
            del endpoint, timeout_seconds

        def health(self):  # type: ignore[no-untyped-def]
            return type("Health", (), {"protocol_version": "v1"})()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.run_tmux_shared",
        _fake_run_tmux,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.list_tmux_panes_shared",
        _fake_list_tmux_panes,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.GatewayClient",
        _HealthyGatewayClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._backend_state_for_session",
        lambda session: {
            "api_base_url": "http://127.0.0.1:9889",
            "session_name": "cao-gpu",
            "terminal_id": "term-123",
            "parsing_mode": "shadow_only",
            "tmux_window_name": "developer-1",
        },
    )

    first_attach = controller.attach_gateway()
    assert first_attach.status == "ok"
    first_current_instance = GatewayCurrentInstanceV1.model_validate(
        json.loads(paths.current_instance_path.read_text(encoding="utf-8"))
    )
    assert first_current_instance.execution_mode == "tmux_auxiliary_window"
    assert first_current_instance.tmux_window_id == "@9"
    assert first_current_instance.tmux_pane_id == "%9"

    tmux_state["alive"]["%9"] = False

    second_attach = controller.attach_gateway()
    assert second_attach.status == "ok"
    second_current_instance = GatewayCurrentInstanceV1.model_validate(
        json.loads(paths.current_instance_path.read_text(encoding="utf-8"))
    )
    assert second_current_instance.tmux_window_id == "@10"
    assert second_current_instance.tmux_pane_id == "%10"

    detach_result = controller.detach_gateway()
    assert detach_result.status == "ok"
    assert tmux_state["kill_calls"] == [
        ["kill-window", "-t", "@9"],
        ["kill-window", "-t", "@10"],
    ]
    assert not paths.current_instance_path.exists()


class _FakeCaoRestClient:
    def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
        del timeout_seconds
        self.base_url = base_url
        self.submitted_prompts: list[tuple[str, str]] = []

    def get_terminal(self, terminal_id: str) -> CaoTerminal:
        return CaoTerminal(
            id=terminal_id,
            name="developer-1",
            provider="codex",
            session_name="AGENTSYS-gpu",
            agent_profile="runtime-profile",
            status="idle",
        )

    def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
        self.submitted_prompts.append((terminal_id, message))
        return CaoSuccessResponse(success=True)

    def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
        self.submitted_prompts.append((terminal_id, "<interrupt>"))
        return CaoSuccessResponse(success=True)


def _seed_cao_gateway_root(
    tmp_path: Path,
    *,
    terminal_id: str = "term-123",
    mailbox_enabled: bool = False,
) -> Path:
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    plan = (
        _sample_cao_plan_with_mailbox(tmp_path) if mailbox_enabled else _sample_cao_plan(tmp_path)
    )
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="AGENTSYS-gpu",
            agent_id=derive_agent_id_from_name("AGENTSYS-gpu"),
            tmux_session_name="AGENTSYS-gpu",
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "AGENTSYS-gpu",
                "terminal_id": terminal_id,
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
                "turn_index": 1,
            },
        )
    )
    write_session_manifest(manifest_path, payload)
    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="cao_rest",
            tool="codex",
            session_id="cao-rest-1",
            tmux_session_name="AGENTSYS-gpu",
            working_directory=tmp_path,
            backend_state={
                "api_base_url": "http://localhost:9889",
                "terminal_id": terminal_id,
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
            },
            agent_def_dir=tmp_path / "agents",
        )
    )
    return paths.gateway_root


def _seed_headless_gateway_root(
    tmp_path: Path,
    *,
    managed_api_base_url: str | None = None,
    managed_agent_ref: str | None = None,
) -> Path:
    manifest_path = default_manifest_path(tmp_path, "claude_headless", "claude-headless-1")
    _write(manifest_path, "{}\n")
    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="claude_headless",
            tool="claude",
            session_id="claude-headless-1",
            tmux_session_name="AGENTSYS-headless",
            working_directory=tmp_path,
            backend_state={"session_id": "claude-session-1"},
            agent_def_dir=tmp_path / "agents",
        )
    )
    if managed_api_base_url is not None and managed_agent_ref is not None:
        attach_payload = json.loads(paths.attach_path.read_text(encoding="utf-8"))
        attach_payload["backend_metadata"]["managed_api_base_url"] = managed_api_base_url
        attach_payload["backend_metadata"]["managed_agent_ref"] = managed_agent_ref
        paths.attach_path.write_text(
            json.dumps(attach_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return paths.gateway_root


def _seed_local_interactive_gateway_root(tmp_path: Path) -> Path:
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    backend_state = {
        "turn_index": 2,
        "role_bootstrap_applied": True,
        "working_directory": str(tmp_path),
        "tmux_session_name": "AGENTSYS-local",
    }
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_local_interactive_plan(tmp_path),
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="AGENTSYS-local",
            agent_id=derive_agent_id_from_name("AGENTSYS-local"),
            tmux_session_name="AGENTSYS-local",
            backend_state=backend_state,
        )
    )
    write_session_manifest(manifest_path, payload)
    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="local_interactive",
            tool="codex",
            session_id="local-interactive-1",
            tmux_session_name="AGENTSYS-local",
            working_directory=tmp_path,
            backend_state=backend_state,
            agent_def_dir=tmp_path / "agents",
        )
    )
    return paths.gateway_root


class _FakeGatewayHeadlessSession:
    def __init__(
        self,
        *,
        block_prompt: bool = False,
        tmux_session_name: str = "AGENTSYS-headless",
        session_id: str | None = "claude-session-1",
        backend: str = "claude_headless",
    ) -> None:
        self.backend = backend
        self.state = type(
            "State",
            (),
            {
                "turn_index": 0,
                "tmux_session_name": tmux_session_name,
                "session_id": session_id,
            },
        )()
        self.prompt_calls: list[tuple[str, str | None]] = []
        self.block_prompt = block_prompt
        self.started_event = threading.Event()
        self.release_event = threading.Event()

    def send_prompt(
        self, prompt: str, *, turn_artifact_dir_name: str | None = None
    ) -> list[object]:
        self.prompt_calls.append((prompt, turn_artifact_dir_name))
        self.started_event.set()
        if self.block_prompt:
            self.release_event.wait(timeout=5.0)
        self.state.turn_index += 1
        return []

    def interrupt(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")


class _FakeGatewayHeadlessController:
    def __init__(self, session: _FakeGatewayHeadlessSession) -> None:
        self.backend_session = session
        self.persist_manifest_calls: list[bool] = []
        self.interrupt_calls = 0
        self.interrupted_event = threading.Event()
        self.send_input_calls: list[tuple[str, bool]] = []
        self.send_input_event = threading.Event()

    def persist_manifest(self, *, refresh_registry: bool = True) -> None:
        self.persist_manifest_calls.append(refresh_registry)

    def interrupt(self) -> SessionControlResult:
        self.interrupt_calls += 1
        self.interrupted_event.set()
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def send_input_ex(
        self, sequence: str, *, escape_special_keys: bool = False
    ) -> SessionControlResult:
        self.send_input_calls.append((sequence, escape_special_keys))
        self.send_input_event.set()
        return SessionControlResult(
            status="ok",
            action="control_input",
            detail="Delivered control input to the local interactive session.",
        )


def _tracked_terminal_id(identity: HoumaoTrackedSessionIdentity) -> str:
    if identity.terminal_aliases:
        return identity.terminal_aliases[0]
    return identity.tracked_session_id


def _sample_gateway_tracked_state(
    identity: HoumaoTrackedSessionIdentity,
) -> HoumaoTerminalStateResponse:
    terminal_id = _tracked_terminal_id(identity)
    return HoumaoTerminalStateResponse(
        terminal_id=terminal_id,
        tracked_session=identity,
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
            signature="local-interactive-ready",
            stable=True,
            stable_for_seconds=3.0,
            stable_since_utc="2026-03-25T18:00:00+00:00",
        ),
        recent_transitions=[],
    )


def _sample_gateway_tracked_history(
    identity: HoumaoTrackedSessionIdentity,
    *,
    limit: int,
) -> HoumaoTerminalHistoryResponse:
    terminal_id = _tracked_terminal_id(identity)
    return HoumaoTerminalHistoryResponse(
        terminal_id=terminal_id,
        tracked_session_id=identity.tracked_session_id,
        entries=[
            HoumaoRecentTransition(
                recorded_at_utc="2026-03-25T18:00:00+00:00",
                summary=f"limit={limit}",
                changed_fields=["turn_phase"],
                diagnostics_availability="available",
                turn_phase="ready",
                last_turn_result="none",
                last_turn_source="none",
                transport_state="tmux_up",
                process_state="tui_up",
                parse_status="parsed",
                operator_status="ready",
            )
        ],
    )


class _FakeGatewayTrackingRuntime:
    m_identities: list[HoumaoTrackedSessionIdentity] = []
    m_started_session_ids: list[str] = []
    m_stopped_session_ids: list[str] = []
    m_prompt_notes: list[str] = []

    def __init__(self, *, identity: HoumaoTrackedSessionIdentity, **_: object) -> None:
        self.m_identity = identity
        type(self).m_identities.append(identity)

    @classmethod
    def reset(cls) -> None:
        cls.m_identities = []
        cls.m_started_session_ids = []
        cls.m_stopped_session_ids = []
        cls.m_prompt_notes = []

    def start(self) -> None:
        type(self).m_started_session_ids.append(self.m_identity.tracked_session_id)

    def stop(self) -> None:
        type(self).m_stopped_session_ids.append(self.m_identity.tracked_session_id)

    def current_state(self) -> HoumaoTerminalStateResponse:
        return _sample_gateway_tracked_state(self.m_identity)

    def history(self, *, limit: int) -> HoumaoTerminalHistoryResponse:
        return _sample_gateway_tracked_history(self.m_identity, limit=limit)

    def note_prompt_submission(self, *, message: str) -> HoumaoTerminalStateResponse:
        type(self).m_prompt_notes.append(message)
        return _sample_gateway_tracked_state(self.m_identity)


def _seed_cao_gateway_root_with_stalwart_mailbox(
    tmp_path: Path,
    *,
    terminal_id: str = "term-123",
) -> Path:
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    plan = _sample_cao_plan_with_stalwart_mailbox(tmp_path)
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="AGENTSYS-gpu",
            agent_id=derive_agent_id_from_name("AGENTSYS-gpu"),
            tmux_session_name="AGENTSYS-gpu",
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "AGENTSYS-gpu",
                "terminal_id": terminal_id,
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
                "turn_index": 1,
            },
        )
    )
    write_session_manifest(manifest_path, payload)

    mailbox = plan.mailbox
    assert isinstance(mailbox, StalwartMailboxResolvedConfig)
    credential_path = runtime_stalwart_credential_path(tmp_path, mailbox.credential_ref)
    credential_path.parent.mkdir(parents=True, exist_ok=True)
    credential_path.write_text(
        json.dumps(
            {
                "credential_ref": mailbox.credential_ref,
                "login_identity": mailbox.login_identity,
                "password": "stalwart-password",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    credential_path.chmod(0o600)

    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="cao_rest",
            tool="codex",
            session_id="cao-rest-1",
            tmux_session_name="AGENTSYS-gpu",
            working_directory=tmp_path,
            backend_state={
                "api_base_url": "http://localhost:9889",
                "terminal_id": terminal_id,
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
            },
            agent_def_dir=tmp_path / "agents",
        )
    )
    return paths.gateway_root


def _deliver_unread_mailbox_message(
    tmp_path: Path,
    *,
    message_id: str = "msg-20260316T090000Z-a1b2c3d4e5f64798aabbccddeeff0011",
    created_at_utc: str = "2026-03-16T09:00:00Z",
    subject: str = "Gateway unread reminder",
) -> str:
    mailbox_root = tmp_path / "mailbox"
    sender = MailboxPrincipal(
        principal_id="AGENTSYS-sender",
        address="AGENTSYS-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id="AGENTSYS-gpu",
        address="AGENTSYS-gpu@agents.localhost",
    )
    bootstrap_filesystem_mailbox(mailbox_root, principal=sender)

    staged_message = mailbox_root / "staging" / "gateway-unread.md"
    request = DeliveryRequest.from_payload(
        {
            "staged_message_path": str(staged_message),
            "message_id": message_id,
            "thread_id": message_id,
            "in_reply_to": None,
            "references": [],
            "created_at_utc": created_at_utc,
            "sender": {
                "principal_id": sender.principal_id,
                "address": sender.address,
            },
            "to": [
                {
                    "principal_id": recipient.principal_id,
                    "address": recipient.address,
                }
            ],
            "cc": [],
            "reply_to": [],
            "subject": subject,
            "attachments": [],
            "headers": {},
        }
    )
    _write_canonical_staged_message(staged_message, request)
    deliver_message(mailbox_root, request)
    return request.message_id


def test_gateway_request_model_rejects_invalid_submit_prompt_payload() -> None:
    with pytest.raises(ValidationError, match="prompt"):
        GatewayRequestCreateV1(
            kind="submit_prompt",
            payload=GatewayRequestPayloadSubmitPromptV1(prompt=""),
        )


def test_gateway_service_accepts_requests_and_separates_health(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path)
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    runtime.start()
    try:
        health = runtime.health()
        assert health.protocol_version == "v1"

        status = runtime.status()
        assert status.gateway_health == "healthy"
        assert status.managed_agent_connectivity == "connected"

        accepted = runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(prompt="hello"),
            )
        )
        assert accepted.request_kind == "submit_prompt"

        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not fake_client.submitted_prompts:
            time.sleep(0.05)

        assert fake_client.submitted_prompts == [("term-123", "hello")]
    finally:
        runtime.shutdown()


def test_gateway_service_restart_recovers_accepted_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path)
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    paths = gateway_paths_from_manifest_path(
        default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    )
    assert paths is not None
    with sqlite3.connect(paths.queue_path) as connection:
        connection.execute(
            """
            INSERT INTO gateway_requests (
                request_id,
                request_kind,
                payload_json,
                state,
                accepted_at_utc,
                managed_agent_instance_epoch
            )
            VALUES (?, ?, ?, 'accepted', ?, ?)
            """,
            (
                "gwreq-1",
                "submit_prompt",
                json.dumps({"prompt": "queued"}),
                "2026-03-13T00:00:00+00:00",
                1,
            ),
        )
        connection.commit()

    runtime.start()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and fake_client.submitted_prompts != [("term-123", "queued")]:
        time.sleep(0.05)
    runtime.shutdown()

    assert fake_client.submitted_prompts == [("term-123", "queued")]


def test_gateway_service_blocks_replay_when_instance_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, terminal_id="term-new")
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None

    write_gateway_current_instance(
        paths.current_instance_path,
        GatewayCurrentInstanceV1(
            pid=12345,
            host="127.0.0.1",
            port=43123,
            managed_agent_instance_epoch=1,
            managed_agent_instance_id="term-old",
        ),
    )
    with sqlite3.connect(paths.queue_path) as connection:
        connection.execute(
            """
            INSERT INTO gateway_requests (
                request_id,
                request_kind,
                payload_json,
                state,
                accepted_at_utc,
                managed_agent_instance_epoch
            )
            VALUES (?, ?, ?, 'accepted', ?, ?)
            """,
            (
                "gwreq-1",
                "submit_prompt",
                json.dumps({"prompt": "queued"}),
                "2026-03-13T00:00:00+00:00",
                1,
            ),
        )
        connection.commit()

    runtime.start()
    status = runtime.status()
    runtime.shutdown()

    assert status.request_admission == "blocked_reconciliation"
    with sqlite3.connect(paths.queue_path) as connection:
        row = connection.execute(
            "SELECT state FROM gateway_requests WHERE request_id = ?",
            ("gwreq-1",),
        ).fetchone()
    assert row == ("accepted",)
    assert fake_client.submitted_prompts == []


def test_gateway_mail_notifier_rejects_enablement_without_manifest_mailbox_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    status = runtime.get_mail_notifier()
    assert status.enabled is False
    assert status.supported is False
    assert status.support_error is not None

    with pytest.raises(HTTPException, match="no mailbox binding"):
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=60))


def test_gateway_mail_notifier_rejects_enablement_when_manifest_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None

    attach_payload = json.loads(paths.attach_path.read_text(encoding="utf-8"))
    attach_payload["manifest_path"] = str((tmp_path / "missing-manifest.json").resolve())
    paths.attach_path.write_text(
        json.dumps(attach_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    with pytest.raises(HTTPException, match="unreadable"):
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=60))


def test_gateway_mail_routes_support_filesystem_mailbox_without_runtime_roundtrip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    unread_message_id = _deliver_unread_mailbox_message(tmp_path)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    status_response = client.get("/v1/mail/status")
    assert status_response.status_code == 200
    assert status_response.json()["transport"] == "filesystem"

    check_response = client.post(
        "/v1/mail/check",
        json=GatewayMailCheckRequestV1(unread_only=True, limit=10).model_dump(mode="json"),
    )
    assert check_response.status_code == 200
    check_payload = check_response.json()
    assert check_payload["transport"] == "filesystem"
    assert check_payload["message_count"] == 1
    assert check_payload["unread_count"] == 1
    assert check_payload["messages"][0]["message_ref"] == f"filesystem:{unread_message_id}"

    send_response = client.post(
        "/v1/mail/send",
        json=GatewayMailSendRequestV1(
            to=["AGENTSYS-sender@agents.localhost"],
            subject="Gateway route send",
            body_content="filesystem send body",
        ).model_dump(mode="json"),
    )
    assert send_response.status_code == 200
    send_payload = send_response.json()
    assert send_payload["operation"] == "send"
    assert send_payload["transport"] == "filesystem"
    assert send_payload["message"]["message_ref"].startswith("filesystem:msg-")

    reply_response = client.post(
        "/v1/mail/reply",
        json=GatewayMailReplyRequestV1(
            message_ref=f"filesystem:{unread_message_id}",
            body_content="filesystem reply body",
        ).model_dump(mode="json"),
    )
    assert reply_response.status_code == 200
    reply_payload = reply_response.json()
    assert reply_payload["operation"] == "reply"
    assert reply_payload["transport"] == "filesystem"
    assert reply_payload["message"]["subject"] == "Re: Gateway unread reminder"
    assert reply_payload["message"]["message_ref"].startswith("filesystem:msg-")


def test_gateway_mail_state_route_marks_filesystem_message_read_without_queue_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    unread_message_id = _deliver_unread_mailbox_message(tmp_path)
    mailbox_root = tmp_path / "mailbox"
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    response = client.post(
        "/v1/mail/state",
        json=GatewayMailStateRequestV1(
            message_ref=f"filesystem:{unread_message_id}",
            read=True,
        ).model_dump(mode="json"),
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "schema_version",
        "transport",
        "principal_id",
        "address",
        "message_ref",
        "read",
    }
    assert response.json()["transport"] == "filesystem"
    assert response.json()["message_ref"] == f"filesystem:{unread_message_id}"
    assert response.json()["read"] is True
    assert runtime.status().queue_depth == 0

    local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
        mailbox_root,
        address="AGENTSYS-gpu@agents.localhost",
    )
    with sqlite3.connect(local_sqlite_path) as connection:
        state_row = connection.execute(
            "SELECT is_read FROM message_state WHERE message_id = ?",
            (unread_message_id,),
        ).fetchone()
    assert state_row == (1,)


def test_gateway_mail_state_route_rejects_unsupported_mailbox_state_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    unread_message_id = _deliver_unread_mailbox_message(tmp_path)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    response = client.post(
        "/v1/mail/state",
        json={
            "schema_version": 1,
            "message_ref": f"filesystem:{unread_message_id}",
            "read": True,
            "starred": True,
        },
    )

    assert response.status_code == 422
    assert "extra_forbidden" in response.text


def test_gateway_mail_routes_reject_non_loopback_listener(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="0.0.0.0",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    response = client.get("/v1/mail/status")

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


def test_gateway_mail_routes_reject_missing_mailbox_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    response = client.post(
        "/v1/mail/check",
        json=GatewayMailCheckRequestV1(unread_only=False).model_dump(mode="json"),
    )

    assert response.status_code == 422
    assert "no mailbox binding" in response.json()["detail"]


def test_gateway_mail_routes_support_stalwart_mailbox_with_mocked_jmap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root_with_stalwart_mailbox(tmp_path)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )

    class _FakeStalwartJmapClient:
        def __init__(self, *, jmap_url: str, login_identity: str, credential_file: Path) -> None:
            self.m_jmap_url = jmap_url
            self.m_login_identity = login_identity
            self.m_credential_file = credential_file
            self.m_read_updates: list[tuple[str, bool]] = []

        def status(self) -> dict[str, object]:
            return {"account_id": "acc-1"}

        def check(
            self,
            *,
            unread_only: bool,
            limit: int | None,
            since: str | None,
        ) -> list[dict[str, object]]:
            del unread_only, limit, since
            return [
                {
                    "id": "mail-1",
                    "threadId": "thread-1",
                    "receivedAt": "2026-03-19T08:00:00Z",
                    "subject": "Stalwart unread",
                    "preview": "preview",
                    "body": "full body",
                    "from": [{"email": "sender@agents.localhost", "name": "Sender"}],
                    "to": [{"email": "AGENTSYS-gpu@agents.localhost"}],
                    "cc": [],
                    "replyTo": [],
                    "attachments": [],
                    "unread": True,
                }
            ]

        def send(
            self,
            *,
            sender_address: str,
            to_addresses: list[str] | tuple[str, ...],
            cc_addresses: list[str] | tuple[str, ...],
            subject: str,
            body_content: str,
            attachments: list[Path] | tuple[Path, ...],
        ) -> dict[str, object]:
            del to_addresses, cc_addresses, subject, body_content, attachments
            return {
                "id": "sent-1",
                "threadId": "thread-sent-1",
                "receivedAt": "2026-03-19T08:01:00Z",
                "subject": "Stalwart send",
                "preview": "send preview",
                "body": "send body",
                "from": [{"email": sender_address}],
                "to": [{"email": "recipient@agents.localhost"}],
                "cc": [],
                "replyTo": [],
                "attachments": [],
                "unread": False,
            }

        def reply(
            self,
            *,
            message_ref: str,
            sender_address: str,
            body_content: str,
            attachments: list[Path] | tuple[Path, ...],
        ) -> dict[str, object]:
            del message_ref, body_content, attachments
            return {
                "id": "reply-1",
                "threadId": "thread-1",
                "receivedAt": "2026-03-19T08:02:00Z",
                "subject": "Re: Stalwart unread",
                "preview": "reply preview",
                "body": "reply body",
                "from": [{"email": sender_address}],
                "to": [{"email": "sender@agents.localhost"}],
                "cc": [],
                "replyTo": [],
                "attachments": [],
                "unread": False,
            }

        def update_read_state(
            self,
            *,
            message_ref: str,
            read: bool,
        ) -> dict[str, object]:
            self.m_read_updates.append((message_ref, read))
            return {
                "id": message_ref,
                "threadId": "thread-1",
                "receivedAt": "2026-03-19T08:00:00Z",
                "subject": "Stalwart unread",
                "preview": "preview",
                "body": "full body",
                "from": [{"email": "sender@agents.localhost", "name": "Sender"}],
                "to": [{"email": "AGENTSYS-gpu@agents.localhost"}],
                "cc": [],
                "replyTo": [],
                "attachments": [],
                "unread": not read,
            }

    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_mailbox.StalwartJmapClient",
        _FakeStalwartJmapClient,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    status_response = client.get("/v1/mail/status")
    assert status_response.status_code == 200
    assert status_response.json()["transport"] == "stalwart"

    check_response = client.post(
        "/v1/mail/check",
        json=GatewayMailCheckRequestV1(unread_only=True, limit=5).model_dump(mode="json"),
    )
    assert check_response.status_code == 200
    check_payload = check_response.json()
    assert check_payload["transport"] == "stalwart"
    assert check_payload["messages"][0]["message_ref"] == "stalwart:mail-1"
    assert check_payload["messages"][0]["thread_ref"] == "stalwart-thread:thread-1"

    send_response = client.post(
        "/v1/mail/send",
        json=GatewayMailSendRequestV1(
            to=["recipient@agents.localhost"],
            subject="ignored by fake client",
            body_content="hello from test",
        ).model_dump(mode="json"),
    )
    assert send_response.status_code == 200
    assert send_response.json()["message"]["message_ref"] == "stalwart:sent-1"

    reply_response = client.post(
        "/v1/mail/reply",
        json=GatewayMailReplyRequestV1(
            message_ref="stalwart:mail-1",
            body_content="reply body",
        ).model_dump(mode="json"),
    )
    assert reply_response.status_code == 200
    assert reply_response.json()["message"]["message_ref"] == "stalwart:reply-1"

    state_response = client.post(
        "/v1/mail/state",
        json=GatewayMailStateRequestV1(
            message_ref="stalwart:mail-1",
            read=True,
        ).model_dump(mode="json"),
    )
    assert state_response.status_code == 200
    assert state_response.json()["transport"] == "stalwart"
    assert state_response.json()["message_ref"] == "stalwart:mail-1"
    assert state_response.json()["read"] is True


def test_gateway_mail_state_route_rejects_malformed_stalwart_state_normalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root_with_stalwart_mailbox(tmp_path)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )

    class _MalformedStalwartJmapClient:
        def __init__(self, *, jmap_url: str, login_identity: str, credential_file: Path) -> None:
            del jmap_url, login_identity, credential_file

        def update_read_state(
            self,
            *,
            message_ref: str,
            read: bool,
        ) -> dict[str, object]:
            del read
            return {
                "id": message_ref,
                "threadId": "thread-1",
                "receivedAt": "2026-03-19T08:00:00Z",
                "subject": "Stalwart unread",
                "preview": "preview",
                "body": "full body",
                "from": [{"email": "sender@agents.localhost", "name": "Sender"}],
                "to": [{"email": "AGENTSYS-gpu@agents.localhost"}],
                "cc": [],
                "replyTo": [],
                "attachments": [],
            }

    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_mailbox.StalwartJmapClient",
        _MalformedStalwartJmapClient,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    response = client.post(
        "/v1/mail/state",
        json=GatewayMailStateRequestV1(
            message_ref="stalwart:mail-1",
            read=True,
        ).model_dump(mode="json"),
    )
    assert response.status_code == 502
    assert "explicit boolean `unread` state" in response.json()["detail"]


def test_gateway_mail_notifier_polls_mailbox_local_state_and_deduplicates_after_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    message_id = _deliver_unread_mailbox_message(tmp_path)
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    runtime.start()
    try:
        status = runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))
        assert status.enabled is True
        assert status.supported is True

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not fake_client.submitted_prompts:
            time.sleep(0.05)

        assert len(fake_client.submitted_prompts) == 1
        assert message_id in fake_client.submitted_prompts[0][1]
        time.sleep(1.3)
        assert len(fake_client.submitted_prompts) == 1
    finally:
        runtime.shutdown()

    fake_client.submitted_prompts.clear()
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    runtime.start()
    try:
        time.sleep(1.3)
        assert fake_client.submitted_prompts == []
        status = runtime.get_mail_notifier()
        assert status.enabled is True
        assert status.last_notification_at_utc is not None
    finally:
        runtime.shutdown()

    log_text = (gateway_root / "logs" / "gateway.log").read_text(encoding="utf-8")
    assert "mail notifier enabled" in log_text
    assert "mail notifier enqueued" in log_text
    audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
    enqueued_rows = [row for row in audit_rows if row.outcome == "enqueued"]
    dedup_rows = [row for row in audit_rows if row.outcome == "dedup_skip"]
    assert enqueued_rows
    assert dedup_rows
    assert enqueued_rows[-1].unread_count == 1
    assert enqueued_rows[-1].unread_summary[0].message_ref == f"filesystem:{message_id}"
    assert enqueued_rows[-1].enqueued_request_id is not None
    assert all(row.unread_digest == enqueued_rows[-1].unread_digest for row in dedup_rows)


def test_gateway_mail_notifier_deduplicates_even_if_prompt_rendering_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    _deliver_unread_mailbox_message(tmp_path)
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    runtime.start()
    try:
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not fake_client.submitted_prompts:
            time.sleep(0.05)

        assert len(fake_client.submitted_prompts) == 1
        monkeypatch.setattr(
            runtime,
            "_build_mail_notifier_prompt",
            lambda unread_messages: "a completely rewritten notifier prompt",
        )
        time.sleep(1.3)
        assert len(fake_client.submitted_prompts) == 1
    finally:
        runtime.shutdown()


def test_gateway_mail_notifier_nominates_oldest_target_with_gateway_first_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    first_message_id = _deliver_unread_mailbox_message(
        tmp_path,
        message_id="msg-20260316T090000Z-11111111111111111111111111111111",
        created_at_utc="2026-03-16T09:00:00Z",
        subject="Gateway unread reminder one",
    )
    second_message_id = _deliver_unread_mailbox_message(
        tmp_path,
        message_id="msg-20260316T090100Z-22222222222222222222222222222222",
        created_at_utc="2026-03-16T09:01:00Z",
        subject="Gateway unread reminder two",
    )
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    runtime.start()
    try:
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not fake_client.submitted_prompts:
            time.sleep(0.05)

        assert len(fake_client.submitted_prompts) == 1
        prompt = fake_client.submitted_prompts[0][1]
        assert first_message_id in prompt
        assert second_message_id not in prompt
        assert "thread_ref: filesystem:" in prompt
        assert "from: AGENTSYS-sender@agents.localhost" in prompt
        assert "subject: Gateway unread reminder one" in prompt
        assert "Remaining unread after this target: 1." in prompt
        assert "email-via-filesystem" in prompt
        assert "email-via-stalwart" in prompt
        assert "skills/mailbox/email-via-filesystem/SKILL.md" in prompt
        assert "skills/mailbox/email-via-stalwart/SKILL.md" in prompt
        assert "Do not inspect repo docs or OpenAPI" in prompt
        assert '{"schema_version":1,"message_ref":"<opaque message_ref>","read":true}' in prompt
        assert "POST /v1/mail/state" in prompt
        assert "deliver_message.py" not in prompt
        assert "update_mailbox_state.py" not in prompt
    finally:
        runtime.shutdown()

    audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
    enqueued_rows = [row for row in audit_rows if row.outcome == "enqueued"]
    assert enqueued_rows
    latest_row = enqueued_rows[-1]
    assert latest_row.unread_count == 2
    assert [item.message_ref for item in latest_row.unread_summary] == [
        f"filesystem:{first_message_id}",
        f"filesystem:{second_message_id}",
    ]


def test_gateway_mail_notifier_stalwart_adapter_defers_enqueues_and_deduplicates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root_with_stalwart_mailbox(tmp_path)

    class _SlowFakeCaoRestClient(_FakeCaoRestClient):
        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            if message == "busy-work":
                time.sleep(1.5)
            return super().send_terminal_input(terminal_id, message)

    class _FakeStalwartJmapClient:
        def __init__(self, *, jmap_url: str, login_identity: str, credential_file: Path) -> None:
            del jmap_url, login_identity, credential_file

        def status(self) -> dict[str, object]:
            return {"account_id": "acc-1"}

        def check(
            self,
            *,
            unread_only: bool,
            limit: int | None,
            since: str | None,
        ) -> list[dict[str, object]]:
            del unread_only, limit, since
            return [
                {
                    "id": "mail-1",
                    "threadId": "thread-1",
                    "receivedAt": "2026-03-19T08:00:00Z",
                    "subject": "Stalwart unread notifier",
                    "preview": "preview",
                    "body": "full body",
                    "from": [{"email": "sender@agents.localhost"}],
                    "to": [{"email": "AGENTSYS-gpu@agents.localhost"}],
                    "cc": [],
                    "replyTo": [],
                    "attachments": [],
                    "unread": True,
                }
            ]

    fake_client = _SlowFakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_mailbox.StalwartJmapClient",
        _FakeStalwartJmapClient,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None

    runtime.start()
    try:
        runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(prompt="busy-work"),
            )
        )
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
            outcomes = {row.outcome for row in audit_rows}
            if {"busy_skip", "enqueued", "dedup_skip"} <= outcomes and len(
                fake_client.submitted_prompts
            ) >= 2:
                break
            time.sleep(0.05)

        assert fake_client.submitted_prompts[0] == ("term-123", "busy-work")
        assert len(fake_client.submitted_prompts) == 2
        assert "stalwart:mail-1" in fake_client.submitted_prompts[1][1]
        assert "POST /v1/mail/state" in fake_client.submitted_prompts[1][1]
    finally:
        runtime.shutdown()

    audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
    busy_rows = [row for row in audit_rows if row.outcome == "busy_skip"]
    enqueued_rows = [row for row in audit_rows if row.outcome == "enqueued"]
    dedup_rows = [row for row in audit_rows if row.outcome == "dedup_skip"]
    assert busy_rows
    assert enqueued_rows
    assert dedup_rows
    assert enqueued_rows[-1].unread_summary[0].message_ref == "stalwart:mail-1"


def test_gateway_mail_notifier_stalwart_adapter_records_poll_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root_with_stalwart_mailbox(tmp_path)

    class _FailingStalwartJmapClient:
        def __init__(self, *, jmap_url: str, login_identity: str, credential_file: Path) -> None:
            del jmap_url, login_identity, credential_file

        def status(self) -> dict[str, object]:
            return {"account_id": "acc-1"}

        def check(
            self,
            *,
            unread_only: bool,
            limit: int | None,
            since: str | None,
        ) -> list[dict[str, object]]:
            del unread_only, limit, since
            raise StalwartError("simulated stalwart mailbox failure")

    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_mailbox.StalwartJmapClient",
        _FailingStalwartJmapClient,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None

    runtime.start()
    try:
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
            if any(row.outcome == "poll_error" for row in audit_rows):
                break
            time.sleep(0.05)

        status = runtime.get_mail_notifier()
        assert status.last_error is not None
        assert "simulated stalwart mailbox failure" in status.last_error
        assert fake_client.submitted_prompts == []
    finally:
        runtime.shutdown()

    audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
    poll_error_rows = [row for row in audit_rows if row.outcome == "poll_error"]
    assert poll_error_rows
    assert poll_error_rows[-1].detail is not None
    assert "simulated stalwart mailbox failure" in poll_error_rows[-1].detail


def test_gateway_mail_notifier_defers_while_busy_and_logs_the_skip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    message_id = _deliver_unread_mailbox_message(tmp_path)

    class _SlowFakeCaoRestClient(_FakeCaoRestClient):
        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            if message == "busy-work":
                time.sleep(1.5)
            return super().send_terminal_input(terminal_id, message)

    fake_client = _SlowFakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    runtime.start()
    try:
        runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(prompt="busy-work"),
            )
        )
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))

        deadline = time.monotonic() + 4.5
        while time.monotonic() < deadline and len(fake_client.submitted_prompts) < 2:
            time.sleep(0.05)

        assert fake_client.submitted_prompts[0] == ("term-123", "busy-work")
        assert len(fake_client.submitted_prompts) == 2
        assert message_id in fake_client.submitted_prompts[1][1]
    finally:
        runtime.shutdown()

    log_text = (gateway_root / "logs" / "gateway.log").read_text(encoding="utf-8")
    assert "mail notifier poll deferred" in log_text
    audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
    busy_rows = [row for row in audit_rows if row.outcome == "busy_skip"]
    enqueued_rows = [row for row in audit_rows if row.outcome == "enqueued"]
    assert busy_rows
    assert enqueued_rows
    assert any(
        row.active_execution == "running" or (row.queue_depth is not None and row.queue_depth > 0)
        for row in busy_rows
    )
    assert enqueued_rows[-1].unread_summary[0].message_ref == f"filesystem:{message_id}"
