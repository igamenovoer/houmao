from __future__ import annotations

import json
import sqlite3
import subprocess
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
    GatewayMailCheckRequestV1,
    GatewayMailNotifierPutV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStateRequestV1,
    GatewayRequestCreateV1,
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
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentHeadlessDetailView,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
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


def test_gateway_service_routes_server_managed_headless_prompts_through_houmao_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_headless_gateway_root(
        tmp_path,
        managed_api_base_url="http://127.0.0.1:9889",
        managed_agent_ref="claude-headless-1",
    )
    fake_client = _FakeManagedHeadlessServerClient(can_accept_prompt_now=True)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.HoumaoServerClient",
        lambda *args, **kwargs: fake_client,
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
                payload=GatewayRequestPayloadSubmitPromptV1(prompt="hello"),
            )
        )
        assert accepted.request_kind == "submit_prompt"

        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not fake_client.m_request_calls:
            time.sleep(0.05)
    finally:
        runtime.shutdown()

    assert fake_client.m_request_calls
    assert fake_client.m_request_calls[0][0] == "claude-headless-1"
    assert getattr(fake_client.m_request_calls[0][1], "request_kind", None) == "submit_prompt"


def test_gateway_service_blocks_server_managed_headless_when_prompt_admission_is_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_headless_gateway_root(
        tmp_path,
        managed_api_base_url="http://127.0.0.1:9889",
        managed_agent_ref="claude-headless-1",
    )
    fake_client = _FakeManagedHeadlessServerClient(can_accept_prompt_now=False)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.HoumaoServerClient",
        lambda *args, **kwargs: fake_client,
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
        assert status.terminal_surface_eligibility == "not_ready"
        assert status.request_admission == "blocked_unavailable"

        with pytest.raises(HTTPException, match="unavailable"):
            runtime.create_request(
                GatewayRequestCreateV1(
                    kind="submit_prompt",
                    payload=GatewayRequestPayloadSubmitPromptV1(prompt="hello"),
                )
            )
    finally:
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


class _FakeManagedHeadlessServerClient:
    def __init__(self, *, can_accept_prompt_now: bool = True) -> None:
        self.m_can_accept_prompt_now = can_accept_prompt_now
        self.m_request_calls: list[tuple[str, object]] = []

    def get_managed_agent_state_detail(self, agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        identity = HoumaoManagedAgentIdentity(
            tracked_agent_id=agent_ref,
            transport="headless",
            tool="claude",
            runtime_session_id=agent_ref,
            tmux_session_name="AGENTSYS-headless",
            manifest_path="/tmp/manifest.json",
            session_root="/tmp/session-root",
            agent_name="AGENTSYS-headless",
            agent_id="agent-1234",
        )
        summary_state = HoumaoManagedAgentStateResponse(
            tracked_agent_id=agent_ref,
            identity=identity,
            availability="available",
            turn=HoumaoManagedAgentTurnView(
                phase="ready" if self.m_can_accept_prompt_now else "active",
                active_turn_id=None if self.m_can_accept_prompt_now else "turn-live",
            ),
            last_turn=HoumaoManagedAgentLastTurnView(
                result="none",
                turn_id=None,
                turn_index=None,
                updated_at_utc=None,
            ),
            diagnostics=[],
            mailbox=None,
            gateway=None,
        )
        detail = HoumaoManagedAgentHeadlessDetailView(
            runtime_resumable=True,
            tmux_session_live=True,
            can_accept_prompt_now=self.m_can_accept_prompt_now,
            interruptible=not self.m_can_accept_prompt_now,
            turn=summary_state.turn,
            last_turn=summary_state.last_turn,
            active_turn_started_at_utc=None,
            active_turn_interrupt_requested_at_utc=None,
            last_turn_status=None,
            last_turn_started_at_utc=None,
            last_turn_completed_at_utc=None,
            last_turn_completion_source=None,
            last_turn_returncode=None,
            last_turn_history_summary=None,
            last_turn_error=None,
            mailbox=None,
            gateway=None,
            diagnostics=[],
        )
        return HoumaoManagedAgentDetailResponse(
            tracked_agent_id=agent_ref,
            identity=identity,
            summary_state=summary_state,
            detail=detail,
        )

    def submit_managed_agent_request(
        self,
        agent_ref: str,
        request_model: object,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        self.m_request_calls.append((agent_ref, request_model))
        return HoumaoManagedAgentRequestAcceptedResponse(
            success=True,
            tracked_agent_id=agent_ref,
            request_id="mreq-123",
            request_kind=getattr(request_model, "request_kind", "submit_prompt"),
            disposition="accepted",
            detail="accepted",
            headless_turn_id="turn-123",
            headless_turn_index=1,
        )


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
