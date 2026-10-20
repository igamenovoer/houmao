"""Launch-plan and launch-wrapper tests for hook observation."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller.backends import headless_base
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
)
from houmao.agents.realm_controller.backends.local_interactive import LocalInteractiveSession
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
    allocate_next_generation,
    claude_hook_artifact_dir,
    hook_observation_enabled,
    kimi_hook_artifact_dir,
    remove_kimi_observer_configuration,
)
from houmao.hook_observation.kimi_hooks_generator import (
    KIMI_EVENTS,
    OBSERVER_BLOCK_BEGIN_MARKER,
    validate_hooks_file,
)
from houmao.hook_observation.settings_generator import (
    HTTP_EVENTS,
    TOKEN_ENV_VAR,
    is_observer_hook_entry,
)

FLAG = HOOK_OBSERVATION_CLAUDE_ENV_FLAG
CODEX_FLAG = HOOK_OBSERVATION_CODEX_ENV_FLAG
KIMI_FLAG = HOOK_OBSERVATION_KIMI_ENV_FLAG


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _manifest(
    tmp_path: Path,
    *,
    tool: str = "claude",
    backend_args: dict[str, Any] | None = None,
    operator_prompt_mode: str | None = "as_is",
) -> dict[str, Any]:
    home_path = tmp_path / "home"
    home_path.mkdir(parents=True, exist_ok=True)
    env_file = tmp_path / "vars.env"
    if tool == "claude":
        env_var = "ANTHROPIC_API_KEY"
        home_env_var = "CLAUDE_CONFIG_DIR"
    elif tool == "codex":
        env_var = "OPENAI_API_KEY"
        home_env_var = "CODEX_HOME"
    else:
        env_var = "KIMI_MODEL_API_KEY"
        home_env_var = "KIMI_CODE_HOME"
    env_file.write_text(f"{env_var}=secret\n", encoding="utf-8")
    runtime: dict[str, Any] = {
        "runtime_root": str(tmp_path),
        "home_id": "test-home",
        "home_path": str(home_path),
        "launch_helper": str(home_path / "launch.sh"),
        "launch_executable": tool,
        "launch_home_selector": {
            "env_var": home_env_var,
            "value": str(home_path),
        },
        "launch_contract": {
            "adapter_defaults": {"args": [], "tool_params": {}},
            "requested_overrides": {
                "preset": None,
                "direct": backend_args,
            },
            "tool_metadata": {"tool_params": {}},
            "construction_provenance": {
                "adapter_path": "/tmp/tool-adapter.yaml",
                "preset_path": None,
                "preset_overrides_present": False,
                "direct_overrides_present": backend_args is not None,
            },
        },
    }
    manifest: dict[str, Any] = {
        "schema_version": 3,
        "inputs": {
            "tool": tool,
            "skills": [],
            "setup": "default",
            "auth": "default",
            "adapter_path": "/tmp/tool-adapter.yaml",
            "preset_path": None,
        },
        "runtime": runtime,
        "credentials": {
            "auth_path": str(tmp_path / "auth"),
            "projected_files": [],
            "env_contract": {
                "source_file": str(env_file),
                "allowlisted_env_vars": [env_var],
            },
        },
    }
    if operator_prompt_mode is not None:
        manifest["launch_policy"] = {"operator_prompt_mode": operator_prompt_mode}
    return manifest


def _seed_settings(home_path: Path, payload: dict[str, Any]) -> Path:
    settings_path = home_path / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return settings_path


def _role(agent_def_dir: Path) -> Any:
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")
    return load_role_package(agent_def_dir, "r")


def _build(
    tmp_path: Path,
    *,
    manifest: dict[str, Any],
    session_root: Path | None,
    backend: str = "local_interactive",
    agent_def_dir: Path | None = None,
) -> LaunchPlan:
    role = _role(agent_def_dir or (tmp_path / "repo"))
    return build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend=backend,  # type: ignore[arg-type]
            working_directory=tmp_path,
            session_root=session_root,
        )
    )


def _observer_entries(entries: list[Any]) -> list[Any]:
    return [entry for entry in entries if is_observer_hook_entry(entry)]


def _operator_user_prompt_entry() -> dict[str, Any]:
    return {
        "hooks": [
            {
                "type": "command",
                "command": "echo operator",
            }
        ]
    }


def test_flag_off_is_an_exact_noop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(FLAG, raising=False)
    settings_path = _seed_settings(
        tmp_path / "home",
        {"skipDangerousModePermissionPrompt": True, "hooks": {}},
    )
    original_settings = settings_path.read_text(encoding="utf-8")
    session_root = tmp_path / "session"

    plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path),
        session_root=session_root,
    )

    assert "hook_observation" not in plan.metadata
    assert settings_path.read_text(encoding="utf-8") == original_settings
    assert not session_root.exists()
    assert "--settings" not in plan.args


@pytest.mark.parametrize("value", ["0", "true", "yes", ""])
def test_non_one_flag_value_is_a_noop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    value: str,
) -> None:
    monkeypatch.setenv(FLAG, value)
    session_root = tmp_path / "session"

    plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path),
        session_root=session_root,
    )

    assert "hook_observation" not in plan.metadata
    assert not session_root.exists()


def test_missing_session_root_is_a_noop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(FLAG, "1")

    plan = _build(tmp_path, manifest=_manifest(tmp_path), session_root=None)

    assert "hook_observation" not in plan.metadata
    assert "--settings" not in plan.args


def test_non_claude_or_non_local_backend_is_a_noop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(FLAG, "1")
    session_root = tmp_path / "session"

    codex_plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path, tool="codex"),
        session_root=session_root,
    )
    claude_headless_plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path),
        session_root=session_root,
        backend="claude_headless",
    )

    assert "hook_observation" not in codex_plan.metadata
    assert "hook_observation" not in claude_headless_plan.metadata
    assert not session_root.exists()


def test_managed_home_block_is_marker_merged_and_preserves_entries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(FLAG, "1")
    operator_entry = _operator_user_prompt_entry()
    operator_pre_tool_use = {"hooks": [{"type": "command", "command": "audit-tool"}]}
    settings_path = _seed_settings(
        tmp_path / "home",
        {
            "skipDangerousModePermissionPrompt": True,
            "permissions": {"allow": ["Bash(ls)"]},
            "hooks": {
                "UserPromptSubmit": [operator_entry],
                "PreToolUse": [operator_pre_tool_use],
            },
        },
    )
    session_root = tmp_path / "session"

    plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path),
        session_root=session_root,
    )

    metadata = plan.metadata["hook_observation"]
    assert metadata["install_path"] == "managed_home"
    assert metadata["generation"] == 1
    assert metadata["settings_args"] == []
    assert "--settings" not in plan.args
    assert plan.env.get(TOKEN_ENV_VAR) is None

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["skipDangerousModePermissionPrompt"] is True
    assert settings["permissions"] == {"allow": ["Bash(ls)"]}
    assert settings["hooks"]["UserPromptSubmit"][0] == operator_entry
    assert settings["hooks"]["PreToolUse"] == [operator_pre_tool_use]
    for event_name in HTTP_EVENTS:
        entries = settings["hooks"][event_name]
        observers = _observer_entries(entries)
        assert len(observers) == 1
        handler = observers[0]["hooks"][0]
        assert handler["type"] == "http"
        assert handler["url"] == "http://127.0.0.1:0/v1/hook"
        assert handler["headers"] == {"Authorization": f"Bearer ${TOKEN_ENV_VAR}"}
    session_start_command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "houmao.hook_observation.emitter" in session_start_command
    assert "--generation 1" in session_start_command

    channel = json.loads(
        (claude_hook_artifact_dir(session_root) / "channel.json").read_text(encoding="utf-8")
    )
    assert channel["status"] == "stopped"
    assert channel["channel_state"] == "installing"
    assert channel["install"]["path"] == "managed_home"
    assert channel["install"]["generation"] == 1


def test_stale_observer_block_is_repaired_on_a_reused_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(FLAG, "1")
    stale_entry = {
        "hooks": [
            {
                "type": "http",
                "url": "http://127.0.0.1:9999/v1/hook",
                "timeout": 2,
                "headers": {"Authorization": f"Bearer ${TOKEN_ENV_VAR}"},
                "allowedEnvVars": [TOKEN_ENV_VAR],
            }
        ]
    }
    operator_entry = _operator_user_prompt_entry()
    settings_path = _seed_settings(
        tmp_path / "home",
        {
            "skipDangerousModePermissionPrompt": True,
            "hooks": {"UserPromptSubmit": [stale_entry, operator_entry]},
        },
    )
    session_root = tmp_path / "session"

    first_plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path),
        session_root=session_root,
    )
    second_plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path),
        session_root=session_root,
    )

    assert first_plan.metadata["hook_observation"]["generation"] == 1
    assert second_plan.metadata["hook_observation"]["generation"] == 2
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    entries = settings["hooks"]["UserPromptSubmit"]
    assert entries[0] == operator_entry
    observers = _observer_entries(entries)
    assert len(observers) == 1
    assert observers[0]["hooks"][0]["url"] == "http://127.0.0.1:0/v1/hook"
    session_start_command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "--generation 2" in session_start_command


def test_unmergeable_home_falls_back_to_launch_owned_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(FLAG, "1")
    settings_path = tmp_path / "home" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("{not json", encoding="utf-8")
    session_root = tmp_path / "session"

    plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path),
        session_root=session_root,
    )

    metadata = plan.metadata["hook_observation"]
    assert metadata["install_path"] == "settings_file"
    fallback_path = claude_hook_artifact_dir(session_root) / "observer-settings.json"
    assert fallback_path.is_file()
    assert stat.S_IMODE(fallback_path.stat().st_mode) == 0o600
    assert plan.args[-2:] == ["--settings", str(fallback_path)]
    assert metadata["settings_args"] == ["--settings", str(fallback_path)]
    fallback = json.loads(fallback_path.read_text(encoding="utf-8"))
    assert set(fallback["hooks"]) == {*HTTP_EVENTS, "SessionStart"}
    assert settings_path.read_text(encoding="utf-8") == "{not json"


def test_fallback_settings_conflict_degrades_to_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(FLAG, "1")
    operator_settings = tmp_path / "operator-settings.json"
    operator_settings.write_text("{}", encoding="utf-8")
    direct_overrides = {
        "args": {"mode": "append", "values": ["--settings", str(operator_settings)]},
        "tool_params": {},
    }
    session_root = tmp_path / "session"

    plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path, backend_args=direct_overrides),
        session_root=session_root,
    )

    metadata = plan.metadata["hook_observation"]
    assert metadata["install_path"] == "unavailable"
    assert "settings" in (metadata["detail"] or "")
    assert plan.args.count("--settings") == 1
    assert str(operator_settings) in plan.args
    fallback_path = claude_hook_artifact_dir(session_root) / "observer-settings.json"
    assert not fallback_path.exists()
    channel = json.loads(
        (claude_hook_artifact_dir(session_root) / "channel.json").read_text(encoding="utf-8")
    )
    assert channel["channel_state"] == "unavailable"


def test_generation_counter_persists_and_increments(tmp_path: Path) -> None:
    session_root = tmp_path / "session"

    assert allocate_next_generation(session_root) == 1
    assert allocate_next_generation(session_root) == 2
    counter = claude_hook_artifact_dir(session_root) / "generation.json"
    counter_payload = json.loads(counter.read_text(encoding="utf-8"))
    assert counter_payload["generation"] == 2
    assert stat.S_IMODE(counter.stat().st_mode) == 0o600
    assert hook_observation_enabled({FLAG: "1"}) is True
    assert hook_observation_enabled({FLAG: "0"}) is False
    assert hook_observation_enabled({}) is False


def test_launch_wrapper_exports_token_without_exposing_it_in_the_pane_command(
    tmp_path: Path,
) -> None:
    token = "launch-token-secret-123"
    plan = LaunchPlan(
        backend="local_interactive",
        tool="claude",
        executable="sh",
        args=["-c", 'printf "%s" "$HOUMAO_HOOK_TOKEN"'],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
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
    session._session_manifest_path = (tmp_path / "session" / "manifest.json").resolve()

    pane_command, wrapper_path = session._provider_pane_command()

    assert wrapper_path is not None
    assert token not in pane_command
    assert stat.S_IMODE(wrapper_path.stat().st_mode) == 0o600
    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    assert f"export {TOKEN_ENV_VAR}={token}" in wrapper_text

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


def test_published_tmux_environment_never_contains_the_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    token = "tmux-leak-sentinel-456"
    plan = LaunchPlan(
        backend="local_interactive",
        tool="claude",
        executable="claude",
        args=[],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env={"ANTHROPIC_API_KEY": "secret"},
        env_var_names=["ANTHROPIC_API_KEY"],
        role_injection=RoleInjectionPlan(method="cao_profile", role_name="r", prompt=""),
        metadata={
            "hook_observation": {
                "enabled": True,
                "token": token,
                "token_env": TOKEN_ENV_VAR,
            }
        },
    )
    captured: dict[str, dict[str, str]] = {}

    def _capture(*, session_name: str, env_vars: dict[str, str]) -> None:
        captured["env"] = dict(env_vars)

    monkeypatch.setattr(
        headless_base,
        "set_tmux_session_environment_shared",
        _capture,
    )
    session = object.__new__(HeadlessInteractiveSession)
    session._state = HeadlessSessionState(
        tmux_session_name="HOUMAO-test",
        session_id="sess-1",
    )
    session._plan = plan
    session._session_manifest_path = (tmp_path / "session" / "manifest.json").resolve()
    session._agent_def_dir = None

    session._publish_tmux_session_environment()

    published = captured["env"]
    assert TOKEN_ENV_VAR not in published
    assert token not in published.values()
    assert token not in plan.env.values()


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


def _kimi_config(home_path: Path) -> dict[str, Any]:
    return tomllib.loads((home_path / KIMI_CONFIG_FILENAME).read_text(encoding="utf-8"))


def _kimi_observer_entries(home_path: Path) -> list[dict[str, Any]]:
    return [
        entry
        for entry in _kimi_config(home_path).get("hooks", [])
        if "emitter.py" in entry.get("command", "")
    ]


def test_kimi_gate_is_open_for_local_interactive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(KIMI_FLAG, "1")
    session_root = tmp_path / "session"

    plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path, tool="kimi"),
        session_root=session_root,
    )

    metadata = plan.metadata["hook_observation"]
    assert metadata["install_path"] == "managed_home"
    assert metadata["generation"] == 1
    assert metadata["port"] is None
    assert metadata["settings_path"] == str(tmp_path / "home" / KIMI_CONFIG_FILENAME)
    assert metadata["settings_args"] == []
    assert plan.env.get(TOKEN_ENV_VAR) is None
    assert "--settings" not in plan.args

    entries = _kimi_observer_entries(tmp_path / "home")
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
    assert not (session_root / "hook-observation" / "claude").exists()
    assert not (session_root / "hook-observation" / "codex").exists()


def test_kimi_flag_is_required_and_headless_is_a_noop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.delenv(KIMI_FLAG, raising=False)
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setenv(CODEX_FLAG, "1")
    local_session_root = tmp_path / "local-session"

    local_plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path, tool="kimi"),
        session_root=local_session_root,
    )

    assert "hook_observation" not in local_plan.metadata
    assert not (tmp_path / "home" / KIMI_CONFIG_FILENAME).exists()
    assert not local_session_root.exists()

    monkeypatch.setenv(KIMI_FLAG, "1")
    headless_session_root = tmp_path / "headless-session"
    headless_plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path, tool="kimi"),
        session_root=headless_session_root,
        backend="kimi_headless",
    )

    assert "hook_observation" not in headless_plan.metadata
    assert not headless_session_root.exists()


def test_kimi_managed_home_block_coexists_with_launch_policy_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(KIMI_FLAG, "1")
    home = tmp_path / "home"
    home.mkdir()
    (home / KIMI_CONFIG_FILENAME).write_text(
        """
