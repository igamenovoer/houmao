from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.gateway_models import GatewayCurrentInstanceV1
from houmao.agents.realm_controller.gateway_storage import (
    delete_gateway_current_instance,
    gateway_paths_from_manifest_path,
    write_gateway_current_instance,
)
from houmao.agents.realm_controller.models import (
    GatewayControlResult,
    LaunchPlan,
    SessionControlResult,
)
from houmao.agents.realm_controller.registry_storage import resolve_live_agent_record
from houmao.agents.realm_controller.runtime import resume_runtime_session, start_runtime_session


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_role(agent_def_dir: Path) -> None:
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")


def _seed_brain_manifest(tmp_path: Path) -> Path:
    env_file = tmp_path / "vars.env"
    env_file.write_text("ANTHROPIC_API_KEY=secret\n", encoding="utf-8")
    manifest_path = tmp_path / "brain.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "schema_version: 2",
                "inputs:",
                "  tool: claude",
                "runtime:",
                "  launch_executable: claude",
                "  launch_home_selector:",
                "    env_var: CLAUDE_CONFIG_DIR",
                f"    value: {tmp_path / 'home'}",
                "  launch_contract:",
                "    adapter_defaults:",
                "      args: []",
                "      tool_params: {}",
                "    requested_overrides:",
                "      recipe: null",
                "      direct: null",
                "    tool_metadata:",
                "      tool_params: {}",
                "credentials:",
                "  env_contract:",
                f"    source_file: {env_file}",
                "    allowlisted_env_vars:",
                "      - ANTHROPIC_API_KEY",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


class _FakeHeadlessSession:
    def __init__(self, *, tmux_session_name: str, launch_plan: LaunchPlan) -> None:
        self.backend = "claude_headless"
        self.m_launch_plan = launch_plan
        self.m_state = HeadlessSessionState(
            session_id="sess-1",
            turn_index=0,
            role_bootstrap_applied=True,
            working_directory=str(launch_plan.working_directory),
            tmux_session_name=tmux_session_name,
        )
        self.m_force_cleanup = False

    @property
    def state(self) -> HeadlessSessionState:
        return self.m_state

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        self.m_launch_plan = launch_plan

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        self.m_force_cleanup = force_cleanup

    def send_prompt(self, prompt: str) -> list[object]:
        del prompt
        self.m_state = replace(self.m_state, turn_index=self.m_state.turn_index + 1)
        return []

    def interrupt(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def close(self) -> None:
        return


def test_start_resume_send_prompt_and_stop_refresh_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(
                kwargs.get("agent_identity")
                or kwargs["resume_state"].backend_state["tmux_session_name"]
            ),
            launch_plan=kwargs["launch_plan"],
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_identity="gpu",
    )

    started_record = resolve_live_agent_record("gpu")
    assert started_record is not None
    assert started_record.agent_name == "AGENTSYS-gpu"
    assert started_record.generation_id == controller.registry_generation_id
    assert started_record.gateway is not None

    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["registry_generation_id"] == controller.registry_generation_id

    controller.send_prompt("hello")
    refreshed_record = resolve_live_agent_record("AGENTSYS-gpu")
    assert refreshed_record is not None
    assert refreshed_record.generation_id == controller.registry_generation_id

    resumed = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=controller.manifest_path,
    )
    resumed_record = resolve_live_agent_record("gpu")
    assert resumed_record is not None
    assert resumed.registry_generation_id == controller.registry_generation_id
    assert resumed_record.generation_id == controller.registry_generation_id

    stop_result = resumed.stop(force_cleanup=True)
    assert stop_result.status == "ok"
    assert resolve_live_agent_record("gpu") is None


def test_send_prompt_preserves_success_when_registry_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(kwargs.get("agent_identity") or "AGENTSYS-gpu"),
            launch_plan=kwargs["launch_plan"],
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_identity="gpu",
    )
    monkeypatch.setattr(
        controller,
        "refresh_shared_registry_record",
        lambda: (_ for _ in ()).throw(SessionManifestError("registry write failed")),
    )

    events = controller.send_prompt("hello")

    assert events == []
    assert controller.consume_operation_warnings() == (
        "Shared-registry refresh failed after manifest persistence: registry write failed",
    )


def test_stop_preserves_success_when_registry_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(kwargs.get("agent_identity") or "AGENTSYS-gpu"),
            launch_plan=kwargs["launch_plan"],
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_identity="gpu",
    )
    monkeypatch.setattr(
        controller,
        "clear_shared_registry_record",
        lambda: (_ for _ in ()).throw(OSError("permission denied")),
    )

    result = controller.stop(force_cleanup=True)

    assert result.status == "ok"
    assert controller.consume_operation_warnings() == (
        "Shared-registry cleanup failed after successful stop-session teardown: permission denied",
    )


def test_refresh_mailbox_bindings_preserves_success_when_registry_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(kwargs.get("agent_identity") or "AGENTSYS-gpu"),
            launch_plan=kwargs["launch_plan"],
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_identity="gpu",
        mailbox_transport="filesystem",
        mailbox_root=tmp_path / "mail-old",
        mailbox_principal_id="AGENTSYS-research",
        mailbox_address="AGENTSYS-research@agents.localhost",
    )
    monkeypatch.setattr(
        controller,
        "refresh_shared_registry_record",
        lambda: (_ for _ in ()).throw(SessionManifestError("registry refresh failed")),
    )

    refreshed = controller.refresh_mailbox_bindings(filesystem_root=tmp_path / "mail-new")

    assert refreshed.filesystem_root == (tmp_path / "mail-new").resolve()
    assert controller.consume_operation_warnings() == (
        "Shared-registry refresh failed after manifest persistence: registry refresh failed",
    )


def test_attach_and_detach_gateway_refreshes_registry_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(kwargs.get("agent_identity") or "AGENTSYS-gpu"),
            launch_plan=kwargs["launch_plan"],
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_identity="gpu",
    )
    paths = gateway_paths_from_manifest_path(controller.manifest_path)
    assert paths is not None

    def _fake_attach_gateway_for_controller(
        controller: Any,
        *,
        host_override: str | None,
        port_override: int | None,
    ) -> GatewayControlResult:
        del controller, host_override, port_override
        write_gateway_current_instance(
            paths.current_instance_path,
            GatewayCurrentInstanceV1(
                pid=4242,
                host="127.0.0.1",
                port=43123,
                managed_agent_instance_epoch=1,
            ),
        )
        return GatewayControlResult(
            status="ok",
            action="gateway_attach",
            detail="attached",
            gateway_root=str(paths.gateway_root),
            gateway_host="127.0.0.1",
            gateway_port=43123,
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._attach_gateway_for_controller",
        _fake_attach_gateway_for_controller,
    )

    attach_result = controller.attach_gateway()
    assert attach_result.status == "ok"

    attached_record = resolve_live_agent_record("gpu")
    assert attached_record is not None
    assert attached_record.gateway is not None
    assert attached_record.gateway.host == "127.0.0.1"
    assert attached_record.gateway.port == 43123

    def _fake_detach_gateway_for_controller(controller: Any) -> GatewayControlResult:
        del controller
        delete_gateway_current_instance(paths)
        return GatewayControlResult(
            status="ok",
            action="gateway_detach",
            detail="detached",
            gateway_root=str(paths.gateway_root),
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._detach_gateway_for_controller",
        _fake_detach_gateway_for_controller,
    )

    detach_result = controller.detach_gateway()
    assert detach_result.status == "ok"

    detached_record = resolve_live_agent_record("gpu")
    assert detached_record is not None
    assert detached_record.gateway is not None
    assert detached_record.gateway.host is None
