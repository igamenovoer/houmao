"""Verify managed Hermes configuration and executable lookup using isolated inputs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shlex
import shutil
import stat
from unittest.mock import Mock

import pytest
import yaml

from houmao.agents.brain_builder import BuildError, BuildRequest, build_brain_home
from houmao.agents.hermes_configuration import (
    HERMES_API_KEY_ENV,
    HERMES_HOME_ENV,
    HERMES_LOCK_DIR_ENV,
    hermes_runtime_environment,
    project_hermes_approval_policy,
    resolve_hermes_executable,
    write_hermes_role,
)
from houmao.agents.model_selection import ModelConfig, ModelReasoningConfig
from houmao.agents.launch_policy import cli as launch_policy_cli
from houmao.agents.realm_controller.errors import BackendExecutionError, SessionManifestError
from houmao.agents.realm_controller.gateway_models import GatewayTuiTrackingTimingOverridesV1
from houmao.agents.realm_controller.models import BackendKind, LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.runtime import RuntimeSessionController, start_runtime_session
from houmao.execution.tmux_selection import ResolvedTmuxServer


@pytest.fixture()
def build_request(tmp_path: Path) -> BuildRequest:
    """Seed the shipped Hermes adapter and an explicit fake provider binding."""

    definitions = tmp_path / "definitions"
    tool = definitions / "tools/hermes"
    starter = (
        Path(__file__).resolve().parents[3]
        / "src/houmao/project/assets/starter_agents/tools/hermes"
    )
    shutil.copytree(starter, tool)
    environment = tool / "auth/explicit/env/vars.env"
    environment.parent.mkdir(parents=True)
    environment.write_text(f"{HERMES_API_KEY_ENV}=synthetic-secret\n", encoding="utf-8")
    skill = definitions / "skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Example\n", encoding="utf-8")
    return BuildRequest(
        agent_def_dir=definitions,
        runtime_root=tmp_path / "runtime",
        tool="hermes",
        setup="default",
        auth="explicit",
        home_id="hermes-brain",
        skills=["example"],
        role_prompt_override="Literal managed role.\n",
        direct_tool_params={"base_url": "https://fixture.example/v1"},
        direct_model_config=ModelConfig(name="fixture-model"),
    )


def test_hermes_path_lookup_requires_only_an_executable(tmp_path: Path) -> None:
    """Allow a command whose own execution would fail for any invocation."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "hermes"
    executable.write_text("#!/bin/sh\nexit 55\n", encoding="utf-8")
    executable.chmod(0o700)
    assert resolve_hermes_executable(
        environment={"PATH": "bin"}, working_directory=tmp_path
    ) == str(executable)
    with pytest.raises(ValueError, match="Hermes was not found on PATH in execution context"):
        resolve_hermes_executable(environment={"PATH": "elsewhere"}, working_directory=tmp_path)


def test_hermes_build_projects_native_route_roles_and_skills(build_request: BuildRequest) -> None:
    """Write the private route and copy skills while keeping credentials external."""

    result = build_brain_home(build_request)
    config_path = result.home_path / "config.yaml"
    role_path = result.home_path / "SOUL.md"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["model"] == {
        "default": "fixture-model",
        "provider": "custom",
        "base_url": "https://fixture.example/v1",
        "api_mode": "chat_completions",
        "key_env": HERMES_API_KEY_ENV,
    }
    assert config["fallback_providers"] == []
    assert config["agent"]["disabled_toolsets"] == ["browser", "computer_use"]
    assert "reasoning_effort" not in config["agent"]
    selection = result.manifest["runtime"]["launch_contract"]["model_selection"]
    assert selection["native_projection"]["reasoning"] is None
    assert config["security"]["allow_lazy_installs"] is False
    assert config["approvals"] == {
        "mode": "off",
        "single_query_mode": "approve",
        "unattended_mode": "approve",
    }
    assert role_path.read_text(encoding="utf-8") == build_request.role_prompt_override
    assert stat.S_IMODE(result.home_path.stat().st_mode) == 0o700
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(role_path.stat().st_mode) == 0o600
    for name in ("example", "houmao-shared-routines"):
        projected_skill = result.home_path / "skills" / name
        assert (projected_skill / "SKILL.md").is_file()
        assert not projected_skill.is_symlink()
    for path in (config_path, result.manifest_path, result.launch_helper_path):
        assert "synthetic-secret" not in path.read_text(encoding="utf-8")
    assert not (result.home_path / ".env").exists()
    assert HERMES_API_KEY_ENV in result.manifest["credentials"]["env_contract"]["selected_env_vars"]


