from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
    LaunchPlanError,
    SessionManifestError,
)
from houmao.agents.realm_controller.gateway_models import GatewayCurrentInstanceV1
from houmao.agents.realm_controller.gateway_access_runtime import gateway_access_for_manifest
from houmao.agents.realm_controller.gateway_storage import (
    delete_gateway_current_instance,
    gateway_paths_from_manifest_path,
    load_gateway_desired_config,
    write_gateway_current_instance,
)
from houmao.agents.realm_controller.models import (
    GatewayControlResult,
    LaunchPlan,
    RelaunchChatSessionSelection,
    SessionControlResult,
)
from houmao.agents.realm_controller.registry_storage import (
    TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL,
    load_managed_agent_record_by_agent_id,
    publish_live_agent_record,
    resolve_live_agent_record,
)
from houmao.agents.realm_controller import runtime as runtime_module
from houmao.execution.context import current_execution_binding, execution_read_only_scope
from houmao.execution.models import ExecutionBindingV1
from houmao.execution.tmux import current_tmux_socket_path, tmux_server_scope
from houmao.gateway.access import GatewayAdminKey, GatewayLaunchSeed, public_key_text
from houmao.gateway.deployment import GatewayEndpointDescriptor
from houmao.mailbox.registry_config import associate_registry_store
from houmao.project.catalog import LaunchProfileCatalogEntry, ProjectCatalog
from houmao.project.launch_profiles import profile_run_mode
from houmao.project.overlay import bootstrap_project_overlay, require_project_overlay
from houmao.agents.realm_controller.runtime import (
    resume_runtime_session,
    resume_stopped_runtime_session,
    start_runtime_session,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_role(agent_def_dir: Path) -> None:
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")


def _seed_brain_manifest(
    tmp_path: Path,
    *,
    gateway_extra: dict[str, object] | None = None,
) -> Path:
    env_file = tmp_path / "vars.env"
    env_file.write_text("ANTHROPIC_API_KEY=secret\n", encoding="utf-8")
    extra_lines: list[str] = []
    if gateway_extra is not None:
        extra_lines = [
            "  extra:",
            "    gateway:",
        ]
        host = gateway_extra.get("host")
        if host is not None:
            extra_lines.append(f"      host: {host}")
        port = gateway_extra.get("port")
        if port is not None:
            extra_lines.append(f"      port: {port}")
    manifest_path = tmp_path / "brain.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "schema_version: 3",
                "inputs:",
                "  tool: claude",
                "  skills: []",
                "  setup: default",
                "  auth: default",
                "  adapter_path: /tmp/tool-adapter.yaml",
                "  preset_path: null",
                *extra_lines,
                "runtime:",
                f"  runtime_root: {tmp_path}",
                "  home_id: test-home",
                f"  home_path: {tmp_path / 'home'}",
                f"  launch_helper: {tmp_path / 'home' / 'launch.sh'}",
                "  launch_executable: claude",
                "  launch_home_selector:",
                "    env_var: CLAUDE_CONFIG_DIR",
                f"    value: {tmp_path / 'home'}",
                "  launch_contract:",
                "    adapter_defaults:",
                "      args: []",
                "      tool_params: {}",
                "    requested_overrides:",
                "      preset: null",
                "      direct: null",
                "    tool_metadata:",
                "      tool_params: {}",
                "    construction_provenance:",
                "      adapter_path: /tmp/tool-adapter.yaml",
                "      preset_path: null",
                "      preset_overrides_present: false",
                "      direct_overrides_present: false",
                "credentials:",
                f"  auth_path: {tmp_path / 'auth'}",
                "  projected_files: []",
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
        self.m_relaunch_chat_sessions: list[RelaunchChatSessionSelection | None] = []
        self.m_execution_scopes: list[tuple[str | None, ExecutionBindingV1 | None]] = []

    @property
    def state(self) -> HeadlessSessionState:
        return self.m_state

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        self.m_launch_plan = launch_plan

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        self.m_force_cleanup = force_cleanup

    def prepare_stopped_revival(self, *, tmux_session_name: str) -> None:
        """Model the explicit lifecycle boundary without touching tmux."""

        if self.m_state.tmux_session_name is None:
            self.m_state.tmux_session_name = tmux_session_name

    def send_prompt(self, prompt: str, **kwargs: object) -> list[object]:
        del prompt, kwargs
        self.m_execution_scopes.append((current_tmux_socket_path(), current_execution_binding()))
        self.m_state = replace(self.m_state, turn_index=self.m_state.turn_index + 1)
        return []

    def interrupt(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
        self.m_execution_scopes.append((current_tmux_socket_path(), current_execution_binding()))
        self.m_state = replace(self.m_state, tmux_session_name=None)
        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def relaunch(
        self,
        *,
        chat_session: RelaunchChatSessionSelection | None = None,
    ) -> SessionControlResult:
        self.m_relaunch_chat_sessions.append(chat_session)
        return SessionControlResult(status="ok", action="relaunch", detail="relaunched")

    def close(self) -> None:
        return


def test_start_runtime_session_rejects_retired_houmao_server_backend(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)

    with pytest.raises(SessionManifestError, match="houmao_server_rest.*retired"):
        start_runtime_session(
            agent_def_dir=agent_def_dir,
            brain_manifest_path=brain_manifest_path,
            role_name="r",
            runtime_root=runtime_root,
            backend="houmao_server_rest",
            working_directory=tmp_path,
            agent_name="gpu",
        )


def test_kimi_web_rejects_unqualified_version_before_runtime_or_native_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reject the unqualified binary before preparing its workspace or starting a host."""

    executable = tmp_path / "kimi"
    executable.write_text("#!/bin/sh\nprintf '2.5.0\\n'\n")
    executable.chmod(0o700)
    monkeypatch.setattr(
        runtime_module,
        "load_brain_manifest",
        lambda path: {
            "inputs": {"tool": "kimi"},
            "runtime": {"launch_executable": str(executable)},
        },
    )

    def unexpected_mutation(*args: object, **kwargs: object) -> None:
        pytest.fail("Unavailable Kimi Web reached runtime preparation")

    monkeypatch.setattr(runtime_module, "resolve_runtime_root", unexpected_mutation)
    monkeypatch.setattr(runtime_module, "build_launch_plan", unexpected_mutation)
    monkeypatch.setattr(runtime_module, "_create_backend_session", unexpected_mutation)
    with pytest.raises(LaunchPlanError, match=r"Kimi Web requires Kimi Code 2\.6\.0.*2\.5\.0"):
        start_runtime_session(
            agent_def_dir=tmp_path / "repo",
            brain_manifest_path=tmp_path / "manifest.yaml",
            role_name="missing",
            runtime_root=tmp_path / "runtime",
            mode="web",
            working_directory=tmp_path,
        )
    assert not (tmp_path / "runtime").exists()


def test_start_resume_send_prompt_and_stop_refresh_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "owner-config"))
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    admin_keys = tuple(
        GatewayAdminKey(
            principal=name, public_key=public_key_text(Ed25519PrivateKey.generate().public_key())
        )
        for name in ("first", "second")
    )
    seed = GatewayLaunchSeed(admin_keys=admin_keys)
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
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_name="gpu",
        gateway_admin_seed=seed,
        launch_env_overrides={"CURRENT_GEN_FEATURE": "private-live-value"},
    )
    first_access = gateway_access_for_manifest(controller.manifest_path)
    first_self = first_access.store.load_self(first_access.target.incarnation)
    assert (
        first_access.store.self_signer_path(first_access.target.incarnation).stat().st_mode & 0o777
        == 0o600
    )
    assert tuple(entry.key for entry in first_access.store.load().keys) == admin_keys
    first_access.store.update(
        lambda state: state.model_copy(update={"keys": state.keys[1:], "revision": 1})
    )

    started_record = resolve_live_agent_record("gpu")
    assert started_record is not None
    assert started_record.agent_name == "gpu"
    assert started_record.generation_id == controller.registry_generation_id
    assert started_record.lifecycle.state == "active"
    assert started_record.lifecycle.relaunchable is True
    assert started_record.terminal.current_session_name is not None
    assert started_record.gateway is None
    binding = controller.execution_binding
    assert binding is not None
    assert binding.uid == os.geteuid()
    assert binding.gid == os.getegid()
    assert binding.transport == "local"
    assert binding.runtime_root == str(runtime_root)
    assert binding.registry_root == str(registry_root)
    assert started_record.execution_binding == binding
    assert started_record.terminal.socket_path == controller.tmux_socket_path
    capabilities = controller.control_capabilities()
    assert capabilities.mode == "headless"
    assert capabilities.evidence_source == "headless_artifacts"
    assert "prompt" in capabilities.operations
    assert "send_keys" not in capabilities.operations
    started_published_at = datetime.fromisoformat(started_record.published_at)
    started_lease_expires_at = datetime.fromisoformat(started_record.lease_expires_at)
    assert (
        started_lease_expires_at - started_published_at == TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL
    )

    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["registry_generation_id"] == controller.registry_generation_id
    assert persisted["gateway_admin_seed"] == seed.model_dump(mode="json")
    assert "PRIVATE KEY" not in json.dumps(persisted)
    assert str(first_access.private_root) not in json.dumps(persisted)
    assert persisted["registry_launch_authority"] == "runtime"
    assert persisted["runtime"]["execution_binding"] == binding.model_dump(mode="json")
    assert persisted["launch_plan"]["execution_binding"] == binding.model_dump(mode="json")
    assert persisted["tmux"]["socket_path"] == binding.tmux_socket
    environment_file = (
        controller.manifest_path.parent / persisted["runtime"]["launch_environment_file"]
    )
    assert environment_file.stat().st_mode & 0o777 == 0o600
    assert "private-live-value" not in json.dumps(persisted)
    assert "CURRENT_GEN_FEATURE" not in persisted["launch_plan"]["env_var_names"]
    initial_prompt = controller.launch_plan.role_injection.prompt
    _write(agent_def_dir / "roles/r/system-prompt.md", "Updated role for next launch")

    before_read = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    with monkeypatch.context() as read_patch:

        def forbid_setup(*_args: object, **_kwargs: object) -> None:
            """Fail if passive reconstruction tries to prepare owned materials."""

            pytest.fail("Read-only reconstruction attempted runtime setup")

        read_patch.setattr(runtime_module, "ensure_agent_memory", forbid_setup)
        read_patch.setattr(runtime_module, "ensure_hook_observation_on_resume", forbid_setup)
        read_patch.setattr(runtime_module, "build_launch_plan", forbid_setup)
        with execution_read_only_scope():
            snapshot = resume_runtime_session(
                agent_def_dir=agent_def_dir,
                session_manifest_path=controller.manifest_path,
                read_only=True,
            )
            assert snapshot.execution_binding == binding
            assert snapshot.launch_plan.args == controller.launch_plan.args
            assert snapshot.launch_plan.role_injection.prompt == initial_prompt
            assert snapshot.launch_plan.env["CURRENT_GEN_FEATURE"] == "private-live-value"
            with pytest.raises(SessionManifestError, match="Read-only"):
                snapshot.interrupt()
    assert before_read == {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    with tmux_server_scope("/unrelated/operator.sock"):
        controller.send_prompt("hello")
        assert current_tmux_socket_path() == "/unrelated/operator.sock"
    assert controller.backend_session.m_execution_scopes[-1] == (binding.tmux_socket, binding)
    refreshed_record = resolve_live_agent_record("gpu")
    assert refreshed_record is not None
    assert refreshed_record.generation_id == controller.registry_generation_id

    before_relaunch = controller.registry_generation_id
    assert before_relaunch is not None
    retained_manifest = runtime_root / "retained-predecessor.json"
    retained_manifest.write_bytes(controller.manifest_path.read_bytes())
    with pytest.raises(SessionManifestError, match="no longer names"):
        runtime_module.require_active_managed_control_manifest(
            retained_manifest, generation_id=before_relaunch
        )
    assert controller.relaunch().status == "ok"
    assert controller.registry_generation_id != before_relaunch
    assert "Updated role for next launch" in controller.launch_plan.role_injection.prompt
    assert "CURRENT_GEN_FEATURE" not in controller.launch_plan.env
    assert controller.launch_plan.runtime_launch_environment_file != environment_file.name
    relaunched_access = gateway_access_for_manifest(controller.manifest_path)
    assert relaunched_access.store.load_self(relaunched_access.target.incarnation) != first_self
    assert relaunched_access.store.load().find(admin_keys[0].key_id) is None
    assert relaunched_access.store.load().find(admin_keys[1].key_id) is not None
    with pytest.raises(SessionManifestError, match="authority has changed"):
        first_access.require_current()
    assert controller.execution_binding == binding
    relaunched_record = resolve_live_agent_record("gpu")
    assert relaunched_record is not None
    assert relaunched_record.generation_id == controller.registry_generation_id
    manifest_after_relaunch = controller.manifest_path.read_bytes()
    with pytest.raises(SessionManifestError, match="generation changed"):
        snapshot.interrupt()
    with pytest.raises(SessionManifestError, match="generation changed"):
        snapshot.persist_manifest()
    with pytest.raises(SessionManifestError, match="no longer names"):
        runtime_module.require_active_managed_control_manifest(
            retained_manifest, generation_id=before_relaunch
        )
    assert controller.manifest_path.read_bytes() == manifest_after_relaunch

    resumed = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=controller.manifest_path,
    )
    resumed_record = resolve_live_agent_record("gpu")
    assert resumed_record is not None
    assert resumed.registry_generation_id == controller.registry_generation_id
    assert resumed_record.generation_id == controller.registry_generation_id
    assert resumed.execution_binding == binding
    assert resumed_record.execution_binding == binding

    stop_result = resumed.stop(force_cleanup=True)
    assert stop_result.status == "ok"
    assert resolve_live_agent_record("gpu") is None
    assert resumed.agent_id is not None
    stopped_record = load_managed_agent_record_by_agent_id(resumed.agent_id)
    assert stopped_record is not None
    assert stopped_record.lifecycle.state == "stopped"
    with pytest.raises(SessionManifestError, match="no longer names"):
        resumed.require_managed_control_owner()
    assert stopped_record.lifecycle.relaunchable is True
    assert stopped_record.liveness is None
    assert stopped_record.gateway is None
    assert stopped_record.terminal.current_session_name is None
    assert relaunched_access.store.load().revision == 1
    assert relaunched_access.current_self() is None
    assert stopped_record.terminal.last_session_name == started_record.terminal.current_session_name
    assert stopped_record.execution_binding == binding
    assert stopped_record.terminal.socket_path == binding.tmux_socket
    assert resumed.backend_session.m_execution_scopes[-1] == (binding.tmux_socket, binding)
    stopped_payload = json.loads(resumed.manifest_path.read_text(encoding="utf-8"))
    assert stopped_payload["tmux_session_name"] == started_record.terminal.current_session_name


def test_start_runtime_session_does_not_publish_registry_when_surface_preparation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **_kwargs: (_ for _ in ()).throw(
            BackendExecutionError(
                "Failed to prepare tmux agent surface in `HOUMAO-gpu`: base-index conflict"
            )
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.publish_live_agent_record",
        lambda _record: (_ for _ in ()).throw(AssertionError("registry publish must not run")),
    )

    with pytest.raises(BackendExecutionError, match="base-index conflict"):
        start_runtime_session(
            agent_def_dir=agent_def_dir,
            brain_manifest_path=brain_manifest_path,
            role_name="r",
            runtime_root=tmp_path / "runtime",
            backend="claude_headless",
            working_directory=tmp_path,
            agent_name="gpu",
        )

    assert resolve_live_agent_record("gpu") is None


def test_resume_stopped_runtime_session_revives_headless_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
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
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_name="gpu",
    )
    original_session_name = controller.tmux_session_name
    original_generation_id = controller.registry_generation_id
    assert original_session_name is not None
    assert original_generation_id is not None

    stop_result = controller.stop(force_cleanup=True)
    assert stop_result.status == "ok"

    revived = resume_stopped_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=controller.manifest_path,
    )
    assert revived.tmux_session_name is not None
    assert revived.tmux_session_name != original_session_name

    result = revived.revive_stopped_session(
        chat_session=RelaunchChatSessionSelection(mode="tool_last_or_new")
    )

    assert result.status == "ok"
    assert isinstance(revived.backend_session, _FakeHeadlessSession)
    assert revived.backend_session.m_relaunch_chat_sessions[-1] is not None
    assert revived.backend_session.m_relaunch_chat_sessions[-1].mode == "tool_last_or_new"

    active_record = resolve_live_agent_record("gpu")
    assert active_record is not None
    assert active_record.lifecycle.state == "active"
    assert active_record.generation_id != original_generation_id
    assert active_record.terminal.current_session_name == revived.tmux_session_name
    assert active_record.terminal.last_session_name == revived.tmux_session_name

    revived_payload = json.loads(revived.manifest_path.read_text(encoding="utf-8"))
    assert revived_payload["tmux_session_name"] == revived.tmux_session_name
    assert revived_payload["registry_generation_id"] == revived.registry_generation_id
    assert revived_payload["registry_generation_id"] != original_generation_id


def test_stopped_revival_uses_saved_mode_and_relaunch_policy_after_profile_edit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Revive the recorded TUI mode after the reusable profile changes to headless."""

    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    bootstrap_project_overlay(agent_def_dir)
    catalog = ProjectCatalog.from_overlay(require_project_overlay(agent_def_dir))

    def store_profile(mode: str) -> LaunchProfileCatalogEntry:
        """Change the live catalog default for the profile used to start this agent."""

        return catalog.store_launch_profile(
            name="reviewer-default",
            profile_lane="launch_profile",
            source_kind="recipe",
            source_name="reviewer-claude-default",
            managed_agent_name="gpu",
            managed_agent_id=None,
            workdir=None,
            auth_tool=None,
            auth_name=None,
            operator_prompt_mode=None,
            env_mapping=None,
            mailbox_mapping=None,
            posture_mapping={"mode": mode},
            prompt_overlay_mode=None,
            prompt_overlay_text=None,
        )

    initial_profile = store_profile("tui")
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
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
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        mode=profile_run_mode(
            initial_profile.posture_payload, tool="claude", source="test profile"
        ),
        working_directory=tmp_path,
        agent_name="gpu",
    )
    controller.launch_plan = replace(
        controller.launch_plan,
        metadata={
            **controller.launch_plan.metadata,
            "launch_overrides": {
                "construction_provenance": {
                    "launch_profile": {
                        "name": "reviewer-default",
                        "relaunch": {
                            "chat_session": {
                                "mode": "tool_last_or_new",
                            }
                        },
                    }
                }
            },
        },
    )

    stop_result = controller.stop(force_cleanup=True)
    assert stop_result.status == "ok"
    store_profile("headless")
    assert catalog.load_launch_profile(initial_profile.name).posture_payload["mode"] == "headless"

    revived = resume_stopped_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=controller.manifest_path,
    )
    result = revived.revive_stopped_session()

    assert result.status == "ok"
    assert isinstance(revived.backend_session, _FakeHeadlessSession)
    assert (revived.launch_plan.mode, revived.launch_plan.backend) == ("tui", "local_interactive")
    assert revived.backend_session.m_launch_plan.mode == "tui"
    assert revived.backend_session.m_relaunch_chat_sessions[-1] is not None
    assert revived.backend_session.m_relaunch_chat_sessions[-1].mode == "tool_last_or_new"
    manifest = json.loads(revived.manifest_path.read_text(encoding="utf-8"))
    assert manifest["mode"] == manifest["launch_plan"]["mode"] == "tui"
    record = resolve_live_agent_record("gpu")
    assert record is not None
    assert record.mode == "tui"


