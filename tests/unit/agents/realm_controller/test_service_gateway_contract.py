"""Verify providers attach to the shared signed service control surface."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.backends.service_runtime import (
    ManagedServiceSession,
    ManagedServiceSessionState,
    ServiceRequestSnapshot,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachContractV1,
    GatewayServiceRequestSnapshotV1,
)
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime
from houmao.agents.realm_controller.gateway_storage import (
    GatewayCapabilityPublication,
    ensure_gateway_capability,
    load_gateway_manifest,
)
from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    parse_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    BackendKind,
    LaunchPlan,
    RoleInjectionMethod,
    RoleInjectionPlan,
    SessionEvent,
)
from houmao.execution.context import observed_local_binding
from tests.fixtures.gateway_access import (
    FixtureProofAuth,
    enroll_fixture_admin,
    fixture_admin_key,
    gateway_fixture_client,
)


@pytest.mark.usefixtures("gateway_fixture_access")
@pytest.mark.parametrize(
    ("tool", "kind", "args", "home_env_var", "role_method", "native_turn"),
    [
        ("kimi", "kimi_acp", ["acp"], "KIMI_CODE_HOME", "native_home_system_prompt", "0"),
        (
            "codex",
            "codex_app_server",
            ["app-server", "--listen", "stdio://"],
            "CODEX_HOME",
            "native_developer_instructions",
            "turn-native-1",
        ),
    ],
)
def test_gateway_requires_signed_control_and_projects_exact_native_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    kind: BackendKind,
    args: list[str],
    home_env_var: str,
    role_method: RoleInjectionMethod,
    native_turn: str,
) -> None:
    """Expose exact native evidence while guarding busy and unsupported operations."""

    generation = "fixture-generation"
    runtime_id = f"managed-{tool}"
    manifest_path = default_manifest_path(tmp_path, kind, runtime_id)
    socket_path = str(tmp_path / "tmux.sock")
    backend_state = ManagedServiceSessionState(
        runtime_session_id=runtime_id,
        generation_id=generation,
        service_incarnation="native-owner",
        native_session_id="native-session",
        working_directory=str(tmp_path),
        tmux_session_name="HOUMAO-service",
        tmux_pane_id="%0",
        tmux_window_id="@0",
    ).to_payload()
    plan = LaunchPlan(
        backend=kind,
        tool=tool,
        executable=tool,
        args=args,
        working_directory=tmp_path,
        home_env_var=home_env_var,
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method=role_method, role_name="role", prompt="role prompt"
        ),
        metadata={"tmux_socket_path": socket_path},
        execution_binding=observed_local_binding(
            working_directory=tmp_path,
            runtime_root=tmp_path / "runtime",
            registry_root=tmp_path / "registry",
            tmux_socket=socket_path,
        ),
    )
    raw_manifest = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
            backend_state=backend_state,
            agent_name="HOUMAO-service",
            agent_id="fixture-agent",
            tmux_session_name="HOUMAO-service",
            session_id=runtime_id,
            agent_def_dir=tmp_path / "agents",
            registry_generation_id=generation,
        )
    )
    write_session_manifest(manifest_path, raw_manifest)
    manifest = parse_session_manifest_payload(raw_manifest, source=str(manifest_path))
    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend=kind,
            tool=tool,
            session_id=runtime_id,
            tmux_session_name="HOUMAO-service",
            working_directory=tmp_path,
            backend_state=backend_state,
            agent_def_dir=tmp_path / "agents",
        )
    )
    assert load_gateway_manifest(paths.gateway_manifest_path).backend_metadata.model_dump() == {
        "control_kind": "service",
        "tool": tool,
    }
    foreign = GatewayAttachContractV1.model_validate_json(paths.attach_path.read_text())
    with pytest.raises(ValidationError, match="do not agree"):
        GatewayAttachContractV1.model_validate(
            foreign.model_dump() | {"backend_metadata": {"control_kind": "service", "tool": "dsh"}}
        )
    with pytest.raises(ValidationError, match="service attach schema"):
        GatewayAttachContractV1.model_validate(
            foreign.model_dump() | {"backend_metadata": {"tool": tool, "session_id": "legacy"}}
        )

    busy = ManagedControlObservationV1(
        source="service_native",
        freshness="current",
        owner_available=True,
        connection_ready=True,
        can_accept_prompt_now=False,
        service_incarnation="native-owner",
        native_session_id="native-session",
        active_request_id="busy-request",
        active_turn_id="native-pending-turn",
    )
    snapshot = ServiceRequestSnapshot(
        request_id="past-request",
        generation_id=generation,
        service_incarnation="native-owner",
        native_session_id="native-session",
        native_turn_id=native_turn,
        state="completed",
        accepted_at_utc="2026-11-19T00:00:00Z",
        events=[SessionEvent(kind="assistant", message="NATIVE_REPLY", turn_index=1)],
    )
    backend = ManagedServiceSession()
    requests = {
        "past-request": snapshot,
        "busy-request": snapshot.model_copy(
            update={
                "request_id": "busy-request",
                "native_turn_id": "native-pending-turn",
                "state": "handed_off",
                "events": [],
            }
        ),
    }
    monkeypatch.setattr(backend, "read_request", requests.get)
    controller = SimpleNamespace(
        registry_generation_id=generation,
        backend_session=backend,
        require_managed_control_owner=lambda: manifest,
        execution_scope=nullcontext,
        observe_managed_service=lambda: busy,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.resume_runtime_session",
        lambda **_: controller,
    )
    monkeypatch.setattr(
        GatewayServiceRuntime, "_verified_owner_manifest", lambda *_, **__: manifest
    )
    monkeypatch.setattr(GatewayServiceRuntime, "_owner_prompt_attempt", lambda *_: None)
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=paths.gateway_root, host="127.0.0.1", port=43123
    )
    app_client = gateway_fixture_client(runtime)
    admin, signer = fixture_admin_key(tmp_path, "service-admin")
    with app_client:
        enroll_fixture_admin(app_client, admin, signer)
        app_client.auth = FixtureProofAuth(signer, purpose="admin")
        assert app_client.get("/v1/control/service/state", auth=None).status_code == 401
        state = app_client.get("/v1/control/service/state")
        assert state.status_code == 200, state.text
        assert ManagedControlObservationV1.model_validate_json(state.content) == busy
        status = app_client.get("/v1/status").json()
        assert status["mode"] == "service" and status["backend"] == kind
        assert status["native_surface"] is None
        assert status["capabilities"]["correlation"] == "native_turn"
        assert runtime.ag_ui_target_transport_family() == "service"
        assert runtime.m_usage_service is not None
        assert runtime._register_usage_prompt(turn_id="provider-owned-usage") is None
        assert runtime.m_usage_service.store.get_pending_turn("provider-owned-usage") is None

        request = app_client.get("/v1/control/service/requests/past-request")
        assert request.status_code == 200, request.text
        evidence = GatewayServiceRequestSnapshotV1.model_validate_json(request.content)
        assert evidence.native_turn_id == native_turn
        assert evidence.events[0].message == "NATIVE_REPLY"
        current = app_client.get("/v1/control/service/requests/busy-request")
        assert current.status_code == 200, current.text
        active = GatewayServiceRequestSnapshotV1.model_validate_json(current.content)
        assert active.state == "handed_off" and active.native_turn_id == busy.active_turn_id
        assert active.events == [] and active.completed_at_utc is None
        assert app_client.get("/v1/control/service/requests/foreign").status_code == 404

        prompt = "/v1/control/prompt"
        assert app_client.post(prompt, json={"prompt": "busy"}).status_code == 409
        assert (
            app_client.post(
                prompt, json={"prompt": "new", "chat_session": {"mode": "new"}}
            ).status_code
            == 422
        )
        override = app_client.post(
            prompt, json={"prompt": "switched", "execution": {"model": {"name": "other"}}}
        )
        assert override.status_code == 422
        assert override.json()["detail"]["error_code"] == "invalid_execution"
        keys = app_client.post("/v1/control/send-keys", json={"sequence": "Enter"})
        assert keys.status_code == 501
        assert keys.json()["detail"]["error_code"] == "unsupported_capability"

        busy = busy.model_copy(
            update={
                "freshness": "stale",
                "connection_ready": False,
                "last_request_id": "busy-request",
                "last_turn_id": "native-pending-turn",
                "last_outcome": "uncertain",
            }
        )
        requests["busy-request"] = requests["busy-request"].model_copy(
            update={"state": "uncertain"}
        )
        stale = app_client.get("/v1/control/service/state")
        assert stale.status_code == 200, stale.text
        assert ManagedControlObservationV1.model_validate_json(stale.content) == busy
        recovered = app_client.get("/v1/control/service/requests/busy-request")
        assert recovered.status_code == 200, recovered.text
        saved = GatewayServiceRequestSnapshotV1.model_validate_json(recovered.content)
        assert saved.state == "uncertain" and saved.native_turn_id == active.native_turn_id
        assert app_client.post(prompt, json={"prompt": "retry"}).status_code == 503