default_model = "kimi-code/kimi-for-coding"
extra_skill_dirs = ["/project/skills"]

[providers."managed:kimi-code"]
type = "moonshot"

[models."kimi-k2.5"]
provider = "managed"
""".lstrip(),
        encoding="utf-8",
    )
    session_root = tmp_path / "session"

    plan = _build(
        tmp_path,
        manifest=_manifest(tmp_path, tool="kimi", operator_prompt_mode="unattended"),
        session_root=session_root,
    )

    config_text = (home / KIMI_CONFIG_FILENAME).read_text(encoding="utf-8")
    payload = _kimi_config(home)
    assert payload["default_permission_mode"] == "auto"
    assert payload["default_model"] == "kimi-code/kimi-for-coding"
    assert payload["extra_skill_dirs"] == ["/project/skills"]
    assert payload["providers"]["managed:kimi-code"]["type"] == "moonshot"
    assert payload["models"]["kimi-k2.5"]["provider"] == "managed"
    assert config_text.count(OBSERVER_BLOCK_BEGIN_MARKER) == 1
    assert config_text.index("default_permission_mode") < config_text.index(
        OBSERVER_BLOCK_BEGIN_MARKER
    )
    assert len(_kimi_observer_entries(home)) == len(KIMI_EVENTS)
    report = validate_hooks_file(home / KIMI_CONFIG_FILENAME)
    assert report.entry_count == len(KIMI_EVENTS)
    assert "--auto" in plan.args
    assert plan.metadata["hook_observation"]["install_path"] == "managed_home"


def test_kimi_observer_block_survives_the_policy_rerender_on_relaunch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(KIMI_FLAG, "1")
    home = tmp_path / "home"
    home.mkdir()
    (home / KIMI_CONFIG_FILENAME).write_text(
        'default_model = "kimi-code/kimi-for-coding"\n',
        encoding="utf-8",
    )
    session_root = tmp_path / "session"

    first = _build(
        tmp_path,
        manifest=_manifest(tmp_path, tool="kimi", operator_prompt_mode="unattended"),
        session_root=session_root,
    )
    second = _build(
        tmp_path,
        manifest=_manifest(tmp_path, tool="kimi", operator_prompt_mode="unattended"),
        session_root=session_root,
    )

    assert first.metadata["hook_observation"]["generation"] == 1
    assert second.metadata["hook_observation"]["generation"] == 2
    config_text = (home / KIMI_CONFIG_FILENAME).read_text(encoding="utf-8")
    assert config_text.count(OBSERVER_BLOCK_BEGIN_MARKER) == 1
    assert "generation 2" in config_text
    assert "generation 1" not in config_text
    payload = _kimi_config(home)
    assert payload["default_permission_mode"] == "auto"
    assert payload["default_model"] == "kimi-code/kimi-for-coding"
    entries = _kimi_observer_entries(home)
    assert len(entries) == len(KIMI_EVENTS)
    assert all("--generation 2" in entry["command"] for entry in entries)
    assert validate_hooks_file(home / KIMI_CONFIG_FILENAME).entry_count == len(KIMI_EVENTS)


def test_kimi_teardown_removes_the_installed_block(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_kimi_version(monkeypatch)
    monkeypatch.setenv(KIMI_FLAG, "1")
    home = tmp_path / "home"
    home.mkdir()
    original_config = (
        'default_model = "kimi-code/kimi-for-coding"\n'
        'extra_skill_dirs = ["/project/skills"]\n'
        '\n[[hooks]]\nevent = "Notification"\ncommand = "notify-send kimi"\ntimeout = 10\n'
    )
    (home / KIMI_CONFIG_FILENAME).write_text(original_config, encoding="utf-8")
    session_root = tmp_path / "session"

    _build(
        tmp_path,
        manifest=_manifest(tmp_path, tool="kimi"),
        session_root=session_root,
    )
    assert OBSERVER_BLOCK_BEGIN_MARKER in (home / KIMI_CONFIG_FILENAME).read_text(encoding="utf-8")

    remove_kimi_observer_configuration(home_path=home)

    assert (home / KIMI_CONFIG_FILENAME).read_text(encoding="utf-8") == original_config
