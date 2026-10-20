"""Kimi hook observation launch-plan and activation tests."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import time
import tomllib
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.local_interactive import LocalInteractiveSession
from houmao.agents.realm_controller.hook_observation_launch import (
    activate_hook_observation_for_provider_start,
    live_collector,
    stop_collector,
)
from houmao.agents.realm_controller.launch_plan import (
    LaunchPlanRequest,
    build_launch_plan,
)
from houmao.agents.realm_controller.loaders import load_role_package
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.hook_observation.install import (
    HOOK_OBSERVATION_CLAUDE_ENV_FLAG,
    HOOK_OBSERVATION_CODEX_ENV_FLAG,
    HOOK_OBSERVATION_KIMI_ENV_FLAG,
    KIMI_CONFIG_FILENAME,
    KimiObserverInstallResult,
    kimi_hook_artifact_dir,
)
from houmao.hook_observation.kimi_hooks_generator import (
    KIMI_EVENTS,
    OBSERVER_BLOCK_BEGIN_MARKER,
    validate_hooks_file,
)
from houmao.hook_observation.settings_generator import TOKEN_ENV_VAR

FLAG = HOOK_OBSERVATION_KIMI_ENV_FLAG
CLAUDE_FLAG = HOOK_OBSERVATION_CLAUDE_ENV_FLAG
CODEX_FLAG = HOOK_OBSERVATION_CODEX_ENV_FLAG


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _stub_kimi_version(monkeypatch: pytest.MonkeyPatch, version: str = "2.1.1") -> None:
    """Stub the provider version probes the Kimi launch flow performs."""

    def _fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=f"kimi {version}",
            stderr="",
        )

    monkeypatch.setattr("houmao.agents.launch_policy.engine.subprocess.run", _fake_run)


def _manifest(
    tmp_path: Path,
    *,
    operator_prompt_mode: str = "as_is",
) -> dict[str, Any]:
    home_path = tmp_path / "home"
    home_path.mkdir(parents=True, exist_ok=True)
    env_file = tmp_path / "vars.env"
    env_file.write_text("KIMI_MODEL_API_KEY=secret\n", encoding="utf-8")
    return {
        "schema_version": 3,
        "inputs": {
            "tool": "kimi",
            "skills": [],
            "setup": "default",
            "auth": "default",
            "adapter_path": "/tmp/tool-adapter.yaml",
            "preset_path": None,
        },
        "runtime": {
            "runtime_root": str(tmp_path),
            "home_id": "test-home",
            "home_path": str(home_path),
            "launch_helper": str(home_path / "launch.sh"),
            "launch_executable": "kimi",
            "launch_home_selector": {
                "env_var": "KIMI_CODE_HOME",
                "value": str(home_path),
            },
            "launch_contract": {
                "adapter_defaults": {"args": [], "tool_params": {}},
                "requested_overrides": {"preset": None, "direct": None},
                "tool_metadata": {"tool_params": {}},
                "construction_provenance": {
                    "adapter_path": "/tmp/tool-adapter.yaml",
                    "preset_path": None,
                    "preset_overrides_present": False,
                    "direct_overrides_present": False,
                },
            },
        },
        "credentials": {
            "auth_path": str(tmp_path / "auth"),
            "projected_files": [],
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": [],
            },
        },
        "launch_policy": {"operator_prompt_mode": operator_prompt_mode},
    }


def _build(
    tmp_path: Path,
    *,
    session_root: Path | None,
    operator_prompt_mode: str = "as_is",
) -> LaunchPlan:
    _write(tmp_path / "repo" / "roles/r/system-prompt.md", "Role prompt\n")
    role = load_role_package(tmp_path / "repo", "r")
    return build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=_manifest(tmp_path, operator_prompt_mode=operator_prompt_mode),
            role_package=role,
            backend="local_interactive",
            working_directory=tmp_path,
            session_root=session_root,
        )
    )


def _config_text(home_path: Path) -> str:
    return (home_path / KIMI_CONFIG_FILENAME).read_text(encoding="utf-8")


def _observer_entries(home_path: Path) -> list[dict[str, Any]]:
    document = tomllib.loads(_config_text(home_path))
    return [
        entry for entry in document.get("hooks", []) if "emitter.py" in entry.get("command", "")
    ]


def _wait_for_pid_exit(pid: int, *, timeout_seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def test_kimi_flag_off_and_other_adapter_flags_are_exact_noops(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.setenv(CLAUDE_FLAG, "1")
    monkeypatch.setenv(CODEX_FLAG, "1")
    session_root = tmp_path / "session"

    plan = _build(tmp_path, session_root=session_root)

    assert "hook_observation" not in plan.metadata
    assert not (tmp_path / "home" / KIMI_CONFIG_FILENAME).exists()
    assert not session_root.exists()


def test_kimi_provider_start_installs_the_observer_block(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(FLAG, "1")
    session_root = tmp_path / "session"

    plan = _build(tmp_path, session_root=session_root)

    metadata = plan.metadata["hook_observation"]
    assert metadata["install_path"] == "managed_home"
    assert metadata["generation"] == 1
    assert metadata["port"] is None
    assert metadata["settings_path"] == str(tmp_path / "home" / KIMI_CONFIG_FILENAME)
    assert metadata["settings_args"] == []
    assert plan.env.get(TOKEN_ENV_VAR) is None
    assert "--settings" not in plan.args

    config_text = _config_text(tmp_path / "home")
    assert OBSERVER_BLOCK_BEGIN_MARKER in config_text
    assert "generation 1" in config_text
    entries = _observer_entries(tmp_path / "home")
    assert [entry["event"] for entry in entries] == list(KIMI_EVENTS)
    for entry in entries:
        assert set(entry) == {"event", "command", "timeout"}
        assert entry["timeout"] == 5
        assert "http://127.0.0.1:0/v1/hook" in entry["command"]
        assert str(kimi_hook_artifact_dir(session_root)) in entry["command"]
        assert "--generation 1" in entry["command"]
    assert validate_hooks_file(tmp_path / "home" / KIMI_CONFIG_FILENAME).entry_count == len(
        KIMI_EVENTS
    )

    channel = json.loads(
        (kimi_hook_artifact_dir(session_root) / "channel.json").read_text(encoding="utf-8")
    )
    assert channel["channel_state"] == "installing"
    assert channel["install"]["path"] == "managed_home"
    assert channel["install"]["generation"] == 1
    assert channel["install"]["settings_path"] == str(tmp_path / "home" / KIMI_CONFIG_FILENAME)
    assert not (session_root / "hook-observation" / "claude").exists()
    assert not (session_root / "hook-observation" / "codex").exists()


def test_kimi_unattended_synthesis_keeps_the_observer_block(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(FLAG, "1")
    home = tmp_path / "home"
    home.mkdir()
    (home / KIMI_CONFIG_FILENAME).write_text(
        'default_model = "kimi-code/kimi-for-coding"\n'
        'extra_skill_dirs = ["/project/skills"]\n'
        '\n[providers."managed:kimi-code"]\ntype = "moonshot"\n',
        encoding="utf-8",
    )
    session_root = tmp_path / "session"

    plan = _build(
        tmp_path,
        session_root=session_root,
        operator_prompt_mode="unattended",
    )

    config_text = _config_text(home)
    payload = tomllib.loads(config_text)
    assert payload["default_permission_mode"] == "auto"
    assert payload["default_model"] == "kimi-code/kimi-for-coding"
    assert payload["extra_skill_dirs"] == ["/project/skills"]
    assert payload["providers"]["managed:kimi-code"]["type"] == "moonshot"
    assert config_text.count(OBSERVER_BLOCK_BEGIN_MARKER) == 1
    assert config_text.index("default_permission_mode") < config_text.index(
        OBSERVER_BLOCK_BEGIN_MARKER
    )
    assert validate_hooks_file(home / KIMI_CONFIG_FILENAME).entry_count == len(KIMI_EVENTS)
    assert "--auto" in plan.args
    assert plan.metadata["hook_observation"]["install_path"] == "managed_home"


def test_kimi_unattended_relaunch_rewrites_the_block_after_policy_synthesis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(FLAG, "1")
    home = tmp_path / "home"
    home.mkdir()
    (home / KIMI_CONFIG_FILENAME).write_text(
        'default_model = "kimi-code/kimi-for-coding"\n',
        encoding="utf-8",
    )
    session_root = tmp_path / "session"

    first = _build(tmp_path, session_root=session_root, operator_prompt_mode="unattended")
    second = _build(tmp_path, session_root=session_root, operator_prompt_mode="unattended")

    assert first.metadata["hook_observation"]["generation"] == 1
    assert second.metadata["hook_observation"]["generation"] == 2
    config_text = _config_text(home)
    assert config_text.count(OBSERVER_BLOCK_BEGIN_MARKER) == 1
    assert "generation 2" in config_text
    assert "generation 1" not in config_text
    payload = tomllib.loads(config_text)
    assert payload["default_permission_mode"] == "auto"
    assert payload["default_model"] == "kimi-code/kimi-for-coding"
    entries = _observer_entries(home)
    assert len(entries) == len(KIMI_EVENTS)
    assert all("--generation 2" in entry["command"] for entry in entries)
    assert validate_hooks_file(home / KIMI_CONFIG_FILENAME).entry_count == len(KIMI_EVENTS)


def test_kimi_activation_installs_the_real_port_and_keeps_the_token_out_of_plan_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(FLAG, "1")
    session_root = tmp_path / "session"
    plan = _build(tmp_path, session_root=session_root)

    activated = activate_hook_observation_for_provider_start(plan, session_root=session_root)
    handle = live_collector(session_root, tool="kimi")
    try:
        assert handle is not None
        metadata = activated.metadata["hook_observation"]
        assert metadata["port"] == handle.port
        assert metadata["generation"] == 1
        assert metadata["collector_pid"] == handle.pid
        assert metadata["install_path"] == "managed_home"
        assert isinstance(metadata["token"], str) and metadata["token"]
        assert TOKEN_ENV_VAR not in activated.env
        assert metadata["token"] not in activated.env.values()
        redacted = json.dumps(activated.redacted_payload())
        assert metadata["token"] not in redacted
        assert TOKEN_ENV_VAR not in redacted

        entries = _observer_entries(tmp_path / "home")
        assert len(entries) == len(KIMI_EVENTS)
        assert all(
            f"http://127.0.0.1:{handle.port}/v1/hook" in entry["command"] for entry in entries
        )
        assert all("--generation 1" in entry["command"] for entry in entries)
        assert metadata["token"] not in _config_text(tmp_path / "home")
        assert validate_hooks_file(tmp_path / "home" / KIMI_CONFIG_FILENAME).entry_count == len(
            KIMI_EVENTS
        )

        channel = json.loads(
            (kimi_hook_artifact_dir(session_root) / "channel.json").read_text(encoding="utf-8")
        )
        assert channel["channel_state"] == "active"
        assert channel["install"]["port"] == handle.port
        assert live_collector(session_root) is None
    finally:
        assert stop_collector(session_root, tool="kimi") is True


def test_kimi_relaunch_allocates_a_new_generation_and_rewrites_the_block(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(FLAG, "1")
    session_root = tmp_path / "session"
    first_plan = _build(tmp_path, session_root=session_root)
    first_activated = activate_hook_observation_for_provider_start(
        first_plan,
        session_root=session_root,
    )
    first_handle = live_collector(session_root, tool="kimi")
    assert first_handle is not None
    assert first_activated.metadata["hook_observation"]["generation"] == 1

    second_plan = _build(tmp_path, session_root=session_root)
    assert second_plan.metadata["hook_observation"]["generation"] == 2
    config_text = _config_text(tmp_path / "home")
    assert config_text.count(OBSERVER_BLOCK_BEGIN_MARKER) == 1
    assert "generation 2" in config_text

    second_activated = activate_hook_observation_for_provider_start(
        second_plan,
        session_root=session_root,
    )
    second_handle = live_collector(session_root, tool="kimi")
    try:
        assert second_handle is not None
        assert second_handle.generation == 2
        assert second_handle.pid != first_handle.pid
        assert _wait_for_pid_exit(first_handle.pid)
        assert second_activated.metadata["hook_observation"]["generation"] == 2
        assert second_activated.metadata["hook_observation"]["port"] == second_handle.port

        entries = _observer_entries(tmp_path / "home")
        assert len(entries) == len(KIMI_EVENTS)
        assert all(
            f"http://127.0.0.1:{second_handle.port}/v1/hook" in entry["command"]
            for entry in entries
        )
        assert all("--generation 2" in entry["command"] for entry in entries)
        channel = json.loads(
            (kimi_hook_artifact_dir(session_root) / "channel.json").read_text(encoding="utf-8")
        )
        assert channel["channel_state"] == "active"
        assert channel["install"]["generation"] == 2
    finally:
        assert stop_collector(session_root, tool="kimi") is True


def test_kimi_degrade_removes_the_observer_block(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(FLAG, "1")
    home = tmp_path / "home"
    home.mkdir()
    original_config = 'default_model = "kimi-code/kimi-for-coding"\n'
    (home / KIMI_CONFIG_FILENAME).write_text(original_config, encoding="utf-8")
    session_root = tmp_path / "session"
    plan = _build(tmp_path, session_root=session_root)
    assert OBSERVER_BLOCK_BEGIN_MARKER in _config_text(home)

    def _unavailable_install(**kwargs: object) -> KimiObserverInstallResult:
        return KimiObserverInstallResult(
            install_path="unavailable",
            generation=int(str(kwargs.get("generation", 1))),
            detail="simulated install failure",
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.hook_observation_launch."
        "install_kimi_observer_configuration",
        _unavailable_install,
    )

    degraded = activate_hook_observation_for_provider_start(plan, session_root=session_root)

    metadata = degraded.metadata["hook_observation"]
    assert metadata["install_path"] == "unavailable"
    assert metadata["detail"] == "simulated install failure"
    assert metadata["port"] is None
    assert metadata["collector_pid"] is None
    assert "token" not in metadata
    assert _config_text(home) == original_config
    assert live_collector(session_root, tool="kimi") is None
    channel = json.loads(
        (kimi_hook_artifact_dir(session_root) / "channel.json").read_text(encoding="utf-8")
    )
    assert channel["channel_state"] == "unavailable"


def test_kimi_launch_wrapper_is_adapter_scoped_and_exports_the_token(
    tmp_path: Path,
) -> None:
    token = "kimi-launch-token-secret-789"
    session_root = tmp_path / "session"
    plan = LaunchPlan(
        backend="local_interactive",
        tool="kimi",
        executable="sh",
        args=["-c", 'printf "%s" "$HOUMAO_HOOK_TOKEN"'],
        working_directory=tmp_path,
        home_env_var="KIMI_CODE_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="r",
            prompt="",
        ),
        metadata={
            "hook_observation": {
                "enabled": True,
                "token": token,
                "token_env": TOKEN_ENV_VAR,
            }
        },
    )
    session = object.__new__(LocalInteractiveSession)
    session._plan = plan
    session._session_manifest_path = (session_root / "manifest.json").resolve()

    pane_command, wrapper_path = session._provider_pane_command()

    assert wrapper_path == kimi_hook_artifact_dir(session_root) / "launch-wrapper.sh"
    assert token not in pane_command
    assert stat.S_IMODE(wrapper_path.stat().st_mode) == 0o600
    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    assert f"export {TOKEN_ENV_VAR}={token}" in wrapper_text
    assert TOKEN_ENV_VAR not in plan.env

    completed = subprocess.run(
        ["bash", str(wrapper_path)],
        env={**os.environ, "SHELL": "/bin/true"},
        capture_output=True,
        text=True,
        timeout=10.0,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout.startswith(token)
    wrapper_path.unlink()