def test_hermes_approval_projection_restores_authored_baseline(tmp_path: Path) -> None:
    """A repeated unattended projection must leave the prior as-is values recoverable."""

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "approvals:\n  mode: smart\n  timeout: 10\nsecurity:\n  allow_lazy_installs: false\n"
    )
    project_hermes_approval_policy(tmp_path, "unattended")
    project_hermes_approval_policy(tmp_path, "unattended")
    text = config_path.read_text()
    assert "mode: 'off'" in text
    assert yaml.safe_load(text)["approvals"] == {
        "mode": "off",
        "single_query_mode": "approve",
        "unattended_mode": "approve",
        "timeout": 10,
    }
    project_hermes_approval_policy(tmp_path, "as_is")
    assert yaml.safe_load(config_path.read_text()) == {
        "approvals": {
            "mode": "smart",
            "single_query_mode": "deny",
            "unattended_mode": "deny",
            "timeout": 10,
        },
        "security": {"allow_lazy_installs": False},
    }


def test_hermes_launch_helper_applies_resolved_approval_policy(
    build_request: BuildRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The generated helper's CLI path projects policy before handing off to Hermes."""

    brain = build_brain_home(replace(build_request, operator_prompt_mode="as_is"))
    executable = tmp_path / "hermes"
    executable.write_text("#!/bin/sh\nexit 1\n")
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))
    env_file = brain.home_path / "test-selected.env"
    env_file.write_text(f"{HERMES_API_KEY_ENV}=synthetic-secret\n")

    def exec_native(command: str, args: list[str], env: dict[str, str]) -> None:
        assert command == str(executable)
        assert args == [str(executable), "--tui"]
        assert env["HERMES_NONINTERACTIVE"] == "1"
        assert (
            yaml.safe_load((brain.home_path / "config.yaml").read_text())["approvals"]["mode"]
            == "off"
        )
        raise RuntimeError("native exec reached")

    monkeypatch.setattr(launch_policy_cli.os, "execve", exec_native)
    with pytest.raises(RuntimeError, match="native exec reached"):
        launch_policy_cli.main(
            [
                "--tool",
                "hermes",
                "--backend",
                "raw_launch",
                "--executable",
                "hermes",
                "--working-directory",
                str(tmp_path),
                "--home-path",
                str(brain.home_path),
                "--requested-operator-prompt-mode",
                "unattended",
                "--hermes-credential-env-file",
                str(env_file),
                "--",
                "--tui",
            ]
        )


@pytest.mark.parametrize(
    ("level", "native_default", "expected_effort"),
    (
        (None, "xhigh", "xhigh"),
        (5, None, "xhigh"),
        (0, None, "none"),
        (5, "low", "xhigh"),
        (12, None, "max"),
    ),
)
def test_hermes_build_projects_selected_reasoning(
    build_request: BuildRequest,
    level: int | None,
    native_default: str | None,
    expected_effort: str,
) -> None:
    """Write the winning effort and record its source and native YAML target."""

    tool_params = dict(build_request.direct_tool_params or {})
    if native_default is not None:
        tool_params["reasoning_effort"] = native_default
    profile = ModelConfig(reasoning=ModelReasoningConfig(level)) if level is not None else None
    result = build_brain_home(
        replace(build_request, direct_tool_params=tool_params, launch_profile_model_config=profile)
    )

    config = yaml.safe_load((result.home_path / "config.yaml").read_text(encoding="utf-8"))
    assert config["agent"]["reasoning_effort"] == expected_effort
    assert config["agent"]["disabled_toolsets"] == ["browser", "computer_use"]
    selection = result.manifest["runtime"]["launch_contract"]["model_selection"]
    projection = selection["native_projection"]["reasoning"]
    assert projection["source"] == ("tool_params" if level is None else "launch_profile")
    assert projection["native_value"] == expected_effort
    assert projection["projection_target"] == {
        "surface": "yaml",
        "path": "config.yaml",
        "key_path": ["agent", "reasoning_effort"],
    }
    if level is not None:
        assert projection["requested_level"] == level
        assert projection["effective_level"] == min(level, 6)
        assert projection["saturated"] is (level > 6)


