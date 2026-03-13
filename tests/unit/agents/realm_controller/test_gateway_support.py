from __future__ import annotations

import json
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.errors import GatewayHttpError, LaunchPlanError
from houmao.agents.realm_controller.gateway_models import (
    BlueprintGatewayDefaults,
    GatewayCurrentInstanceV1,
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
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )

    controller.ensure_gateway_capability()
    result = controller.attach_gateway()

    assert result.status == "error"
    assert result.action == "gateway_attach"
    assert "backend='cao_rest'" in result.detail


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


def _seed_cao_gateway_root(tmp_path: Path, *, terminal_id: str = "term-123") -> Path:
    manifest_path = default_manifest_path(tmp_path, "cao_rest", "cao-rest-1")
    plan = _sample_cao_plan(tmp_path)
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="role",
            brain_manifest_path=tmp_path / "brain.yaml",
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
