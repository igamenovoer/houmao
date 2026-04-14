from __future__ import annotations

import json
import sqlite3
import shutil
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

import houmao.agents.realm_controller.gateway_service as gateway_service_module
from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    StalwartMailboxResolvedConfig,
)
from houmao.agents.mailbox_runtime_support import (
    install_runtime_mailbox_system_skills_for_tool,
    mailbox_env_bindings,
    resolved_mailbox_config_from_payload,
)
from houmao.agents.realm_controller.agent_identity import (
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
)
from houmao.agents.realm_controller.errors import (
    GatewayHttpError,
    LaunchPlanError,
    SessionManifestError,
)
from houmao.agents.realm_controller.gateway_models import (
    BlueprintGatewayDefaults,
    GatewayCurrentInstanceV1,
    GatewayControlInputRequestV1,
    GatewayExecutionModelReasoningV1,
    GatewayExecutionModelV1,
    GatewayExecutionOverrideV1,
    GatewayMailArchiveRequestV1,
    GatewayMailListRequestV1,
    GatewayMailMarkRequestV1,
    GatewayMailMessageRequestV1,
    GatewayMailMoveRequestV1,
    GatewayMailNotifierPutV1,
    GatewayMailPostRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayPromptControlRequestV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderDefinitionV1,
    GatewayReminderPutV1,
    GatewayReminderSendKeysV1,
    GatewayDesiredConfigV1,
    GatewayTuiTrackingTimingConfigV1,
    GatewayTuiTrackingTimingOverridesV1,
    resolve_gateway_tui_tracking_timing_config,
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
    load_gateway_current_instance,
    load_gateway_desired_config,
    load_gateway_manifest,
    read_gateway_notifier_audit_records,
    refresh_gateway_manifest_publication,
    write_gateway_desired_config,
    write_gateway_current_instance,
)
from houmao.agents.realm_controller.loaders import load_blueprint
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    load_session_manifest,
    parse_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionControlResult,
)
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    _same_session_gateway_is_alive,
    _same_session_gateway_shell_command,
)


if not hasattr(gateway_service_module, "HeadlessInteractiveSession"):
    gateway_service_module.HeadlessInteractiveSession = object
