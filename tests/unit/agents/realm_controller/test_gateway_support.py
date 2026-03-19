from __future__ import annotations

import json
import sqlite3
import subprocess
import time
from pathlib import Path

from fastapi import HTTPException
import pytest
from pydantic import ValidationError

from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import mailbox_env_bindings
from houmao.agents.realm_controller.errors import GatewayHttpError, LaunchPlanError
from houmao.agents.realm_controller.gateway_models import (
    BlueprintGatewayDefaults,
    GatewayCurrentInstanceV1,
    GatewayMailNotifierPutV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitPromptV1,
)
from houmao.agents.realm_controller.gateway_service import (
    GatewayServiceRuntime,
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
from houmao.mailbox.managed import DeliveryRequest, deliver_message
from houmao.mailbox.protocol import MailboxMessage, serialize_message_document
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name


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
    mailbox = MailboxResolvedConfig(
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


def test_attach_gateway_returns_explicit_unsupported_backend_error(
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

    controller.ensure_gateway_capability()
    result = controller.attach_gateway()

    assert result.status == "error"
    assert result.action == "gateway_attach"
    assert "backend='claude_headless'" in result.detail
    assert "cao_rest" in result.detail
    assert "houmao_server_rest" in result.detail


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
    assert enqueued_rows[-1].unread_summary[0].message_id == message_id
    assert enqueued_rows[-1].enqueued_request_id is not None
    assert all(row.unread_digest == enqueued_rows[-1].unread_digest for row in dedup_rows)


def test_gateway_mail_notifier_summarizes_multiple_unread_messages_in_one_prompt(
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
        assert second_message_id in prompt
    finally:
        runtime.shutdown()

    audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
    enqueued_rows = [row for row in audit_rows if row.outcome == "enqueued"]
    assert enqueued_rows
    latest_row = enqueued_rows[-1]
    assert latest_row.unread_count == 2
    assert [item.message_id for item in latest_row.unread_summary] == [
        first_message_id,
        second_message_id,
    ]


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
    assert enqueued_rows[-1].unread_summary[0].message_id == message_id
