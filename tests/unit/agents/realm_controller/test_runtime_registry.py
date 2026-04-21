from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.gateway_models import GatewayCurrentInstanceV1
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

    @property
    def state(self) -> HeadlessSessionState:
        return self.m_state

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        self.m_launch_plan = launch_plan

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        self.m_force_cleanup = force_cleanup

    def send_prompt(self, prompt: str, **kwargs: object) -> list[object]:
        del prompt, kwargs
        self.m_state = replace(self.m_state, turn_index=self.m_state.turn_index + 1)
        return []

    def interrupt(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
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


def test_start_resume_send_prompt_and_stop_refresh_registry(
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

    started_record = resolve_live_agent_record("gpu")
    assert started_record is not None
    assert started_record.agent_name == "gpu"
    assert started_record.generation_id == controller.registry_generation_id
    assert started_record.lifecycle.state == "active"
    assert started_record.lifecycle.relaunchable is True
    assert started_record.terminal.current_session_name is not None
    assert started_record.gateway is None
    started_published_at = datetime.fromisoformat(started_record.published_at)
    started_lease_expires_at = datetime.fromisoformat(started_record.lease_expires_at)
    assert (
        started_lease_expires_at - started_published_at == TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL
    )

    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["registry_generation_id"] == controller.registry_generation_id
    assert persisted["registry_launch_authority"] == "runtime"

    controller.send_prompt("hello")
    refreshed_record = resolve_live_agent_record("gpu")
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
    assert resumed.agent_id is not None
    stopped_record = load_managed_agent_record_by_agent_id(resumed.agent_id)
    assert stopped_record is not None
    assert stopped_record.lifecycle.state == "stopped"
    assert stopped_record.lifecycle.relaunchable is True
    assert stopped_record.liveness is None
    assert stopped_record.gateway is None
    assert stopped_record.terminal.current_session_name is None
    assert stopped_record.terminal.last_session_name == started_record.terminal.current_session_name
    stopped_payload = json.loads(resumed.manifest_path.read_text(encoding="utf-8"))
    assert stopped_payload["tmux_session_name"] == started_record.terminal.current_session_name


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


def test_stopped_revival_uses_stored_launch_profile_relaunch_policy(
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
        backend="local_interactive",
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

    revived = resume_stopped_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=controller.manifest_path,
    )
    result = revived.revive_stopped_session()

    assert result.status == "ok"
    assert isinstance(revived.backend_session, _FakeHeadlessSession)
    assert revived.backend_session.m_relaunch_chat_sessions[-1] is not None
    assert revived.backend_session.m_relaunch_chat_sessions[-1].mode == "tool_last_or_new"


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
        mailbox_principal_id="HOUMAO-research",
        mailbox_address="HOUMAO-research@agents.localhost",
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

    def _fake_attach_gateway_for_controller(
        controller: Any,
        *,
        host_override: str | None,
        port_override: int | None,
        execution_mode_override: str | None,
        tui_tracking_timing_overrides: object | None = None,
    ) -> GatewayControlResult:
        del (
            controller,
            host_override,
            port_override,
            execution_mode_override,
            tui_tracking_timing_overrides,
        )
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
    assert detached_record.gateway is None