from houmao.agents.realm_controller.backends.tmux_runtime import TmuxPaneRecord
from houmao.cao.models import CaoSuccessResponse, CaoTerminal
from houmao.cao.rest_client import CaoApiError
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.mailbox.filesystem import resolve_active_mailbox_local_sqlite_path
from houmao.mailbox.managed import (
    DeliveryRequest,
    StateUpdateRequest,
    deliver_message,
    update_mailbox_state,
)
from houmao.mailbox.protocol import (
    HOUMAO_NO_REPLY_POLICY_VALUE,
    HOUMAO_OPERATOR_ADDRESS,
    HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
    HOUMAO_REPLY_POLICY_HEADER_NAME,
    MailboxMessage,
    is_operator_origin_headers,
    operator_origin_reply_policy,
    parse_message_document,
    serialize_message_document,
)
from houmao.mailbox.stalwart import (
    StalwartError,
    build_stalwart_credential_ref,
    runtime_stalwart_credential_path,
)
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.server.pair_client import PairAuthorityHealthProbe
from houmao.server.models import (
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentHeadlessDetailView,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
    HoumaoRecentTransition,
    HoumaoStabilityMetadata,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalSnapshotHistoryEntry,
    HoumaoTerminalSnapshotHistoryResponse,
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


def _wait_until(
    predicate: Callable[[], bool],
    *,
    timeout_seconds: float = 5.0,
    interval_seconds: float = 0.05,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval_seconds)
    raise AssertionError("Timed out waiting for condition.")


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


def _sample_cao_plan(tmp_path: Path, *, tool: str = "codex") -> LaunchPlan:
    executable = "claude" if tool == "claude" else "codex"
    home_env_var = "CLAUDE_CONFIG_DIR" if tool == "claude" else "CODEX_HOME"
    return LaunchPlan(
        backend="cao_rest",
        tool=tool,
        executable=executable,
        args=[],
        working_directory=tmp_path,
        home_env_var=home_env_var,
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


def _sample_cao_plan_with_mailbox(tmp_path: Path, *, tool: str = "codex") -> LaunchPlan:
    mailbox_root = tmp_path / "mailbox"
    principal_id = "HOUMAO-gpu"
    address = "HOUMAO-gpu@agents.localhost"
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
    executable = "claude" if tool == "claude" else "codex"
    home_env_var = "CLAUDE_CONFIG_DIR" if tool == "claude" else "CODEX_HOME"
    return LaunchPlan(
        backend="cao_rest",
        tool=tool,
        executable=executable,
        args=[],
        working_directory=tmp_path,
        home_env_var=home_env_var,
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
    principal_id = "HOUMAO-gpu"
    address = "HOUMAO-gpu@agents.localhost"
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
            tmux_session_name="HOUMAO-gpu",
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
    assert paths.gateway_manifest_path.is_file()
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
    gateway_manifest = load_gateway_manifest(paths.gateway_manifest_path)
    assert gateway_manifest.attach_identity == "cao_rest-20260312-120000Z-abcd1234"
    assert gateway_manifest.desired_host == "127.0.0.1"
    assert gateway_manifest.desired_port == 43123
    assert gateway_manifest.gateway_pid is None
    assert gateway_paths_from_manifest_path(manifest_path) == paths
    with sqlite3.connect(paths.queue_path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='gateway_requests'"
        ).fetchone()
    assert row == (1,)


def test_gateway_tui_tracking_timing_config_resolves_precedence() -> None:
    desired = GatewayTuiTrackingTimingConfigV1(
        watch_poll_interval_seconds=0.75,
        stability_threshold_seconds=2.0,
        completion_stability_seconds=2.5,
        unknown_to_stalled_timeout_seconds=15.0,
        stale_active_recovery_seconds=8.0,
        final_stable_active_recovery_seconds=18.0,
    )
    explicit = GatewayTuiTrackingTimingOverridesV1(
        completion_stability_seconds=3.5,
        stale_active_recovery_seconds=4.5,
        final_stable_active_recovery_seconds=9.5,
    )

    resolved = resolve_gateway_tui_tracking_timing_config(
        explicit=explicit,
        desired=desired,
    )

    assert resolved.watch_poll_interval_seconds == 0.75
    assert resolved.stability_threshold_seconds == 2.0
    assert resolved.completion_stability_seconds == 3.5
    assert resolved.unknown_to_stalled_timeout_seconds == 15.0
    assert resolved.stale_active_recovery_seconds == 4.5
    assert resolved.final_stable_active_recovery_seconds == 9.5
    assert resolve_gateway_tui_tracking_timing_config().watch_poll_interval_seconds == 0.5
    assert resolve_gateway_tui_tracking_timing_config().final_stable_active_recovery_seconds == 20.0


@pytest.mark.parametrize(
    "value",
    [0, -1, float("inf"), True, "1.0"],
)
def test_gateway_tui_tracking_timing_config_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ValidationError):
        GatewayTuiTrackingTimingConfigV1(watch_poll_interval_seconds=value)
    with pytest.raises(ValidationError):
        GatewayTuiTrackingTimingOverridesV1(final_stable_active_recovery_seconds=value)


def test_gateway_desired_config_preserves_tui_tracking_timings(tmp_path: Path) -> None:
    manifest_path = default_manifest_path(
        tmp_path,
        "cao_rest",
        "cao_rest-20260312-120000Z-abcd1234",
    )
    _write(manifest_path, "{}\n")
    publication = GatewayCapabilityPublication(
        manifest_path=manifest_path,
        backend="cao_rest",
        tool="codex",
        session_id="cao_rest-20260312-120000Z-abcd1234",
        tmux_session_name="HOUMAO-gpu",
        working_directory=tmp_path,
        backend_state={
            "api_base_url": "http://localhost:9889",
            "terminal_id": "term-123",
            "profile_name": "runtime-profile",
            "profile_path": str(tmp_path / "runtime-profile.md"),
            "parsing_mode": "shadow_only",
        },
        agent_def_dir=tmp_path / "agents",
    )
    paths = ensure_gateway_capability(publication)
    assert (
        load_gateway_desired_config(paths.desired_config_path).desired_tui_tracking_timings is None
    )

    persisted_timings = GatewayTuiTrackingTimingConfigV1(
        watch_poll_interval_seconds=0.25,
        stability_threshold_seconds=1.5,
        completion_stability_seconds=1.75,
        unknown_to_stalled_timeout_seconds=12.0,
        stale_active_recovery_seconds=6.0,
        final_stable_active_recovery_seconds=18.0,
    )
    write_gateway_desired_config(
        paths.desired_config_path,
        GatewayDesiredConfigV1(
            desired_host="127.0.0.1",
            desired_port=43123,
            desired_execution_mode="tmux_auxiliary_window",
            desired_tui_tracking_timings=persisted_timings,
        ),
    )

    ensure_gateway_capability(publication)

    desired_config = load_gateway_desired_config(paths.desired_config_path)
    assert desired_config.desired_tui_tracking_timings == persisted_timings


def test_ensure_gateway_capability_publishes_manifest_first_discovery_env(
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
        agent_identity="HOUMAO-gpu",
        agent_id="published-alpha",
        tmux_session_name="HOUMAO-gpu",
    )

    published_env_calls: list[tuple[str, dict[str, str]]] = []
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda *, session_name, env_vars: published_env_calls.append(
            (session_name, dict(env_vars))
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.resolve_live_agent_record_by_agent_id",
        lambda agent_id: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.publish_live_agent_record",
        lambda record: record,
    )

    controller.ensure_gateway_capability()

    assert ("HOUMAO-gpu",) == tuple({call[0] for call in published_env_calls})
    assert any(
        env_vars.get(AGENT_MANIFEST_PATH_ENV_VAR) == str(manifest_path.resolve())
        and env_vars.get(AGENT_ID_ENV_VAR) == "published-alpha"
        for _, env_vars in published_env_calls
    )


def test_legacy_tmux_session_stop_skips_gateway_teardown(tmp_path: Path) -> None:
    controller = RuntimeSessionController(
        launch_plan=_sample_headless_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=(tmp_path / "legacy-session.json").resolve(),
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="HOUMAO-gpu",
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
        agent_identity="HOUMAO-gpu",
        tmux_session_name="HOUMAO-gpu",
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    captured_attach: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._start_gateway_process",
        lambda *, controller, paths, host, port, execution_mode, tui_tracking_timings: (
            captured_attach.update(
                {
                    "controller": controller,
                    "paths": paths,
                    "host": host,
                    "port": port,
                    "execution_mode": execution_mode,
                    "tui_tracking_timings": tui_tracking_timings,
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
    assert captured_attach["execution_mode"] == "detached_process"
    assert isinstance(captured_attach["tui_tracking_timings"], GatewayTuiTrackingTimingConfigV1)


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
        agent_identity="HOUMAO-local",
        tmux_session_name="HOUMAO-local",
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    captured_attach: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._start_gateway_process",
        lambda *, controller, paths, host, port, execution_mode, tui_tracking_timings: (
            captured_attach.update(
                {
                    "controller": controller,
                    "paths": paths,
                    "host": host,
                    "port": port,
                    "execution_mode": execution_mode,
                    "tui_tracking_timings": tui_tracking_timings,
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
    assert captured_attach["execution_mode"] == "detached_process"
    assert isinstance(captured_attach["tui_tracking_timings"], GatewayTuiTrackingTimingConfigV1)


def test_gateway_service_routes_local_interactive_prompts_through_runtime_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
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


def test_gateway_service_rejects_execution_override_for_local_interactive_prompt_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
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
        with pytest.raises(HTTPException) as exc_info:
            runtime.control_prompt(
                GatewayPromptControlRequestV1(
                    prompt="hello",
                    execution=GatewayExecutionOverrideV1(
                        model=GatewayExecutionModelV1(name="claude-3-7-sonnet")
                    ),
                )
            )
    finally:
        runtime.shutdown()

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error_code"] == "invalid_execution"


def test_gateway_service_exposes_foreground_tmux_execution_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
    )
    _FakeGatewayTrackingRuntime.reset()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.SingleSessionTrackingRuntime",
        _FakeGatewayTrackingRuntime,
    )
    monkeypatch.setenv("HOUMAO_GATEWAY_EXECUTION_MODE", "tmux_auxiliary_window")
    monkeypatch.setenv("HOUMAO_GATEWAY_TMUX_WINDOW_ID", "@9")
    monkeypatch.setenv("HOUMAO_GATEWAY_TMUX_WINDOW_INDEX", "2")
    monkeypatch.setenv("HOUMAO_GATEWAY_TMUX_PANE_ID", "%9")

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    runtime.start()
    try:
        status = runtime.status()
        current_instance = load_gateway_current_instance(paths.current_instance_path)
        gateway_manifest = load_gateway_manifest(paths.gateway_manifest_path)
    finally:
        runtime.shutdown()

    assert status.execution_mode == "tmux_auxiliary_window"
    assert status.gateway_tmux_window_id == "@9"
    assert status.gateway_tmux_window_index == "2"
    assert status.gateway_tmux_pane_id == "%9"
    assert current_instance.execution_mode == "tmux_auxiliary_window"
    assert current_instance.tmux_window_id == "@9"
    assert current_instance.tmux_window_index == "2"
    assert current_instance.tmux_pane_id == "%9"
    assert gateway_manifest.gateway_pid == current_instance.pid
    assert gateway_manifest.gateway_host == "127.0.0.1"
    assert gateway_manifest.gateway_port == 43123
    assert gateway_manifest.gateway_execution_mode == "tmux_auxiliary_window"
    assert gateway_manifest.gateway_tmux_window_index == "2"


def test_refresh_gateway_manifest_publication_overwrites_stale_bookkeeping(tmp_path: Path) -> None:
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_cao_plan(tmp_path),
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="HOUMAO-gpu",
            agent_id=derive_agent_id_from_name("HOUMAO-gpu"),
            tmux_session_name="HOUMAO-gpu",
            session_id="cao-rest-1",
            agent_def_dir=(tmp_path / "agents").resolve(),
            backend_state={
                "api_base_url": "http://127.0.0.1:9889",
                "session_name": "HOUMAO-gpu",
                "terminal_id": "term-123",
                "profile_name": "runtime-profile",
                "profile_path": str(tmp_path / "runtime-profile.md"),
                "parsing_mode": "shadow_only",
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
            tmux_session_name="HOUMAO-gpu",
            working_directory=tmp_path,
            backend_state={
                "api_base_url": "http://127.0.0.1:9889",
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
    paths.gateway_manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "attach_identity": "stale",
                "backend": "cao_rest",
                "tmux_session_name": "stale",
                "working_directory": str(tmp_path),
                "backend_metadata": {
                    "api_base_url": "http://127.0.0.1:9999",
                    "terminal_id": "term-stale",
                    "profile_name": "stale-profile",
                    "profile_path": str(tmp_path / "stale-profile.md"),
                    "parsing_mode": "shadow_only",
                },
                "gateway_pid": 99999,
                "gateway_host": "127.0.0.1",
                "gateway_port": 49999,
                "gateway_protocol_version": "v1",
                "gateway_execution_mode": "detached_process",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_gateway_current_instance(
        paths.current_instance_path,
        GatewayCurrentInstanceV1(
            pid=43210,
            host="127.0.0.1",
            port=43123,
            execution_mode="detached_process",
            managed_agent_instance_epoch=1,
            managed_agent_instance_id="term-123",
        ),
    )

    refreshed = refresh_gateway_manifest_publication(paths)

    assert refreshed.attach_identity == "cao-rest-1"
    assert refreshed.tmux_session_name == "HOUMAO-gpu"
    assert refreshed.gateway_pid == 43210
    assert refreshed.gateway_port == 43123
    assert refreshed.desired_port == 43123
    persisted = load_gateway_manifest(paths.gateway_manifest_path)
    assert persisted.gateway_pid == 43210
    assert persisted.backend_metadata.terminal_id == "term-123"


def test_gateway_service_routes_local_interactive_interrupts_through_runtime_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
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
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
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


def test_gateway_service_builds_local_interactive_tui_tracking_identity_from_manifest_authority(
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")

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
    assert identity.tmux_session_name == "HOUMAO-local"
    assert identity.tmux_window_name == "agent"
    assert identity.terminal_aliases == []
    assert identity.agent_name == "HOUMAO-local"
    assert identity.agent_id == derive_agent_id_from_name("HOUMAO-local")
    assert identity.manifest_path == str(manifest_path)


def test_gateway_service_exposes_local_interactive_state_and_prompt_note_routes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
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
        assert identity.tmux_session_name == "HOUMAO-local"
        assert identity.tmux_window_name == "agent"
        assert identity.terminal_aliases == []
        assert identity.agent_name == "HOUMAO-local"
        assert identity.agent_id == derive_agent_id_from_name("HOUMAO-local")

        state_response = client.get("/v1/control/tui/state")
        assert state_response.status_code == 200
        assert state_response.json()["terminal_id"] == "local-interactive-1"
        assert (
            state_response.json()["tracked_session"]["tracked_session_id"] == "local-interactive-1"
        )
        assert state_response.json()["tracked_session"]["terminal_aliases"] == []

        history_response = client.get("/v1/control/tui/history?limit=7")
        assert history_response.status_code == 200
        assert history_response.json()["tracked_session_id"] == "local-interactive-1"
        assert history_response.json()["entries"][0]["stability"]["signature"] == "limit-7"

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


def test_gateway_service_routes_local_interactive_prompt_through_direct_control_when_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
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
            "/v1/control/prompt",
            json=GatewayPromptControlRequestV1(prompt="hello").model_dump(mode="json"),
        )
        assert response.status_code == 200
        assert response.json() == {
            "action": "submit_prompt",
            "detail": "Prompt dispatched.",
            "forced": False,
            "sent": True,
            "status": "ok",
        }
    finally:
        runtime.shutdown()

    assert fake_session.prompt_calls == [("hello", None)]
    assert _FakeGatewayTrackingRuntime.m_prompt_notes == ["hello"]


def test_gateway_service_rejects_local_interactive_prompt_when_tui_not_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
    )
    _FakeGatewayTrackingRuntime.reset()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.SingleSessionTrackingRuntime",
        _FakeGatewayTrackingRuntime,
    )

    def _busy_state(self: _FakeGatewayTrackingRuntime) -> HoumaoTerminalStateResponse:
        state = _sample_gateway_tracked_state(self.m_identity)
        return state.model_copy(
            update={
                "surface": state.surface.model_copy(
                    update={"accepting_input": "no", "editing_input": "yes", "ready_posture": "no"}
                ),
                "turn": state.turn.model_copy(update={"phase": "active"}),
                "stability": state.stability.model_copy(update={"stable": False}),
            }
        )

    monkeypatch.setattr(_FakeGatewayTrackingRuntime, "current_state", _busy_state)

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    runtime.start()
    try:
        response = client.post(
            "/v1/control/prompt",
            json=GatewayPromptControlRequestV1(prompt="hello").model_dump(mode="json"),
        )
        assert response.status_code == 409
        assert response.json()["detail"]["error_code"] == "not_ready"
    finally:
        runtime.shutdown()

    assert fake_session.prompt_calls == []
    assert _FakeGatewayTrackingRuntime.m_prompt_notes == []


def test_gateway_service_force_bypasses_local_interactive_prompt_readiness_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
    )
    _FakeGatewayTrackingRuntime.reset()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.SingleSessionTrackingRuntime",
        _FakeGatewayTrackingRuntime,
    )

    def _busy_state(self: _FakeGatewayTrackingRuntime) -> HoumaoTerminalStateResponse:
        state = _sample_gateway_tracked_state(self.m_identity)
        return state.model_copy(
            update={
                "surface": state.surface.model_copy(
                    update={"accepting_input": "no", "editing_input": "yes", "ready_posture": "no"}
                ),
                "turn": state.turn.model_copy(update={"phase": "active"}),
                "stability": state.stability.model_copy(update={"stable": False}),
            }
        )

    monkeypatch.setattr(_FakeGatewayTrackingRuntime, "current_state", _busy_state)

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    runtime.start()
    try:
        response = client.post(
            "/v1/control/prompt",
            json=GatewayPromptControlRequestV1(prompt="hello", force=True).model_dump(mode="json"),
        )
        assert response.status_code == 200
        assert response.json()["forced"] is True
    finally:
        runtime.shutdown()

    assert fake_session.prompt_calls == [("hello", None)]
    assert _FakeGatewayTrackingRuntime.m_prompt_notes == ["hello"]


def test_gateway_service_rejects_unsupported_backend_for_direct_prompt_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
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
        runtime.m_attach_contract.backend = "codex_app_server"  # type: ignore[assignment]
        response = client.post(
            "/v1/control/prompt",
            json=GatewayPromptControlRequestV1(prompt="hello").model_dump(mode="json"),
        )
        assert response.status_code == 501
        assert response.json()["detail"]["error_code"] == "unsupported_backend"
    finally:
        runtime.shutdown()


def test_gateway_service_rejects_overlapping_local_headless_direct_prompt_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_headless_gateway_root(tmp_path)
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
        lambda **_kwargs: True,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    runtime.start()
    try:
        first_response = client.post(
            "/v1/control/prompt",
            json=GatewayPromptControlRequestV1(prompt="hello").model_dump(mode="json"),
        )
        assert first_response.status_code == 200
        assert fake_session.started_event.wait(timeout=2.0)

        second_response = client.post(
            "/v1/control/prompt",
            json=GatewayPromptControlRequestV1(prompt="again").model_dump(mode="json"),
        )
        assert second_response.status_code == 409
        assert second_response.json()["detail"]["error_code"] == "not_ready"
    finally:
        fake_session.release_event.set()
        runtime.shutdown()

    assert fake_session.prompt_calls[0][0] == "hello"


def test_gateway_service_routes_server_managed_headless_prompts_through_houmao_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_headless_gateway_root(
        tmp_path,
        managed_api_base_url="http://127.0.0.1:9889",
        managed_agent_ref="claude-headless-1",
        include_local_authority=False,
    )
    fake_client = _FakeManagedPairClient()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resolve_pair_authority_client",
        lambda *, base_url: SimpleNamespace(
            client=fake_client,
            health=PairAuthorityHealthProbe(status="ok", houmao_service="houmao-server"),
        ),
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
                    execution=GatewayExecutionOverrideV1(
                        model=GatewayExecutionModelV1(
                            name="claude-3-7-sonnet",
                            reasoning=GatewayExecutionModelReasoningV1(level=6),
                        )
                    ),
                ),
            )
        )
        assert accepted.request_kind == "submit_prompt"
        assert fake_client.started_event.wait(timeout=2.0)
    finally:
        fake_client.release_event.set()
        runtime.shutdown()

    assert fake_client.prompt_calls == ["hello"]
    assert getattr(fake_client.request_models[0], "execution") == GatewayExecutionOverrideV1(
        model=GatewayExecutionModelV1(
            name="claude-3-7-sonnet",
            reasoning=GatewayExecutionModelReasoningV1(level=6),
        )
    )


def test_gateway_service_blocks_server_managed_headless_when_prompt_admission_is_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_headless_gateway_root(
        tmp_path,
        managed_api_base_url="http://127.0.0.1:9889",
        managed_agent_ref="claude-headless-1",
        include_local_authority=False,
    )
    fake_client = _FakeManagedPairClient(block_prompt=True)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resolve_pair_authority_client",
        lambda *, base_url: SimpleNamespace(
            client=fake_client,
            health=PairAuthorityHealthProbe(status="ok", houmao_service="houmao-passive-server"),
        ),
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
        assert fake_client.started_event.wait(timeout=2.0)

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
        fake_client.release_event.set()
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
            tmux_session_name="HOUMAO-gpu",
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
        agent_identity="HOUMAO-gpu",
        tmux_session_name="HOUMAO-gpu",
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
    assert captured_unset["session_name"] == "HOUMAO-gpu"
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
            tmux_session_name="HOUMAO-gpu",
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
        agent_identity="HOUMAO-gpu",
        tmux_session_name="HOUMAO-gpu",
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
        assert session_name == "HOUMAO-gpu"
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


def test_same_session_gateway_shell_command_expands_live_tmux_pane(tmp_path: Path) -> None:
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    _seed_local_interactive_gateway_root(tmp_path)
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None

    command = _same_session_gateway_shell_command(
        paths=paths,
        host="127.0.0.1",
        port=43123,
        tui_tracking_timings=GatewayTuiTrackingTimingConfigV1(
            watch_poll_interval_seconds=0.25,
            stability_threshold_seconds=1.5,
            completion_stability_seconds=1.75,
            unknown_to_stalled_timeout_seconds=12.0,
            stale_active_recovery_seconds=6.0,
            final_stable_active_recovery_seconds=18.0,
        ),
    )

    assert "tmux display-message -p -t \"$TMUX_PANE\" '#{window_id}'" in command
    assert "tmux display-message -p -t \"$TMUX_PANE\" '#{window_index}'" in command
    assert "--tui-watch-poll-interval-seconds 0.25" in command
    assert "--tui-stale-active-recovery-seconds 6.0" in command
    assert "--tui-final-stable-active-recovery-seconds 18.0" in command
    assert "'$TMUX_PANE'" not in command


def test_gateway_service_main_parses_tui_tracking_args(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    class _FakeConfig:
        def __init__(self, *args: object, **kwargs: object) -> None:
            captured["uvicorn_config"] = (args, kwargs)

    class _FakeServer:
        def __init__(self, config: object, *, runtime: object, requested_host: object) -> None:
            captured["server_config"] = config
            captured["server_runtime"] = runtime
            captured["requested_host"] = requested_host

        def run(self) -> None:
            captured["server_run"] = True

    fake_runtime = object()

    def _fake_from_gateway_root(**kwargs: object) -> object:
        captured.update(kwargs)
        return fake_runtime

    monkeypatch.setattr(gateway_service_module.uvicorn, "Config", _FakeConfig)
    monkeypatch.setattr(gateway_service_module, "_GatewayUvicornServer", _FakeServer)
    monkeypatch.setattr(gateway_service_module, "create_app", lambda *, runtime: object())
    monkeypatch.setattr(
        gateway_service_module.GatewayServiceRuntime,
        "from_gateway_root",
        staticmethod(_fake_from_gateway_root),
    )

    exit_code = gateway_service_module.main(
        [
            "--gateway-root",
            str(tmp_path / "gateway"),
            "--host",
            "127.0.0.1",
            "--port",
            "43123",
            "--tui-watch-poll-interval-seconds",
            "0.25",
            "--tui-stability-threshold-seconds",
            "1.5",
            "--tui-completion-stability-seconds",
            "1.75",
            "--tui-unknown-to-stalled-timeout-seconds",
            "12",
            "--tui-stale-active-recovery-seconds",
            "6",
            "--tui-final-stable-active-recovery-seconds",
            "18",
        ]
    )

    timings = captured["tui_tracking_timings"]
    assert exit_code == 0
    assert captured["server_runtime"] is fake_runtime
    assert isinstance(timings, GatewayTuiTrackingTimingOverridesV1)
    assert timings.watch_poll_interval_seconds == 0.25
    assert timings.stability_threshold_seconds == 1.5
    assert timings.completion_stability_seconds == 1.75
    assert timings.unknown_to_stalled_timeout_seconds == 12.0
    assert timings.stale_active_recovery_seconds == 6.0
    assert timings.final_stable_active_recovery_seconds == 18.0


def test_same_session_gateway_liveness_ignores_current_agent_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_instance = GatewayCurrentInstanceV1(
        pid=4242,
        host="127.0.0.1",
        port=43123,
        execution_mode="tmux_auxiliary_window",
        tmux_window_id="@9",
        tmux_window_index="1",
        tmux_pane_id="%9",
        managed_agent_instance_epoch=1,
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.list_tmux_panes_shared",
        lambda *, session_name: (
            TmuxPaneRecord(
                pane_id="%1",
                session_name=session_name,
                window_id="@1",
                window_index="0",
                window_name="agent",
                pane_index="0",
                pane_active=True,
                pane_dead=False,
                pane_pid=1111,
            ),
            TmuxPaneRecord(
                pane_id="%9",
                session_name=session_name,
                window_id="@9",
                window_index="1",
                window_name="gateway",
                pane_index="0",
                pane_active=False,
                pane_dead=False,
                pane_pid=4242,
            ),
        ),
    )

    assert (
        _same_session_gateway_is_alive(
            session_name="HOUMAO-local",
            current_instance=current_instance,
        )
        is True
    )


def test_runtime_owned_foreground_gateway_attach_persists_tmux_execution_handle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    _seed_local_interactive_gateway_root(tmp_path)
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    controller = RuntimeSessionController(
        launch_plan=_sample_local_interactive_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="HOUMAO-local",
        tmux_session_name="HOUMAO-local",
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
        assert session_name == "HOUMAO-local"
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

    first_attach = controller.attach_gateway(execution_mode_override="tmux_auxiliary_window")
    assert first_attach.status == "ok"
    first_current_instance = load_gateway_current_instance(paths.current_instance_path)
    first_desired_config = load_gateway_desired_config(paths.desired_config_path)
    assert first_current_instance.execution_mode == "tmux_auxiliary_window"
    assert first_current_instance.tmux_window_id == "@9"
    assert first_current_instance.tmux_window_index == "1"
    assert first_current_instance.tmux_pane_id == "%9"
    assert first_desired_config.desired_execution_mode == "tmux_auxiliary_window"
    assert first_desired_config.desired_port == 43123

    tmux_state["alive"]["%9"] = False

    second_attach = controller.attach_gateway()
    assert second_attach.status == "ok"
    second_current_instance = load_gateway_current_instance(paths.current_instance_path)
    second_desired_config = load_gateway_desired_config(paths.desired_config_path)
    assert second_current_instance.execution_mode == "tmux_auxiliary_window"
    assert second_current_instance.tmux_window_id == "@10"
    assert second_current_instance.tmux_window_index == "2"
    assert second_current_instance.tmux_pane_id == "%10"
    assert second_desired_config.desired_execution_mode == "tmux_auxiliary_window"

    detach_result = controller.detach_gateway()
    assert detach_result.status == "ok"
    assert tmux_state["kill_calls"] == [
        ["kill-window", "-t", "@9"],
        ["kill-window", "-t", "@10"],
    ]
    assert not paths.current_instance_path.exists()


def test_runtime_owned_foreground_gateway_attach_tolerates_initial_tmux_pane_delay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    _seed_local_interactive_gateway_root(tmp_path)
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    controller = RuntimeSessionController(
        launch_plan=_sample_local_interactive_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="HOUMAO-local",
        tmux_session_name="HOUMAO-local",
    )

    tmux_state = {
        "current": None,
        "list_calls": 0,
    }

    def _fake_run_tmux(
        args: list[str], *, timeout_seconds: float | None = None
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        if args[:1] != ["new-window"]:
            raise AssertionError(f"Unexpected tmux call: {args}")
        tmux_state["current"] = ("@9", "1", "%9")
        write_gateway_current_instance(
            paths.current_instance_path,
            GatewayCurrentInstanceV1(
                pid=4242,
                host="127.0.0.1",
                port=43123,
                execution_mode="tmux_auxiliary_window",
                tmux_window_id="@9",
                tmux_window_index="1",
                tmux_pane_id="%9",
                managed_agent_instance_epoch=1,
            ),
        )
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="@9\t1\t%9\n",
            stderr="",
        )

    def _fake_list_tmux_panes(*, session_name: str):  # type: ignore[no-untyped-def]
        assert session_name == "HOUMAO-local"
        tmux_state["list_calls"] += 1
        if tmux_state["list_calls"] < 3:
            return ()
        window_id, window_index, pane_id = tmux_state["current"]
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

    result = controller.attach_gateway(execution_mode_override="tmux_auxiliary_window")

    assert result.status == "ok"
    assert load_gateway_current_instance(paths.current_instance_path).tmux_pane_id == "%9"
    assert tmux_state["list_calls"] >= 2


def test_runtime_owned_foreground_gateway_attach_accepts_current_instance_before_tmux_pane_visible(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    _seed_local_interactive_gateway_root(tmp_path)
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    controller = RuntimeSessionController(
        launch_plan=_sample_local_interactive_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="HOUMAO-local",
        tmux_session_name="HOUMAO-local",
    )

    def _fake_run_tmux(
        args: list[str], *, timeout_seconds: float | None = None
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        if args[:1] != ["new-window"]:
            raise AssertionError(f"Unexpected tmux call: {args}")
        write_gateway_current_instance(
            paths.current_instance_path,
            GatewayCurrentInstanceV1(
                pid=4242,
                host="127.0.0.1",
                port=43123,
                execution_mode="tmux_auxiliary_window",
                tmux_window_id="@9",
                tmux_window_index="1",
                tmux_pane_id="%9",
                managed_agent_instance_epoch=1,
            ),
        )
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="@9\t1\t%9\n",
            stderr="",
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
        lambda *, session_name: (),
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

    result = controller.attach_gateway(execution_mode_override="tmux_auxiliary_window")

    assert result.status == "ok"
    assert load_gateway_current_instance(paths.current_instance_path).tmux_pane_id == "%9"


def test_same_session_gateway_detach_refuses_reserved_window_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    _seed_local_interactive_gateway_root(tmp_path)
    controller = RuntimeSessionController(
        launch_plan=_sample_local_interactive_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="HOUMAO-local",
        tmux_session_name="HOUMAO-local",
    )

    reserved_window_instance = type(
        "CurrentInstance",
        (),
        {
            "execution_mode": "tmux_auxiliary_window",
            "tmux_window_id": "@0",
            "tmux_window_index": "0",
            "tmux_pane_id": "%0",
        },
    )()

    def _fake_list_tmux_panes(*, session_name: str):  # type: ignore[no-untyped-def]
        assert session_name == "HOUMAO-local"
        return (
            type(
                "Pane",
                (),
                {
                    "pane_id": "%0",
                    "session_name": session_name,
                    "window_id": "@0",
                    "window_index": "0",
                    "window_name": "agent",
                    "pane_index": "0",
                    "pane_active": True,
                    "pane_dead": False,
                    "pane_pid": 4242,
                },
            )(),
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.load_gateway_current_instance",
        lambda _path: reserved_window_instance,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.list_tmux_panes_shared",
        _fake_list_tmux_panes,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.run_tmux_shared",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("reserved tmux window `0` must not be targeted")
        ),
    )

    result = controller.detach_gateway()

    assert result.status == "error"
    assert "reserved agent window `0`" in result.detail


def test_same_session_gateway_stale_cleanup_skips_reserved_window_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    _seed_local_interactive_gateway_root(tmp_path)
    controller = RuntimeSessionController(
        launch_plan=_sample_local_interactive_plan(tmp_path),
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        agent_def_dir=(tmp_path / "agents").resolve(),
        backend_session=_FakeInteractiveSession(),
        agent_identity="HOUMAO-local",
        tmux_session_name="HOUMAO-local",
    )

    reserved_window_instance = type(
        "CurrentInstance",
        (),
        {
            "execution_mode": "tmux_auxiliary_window",
            "tmux_window_id": "@0",
            "tmux_window_index": "0",
            "tmux_pane_id": "%0",
        },
    )()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.load_gateway_current_instance",
        lambda _path: reserved_window_instance,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.list_tmux_panes_shared",
        lambda *, session_name: (),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.run_tmux_shared",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("reserved tmux window `0` must not be targeted")
        ),
    )

    status = controller.gateway_status()

    assert status.gateway_health == "not_attached"


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
            session_name="HOUMAO-gpu",
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
    tool: str = "codex",
) -> Path:
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    plan = (
        _sample_cao_plan_with_mailbox(tmp_path, tool=tool)
        if mailbox_enabled
        else _sample_cao_plan(tmp_path, tool=tool)
    )
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="HOUMAO-gpu",
            agent_id=derive_agent_id_from_name("HOUMAO-gpu"),
            tmux_session_name="HOUMAO-gpu",
            session_id="cao-rest-1",
            agent_def_dir=(tmp_path / "agents").resolve(),
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "HOUMAO-gpu",
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
            tool=tool,
            session_id="cao-rest-1",
            tmux_session_name="HOUMAO-gpu",
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
    include_local_authority: bool = True,
) -> Path:
    manifest_path = default_manifest_path(tmp_path, "claude_headless", "claude-headless-1")
    agent_def_dir = (tmp_path / "agents").resolve() if include_local_authority else None
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_headless_plan(tmp_path),
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="HOUMAO-headless",
            agent_id=derive_agent_id_from_name("HOUMAO-headless"),
            tmux_session_name="HOUMAO-headless",
            session_id="claude-headless-1",
            agent_def_dir=agent_def_dir,
            backend_state={
                "session_id": "claude-session-1",
                "api_base_url": managed_api_base_url,
                "managed_agent_ref": managed_agent_ref,
            },
        )
    )
    write_session_manifest(manifest_path, payload)
    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="claude_headless",
            tool="claude",
            session_id="claude-headless-1",
            tmux_session_name="HOUMAO-headless",
            working_directory=tmp_path,
            backend_state={"session_id": "claude-session-1"},
            agent_def_dir=tmp_path / "agents",
        )
    )
    return paths.gateway_root