def test_rc2_dsh_acp_manifest_cannot_restore_a_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reject a per-turn ACP manifest at the schema boundary before backend setup."""

    manifest_path = tmp_path / "manifest.json"
    legacy_manifest = json.dumps(
        {
            "schema_version": 5,
            "tool": "dsh",
            "backend": "dsh_acp",
            "launch_plan": {"schema_version": 2, "tool": "dsh", "backend": "dsh_acp"},
            "headless": {"session_id": "previous-native-session", "turn_index": 1},
        }
    )
    manifest_path.write_text(legacy_manifest, encoding="utf-8")

    def unexpected_backend(**_kwargs: object) -> None:
        """Fail if legacy authority proceeds past manifest validation."""

        pytest.fail("RC2 per-turn ACP cannot create a current backend")

    monkeypatch.setattr(runtime_module, "_create_backend_session", unexpected_backend)
    with pytest.raises(SessionManifestError, match="got 5.*Start a fresh runtime session"):
        resume_runtime_session(agent_def_dir=tmp_path, session_manifest_path=manifest_path)

    assert manifest_path.read_text(encoding="utf-8") == legacy_manifest


def test_shared_registry_record_builder_skips_non_tmux_backed_controller() -> None:
    controller = SimpleNamespace(_is_tmux_backed=lambda: False)

    assert runtime_module._build_shared_registry_record_for_controller(controller) is None


def test_start_runtime_session_persists_managed_force_mode_in_launch_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(kwargs.get("agent_identity") or "gpu"),
            launch_plan=kwargs["launch_plan"],
        ),
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
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_name="gpu",
        managed_force_mode="keep-stale",
    )

    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["launch_plan"]["metadata"]["managed_force_mode"] == "keep-stale"


def test_start_runtime_session_seeds_gateway_defaults_from_manifest_extra(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(
        tmp_path,
        gateway_extra={"host": "127.0.0.1", "port": 43123},
    )
    _seed_role(agent_def_dir)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
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
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_name="gpu",
    )

    paths = gateway_paths_from_manifest_path(controller.manifest_path)
    assert paths is not None
    desired = load_gateway_desired_config(paths.desired_config_path)
    assert desired.desired_host == "127.0.0.1"
    assert desired.desired_port == 43123


def test_external_launch_authority_defers_runtime_publish_but_stop_preserves_stopped_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
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
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_name="gpu",
        registry_launch_authority="external",
    )

    assert resolve_live_agent_record("gpu") is None
    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["registry_launch_authority"] == "external"

    seeded_record = controller.build_shared_registry_record()
    assert seeded_record is not None
    published = publish_live_agent_record(seeded_record)

    controller.send_prompt("hello")

    refreshed_record = resolve_live_agent_record("gpu")
    assert refreshed_record is not None
    assert refreshed_record.generation_id == published.generation_id
    assert refreshed_record.published_at == published.published_at

    stop_result = controller.stop(force_cleanup=True)
    assert stop_result.status == "ok"
    assert resolve_live_agent_record("gpu") is None
    assert controller.agent_id is not None
    stopped_record = load_managed_agent_record_by_agent_id(controller.agent_id)
    assert stopped_record is not None
    assert stopped_record.lifecycle.state == "stopped"
    assert stopped_record.terminal.last_session_name == published.terminal.current_session_name


def test_send_prompt_preserves_success_when_registry_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(kwargs.get("agent_identity") or "HOUMAO-gpu"),
            launch_plan=kwargs["launch_plan"],
        ),
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
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_name="gpu",
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
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(kwargs.get("agent_identity") or "HOUMAO-gpu"),
            launch_plan=kwargs["launch_plan"],
        ),
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
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="claude_headless",
        working_directory=tmp_path,
        agent_name="gpu",
    )
    monkeypatch.setattr(
        controller,
        "publish_stopped_shared_registry_record",
        lambda *, last_tmux_session_name: (_ for _ in ()).throw(OSError("permission denied")),
    )

    result = controller.stop(force_cleanup=True)

    assert result.status == "ok"
    assert controller.consume_operation_warnings() == (
        "Shared-registry stop transition failed after successful stop-session teardown: permission denied",
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
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(kwargs.get("agent_identity") or "HOUMAO-gpu"),
            launch_plan=kwargs["launch_plan"],
        ),
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
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    associate_registry_store(registry_root, tmp_path / "mail-old")
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
        mailbox_address="HOUMAO-research@agents.localhost",
    )
    monkeypatch.setattr(
        controller,
        "refresh_shared_registry_record",
        lambda: (_ for _ in ()).throw(SessionManifestError("registry refresh failed")),
    )

    refreshed = controller.refresh_mailbox_bindings(filesystem_root=tmp_path / "mail-old")

    assert refreshed.filesystem_root == (tmp_path / "mail-old").resolve()
    warnings = controller.consume_operation_warnings()
    assert len(warnings) == 1
    assert f"Offline binding committed at revision {refreshed.bindings_version}" in warnings[0]
    assert "shared-registry projection refresh failed" in warnings[0]
    assert "reconcile" in warnings[0]


def test_attach_and_detach_gateway_refreshes_registry_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(kwargs.get("agent_identity") or "HOUMAO-gpu"),
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
        agent_name="gpu",
    )
    paths = gateway_paths_from_manifest_path(controller.manifest_path)
    assert paths is not None
    access = gateway_access_for_manifest(controller.manifest_path)
    assert access.store.load().mode == "open"
    descriptor = GatewayEndpointDescriptor(
        protocol="v1",
        target=access.target,
        presence_id="fixture-instance",
        advertised_url="https://gateway.example.org/agents/gpu",
        admin_access="open",
        private_proof="none",
        public_operations=("messages", "public_prompt"),
    )

    def _fake_attach_gateway_for_controller(
        controller: Any,
        *,
        host_override: str | None,
        port_override: int | None,
        execution_mode_override: str | None,
        tui_tracking_timing_overrides: object | None = None,
        plugin_config: object | None = None,
        access_config: object | None = None,
    ) -> GatewayControlResult:
        del (
            controller,
            host_override,
            port_override,
            execution_mode_override,
            tui_tracking_timing_overrides,
            plugin_config,
            access_config,
        )
        write_gateway_current_instance(
            paths.current_instance_path,
            GatewayCurrentInstanceV1(
                pid=4242,
                host="127.0.0.1",
                port=43123,
                managed_agent_instance_epoch=1,
                endpoint_descriptor=descriptor,
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
    assert attached_record.gateway.owner_connect_url == "http://127.0.0.1:43123"
    assert attached_record.gateway.endpoint_descriptor == descriptor
    older_record = attached_record.model_dump(mode="python")
    older_record["gateway"]["endpoint_descriptor"].pop("private_proof")
    legacy_gateway = type(attached_record).model_validate(older_record).gateway
    assert legacy_gateway is not None and legacy_gateway.endpoint_descriptor is not None
    assert legacy_gateway.endpoint_descriptor.private_proof == "self_or_admin"

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
    assert detached_record.gateway is None