@pytest.mark.parametrize("invalid_effort", ("ultra", "XHIGH", True))
def test_hermes_build_rejects_invalid_reasoning_default_before_preparing_home(
    build_request: BuildRequest, invalid_effort: object
) -> None:
    """Validate every native input even when the numeric preset takes precedence."""

    request = replace(
        build_request,
        launch_profile_tool_params={"reasoning_effort": invalid_effort},
        direct_model_config=ModelConfig(name="fixture-model", reasoning=ModelReasoningConfig(5)),
    )
    with pytest.raises(
        BuildError, match=r"reasoning_effort.*none, minimal, low, medium, high, xhigh, max"
    ):
        build_brain_home(request)
    assert build_request.runtime_root is not None
    assert not (build_request.runtime_root / "homes").exists()


def test_hermes_path_only_command_reaches_native_startup(
    build_request: BuildRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Use the workspace's executable and surface failures from the native process."""

    workspace = tmp_path / "workspace"
    bin_dir = workspace / "bin"
    bin_dir.mkdir(parents=True)
    executable = bin_dir / "hermes"
    calls = tmp_path / "native-calls"
    executable.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> {shlex.quote(str(calls))}\n"
        "[ \"$*\" = 'gateway run --external-supervisor' ] || exit 78\n"
        '[ "$HERMES_MANAGED_API_KEY" = synthetic-secret ] || exit 79\n'
        '[ -z "$OPENAI_API_KEY$HERMES_CONFIG_PATH" ] || exit 80\n'
        '[ -n "$HOUMAO_AGENT_ID" ] || exit 81\n'
        'printf \'%s\\n\' "$PWD" "$HERMES_HOME" > "$HERMES_HOME/native-start"\n'
        "printf 'Synthetic native startup diagnostic\\n' >&2\n"
        "exit 37\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    operator_home = tmp_path / "operator-hermes"
    operator_home.mkdir()
    operator_config = operator_home / "config.yaml"
    operator_config.write_text("operator state remains private", encoding="utf-8")
    monkeypatch.setenv("PATH", "bin")
    monkeypatch.setenv("HERMES_HOME", str(operator_home))
    monkeypatch.setenv("HERMES_CONFIG_PATH", str(operator_config))
    monkeypatch.setenv(HERMES_API_KEY_ENV, "synthetic-ambient-hermes-key")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-ambient-provider-key")
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)

    brain = build_brain_home(build_request)
    runtime = tmp_path / "sessions"
    startup = {
        "agent_def_dir": build_request.agent_def_dir,
        "brain_manifest_path": brain.manifest_path,
        "role_name": None,
        "runtime_root": runtime,
        "project_overlay_dir": tmp_path / "overlay",
        "mode": "headless",
        "working_directory": workspace,
        "agent_name": "hermes-fixture",
        "tmux_session_name": "hermes-fixture",
        "resolved_tmux_server": ResolvedTmuxServer(str(tmp_path / "private.sock"), False),
    }
    for name in ("HERMES_CONFIG_PATH", "OPENAI_BASE_URL"):
        with pytest.raises(SessionManifestError, match="controls are Houmao-owned"):
            start_runtime_session(**startup, launch_env_overrides={name: "unqualified"})
        assert not calls.exists()
        assert not runtime.exists()
    with pytest.raises(BackendExecutionError, match=r"Hermes daemon exited with status 37") as exc:
        start_runtime_session(**startup)
    assert calls.read_text(encoding="utf-8").splitlines() == ["gateway run --external-supervisor"]
    assert (brain.home_path / "native-start").read_text(encoding="utf-8").splitlines() == [
        str(workspace),
        str(brain.home_path),
    ]
    [log] = runtime.rglob("hermes-daemon.log")
    assert log.read_text(encoding="utf-8") == "Synthetic native startup diagnostic\n"
    assert str(log) in str(exc.value)
    assert stat.S_IMODE(log.stat().st_mode) == 0o600
    assert operator_config.read_text(encoding="utf-8") == "operator state remains private"
    assert list(operator_home.iterdir()) == [operator_config]