def _seed_local_interactive_gateway_root(tmp_path: Path) -> Path:
    manifest_path = default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    backend_state = {
        "turn_index": 2,
        "role_bootstrap_applied": True,
        "working_directory": str(tmp_path),
        "tmux_session_name": "HOUMAO-local",
    }
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_local_interactive_plan(tmp_path),
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="HOUMAO-local",
            agent_id=derive_agent_id_from_name("HOUMAO-local"),
            tmux_session_name="HOUMAO-local",
            session_id="local-interactive-1",
            agent_def_dir=(tmp_path / "agents").resolve(),
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
            tmux_session_name="HOUMAO-local",
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
        tmux_session_name: str = "HOUMAO-headless",
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
        self.execution_models: list[object | None] = []
        self.session_selections: list[object | None] = []
        self.block_prompt = block_prompt
        self.started_event = threading.Event()
        self.release_event = threading.Event()

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
        session_selection: object | None = None,
        execution_model: object | None = None,
    ) -> list[object]:
        self.prompt_calls.append((prompt, turn_artifact_dir_name))
        self.session_selections.append(session_selection)
        self.execution_models.append(execution_model)
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
        self.send_prompt_calls: list[dict[str, object]] = []

    def persist_manifest(self, *, refresh_registry: bool = True) -> None:
        self.persist_manifest_calls.append(refresh_registry)

    def send_prompt(
        self,
        prompt: str,
        *,
        session_selection: object | None = None,
        turn_artifact_dir_name: str | None = None,
        execution_model: object | None = None,
        refresh_registry: bool = True,
    ) -> list[object]:
        self.send_prompt_calls.append(
            {
                "prompt": prompt,
                "session_selection": session_selection,
                "turn_artifact_dir_name": turn_artifact_dir_name,
                "execution_model": execution_model,
                "refresh_registry": refresh_registry,
            }
        )
        result = self.backend_session.send_prompt(
            prompt,
            turn_artifact_dir_name=turn_artifact_dir_name,
            session_selection=session_selection,
            execution_model=execution_model,
        )
        self.persist_manifest(refresh_registry=refresh_registry)
        return result

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


