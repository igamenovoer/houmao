"""Real-subprocess tests for the hook observation collector lifecycle."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller import runtime as runtime_module
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.hook_observation_launch import (
    activate_hook_observation_for_provider_start,
    ensure_hook_observation_on_resume,
    live_collector,
    start_collector,
    stop_collector,
)
from houmao.agents.realm_controller.launch_plan import LaunchPlanRequest, build_launch_plan
from houmao.agents.realm_controller.loaders import load_brain_manifest, load_role_package
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionControlResult,
)
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    resume_runtime_session,
    start_runtime_session,
)
from houmao.hook_observation.install import (
    HOOK_OBSERVATION_CLAUDE_ENV_FLAG,
    allocate_next_generation,
    claude_hook_artifact_dir,
    install_observer_configuration,
)
from houmao.hook_observation.settings_generator import TOKEN_ENV_VAR
from houmao.hook_observation.store import read_store

FLAG = HOOK_OBSERVATION_CLAUDE_ENV_FLAG


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _post(
    port: int,
    payload: dict[str, Any],
    *,
    token: str | None,
) -> int:
    query = f"http://127.0.0.1:{port}/v1/hook"
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        query,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _wait_for_pid_exit(pid: int, *, timeout_seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def _plan_with_observer_metadata(
    tmp_path: Path,
    *,
    session_root: Path,
    generation: int,
) -> LaunchPlan:
    home_path = tmp_path / "home"
    home_path.mkdir(parents=True, exist_ok=True)
    (home_path / "settings.json").write_text(
        json.dumps({"skipDangerousModePermissionPrompt": True}) + "\n",
        encoding="utf-8",
    )
    install_result = install_observer_configuration(
        home_path=home_path,
        session_root=session_root,
        generation=generation,
        port=0,
    )
    return LaunchPlan(
        backend="local_interactive",
        tool="claude",
        executable="claude",
        args=[*install_result.appended_args],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=home_path,
        env={"ANTHROPIC_API_KEY": "secret"},
        env_var_names=["ANTHROPIC_API_KEY"],
        role_injection=RoleInjectionPlan(method="cao_profile", role_name="r", prompt=""),
        metadata={
            "hook_observation": {
                "enabled": True,
                "install_path": install_result.install_path,
                "generation": generation,
                "port": None,
                "settings_path": (
                    str(install_result.settings_path)
                    if install_result.settings_path is not None
                    else None
                ),
                "settings_args": list(install_result.appended_args),
                "detail": install_result.detail,
                "session_root": str(session_root.resolve()),
                "token_env": TOKEN_ENV_VAR,
            }
        },
    )


def test_collector_start_auth_and_stop(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    token = "integration-collector-token"
    handle = start_collector(session_root=session_root, generation=3, token=token)
    try:
        assert live_collector(session_root) == handle
        assert _post(handle.port, {"hook_event_name": "Stop"}, token=None) == 403
        assert _post(handle.port, {"hook_event_name": "SessionStart"}, token=token) == 204
        deadline = time.monotonic() + 5.0
        envelopes: tuple[Any, ...] = ()
        while time.monotonic() < deadline:
            envelopes = read_store(
                claude_hook_artifact_dir(session_root) / "events.ndjson"
            ).envelopes
            if any(item.event_name == "SessionStart" for item in envelopes):
                break
            time.sleep(0.05)
        accepted = [item for item in envelopes if item.event_name == "SessionStart"]
        assert len(accepted) == 1
        assert accepted[0].channel_generation == 3
        assert accepted[0].sequence == 1
    finally:
        assert stop_collector(session_root) is True

    assert _wait_for_pid_exit(handle.pid)
    record = json.loads(
        (claude_hook_artifact_dir(session_root) / "collector.json").read_text(encoding="utf-8")
    )
    assert record["status"] == "stopped"
    assert live_collector(session_root) is None
    assert stop_collector(session_root) is False


def test_generation_isolation_across_collector_restarts(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    events_path = claude_hook_artifact_dir(session_root) / "events.ndjson"
    first = start_collector(session_root=session_root, generation=1, token="token-one")
    try:
        assert _post(first.port, {"hook_event_name": "UserPromptSubmit"}, token="token-one") == 204
        assert _post(first.port, {"hook_event_name": "Stop"}, token="token-one") == 204
    finally:
        assert stop_collector(session_root) is True
    assert _wait_for_pid_exit(first.pid)

    second = start_collector(session_root=session_root, generation=2, token="token-two")
    try:
        assert _post(second.port, {"hook_event_name": "UserPromptSubmit"}, token="token-two") == 204
    finally:
        assert stop_collector(session_root) is True
    assert _wait_for_pid_exit(second.pid)

    envelopes = read_store(events_path).envelopes
    events = [item for item in envelopes if not item.is_generation_boundary]
    assert [item.channel_generation for item in events] == [1, 1, 2]
    boundaries = [item for item in envelopes if item.is_generation_boundary]
    assert [item.channel_generation for item in boundaries] == [1, 2]


def test_activation_installs_real_port_and_keeps_token_out_of_plan_env(
    tmp_path: Path,
) -> None:
    session_root = tmp_path / "session"
    generation = allocate_next_generation(session_root)
    plan = _plan_with_observer_metadata(tmp_path, session_root=session_root, generation=generation)

    activated = activate_hook_observation_for_provider_start(plan, session_root=session_root)
    metadata = activated.metadata["hook_observation"]
    try:
        handle = live_collector(session_root)
        assert handle is not None
        assert metadata["port"] == handle.port
        assert metadata["generation"] == generation
        assert metadata["install_path"] == "managed_home"
        assert isinstance(metadata["token"], str) and metadata["token"]
        assert TOKEN_ENV_VAR not in activated.env
        assert metadata["token"] not in activated.env.values()
        redacted = json.dumps(activated.redacted_payload())
        assert metadata["token"] not in redacted
        assert TOKEN_ENV_VAR not in redacted

        settings_text = (plan.home_path / "settings.json").read_text(encoding="utf-8")
        assert metadata["token"] not in settings_text
        settings = json.loads(settings_text)
        observer_url = settings["hooks"]["Stop"][0]["hooks"][0]["url"]
        assert observer_url == f"http://127.0.0.1:{handle.port}/v1/hook"
        assert "--generation" in settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        assert (
            json.loads(
                (claude_hook_artifact_dir(session_root) / "channel.json").read_text(
                    encoding="utf-8"
                )
            )["channel_state"]
            == "active"
        )
    finally:
        assert stop_collector(session_root) is True


def test_resume_reuses_live_collector_and_bumps_generation_when_dead(
    tmp_path: Path,
) -> None:
    session_root = tmp_path / "session"
    generation = allocate_next_generation(session_root)
    plan = _plan_with_observer_metadata(tmp_path, session_root=session_root, generation=generation)
    activated = activate_hook_observation_for_provider_start(plan, session_root=session_root)
    first = live_collector(session_root)
    assert first is not None
    try:
        resumed = ensure_hook_observation_on_resume(
            activated,
            session_root=session_root,
            env={FLAG: "1"},
        )
        resumed_metadata = resumed.metadata["hook_observation"]
        assert resumed_metadata["generation"] == first.generation
        assert resumed_metadata["port"] == first.port
        assert live_collector(session_root) == first
    finally:
        assert stop_collector(session_root) is True
    assert _wait_for_pid_exit(first.pid)

    restarted = ensure_hook_observation_on_resume(
        activated,
        session_root=session_root,
        env={FLAG: "1"},
    )
    restarted_metadata = restarted.metadata["hook_observation"]
    try:
        assert restarted_metadata["generation"] == generation + 1
        new_handle = live_collector(session_root)
        assert new_handle is not None
        assert new_handle.generation == generation + 1
        assert restarted_metadata["port"] == new_handle.port
        assert new_handle.pid != first.pid
    finally:
        assert stop_collector(session_root) is True


def test_flag_off_resume_leaves_the_channel_alone(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    generation = allocate_next_generation(session_root)
    plan = _plan_with_observer_metadata(tmp_path, session_root=session_root, generation=generation)
    activated = activate_hook_observation_for_provider_start(plan, session_root=session_root)
    handle = live_collector(session_root)
    assert handle is not None
    try:
        resumed = ensure_hook_observation_on_resume(
            activated,
            session_root=session_root,
            env={FLAG: "0"},
        )
        assert resumed.metadata["hook_observation"]["generation"] == handle.generation
        assert live_collector(session_root) == handle
    finally:
        assert stop_collector(session_root) is True


def test_collector_start_failure_degrades_to_tui_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_root = tmp_path / "session"
    generation = allocate_next_generation(session_root)
    plan = _plan_with_observer_metadata(tmp_path, session_root=session_root, generation=generation)

    def _fail_start(**kwargs: object) -> object:
        del kwargs
        raise RuntimeError("collector unavailable")

    monkeypatch.setattr(
        "houmao.agents.realm_controller.hook_observation_launch.start_collector",
        _fail_start,
    )

    degraded = activate_hook_observation_for_provider_start(plan, session_root=session_root)
    metadata = degraded.metadata["hook_observation"]
    assert metadata["install_path"] == "unavailable"
    assert "collector start failed" in (metadata["detail"] or "")
    assert "--settings" not in degraded.args
    assert live_collector(session_root) is None
    channel = json.loads(
        (claude_hook_artifact_dir(session_root) / "channel.json").read_text(encoding="utf-8")
    )
    assert channel["channel_state"] == "unavailable"


def test_activation_settings_conflict_degrades_and_leaves_no_collector(
    tmp_path: Path,
) -> None:
    session_root = tmp_path / "session"
    generation = allocate_next_generation(session_root)
    plan = _plan_with_observer_metadata(tmp_path, session_root=session_root, generation=generation)
    (plan.home_path / "settings.json").unlink()
    operator_settings = tmp_path / "operator-settings.json"
    operator_settings.write_text("{}", encoding="utf-8")
    conflicted = replace(plan, args=["--settings", str(operator_settings)])

    degraded = activate_hook_observation_for_provider_start(
        conflicted,
        session_root=session_root,
    )

    metadata = degraded.metadata["hook_observation"]
    assert metadata["install_path"] == "unavailable"
    assert "settings" in (metadata["detail"] or "")
    assert degraded.args == ["--settings", str(operator_settings)]
    assert live_collector(session_root) is None
    assert not (claude_hook_artifact_dir(session_root) / "collector.json").exists() or (
        json.loads(
            (claude_hook_artifact_dir(session_root) / "collector.json").read_text(encoding="utf-8")
        )["status"]
        == "stopped"
    )


def _seed_manifest(tmp_path: Path) -> Path:
    home_path = tmp_path / "home"
    home_path.mkdir(parents=True, exist_ok=True)
    (home_path / "settings.json").write_text(
        json.dumps({"skipDangerousModePermissionPrompt": True}) + "\n",
        encoding="utf-8",
    )
    env_file = tmp_path / "vars.env"
    env_file.write_text("ANTHROPIC_API_KEY=secret\n", encoding="utf-8")
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
                "runtime:",
                f"  runtime_root: {tmp_path}",
                "  home_id: test-home",
                f"  home_path: {home_path}",
                f"  launch_helper: {home_path / 'launch.sh'}",
                "  launch_executable: claude",
                "  launch_home_selector:",
                "    env_var: CLAUDE_CONFIG_DIR",
                f"    value: {home_path}",
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
                "launch_policy:",
                "  operator_prompt_mode: as_is",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


class _StopLaunch(RuntimeError):
    """Sentinel raised after asserting collector ordering."""


def test_start_runtime_session_starts_collector_before_backend_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    agent_def_dir = tmp_path / "repo"
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")
    brain_manifest_path = _seed_manifest(tmp_path)
    observed: dict[str, Any] = {}

    def _fake_create_backend_session(**kwargs: Any) -> object:
        manifest_path = Path(kwargs["session_manifest_path"])
        session_root = manifest_path.parent
        plan: LaunchPlan = kwargs["launch_plan"]
        handle = live_collector(session_root)
        observed["handle"] = handle
        observed["hook_metadata"] = plan.metadata.get("hook_observation")
        observed["home_settings"] = json.loads(
            (plan.home_path / "settings.json").read_text(encoding="utf-8")
        )
        raise _StopLaunch

    monkeypatch.setattr(
        runtime_module,
        "_create_backend_session",
        _fake_create_backend_session,
    )

    with pytest.raises(_StopLaunch):
        start_runtime_session(
            agent_def_dir=agent_def_dir,
            brain_manifest_path=brain_manifest_path,
            role_name="r",
            runtime_root=tmp_path / "runtime",
            backend="local_interactive",
            working_directory=tmp_path,
            agent_name="hookobs",
        )

    handle = observed["handle"]
    assert handle is not None
    metadata = observed["hook_metadata"]
    assert metadata["port"] == handle.port
    observer_url = observed["home_settings"]["hooks"]["Stop"][0]["hooks"][0]["url"]
    assert observer_url == f"http://127.0.0.1:{handle.port}/v1/hook"

    session_roots = list((tmp_path / "runtime" / "sessions" / "local_interactive").iterdir())
    assert len(session_roots) == 1
    assert _wait_for_pid_exit(handle.pid)
    assert live_collector(session_roots[0]) is None


class _FakeBackend:
    """Minimal backend used to exercise the controller stop path."""

    def terminate(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        del force_cleanup


def test_controller_stop_terminates_the_collector(tmp_path: Path) -> None:
    session_root = tmp_path / "session"
    plan = _plan_with_observer_metadata(
        tmp_path,
        session_root=session_root,
        generation=allocate_next_generation(session_root),
    )
    activated = activate_hook_observation_for_provider_start(plan, session_root=session_root)
    handle = live_collector(session_root)
    assert handle is not None
    controller = RuntimeSessionController(
        launch_plan=activated,
        role_name="r",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=session_root / "manifest.json",
        backend_session=_FakeBackend(),  # type: ignore[arg-type]
    )
    controller.detach_gateway = lambda: None  # type: ignore[method-assign]
    controller.persist_manifest = lambda **kwargs: None  # type: ignore[method-assign]
    controller.publish_stopped_shared_registry_record = (  # type: ignore[method-assign]
        lambda **kwargs: None
    )
    controller.clear_shared_registry_record = lambda: False  # type: ignore[method-assign]

    result = controller.stop()

    assert result.status == "ok"
    assert _wait_for_pid_exit(handle.pid)
    assert live_collector(session_root) is None


def test_resume_runtime_session_bumps_generation_before_backend_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    agent_def_dir = tmp_path / "repo"
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")
    brain_manifest_path = _seed_manifest(tmp_path)
    manifest = load_brain_manifest(brain_manifest_path)
    role = load_role_package(agent_def_dir, "r")
    session_root = tmp_path / "sessions" / "local_interactive" / "sess-hookobs"
    session_root.mkdir(parents=True)
    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="local_interactive",
            working_directory=tmp_path,
            session_root=session_root,
        )
    )
    assert launch_plan.metadata["hook_observation"]["generation"] == 1
    session_payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            agent_name="HOUMAO-hookobs",
            agent_id=derive_agent_id_from_name("HOUMAO-hookobs"),
            tmux_session_name="HOUMAO-hookobs",
            backend_state={
                "turn_index": 0,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-hookobs",
            },
        )
    )
    manifest_path = session_root / "manifest.json"
    manifest_path.write_text(json.dumps(session_payload), encoding="utf-8")
    observed: dict[str, Any] = {}

    def _fake_create_backend_session(**kwargs: Any) -> object:
        plan: LaunchPlan = kwargs["launch_plan"]
        handle = live_collector(session_root)
        observed["handle"] = handle
        observed["metadata"] = plan.metadata.get("hook_observation")
        raise _StopLaunch

    monkeypatch.setattr(
        runtime_module,
        "_create_backend_session",
        _fake_create_backend_session,
    )

    try:
        with pytest.raises(_StopLaunch):
            resume_runtime_session(
                agent_def_dir=agent_def_dir,
                session_manifest_path=manifest_path,
            )
        handle = observed["handle"]
        metadata = observed["metadata"]
        assert handle is not None
        assert metadata["generation"] == 2
        assert metadata["port"] == handle.port
        assert handle.generation == 2
    finally:
        stop_collector(session_root)