def test_hermes_build_refuses_ambient_auth_and_control_settings(
    build_request: BuildRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Require the selected bundle and reject managed route overrides before allocation."""

    auth_path = build_request.agent_def_dir / "tools/hermes/auth/explicit/env/vars.env"
    auth_path.write_text("OPENAI_API_KEY=wrong-binding\n", encoding="utf-8")
    monkeypatch.setenv(HERMES_API_KEY_ENV, "ambient-key")
    with pytest.raises(BuildError, match="selected Hermes credential bundle"):
        build_brain_home(build_request)
    auth_path.write_text(f"{HERMES_API_KEY_ENV}=synthetic-secret\n", encoding="utf-8")
    with pytest.raises(BuildError, match="explicit model.name"):
        build_brain_home(replace(build_request, direct_model_config=None))
    with pytest.raises(BuildError, match="credentials supplied separately"):
        build_brain_home(
            replace(
                build_request, direct_tool_params={"base_url": "https://key@fixture.example/v1"}
            )
        )
    with pytest.raises(BuildError, match="controls are Houmao-owned"):
        build_brain_home(
            replace(build_request, persistent_env_records={"HERMES_CONFIG_PATH": "/elsewhere"})
        )
    assert build_request.runtime_root is not None
    assert not (build_request.runtime_root / "homes").exists()


def test_hermes_runtime_environment_retains_the_managed_bindings(tmp_path: Path) -> None:
    """Separate managed credentials, runtime control, and user-wide environment."""

    source = {
        HERMES_API_KEY_ENV: "selected",
        "HERMES_CONFIG_PATH": "/elsewhere",
        "OPENAI_API_KEY": "alternate-key",
        "PATH": "/path",
        "HOUMAO_AGENT_ID": "agent",
        "HOUMAO_AGENT_GATEWAY_HOST": "127.0.0.1",
        "HOUMAO_AGENT_GATEWAY_PORT": "19420",
    }
    assert hermes_runtime_environment(tmp_path, source) == {
        HERMES_API_KEY_ENV: "selected",
        HERMES_HOME_ENV: str(tmp_path),
        HERMES_LOCK_DIR_ENV: str(tmp_path / ".houmao-gateway-locks"),
        "PATH": "/path",
        "HOUMAO_AGENT_ID": "agent",
        "HOUMAO_AGENT_GATEWAY_HOST": "127.0.0.1",
        "HOUMAO_AGENT_GATEWAY_PORT": "19420",
    }


@pytest.mark.parametrize("backend", ["hermes_tui", "hermes_service", "hermes_headless"])
def test_hermes_runtime_rejects_prompt_model_override(tmp_path: Path, backend: BackendKind) -> None:
    """A per-turn model cannot advance through the selected Hermes backend."""

    backend_session = Mock()
    controller = RuntimeSessionController(
        launch_plan=LaunchPlan(
            backend=backend,
            tool="hermes",
            executable="hermes",
            args=[],
            working_directory=tmp_path,
            home_env_var=HERMES_HOME_ENV,
            home_path=tmp_path / "home",
            env={},
            env_var_names=[],
            role_injection=RoleInjectionPlan(
                "native_home_system_prompt", "fixture", "Fixture role"
            ),
            metadata={"tmux_socket_path": str(tmp_path / "private.sock")},
        ),
        role_name="fixture",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=tmp_path / "manifest.json",
        backend_session=backend_session,
    )
    with pytest.raises(SessionManifestError, match="launch-selected model"):
        controller.send_prompt("literal prompt", execution_model=ModelConfig(name="wrong-model"))
    assert backend_session.mock_calls == []
    assert not controller.manifest_path.exists()


@pytest.mark.parametrize(
    "controls",
    [
        {"cao_parsing_mode": "shadow_only"},
        {
            "gateway_tui_tracking_timing_overrides": GatewayTuiTrackingTimingOverridesV1(
                watch_poll_interval_seconds=0.2
            )
        },
    ],
)
def test_hermes_tui_launch_refuses_terminal_parser_controls(
    build_request: BuildRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    controls: dict[str, object],
) -> None:
    """Reject parser and timing requests at the runtime launch boundary."""

    executable = tmp_path / "hermes"
    executable.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))
    brain = build_brain_home(build_request)
    backend_start = Mock()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session", backend_start
    )
    with pytest.raises(SessionManifestError, match="Hermes TUI uses native control"):
        start_runtime_session(
            agent_def_dir=build_request.agent_def_dir,
            brain_manifest_path=brain.manifest_path,
            role_name=None,
            runtime_root=tmp_path / "sessions",
            mode="tui",
            working_directory=tmp_path,
            gateway_auto_attach=True,
            resolved_tmux_server=ResolvedTmuxServer(str(tmp_path / "private.sock"), False),
            **controls,
        )
    backend_start.assert_not_called()


def test_hermes_role_projection_replaces_an_existing_link(tmp_path: Path) -> None:
    """Keep an existing role target intact when replacing the managed role."""

    prior = tmp_path / "outside"
    prior.write_text("outside", encoding="utf-8")
    role = tmp_path / "SOUL.md"
    role.symlink_to(prior)
    write_hermes_role(tmp_path, "managed")
    assert prior.read_text(encoding="utf-8") == "outside"
    assert role.read_text(encoding="utf-8") == "managed"
    assert not role.is_symlink()