class _FakeManagedPairClient:
    def __init__(
        self,
        *,
        block_prompt: bool = False,
        pair_authority_kind: str = "houmao-server",
    ) -> None:
        self.pair_authority_kind = pair_authority_kind
        self.block_prompt = block_prompt
        self.prompt_calls: list[str] = []
        self.request_models: list[object] = []
        self.started_event = threading.Event()
        self.release_event = threading.Event()

    def get_managed_agent_state_detail(self, agent_ref: str) -> HoumaoManagedAgentDetailResponse:
        identity = HoumaoManagedAgentIdentity(
            tracked_agent_id=agent_ref,
            transport="headless",
            tool="claude",
            session_name=None,
            terminal_id=None,
            runtime_session_id=agent_ref,
            tmux_session_name="HOUMAO-headless",
            tmux_window_name="agent",
            manifest_path="/tmp/manifest.json",
            session_root="/tmp/runtime",
            agent_name="HOUMAO-headless",
            agent_id=agent_ref,
        )
        summary_state = HoumaoManagedAgentStateResponse(
            tracked_agent_id=agent_ref,
            identity=identity,
            availability="available",
            turn=HoumaoManagedAgentTurnView(phase="ready", active_turn_id=None),
            last_turn=HoumaoManagedAgentLastTurnView(result="none", turn_id=None, turn_index=None),
            diagnostics=[],
            mailbox=None,
            gateway=None,
        )
        return HoumaoManagedAgentDetailResponse(
            tracked_agent_id=agent_ref,
            identity=identity,
            summary_state=summary_state,
            detail=HoumaoManagedAgentHeadlessDetailView(
                runtime_resumable=True,
                tmux_session_live=True,
                can_accept_prompt_now=True,
                interruptible=False,
                turn=summary_state.turn,
                last_turn=summary_state.last_turn,
                mailbox=None,
                gateway=None,
                diagnostics=[],
            ),
        )

    def submit_managed_agent_request(
        self,
        agent_ref: str,
        request_model: object,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        self.request_models.append(request_model)
        request_kind = getattr(request_model, "request_kind", "submit_prompt")
        prompt = getattr(request_model, "prompt", None)
        if isinstance(prompt, str):
            self.prompt_calls.append(prompt)
            self.started_event.set()
            if self.block_prompt:
                self.release_event.wait(timeout=5.0)
        return HoumaoManagedAgentRequestAcceptedResponse(
            success=True,
            tracked_agent_id=agent_ref,
            request_id=f"req-{request_kind}",
            request_kind=request_kind,
            disposition="accepted",
            detail="accepted",
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


def _sample_gateway_tracked_snapshot_history(
    identity: HoumaoTrackedSessionIdentity,
    *,
    limit: int,
) -> HoumaoTerminalSnapshotHistoryResponse:
    terminal_id = _tracked_terminal_id(identity)
    state = _sample_gateway_tracked_state(identity)
    return HoumaoTerminalSnapshotHistoryResponse(
        terminal_id=terminal_id,
        tracked_session_id=identity.tracked_session_id,
        entries=[
            HoumaoTerminalSnapshotHistoryEntry(
                recorded_at_utc="2026-03-25T18:00:00+00:00",
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

    def snapshot_history(self, *, limit: int) -> HoumaoTerminalSnapshotHistoryResponse:
        return _sample_gateway_tracked_snapshot_history(self.m_identity, limit=limit)

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
            agent_name="HOUMAO-gpu",
            agent_id=derive_agent_id_from_name("HOUMAO-gpu"),
            tmux_session_name="HOUMAO-gpu",
            backend_state={
                "api_base_url": "http://localhost:9889",
                "session_name": "HOUMAO-gpu",
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
            tmux_session_name="HOUMAO-gpu",
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


def _install_fake_live_mailbox_projection(
    monkeypatch: pytest.MonkeyPatch,
    *,
    manifest_path: Path,
) -> None:
    """Resolve live mailbox env from the current manifest for notifier tests."""

    def _read_tmux_env(*, session_name: str, variable_name: str) -> str | None:
        del session_name
        handle = load_session_manifest(manifest_path)
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        mailbox = resolved_mailbox_config_from_payload(
            payload.launch_plan.mailbox,
            manifest_path=handle.path,
        )
        if mailbox is None:
            return None
        return mailbox_env_bindings(mailbox).get(variable_name)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime.read_tmux_session_environment_value",
        _read_tmux_env,
    )


def _deliver_unread_mailbox_message(
    tmp_path: Path,
    *,
    message_id: str = "msg-20260316T090000Z-a1b2c3d4e5f64798aabbccddeeff0011",
    created_at_utc: str = "2026-03-16T09:00:00Z",
    subject: str = "Gateway unread reminder",
    recipient_principal_id: str = "HOUMAO-gpu",
    recipient_address: str = "HOUMAO-gpu@agents.localhost",
    body_markdown: str = "Body\n",
) -> str:
    mailbox_root = tmp_path / "mailbox"
    sender = MailboxPrincipal(
        principal_id="HOUMAO-sender",
        address="HOUMAO-sender@agents.localhost",
    )
    recipient = MailboxPrincipal(
        principal_id=recipient_principal_id,
        address=recipient_address,
    )
    bootstrap_filesystem_mailbox(mailbox_root, principal=sender)
    bootstrap_filesystem_mailbox(mailbox_root, principal=recipient)

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
    _write_canonical_staged_message(staged_message, request, body_markdown=body_markdown)
    deliver_message(mailbox_root, request)
    return request.message_id


def test_gateway_request_model_rejects_invalid_submit_prompt_payload() -> None:
    with pytest.raises(ValidationError, match="prompt"):
        GatewayRequestCreateV1(
            kind="submit_prompt",
            payload=GatewayRequestPayloadSubmitPromptV1(prompt=""),
        )


def test_gateway_reminder_models_validate_schedule_repeat_and_batch_shape() -> None:
    with pytest.raises(ValidationError, match="exactly one of prompt or send_keys"):
        GatewayReminderDefinitionV1(
            mode="one_off",
            title="wake up",
            ranking=0,
            start_after_seconds=10,
        )

    with pytest.raises(ValidationError, match="exactly one of prompt or send_keys"):
        GatewayReminderDefinitionV1(
            mode="one_off",
            title="wake up",
            prompt="wake up",
            send_keys=GatewayReminderSendKeysV1(sequence="<\\[Escape\\]>"),
            ranking=0,
            start_after_seconds=10,
        )

    with pytest.raises(
        ValidationError, match="exactly one of start_after_seconds or deliver_at_utc"
    ):
        GatewayReminderDefinitionV1(
            mode="one_off",
            title="wake up",
            prompt="wake up",
            ranking=0,
            start_after_seconds=10,
            deliver_at_utc="2026-03-31T00:00:00+00:00",
        )

    with pytest.raises(ValidationError, match="repeat reminders require interval_seconds"):
        GatewayReminderDefinitionV1(
            mode="repeat",
            title="wake up",
            prompt="wake up",
            ranking=0,
            start_after_seconds=10,
        )

    with pytest.raises(
        ValidationError, match="one_off reminders must not include interval_seconds"
    ):
        GatewayReminderDefinitionV1(
            mode="one_off",
            title="wake up",
            prompt="wake up",
            ranking=0,
            start_after_seconds=10,
            interval_seconds=30,
        )

    with pytest.raises(ValidationError, match="reminders must not be empty"):
        GatewayReminderCreateBatchV1(reminders=[])

    send_keys_reminder = GatewayReminderDefinitionV1(
        mode="one_off",
        title="dismiss dialog",
        send_keys=GatewayReminderSendKeysV1(sequence="<[Escape]>"),
        ranking=0,
        start_after_seconds=10,
    )
    assert send_keys_reminder.prompt is None
    assert send_keys_reminder.send_keys is not None
    assert send_keys_reminder.send_keys.ensure_enter is True


def test_gateway_reminder_routes_batch_create_list_put_and_delete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
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

    create_response = client.post(
        "/v1/reminders",
        json=GatewayReminderCreateBatchV1(
            reminders=[
                GatewayReminderDefinitionV1(
                    mode="one_off",
                    title="effective reminder",
                    prompt="effective reminder prompt",
                    ranking=-10,
                    start_after_seconds=60,
                ),
                GatewayReminderDefinitionV1(
                    mode="one_off",
                    title="blocked reminder",
                    prompt="blocked reminder prompt",
                    ranking=5,
                    start_after_seconds=30,
                ),
            ]
        ).model_dump(mode="json"),
    )

    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["effective_reminder_id"] is not None
    assert len(create_payload["reminders"]) == 2
    first_reminder = create_payload["reminders"][0]
    second_reminder = create_payload["reminders"][1]
    first_id = str(first_reminder["reminder_id"])
    second_id = str(second_reminder["reminder_id"])
    assert first_reminder["selection_state"] == "effective"
    assert first_reminder["delivery_state"] == "scheduled"
    assert first_reminder["delivery_kind"] == "prompt"
    assert first_reminder["send_keys"] is None
    assert second_reminder["selection_state"] == "blocked"
    assert second_reminder["blocked_by_reminder_id"] == first_id

    list_response = client.get("/v1/reminders")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["effective_reminder_id"] == first_id
    assert [reminder["reminder_id"] for reminder in list_payload["reminders"]] == [
        first_id,
        second_id,
    ]

    get_response = client.get(f"/v1/reminders/{first_id}")
    assert get_response.status_code == 200
    assert get_response.json()["prompt"] == "effective reminder prompt"
    assert get_response.json()["delivery_kind"] == "prompt"
    assert get_response.json()["send_keys"] is None

    put_response = client.put(
        f"/v1/reminders/{first_id}",
        json=GatewayReminderPutV1(
            mode="one_off",
            title="effective reminder delayed",
            prompt="effective reminder updated",
            ranking=10,
            start_after_seconds=120,
            paused=False,
        ).model_dump(mode="json"),
    )
    assert put_response.status_code == 200
    assert put_response.json()["selection_state"] == "blocked"
    assert put_response.json()["blocked_by_reminder_id"] == second_id

    list_after_put = client.get("/v1/reminders")
    assert list_after_put.status_code == 200
    assert list_after_put.json()["effective_reminder_id"] == second_id

    delete_response = client.delete(f"/v1/reminders/{second_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["action"] == "delete_reminder"
    assert delete_response.json()["reminder_id"] == second_id

    remaining_payload = client.get("/v1/reminders").json()
    assert remaining_payload["effective_reminder_id"] == first_id
    assert [reminder["reminder_id"] for reminder in remaining_payload["reminders"]] == [first_id]

    assert client.get(f"/v1/reminders/{second_id}").status_code == 404
    assert client.delete(f"/v1/reminders/{second_id}").status_code == 404
    assert (
        client.post("/v1/reminders", json={"schema_version": 1, "reminders": []}).status_code == 422
    )
    assert runtime.status().queue_depth == 0


def test_gateway_rest_backed_reminder_routes_reject_send_keys_delivery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
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

    create_response = client.post(
        "/v1/reminders",
        json=GatewayReminderCreateBatchV1(
            reminders=[
                GatewayReminderDefinitionV1(
                    mode="one_off",
                    title="dismiss dialog",
                    send_keys=GatewayReminderSendKeysV1(sequence="<[Escape]>"),
                    ranking=0,
                    start_after_seconds=5,
                )
            ]
        ).model_dump(mode="json"),
    )

    assert create_response.status_code == 422
    assert "unsupported" in create_response.json()["detail"].lower()
    assert runtime.list_reminders().reminders == []


def test_gateway_reminder_ranking_tie_breaks_by_creation_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
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

    first_result = runtime.create_reminders(
        GatewayReminderCreateBatchV1(
            reminders=[
                GatewayReminderDefinitionV1(
                    mode="one_off",
                    title="first created",
                    prompt="first created prompt",
                    ranking=0,
                    start_after_seconds=60,
                )
            ]
        )
    )
    time.sleep(0.01)
    second_result = runtime.create_reminders(
        GatewayReminderCreateBatchV1(
            reminders=[
                GatewayReminderDefinitionV1(
                    mode="one_off",
                    title="second created",
                    prompt="second created prompt",
                    ranking=0,
                    start_after_seconds=60,
                )
            ]
        )
    )

    first_id = first_result.reminders[0].reminder_id
    second_id = second_result.reminders[0].reminder_id
    reminder_list = runtime.list_reminders()
    assert reminder_list.effective_reminder_id == first_id
    assert [reminder.reminder_id for reminder in reminder_list.reminders] == [first_id, second_id]
    assert runtime.get_reminder(reminder_id=second_id).blocked_by_reminder_id == first_id


def test_gateway_repeat_reminder_reschedules_without_catchup_burst(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _BlockingRepeatFakeCaoRestClient(_FakeCaoRestClient):
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            super().__init__(base_url=base_url, timeout_seconds=timeout_seconds)
            self.first_repeat_started = threading.Event()
            self.release_first_repeat = threading.Event()
            self.repeat_prompt_count = 0

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            self.submitted_prompts.append((terminal_id, message))
            if message == "repeat reminder":
                self.repeat_prompt_count += 1
                if self.repeat_prompt_count == 1:
                    self.first_repeat_started.set()
                    assert self.release_first_repeat.wait(timeout=5.0)
            return CaoSuccessResponse(success=True)

    gateway_root = _seed_cao_gateway_root(tmp_path)
    fake_client = _BlockingRepeatFakeCaoRestClient(base_url="http://localhost:9889")
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
        reminder = runtime.create_reminders(
            GatewayReminderCreateBatchV1(
                reminders=[
                    GatewayReminderDefinitionV1(
                        mode="repeat",
                        title="repeat reminder",
                        prompt="repeat reminder",
                        ranking=0,
                        start_after_seconds=0.05,
                        interval_seconds=0.05,
                    )
                ]
            )
        )
        reminder_id = reminder.reminders[0].reminder_id

        _wait_until(lambda: fake_client.first_repeat_started.is_set())
        time.sleep(0.16)
        fake_client.release_first_repeat.set()

        _wait_until(lambda: fake_client.repeat_prompt_count >= 2)
        time.sleep(0.02)
        assert fake_client.repeat_prompt_count == 2

        live_reminder = runtime.get_reminder(reminder_id=reminder_id)
        assert live_reminder.mode == "repeat"
        assert live_reminder.delivery_state in {"scheduled", "overdue"}
        assert live_reminder.selection_state == "effective"
    finally:
        runtime.delete_reminder(reminder_id=reminder_id)
        runtime.shutdown()


def test_gateway_paused_effective_reminder_blocks_lower_ranked_dispatch(
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
        create_result = runtime.create_reminders(
            GatewayReminderCreateBatchV1(
                reminders=[
                    GatewayReminderDefinitionV1(
                        mode="one_off",
                        title="paused effective",
                        prompt="paused effective prompt",
                        ranking=-10,
                        paused=True,
                        start_after_seconds=0.01,
                    ),
                    GatewayReminderDefinitionV1(
                        mode="one_off",
                        title="ready reminder",
                        prompt="ready reminder prompt",
                        ranking=0,
                        paused=False,
                        start_after_seconds=0.01,
                    ),
                ]
            )
        )
        paused_id = create_result.reminders[0].reminder_id
        blocked_id = create_result.reminders[1].reminder_id

        time.sleep(0.2)
        assert fake_client.submitted_prompts == []

        paused_reminder = runtime.get_reminder(reminder_id=paused_id)
        blocked_reminder = runtime.get_reminder(reminder_id=blocked_id)
        assert paused_reminder.selection_state == "effective"
        assert paused_reminder.delivery_state == "overdue"
        assert paused_reminder.paused is True
        assert blocked_reminder.selection_state == "blocked"
        assert blocked_reminder.blocked_by_reminder_id == paused_id

        updated_reminder = runtime.put_reminder(
            reminder_id=paused_id,
            request_payload=GatewayReminderPutV1(
                mode="one_off",
                title="paused effective delayed",
                prompt="paused effective prompt",
                ranking=10,
                paused=True,
                start_after_seconds=60,
            ),
        )
        assert updated_reminder.selection_state == "blocked"
        assert updated_reminder.blocked_by_reminder_id == blocked_id

        _wait_until(
            lambda: fake_client.submitted_prompts == [("term-123", "ready reminder prompt")],
            timeout_seconds=5.0,
        )
        assert all(
            message != "paused effective prompt" for _, message in fake_client.submitted_prompts
        )
    finally:
        runtime.shutdown()


def test_gateway_local_tmux_send_keys_reminders_execute_with_ensure_enter_rules(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
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
        create_result = runtime.create_reminders(
            GatewayReminderCreateBatchV1(
                reminders=[
                    GatewayReminderDefinitionV1(
                        mode="one_off",
                        title="submit slash command",
                        send_keys=GatewayReminderSendKeysV1(sequence="/model"),
                        ranking=-30,
                        start_after_seconds=0.01,
                    ),
                    GatewayReminderDefinitionV1(
                        mode="one_off",
                        title="keep one trailing enter",
                        send_keys=GatewayReminderSendKeysV1(sequence="/model<[Enter]>"),
                        ranking=-20,
                        start_after_seconds=0.01,
                    ),
                    GatewayReminderDefinitionV1(
                        mode="one_off",
                        title="dismiss dialog",
                        send_keys=GatewayReminderSendKeysV1(
                            sequence="<[Escape]>",
                            ensure_enter=False,
                        ),
                        ranking=-10,
                        start_after_seconds=0.01,
                    ),
                ]
            )
        )

        assert [reminder.delivery_kind for reminder in create_result.reminders] == [
            "send_keys",
            "send_keys",
            "send_keys",
        ]
        assert create_result.reminders[0].send_keys is not None
        assert create_result.reminders[0].send_keys.ensure_enter is True
        assert create_result.reminders[2].send_keys is not None
        assert create_result.reminders[2].send_keys.ensure_enter is False

        _wait_until(lambda: len(fake_controller.send_input_calls) >= 3)
        assert fake_controller.send_input_calls == [
            ("/model<[Enter]>", False),
            ("/model<[Enter]>", False),
            ("<[Escape]>", False),
        ]
        assert fake_session.prompt_calls == []
        assert _FakeGatewayTrackingRuntime.m_prompt_notes == []
    finally:
        runtime.shutdown()


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
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
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


def test_gateway_service_starts_from_manifest_when_internal_attach_contract_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    paths.attach_path.unlink()
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    runtime.start()
    try:
        status = runtime.status()
    finally:
        runtime.shutdown()

    assert status.managed_agent_connectivity == "connected"
    assert paths.attach_path.is_file()


def test_gateway_service_rest_backed_recovery_relaunches_from_manifest_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, terminal_id="term-stale")
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    relaunch_calls: list[str] = []

    class _RecoveringFakeCaoRestClient(_FakeCaoRestClient):
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            super().__init__(base_url, timeout_seconds=timeout_seconds)
            self.m_live_terminal_id = "term-fresh"

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            if terminal_id != self.m_live_terminal_id:
                raise CaoApiError(
                    method="GET",
                    url=f"{self.base_url}/terminals/{terminal_id}",
                    detail="terminal missing",
                    status_code=404,
                )
            return super().get_terminal(terminal_id)

    def _relaunch() -> SimpleNamespace:
        relaunch_calls.append("relaunch")
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload["backend_state"]["terminal_id"] = "term-fresh"
        payload["cao"]["terminal_id"] = "term-fresh"
        payload["interactive"]["terminal_id"] = "term-fresh"
        payload["gateway_authority"]["attach"]["terminal_id"] = "term-fresh"
        payload["gateway_authority"]["control"]["terminal_id"] = "term-fresh"
        manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(status="ok", detail="Runtime relaunched.")

    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _RecoveringFakeCaoRestClient(*args, **kwargs),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_kwargs: SimpleNamespace(relaunch=_relaunch),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.tmux_session_exists",
        lambda *, session_name: session_name == "HOUMAO-gpu",
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    status = runtime.status()

    assert status.managed_agent_connectivity == "connected"
    assert status.request_admission == "open"
    assert relaunch_calls == ["relaunch"]


def test_gateway_service_restart_recovers_accepted_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path)
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
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
    manifest_path.unlink()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    with pytest.raises(SessionManifestError, match="not found"):
        GatewayServiceRuntime.from_gateway_root(
            gateway_root=gateway_root,
            host="127.0.0.1",
            port=43123,
        )


def test_gateway_mail_notifier_supports_manifest_backed_mailbox_without_tmux_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: _FakeCaoRestClient(base_url="http://localhost:9889"),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime.read_tmux_session_environment_value",
        lambda **kwargs: None,
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )

    status = runtime.get_mail_notifier()
    assert status.enabled is False
    assert status.supported is True
    assert status.support_error is None

    enabled = runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=60))
    assert enabled.supported is True
    assert enabled.enabled is True
    assert enabled.interval_seconds == 60


def test_gateway_mail_routes_support_filesystem_mailbox_without_runtime_roundtrip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    unread_message_id = _deliver_unread_mailbox_message(tmp_path)
    operator_mailbox_dir = tmp_path / "mailbox" / "mailboxes" / HOUMAO_OPERATOR_ADDRESS
    with sqlite3.connect((tmp_path / "mailbox" / "index.sqlite").resolve()) as connection:
        connection.execute(
            "DELETE FROM mailbox_registrations WHERE address = ?",
            (HOUMAO_OPERATOR_ADDRESS,),
        )
        connection.commit()
    if operator_mailbox_dir.exists():
        shutil.rmtree(operator_mailbox_dir)
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
        "/v1/mail/list",
        json=GatewayMailListRequestV1(read_state="unread", limit=10).model_dump(mode="json"),
    )
    assert check_response.status_code == 200
    check_payload = check_response.json()
    assert check_payload["transport"] == "filesystem"
    assert check_payload["message_count"] == 1
    assert check_payload["unread_count"] == 1
    assert check_payload["messages"][0]["message_ref"] == f"filesystem:{unread_message_id}"

    peek_response = client.post(
        "/v1/mail/peek",
        json=GatewayMailMessageRequestV1(
            message_ref=f"filesystem:{unread_message_id}",
        ).model_dump(mode="json"),
    )
    assert peek_response.status_code == 200
    assert peek_response.json()["operation"] == "peek"
    assert peek_response.json()["message"]["read"] is False

    read_response = client.post(
        "/v1/mail/read",
        json=GatewayMailMessageRequestV1(
            message_ref=f"filesystem:{unread_message_id}",
        ).model_dump(mode="json"),
    )
    assert read_response.status_code == 200
    assert read_response.json()["operation"] == "read"
    assert read_response.json()["message"]["read"] is True

    send_response = client.post(
        "/v1/mail/send",
        json=GatewayMailSendRequestV1(
            to=["HOUMAO-sender@agents.localhost"],
            subject="Gateway route send",
            body_content="filesystem send body",
        ).model_dump(mode="json"),
    )
    assert send_response.status_code == 200
    send_payload = send_response.json()
    assert send_payload["operation"] == "send"
    assert send_payload["transport"] == "filesystem"
    assert send_payload["message"]["message_ref"].startswith("filesystem:msg-")

    post_response = client.post(
        "/v1/mail/post",
        json={
            "schema_version": 1,
            "subject": "Gateway route post",
            "body_content": "filesystem operator-origin body",
        },
    )
    assert post_response.status_code == 200
    post_payload = post_response.json()
    assert post_payload["operation"] == "post"
    assert post_payload["transport"] == "filesystem"
    assert post_payload["message"]["unread"] is True
    assert post_payload["message"]["sender"]["address"] == HOUMAO_OPERATOR_ADDRESS
    assert post_payload["message"]["to"][0]["address"] == "HOUMAO-gpu@agents.localhost"
    with sqlite3.connect((tmp_path / "mailbox" / "index.sqlite").resolve()) as connection:
        post_row = connection.execute(
            "SELECT canonical_path FROM messages WHERE message_id = ?",
            (post_payload["message"]["message_ref"].split(":", 1)[1],),
        ).fetchone()
    assert post_row is not None
    post_message = parse_message_document(Path(str(post_row[0])).read_text(encoding="utf-8"))
    assert is_operator_origin_headers(post_message.headers) is True
    assert (
        post_message.headers[HOUMAO_REPLY_POLICY_HEADER_NAME]
        == HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE
    )
    assert (
        operator_origin_reply_policy(post_message.headers)
        == HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE
    )
    assert [principal.address for principal in post_message.reply_to] == [HOUMAO_OPERATOR_ADDRESS]

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

    mark_response = client.post(
        "/v1/mail/mark",
        json=GatewayMailMarkRequestV1(
            message_refs=[f"filesystem:{unread_message_id}"],
            answered=True,
        ).model_dump(mode="json"),
    )
    assert mark_response.status_code == 200
    assert mark_response.json()["operation"] == "mark"
    assert mark_response.json()["messages"][0]["answered"] is True

    move_response = client.post(
        "/v1/mail/move",
        json=GatewayMailMoveRequestV1(
            message_refs=[f"filesystem:{unread_message_id}"],
            destination_box="archive",
        ).model_dump(mode="json"),
    )
    assert move_response.status_code == 200
    assert move_response.json()["operation"] == "move"
    assert move_response.json()["messages"][0]["box"] == "archive"
    assert move_response.json()["messages"][0]["archived"] is True

    operator_reply_response = client.post(
        "/v1/mail/reply",
        json=GatewayMailReplyRequestV1(
            message_ref=post_payload["message"]["message_ref"],
            body_content="operator reply body",
        ).model_dump(mode="json"),
    )
    assert operator_reply_response.status_code == 200
    operator_reply_payload = operator_reply_response.json()
    assert operator_reply_payload["operation"] == "reply"
    assert operator_reply_payload["message"]["to"][0]["address"] == HOUMAO_OPERATOR_ADDRESS

    with sqlite3.connect((tmp_path / "mailbox" / "index.sqlite").resolve()) as connection:
        operator_count = connection.execute(
            "SELECT COUNT(*) FROM mailbox_registrations WHERE address = ?",
            (HOUMAO_OPERATOR_ADDRESS,),
        ).fetchone()
    assert operator_count == (1,)


def test_gateway_mail_send_reports_bare_agent_name_with_address_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    bootstrap_filesystem_mailbox(
        tmp_path / "mailbox",
        principal=MailboxPrincipal(
            principal_id="HOUMAO-daq-mgr",
            address="daq-mgr@houmao.localhost",
        ),
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
    client = TestClient(create_app(runtime=runtime))

    response = client.post(
        "/v1/mail/send",
        json=GatewayMailSendRequestV1(
            to=["daq-mgr"],
            subject="Gateway route send",
            body_content="filesystem send body",
        ).model_dump(mode="json"),
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "filesystem mailbox recipient `daq-mgr` is not a registered mailbox address" in detail
    assert "`/v1/mail/send` expects email-like mailbox addresses" in detail
    assert "not managed-agent names" in detail
    assert "Did you mean `daq-mgr@houmao.localhost`?" in detail


def test_gateway_mail_send_reports_inactive_registration_separately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    mailbox_root = tmp_path / "mailbox"
    bootstrap_filesystem_mailbox(
        mailbox_root,
        principal=MailboxPrincipal(
            principal_id="HOUMAO-stale",
            address="stale@houmao.localhost",
        ),
    )
    with sqlite3.connect((mailbox_root / "index.sqlite").resolve()) as connection:
        connection.execute(
            "UPDATE mailbox_registrations SET status = 'inactive' WHERE address = ?",
            ("stale@houmao.localhost",),
        )
        connection.commit()
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
        "/v1/mail/send",
        json=GatewayMailSendRequestV1(
            to=["stale@houmao.localhost"],
            subject="Gateway route send",
            body_content="filesystem send body",
        ).model_dump(mode="json"),
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert (
        "filesystem mailbox recipient `stale@houmao.localhost` is registered with status "
        "`inactive`, not `active`"
    ) in detail
    assert "does not have an active mailbox registration" not in detail


def test_gateway_mail_reply_enabled_operator_post_routes_reply_to_reserved_operator_mailbox(
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
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    post_response = client.post(
        "/v1/mail/post",
        json=GatewayMailPostRequestV1(
            subject="Gateway route post",
            body_content="filesystem operator-origin body",
            reply_policy=HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
        ).model_dump(mode="json"),
    )
    assert post_response.status_code == 200
    post_payload = post_response.json()
    with sqlite3.connect((tmp_path / "mailbox" / "index.sqlite").resolve()) as connection:
        post_row = connection.execute(
            "SELECT canonical_path FROM messages WHERE message_id = ?",
            (post_payload["message"]["message_ref"].split(":", 1)[1],),
        ).fetchone()
    assert post_row is not None
    post_message = parse_message_document(Path(str(post_row[0])).read_text(encoding="utf-8"))
    assert is_operator_origin_headers(post_message.headers) is True
    assert (
        operator_origin_reply_policy(post_message.headers)
        == HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE
    )
    assert [principal.address for principal in post_message.reply_to] == [HOUMAO_OPERATOR_ADDRESS]

    reply_response = client.post(
        "/v1/mail/reply",
        json=GatewayMailReplyRequestV1(
            message_ref=post_payload["message"]["message_ref"],
            body_content="ready",
        ).model_dump(mode="json"),
    )
    assert reply_response.status_code == 200
    reply_payload = reply_response.json()
    assert reply_payload["operation"] == "reply"
    with sqlite3.connect((tmp_path / "mailbox" / "index.sqlite").resolve()) as connection:
        reply_row = connection.execute(
            "SELECT canonical_path FROM messages WHERE message_id = ?",
            (reply_payload["message"]["message_ref"].split(":", 1)[1],),
        ).fetchone()
    assert reply_row is not None
    reply_message = parse_message_document(Path(str(reply_row[0])).read_text(encoding="utf-8"))
    assert [principal.address for principal in reply_message.to] == [HOUMAO_OPERATOR_ADDRESS]


def test_gateway_mail_explicit_no_reply_operator_post_rejects_reply(
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
        host="127.0.0.1",
        port=43123,
    )
    client = TestClient(create_app(runtime=runtime))

    post_response = client.post(
        "/v1/mail/post",
        json=GatewayMailPostRequestV1(
            subject="Gateway route post",
            body_content="filesystem operator-origin body",
            reply_policy=HOUMAO_NO_REPLY_POLICY_VALUE,
        ).model_dump(mode="json"),
    )
    assert post_response.status_code == 200
    post_payload = post_response.json()
    with sqlite3.connect((tmp_path / "mailbox" / "index.sqlite").resolve()) as connection:
        post_row = connection.execute(
            "SELECT canonical_path FROM messages WHERE message_id = ?",
            (post_payload["message"]["message_ref"].split(":", 1)[1],),
        ).fetchone()
    assert post_row is not None
    post_message = parse_message_document(Path(str(post_row[0])).read_text(encoding="utf-8"))
    assert is_operator_origin_headers(post_message.headers) is True
    assert operator_origin_reply_policy(post_message.headers) == HOUMAO_NO_REPLY_POLICY_VALUE
    assert post_message.reply_to == []

    reply_response = client.post(
        "/v1/mail/reply",
        json=GatewayMailReplyRequestV1(
            message_ref=post_payload["message"]["message_ref"],
            body_content="should fail",
        ).model_dump(mode="json"),
    )
    assert reply_response.status_code == 422
    assert "operator-origin" in reply_response.json()["detail"]


def test_gateway_mail_self_send_stays_unread_until_explicit_mark_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    _install_fake_live_mailbox_projection(monkeypatch, manifest_path=manifest_path)
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    runtime.start()
    client = TestClient(create_app(runtime=runtime))
    try:
        send_response = client.post(
            "/v1/mail/send",
            json=GatewayMailSendRequestV1(
                to=["HOUMAO-gpu@agents.localhost"],
                subject="Gateway self-send",
                body_content="filesystem self-send body",
            ).model_dump(mode="json"),
        )
        assert send_response.status_code == 200
        send_payload = send_response.json()
        self_message_ref = send_payload["message"]["message_ref"]
        assert send_payload["message"]["unread"] is True

        check_response = client.post(
            "/v1/mail/list",
            json=GatewayMailListRequestV1(read_state="unread", limit=10).model_dump(mode="json"),
        )
        assert check_response.status_code == 200
        check_payload = check_response.json()
        assert check_payload["unread_count"] == 1
        assert [message["message_ref"] for message in check_payload["messages"]] == [
            self_message_ref
        ]

        status = runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))
        assert status.enabled is True
        assert status.supported is True

        _wait_until(lambda: len(fake_client.submitted_prompts) >= 1, timeout_seconds=5.0)
        _wait_until(
            lambda: any(
                row.outcome == "enqueued"
                and row.unread_summary
                and row.unread_summary[0].message_ref == self_message_ref
                for row in read_gateway_notifier_audit_records(paths.queue_path)
            ),
            timeout_seconds=5.0,
        )

        state_response = client.post(
            "/v1/mail/archive",
            json=GatewayMailArchiveRequestV1(
                message_refs=[self_message_ref],
            ).model_dump(mode="json"),
        )
        assert state_response.status_code == 200
        assert state_response.json()["operation"] == "archive"

        post_mark_read_check = client.post(
            "/v1/mail/list",
            json=GatewayMailListRequestV1(read_state="unread", limit=10).model_dump(mode="json"),
        )
        assert post_mark_read_check.status_code == 200
        assert post_mark_read_check.json()["unread_count"] == 0

        _wait_until(
            lambda: any(
                row.outcome == "empty" and row.unread_count == 0
                for row in read_gateway_notifier_audit_records(paths.queue_path)
            ),
            timeout_seconds=5.0,
        )
    finally:
        runtime.shutdown()


def test_gateway_mail_read_route_marks_filesystem_message_read_without_queue_mutation(
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
        "/v1/mail/read",
        json=GatewayMailMessageRequestV1(
            message_ref=f"filesystem:{unread_message_id}",
        ).model_dump(mode="json"),
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "schema_version",
        "operation",
        "transport",
        "principal_id",
        "address",
        "message",
    }
    assert response.json()["transport"] == "filesystem"
    assert response.json()["operation"] == "read"
    assert response.json()["message"]["message_ref"] == f"filesystem:{unread_message_id}"
    assert response.json()["message"]["read"] is True
    assert runtime.status().queue_depth == 0

    local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
        mailbox_root,
        address="HOUMAO-gpu@agents.localhost",
    )
    with sqlite3.connect(local_sqlite_path) as connection:
        state_row = connection.execute(
            "SELECT is_read FROM message_state WHERE message_id = ?",
            (unread_message_id,),
        ).fetchone()
    assert state_row == (1,)


def test_gateway_mail_mark_route_rejects_unsupported_mailbox_state_fields(
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
        "/v1/mail/mark",
        json={
            "schema_version": 1,
            "message_refs": [f"filesystem:{unread_message_id}"],
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
        "/v1/mail/list",
        json=GatewayMailListRequestV1().model_dump(mode="json"),
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

        def list_messages(
            self,
            *,
            box: str,
            read_state: str,
            answered_state: str,
            archived: bool | None,
            limit: int | None,
            since: str | None,
        ) -> list[dict[str, object]]:
            del box, read_state, answered_state, archived, limit, since
            return [
                {
                    "id": "mail-1",
                    "threadId": "thread-1",
                    "receivedAt": "2026-03-19T08:00:00Z",
                    "subject": "Stalwart unread",
                    "preview": "preview",
                    "body": "full body",
                    "from": [{"email": "sender@agents.localhost", "name": "Sender"}],
                    "to": [{"email": "HOUMAO-gpu@agents.localhost"}],
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

        def mark(
            self,
            *,
            message_ref: str,
            read: bool | None,
            answered: bool | None,
            archived: bool | None,
        ) -> dict[str, object]:
            del answered, archived
            self.m_read_updates.append((message_ref, bool(read)))
            return {
                "id": message_ref,
                "threadId": "thread-1",
                "receivedAt": "2026-03-19T08:00:00Z",
                "subject": "Stalwart unread",
                "preview": "preview",
                "body": "full body",
                "from": [{"email": "sender@agents.localhost", "name": "Sender"}],
                "to": [{"email": "HOUMAO-gpu@agents.localhost"}],
                "cc": [],
                "replyTo": [],
                "attachments": [],
                "read": bool(read),
                "answered": False,
                "archived": False,
                "box": "inbox",
                "unread": not read,
            }

    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_mailbox.StalwartJmapClient",
        _FakeStalwartJmapClient,
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
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
        "/v1/mail/list",
        json=GatewayMailListRequestV1(read_state="unread", limit=5).model_dump(mode="json"),
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

    post_response = client.post(
        "/v1/mail/post",
        json=GatewayMailPostRequestV1(
            subject="ignored by fake client",
            body_content="operator-origin body",
        ).model_dump(mode="json"),
    )
    assert post_response.status_code == 422
    assert "unsupported" in post_response.json()["detail"]

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
        "/v1/mail/mark",
        json=GatewayMailMarkRequestV1(
            message_refs=["stalwart:mail-1"],
            read=True,
        ).model_dump(mode="json"),
    )
    assert state_response.status_code == 200
    assert state_response.json()["transport"] == "stalwart"
    assert state_response.json()["messages"][0]["message_ref"] == "stalwart:mail-1"
    assert state_response.json()["messages"][0]["read"] is True


def test_gateway_mail_mark_route_rejects_malformed_stalwart_message_normalization(
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

        def status(self) -> dict[str, object]:
            return {"account_id": "acc-1"}

        def mark(
            self,
            *,
            message_ref: str,
            read: bool | None,
            answered: bool | None,
            archived: bool | None,
        ) -> dict[str, object]:
            del read, answered, archived
            return {
                "threadId": "thread-1",
                "receivedAt": "2026-03-19T08:00:00Z",
                "subject": "Stalwart unread",
                "preview": "preview",
                "body": "full body",
                "from": [{"email": "sender@agents.localhost", "name": "Sender"}],
                "to": [{"email": "HOUMAO-gpu@agents.localhost"}],
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
        "/v1/mail/mark",
        json=GatewayMailMarkRequestV1(
            message_refs=["stalwart:mail-1"],
            read=True,
        ).model_dump(mode="json"),
    )
    assert response.status_code == 502
    assert "mailbox payload is missing `id`" in response.json()["detail"]


def test_gateway_mail_notifier_polls_mailbox_local_state_and_repeats_after_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    _install_fake_live_mailbox_projection(monkeypatch, manifest_path=manifest_path)
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    message_id = _deliver_unread_mailbox_message(tmp_path)
    update_mailbox_state(
        tmp_path / "mailbox",
        StateUpdateRequest(
            address="HOUMAO-gpu@agents.localhost",
            message_id=message_id,
            read=True,
            answered=True,
        ),
    )
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
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

        _wait_until(lambda: len(fake_client.submitted_prompts) >= 2, timeout_seconds=5.0)

        first_prompt = fake_client.submitted_prompts[0][1]
        repeated_prompt = fake_client.submitted_prompts[1][1]
        assert message_id not in first_prompt
        assert message_id not in repeated_prompt
        assert (
            "List unread mail through the shared gateway mailbox API for this round."
            in first_prompt
        )
        assert "- `GET http://127.0.0.1:43123/v1/mail/status`" in first_prompt
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
        _wait_until(lambda: len(fake_client.submitted_prompts) >= 1, timeout_seconds=5.0)
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
    assert enqueued_rows
    assert not any(row.outcome == "dedup_skip" for row in audit_rows)
    assert len(enqueued_rows) >= 2
    assert enqueued_rows[-1].unread_count == 1
    assert enqueued_rows[-1].unread_summary[0].message_ref == f"filesystem:{message_id}"
    assert enqueued_rows[-1].enqueued_request_id is not None


def test_gateway_mail_notifier_local_interactive_waits_for_prompt_ready_posture_and_repeats(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_local_interactive_gateway_root(tmp_path)
    message_id = _deliver_unread_mailbox_message(tmp_path)
    fake_session = _FakeGatewayHeadlessSession(
        tmux_session_name="HOUMAO-local",
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
        lambda *, session_name: session_name == "HOUMAO-local",
    )
    _FakeGatewayTrackingRuntime.reset()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.SingleSessionTrackingRuntime",
        _FakeGatewayTrackingRuntime,
    )

    readiness = {"busy": True}

    def _tracking_state(self: _FakeGatewayTrackingRuntime) -> HoumaoTerminalStateResponse:
        state = _sample_gateway_tracked_state(self.m_identity)
        if not readiness["busy"]:
            return state
        return state.model_copy(
            update={
                "surface": state.surface.model_copy(
                    update={"accepting_input": "no", "editing_input": "yes", "ready_posture": "no"}
                ),
                "turn": state.turn.model_copy(update={"phase": "active"}),
                "stability": state.stability.model_copy(update={"stable": False}),
            }
        )

    monkeypatch.setattr(_FakeGatewayTrackingRuntime, "current_state", _tracking_state)

    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="HOUMAO-gpu",
        address="HOUMAO-gpu@agents.localhost",
        filesystem_root=(tmp_path / "mailbox").resolve(),
        bindings_version="2026-03-16T08:00:00.000001Z",
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    monkeypatch.setattr(runtime, "_require_live_notifier_mailbox_config_locked", lambda: mailbox)
    monkeypatch.setattr(runtime, "_load_mailbox_config", lambda: mailbox)
    runtime.start()
    try:
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))

        time.sleep(1.3)
        assert fake_session.prompt_calls == []

        readiness["busy"] = False
        _wait_until(lambda: len(fake_session.prompt_calls) >= 1, timeout_seconds=5.0)
        first_prompt = fake_session.prompt_calls[0][0]
        assert message_id not in first_prompt
        assert (
            "List unread mail through the shared gateway mailbox API for this round."
            in first_prompt
        )

        readiness["busy"] = True
        prompt_count = len(fake_session.prompt_calls)
        time.sleep(1.3)
        assert len(fake_session.prompt_calls) == prompt_count

        readiness["busy"] = False
        _wait_until(lambda: len(fake_session.prompt_calls) >= prompt_count + 1, timeout_seconds=5.0)
        repeated_prompt = fake_session.prompt_calls[-1][0]
        assert message_id not in repeated_prompt
        assert (
            "List unread mail through the shared gateway mailbox API for this round."
            in repeated_prompt
        )
    finally:
        runtime.shutdown()

    paths = gateway_paths_from_manifest_path(
        default_manifest_path(tmp_path, "local_interactive", "local-interactive-1")
    )
    assert paths is not None
    audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
    busy_rows = [row for row in audit_rows if row.outcome == "busy_skip"]
    enqueued_rows = [row for row in audit_rows if row.outcome == "enqueued"]
    assert busy_rows
    assert enqueued_rows
    assert len(enqueued_rows) >= 2
    assert not any(row.outcome == "dedup_skip" for row in audit_rows)
    assert any(row.detail is not None and "not prompt-ready" in row.detail for row in busy_rows)
    log_text = paths.log_path.read_text(encoding="utf-8")
    assert "mail notifier poll deferred because the managed session is not prompt-ready" in log_text
    assert "suppressed" not in log_text


def test_gateway_mail_notifier_gemini_headless_processes_mail_with_owned_unattended_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="HOUMAO-gpu",
        address="HOUMAO-gpu@agents.localhost",
        filesystem_root=(tmp_path / "mailbox").resolve(),
        bindings_version="2026-04-02T12:00:00.000001Z",
    )
    launch_plan = LaunchPlan(
        backend="gemini_headless",
        tool="gemini",
        executable="gemini",
        args=["--approval-mode=yolo", "--sandbox=false"],
        working_directory=tmp_path,
        home_env_var="GEMINI_CLI_HOME",
        home_path=tmp_path / "home",
        env=mailbox_env_bindings(mailbox),
        env_var_names=sorted(mailbox_env_bindings(mailbox).keys()),
        role_injection=RoleInjectionPlan(
            method="bootstrap_message",
            role_name="role",
            prompt="role prompt",
            bootstrap_message="bootstrap",
        ),
        metadata={},
        mailbox=mailbox,
    )

    manifest_path = default_manifest_path(tmp_path, "gemini_headless", "gemini-headless-1")
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="HOUMAO-gpu",
            agent_id=derive_agent_id_from_name("HOUMAO-gpu"),
            tmux_session_name="HOUMAO-gemini",
            session_id="gemini-headless-1",
            agent_def_dir=(tmp_path / "agents").resolve(),
            backend_state={"session_id": "sess-gemini-1"},
        )
    )
    write_session_manifest(manifest_path, payload)
    gateway_root = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="gemini_headless",
            tool="gemini",
            session_id="gemini-headless-1",
            tmux_session_name="HOUMAO-gemini",
            working_directory=tmp_path,
            backend_state={"session_id": "sess-gemini-1"},
            agent_def_dir=tmp_path / "agents",
        )
    ).gateway_root
    install_runtime_mailbox_system_skills_for_tool(tool="gemini", home_path=tmp_path / "home")

    output_path = tmp_path / "tmp" / "gateway-mail-processed.txt"

    class _GeminiGatewayHeadlessSession:
        def __init__(self) -> None:
            self.backend = "gemini_headless"
            self.state = type(
                "State",
                (),
                {
                    "turn_index": 0,
                    "tmux_session_name": "HOUMAO-gemini",
                    "session_id": "sess-gemini-1",
                },
            )()
            self.prompt_calls: list[tuple[str, str | None]] = []

        def send_prompt(
            self,
            prompt: str,
            *,
            turn_artifact_dir_name: str | None = None,
            session_selection: object | None = None,
            execution_model: object | None = None,
        ) -> list[object]:
            self.prompt_calls.append((prompt, turn_artifact_dir_name))
            if (
                "--approval-mode=yolo" in launch_plan.args
                and "--sandbox=false" in launch_plan.args
                and "List unread mail through the shared gateway mailbox API for this round."
                in prompt
            ):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("processed by gemini notifier\n", encoding="utf-8")
            self.state.turn_index += 1
            return []

        def interrupt(self) -> SessionControlResult:
            return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    fake_session = _GeminiGatewayHeadlessSession()
    fake_controller = _FakeGatewayHeadlessController(fake_session)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.HeadlessInteractiveSession",
        _GeminiGatewayHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_kwargs: fake_controller,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.tmux_session_exists",
        lambda *, session_name: session_name == "HOUMAO-gemini",
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )

    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    monkeypatch.setattr(runtime, "_require_live_notifier_mailbox_config_locked", lambda: mailbox)
    monkeypatch.setattr(runtime, "_load_mailbox_config", lambda: mailbox)
    runtime.start()
    try:
        runtime.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=1))
        _deliver_unread_mailbox_message(tmp_path)
        _wait_until(lambda: output_path.exists(), timeout_seconds=5.0)
    finally:
        runtime.shutdown()

    assert fake_session.prompt_calls
    prompt = fake_session.prompt_calls[0][0]
    assert "List unread mail through the shared gateway mailbox API for this round." in prompt
    assert "In Gemini this Houmao skill is installed natively." in prompt
    assert "Invoke `houmao-process-emails-via-gateway` by name for this round." in prompt
    assert (
        "Use the lower-level Houmao mailbox communication skill `houmao-agent-email-comms` by name"
    ) in prompt
    assert "skills/mailbox/houmao-process-emails-via-gateway/SKILL.md" not in prompt
    assert ".agents/skills/houmao-process-emails-via-gateway/SKILL.md" not in prompt
    assert ".agents/skills/mailbox/houmao-process-emails-via-gateway/SKILL.md" not in prompt
    assert "Open `" not in prompt
    assert output_path.read_text(encoding="utf-8") == "processed by gemini notifier\n"


def test_gateway_mail_notifier_renders_gateway_bootstrap_prompt_with_houmao_gateway_skill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    _install_fake_live_mailbox_projection(monkeypatch, manifest_path=manifest_path)
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    install_runtime_mailbox_system_skills_for_tool(tool="codex", home_path=tmp_path / "home")
    first_message_id = _deliver_unread_mailbox_message(
        tmp_path,
        message_id="msg-20260316T090000Z-11111111111111111111111111111111",
        created_at_utc="2026-03-16T09:00:00Z",
        subject="Gateway unread reminder one",
        body_markdown="TOP-SECRET-ONE\n",
    )
    second_message_id = _deliver_unread_mailbox_message(
        tmp_path,
        message_id="msg-20260316T090100Z-22222222222222222222222222222222",
        created_at_utc="2026-03-16T09:01:00Z",
        subject="Gateway unread reminder two",
        body_markdown="TOP-SECRET-TWO\n",
    )
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
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
        assert first_message_id not in prompt
        assert second_message_id not in prompt
        assert "Unread email summaries in the current snapshot:" not in prompt
        assert prompt.index(
            "List unread mail through the shared gateway mailbox API for this round."
        ) < prompt.index(
            "Gateway mailbox operations for this round use the exact live gateway base URL:"
        )
        assert "List unread mail through the shared gateway mailbox API for this round." in prompt
        assert "Choose which unread email or emails are relevant to process" in prompt
        assert "thread_ref: filesystem:" not in prompt
        assert "from: HOUMAO-sender@agents.localhost" not in prompt
        assert "subject: Gateway unread reminder one" not in prompt
        assert "subject: Gateway unread reminder two" not in prompt
        assert "TOP-SECRET-ONE" not in prompt
        assert "TOP-SECRET-TWO" not in prompt
        assert "Nominated unread target" not in prompt
        assert "Remaining unread after this target" not in prompt
        assert (
            "Use the installed Houmao email-processing skill "
            "`houmao-process-emails-via-gateway` for this round."
        ) in prompt
        assert "In Codex this Houmao skill is installed natively." in prompt
        assert "$houmao-process-emails-via-gateway http://127.0.0.1:43123" in prompt
        assert "not as a registered slash skill" not in prompt
        assert "`/houmao-process-emails-via-gateway` lookup" not in prompt
        assert "Use the installed Houmao mailbox gateway skill" not in prompt
        assert (
            "use the lower-level Houmao mailbox communication skill `houmao-agent-email-comms`"
            in prompt
        )
        assert "Do not inspect the current project or runtime home for skill files." in prompt
        assert "skills/mailbox/houmao-process-emails-via-gateway/SKILL.md" not in prompt
        assert "skills/mailbox/houmao-agent-email-comms/SKILL.md" not in prompt
        assert "skills/houmao-process-emails-via-gateway/SKILL.md" not in prompt
        assert "skills/houmao-agent-email-comms/SKILL.md" not in prompt
        assert "pixi run houmao-mgr agents mail resolve-live" not in prompt
        assert "http://127.0.0.1:43123" in prompt
        assert "- `GET http://127.0.0.1:43123/v1/mail/status`" in prompt
        assert "- `POST http://127.0.0.1:43123/v1/mail/list`" in prompt
        assert "- `POST http://127.0.0.1:43123/v1/mail/peek`" in prompt
        assert "- `POST http://127.0.0.1:43123/v1/mail/read`" in prompt
        assert "- `POST http://127.0.0.1:43123/v1/mail/send`" in prompt
        assert "- `POST http://127.0.0.1:43123/v1/mail/post`" in prompt
        assert "- `POST http://127.0.0.1:43123/v1/mail/reply`" in prompt
        assert "- `POST http://127.0.0.1:43123/v1/mail/mark`" in prompt
        assert "- `POST http://127.0.0.1:43123/v1/mail/move`" in prompt
        assert "- `POST http://127.0.0.1:43123/v1/mail/archive`" in prompt
        assert "curl -sS -X POST" not in prompt
        assert "stop and wait for the next notification" in prompt
        assert "Houmao mailbox skills are not installed for this session." not in prompt
        assert "python -m houmao.agents.mailbox_runtime_support" not in prompt
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


def test_gateway_mail_notifier_renders_claude_native_skill_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True, tool="claude")
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    _install_fake_live_mailbox_projection(monkeypatch, manifest_path=manifest_path)
    install_runtime_mailbox_system_skills_for_tool(tool="claude", home_path=tmp_path / "home")
    _deliver_unread_mailbox_message(tmp_path)
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
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
        assert (
            "Claude Code the standalone slash-skill line above invokes the installed Houmao skill"
            in prompt
        )
        assert "/houmao-process-emails-via-gateway" in prompt
        assert (
            "Use the lower-level Houmao mailbox communication skill `houmao-agent-email-comms` by name"
            in prompt
        )
        assert "Do not inspect the current project or runtime home for skill files." in prompt
        assert "skills/houmao-process-emails-via-gateway/SKILL.md" not in prompt
        assert "skills/houmao-agent-email-comms/SKILL.md" not in prompt
        assert "skills/mailbox/houmao-process-emails-via-gateway/SKILL.md" not in prompt
        assert "skills/mailbox/houmao-agent-email-comms/SKILL.md" not in prompt
        assert "not as a registered slash skill" not in prompt
    finally:
        runtime.shutdown()


def test_gateway_mail_notifier_falls_back_when_houmao_skills_are_not_installed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root(tmp_path, mailbox_enabled=True)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    _install_fake_live_mailbox_projection(monkeypatch, manifest_path=manifest_path)
    _deliver_unread_mailbox_message(tmp_path)
    fake_client = _FakeCaoRestClient(base_url="http://localhost:9889")
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.CaoRestClient",
        lambda *args, **kwargs: fake_client,
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
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
        assert "Houmao mailbox skills are not installed for this session." in prompt
        assert "List open inbox mail through the shared gateway mailbox API" in prompt
        assert "pixi run houmao-mgr agents mail resolve-live" not in prompt
        assert "http://127.0.0.1:43123" in prompt
        assert "- `GET http://127.0.0.1:43123/v1/mail/status`" in prompt
        assert "houmao-process-emails-via-gateway" not in prompt
        assert "houmao-agent-email-comms" not in prompt
    finally:
        runtime.shutdown()


def test_gateway_mail_notifier_stalwart_adapter_defers_then_repeats_for_unchanged_unread_mail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root_with_stalwart_mailbox(tmp_path)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    _install_fake_live_mailbox_projection(monkeypatch, manifest_path=manifest_path)

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

        def list_messages(
            self,
            *,
            box: str,
            read_state: str,
            answered_state: str,
            archived: bool | None,
            limit: int | None,
            since: str | None,
        ) -> list[dict[str, object]]:
            del box, read_state, answered_state, archived, limit, since
            return [
                {
                    "id": "mail-1",
                    "threadId": "thread-1",
                    "receivedAt": "2026-03-19T08:00:00Z",
                    "subject": "Stalwart unread notifier",
                    "preview": "preview",
                    "body": "full body",
                    "from": [{"email": "sender@agents.localhost"}],
                    "to": [{"email": "HOUMAO-gpu@agents.localhost"}],
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
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
    )
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
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
            if (
                "busy_skip" in outcomes
                and len([row for row in audit_rows if row.outcome == "enqueued"]) >= 2
                and len(fake_client.submitted_prompts) >= 3
            ):
                break
            time.sleep(0.05)

        assert fake_client.submitted_prompts[0] == ("term-123", "busy-work")
        assert len(fake_client.submitted_prompts) >= 3
        assert "stalwart:mail-1" not in fake_client.submitted_prompts[1][1]
        assert "stalwart:mail-1" not in fake_client.submitted_prompts[2][1]
        assert (
            "List open inbox mail through the shared gateway mailbox API"
            in fake_client.submitted_prompts[1][1]
        )
        assert (
            "- `POST http://127.0.0.1:43123/v1/mail/archive`"
            in fake_client.submitted_prompts[1][1]
        )
    finally:
        runtime.shutdown()

    audit_rows = read_gateway_notifier_audit_records(paths.queue_path)
    busy_rows = [row for row in audit_rows if row.outcome == "busy_skip"]
    enqueued_rows = [row for row in audit_rows if row.outcome == "enqueued"]
    assert busy_rows
    assert enqueued_rows
    assert len(enqueued_rows) >= 2
    assert not any(row.outcome == "dedup_skip" for row in audit_rows)
    assert enqueued_rows[-1].unread_summary[0].message_ref == "stalwart:mail-1"


def test_gateway_mail_notifier_stalwart_adapter_records_poll_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway_root = _seed_cao_gateway_root_with_stalwart_mailbox(tmp_path)
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    _install_fake_live_mailbox_projection(monkeypatch, manifest_path=manifest_path)

    class _FailingStalwartJmapClient:
        def __init__(self, *, jmap_url: str, login_identity: str, credential_file: Path) -> None:
            del jmap_url, login_identity, credential_file

        def status(self) -> dict[str, object]:
            return {"account_id": "acc-1"}

        def list_messages(
            self,
            *,
            box: str,
            read_state: str,
            answered_state: str,
            archived: bool | None,
            limit: int | None,
            since: str | None,
        ) -> list[dict[str, object]]:
            del box, read_state, answered_state, archived, limit, since
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
    _install_fake_live_mailbox_projection(monkeypatch, manifest_path=manifest_path)
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
    monkeypatch.setattr(
        GatewayServiceRuntime,
        "_tui_prompt_not_ready_reasons_locked",
        lambda self: [],
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
        assert message_id not in fake_client.submitted_prompts[1][1]
        assert (
            "List unread mail through the shared gateway mailbox API for this round."
            in fake_client.submitted_prompts[1][1]
        )
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
