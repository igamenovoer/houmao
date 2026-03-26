from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
)
from houmao.agents.realm_controller.errors import LaunchPolicyResolutionError
from houmao.server.pair_client import PairAuthorityConnectionError, PairAuthorityHealthProbe
from houmao.server.models import (
    HoumaoCurrentInstance,
    HoumaoHealthResponse,
    HoumaoManagedAgentIdentity,
)
from houmao.srv_ctrl.commands.main import cli
from houmao.srv_ctrl.server_startup import (
    HoumaoDetachedServerStartResult,
    HoumaoServerStartLogPaths,
)


class _FakeSession:
    def __init__(self, session_id: str) -> None:
        self.id = session_id

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        del mode
        return {"id": self.id}


class _FakePairClient:
    def __init__(self) -> None:
        self.m_delete_session_calls: list[str] = []

    def list_sessions(self) -> list[_FakeSession]:
        return [_FakeSession("sess-a"), _FakeSession("sess-b")]

    def delete_session(self, session_name: str) -> object:
        self.m_delete_session_calls.append(session_name)
        return SimpleNamespace(success=True)


def test_top_level_command_inventory_exposes_new_native_surface() -> None:
    assert set(cli.commands.keys()) == {"admin", "agents", "brains", "server"}


def test_bare_invocation_prints_help() -> None:
    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0
    assert "Usage: houmao-mgr" in result.output
    assert "server" in result.output
    assert "agents" in result.output
    assert "cao" not in result.output
    assert "\nTraceback" not in result.output


def test_agents_gateway_attach_help_mentions_foreground_mode() -> None:
    result = CliRunner().invoke(cli, ["agents", "gateway", "attach", "--help"])

    assert result.exit_code == 0
    assert "--foreground" in result.output
    assert "Window `0` remains the agent surface" in result.output
    assert "window index" in result.output


def test_agents_help_mentions_relaunch_and_omits_retired_cao_tree() -> None:
    result = CliRunner().invoke(cli, ["agents", "--help"])

    assert result.exit_code == 0
    assert "relaunch" in result.output
    assert "cao" not in result.output


def test_agents_gateway_attach_forwards_foreground_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: captured.setdefault("resolved_target", kwargs) or "target",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.attach_gateway",
        lambda target, *, foreground=False: (
            captured.update({"target": target, "foreground": foreground}) or {"status": "ok"}
        ),
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "gateway", "attach", "--agent-id", "agent-123", "--foreground"],
    )

    assert result.exit_code == 0, result.output
    assert captured["foreground"] is True
    assert captured["resolved_target"] == {
        "agent_id": "agent-123",
        "agent_name": None,
        "port": None,
    }
    assert json.loads(result.output) == {"status": "ok"}


def test_agents_gateway_attach_current_session_uses_manifest_first_pair_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    manifest_path.write_text("{}\n", encoding="utf-8")
    captured: dict[str, object] = {}
    identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-pair",
        transport="tui",
        tool="codex",
        session_name="pair-session",
        terminal_id="term-123",
        runtime_session_id=None,
        tmux_session_name="pair-session",
        tmux_window_name="agent",
        manifest_path=str(manifest_path),
        session_root=str(tmp_path.resolve()),
        agent_name="AGENTSYS-pair",
        agent_id="agent-123",
    )
    client = SimpleNamespace(
        attach_managed_agent_gateway=lambda agent_ref: {
            "status": "ok",
            "agent_ref": agent_ref,
        }
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._require_current_tmux_session_name",
        lambda: "pair-session",
    )

    def _read_tmux_env(*, session_name: str, variable_name: str) -> str | None:
        assert session_name == "pair-session"
        assert variable_name == AGENT_MANIFEST_PATH_ENV_VAR
        return str(manifest_path)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.read_tmux_session_environment_value",
        _read_tmux_env,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.load_session_manifest",
        lambda path: SimpleNamespace(path=Path(path), payload={"manifest": "payload"}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            backend="houmao_server_rest",
            tool="codex",
            tmux_session_name="pair-session",
            agent_name="AGENTSYS-pair",
            agent_id="agent-123",
            houmao_server=SimpleNamespace(
                api_base_url="http://127.0.0.1:9889",
                session_name="pair-session",
                terminal_id="term-123",
                parsing_mode="shadow_only",
                tmux_window_name="agent",
            ),
        ),
    )

    def _require_pair(*, base_url: str) -> object:
        captured["base_url"] = base_url
        return client

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.require_houmao_server_pair",
        _require_pair,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_identity",
        lambda resolved_client, *, agent_ref: identity,
    )

    result = CliRunner().invoke(cli, ["agents", "gateway", "attach"])

    assert result.exit_code == 0, result.output
    assert captured["base_url"] == "http://127.0.0.1:9889"
    assert json.loads(result.output) == {"status": "ok", "agent_ref": "pair-session"}


def test_agents_gateway_attach_current_session_falls_back_to_registry_agent_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    manifest_path.write_text("{}\n", encoding="utf-8")
    agent_def_dir = (tmp_path / "agent-def").resolve()
    agent_def_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._require_current_tmux_session_name",
        lambda: "headless-session",
    )

    def _read_tmux_env(*, session_name: str, variable_name: str) -> str | None:
        assert session_name == "headless-session"
        mapping = {
            AGENT_MANIFEST_PATH_ENV_VAR: None,
            AGENT_ID_ENV_VAR: "published-alpha",
            AGENT_DEF_DIR_ENV_VAR: None,
        }
        return mapping[variable_name]

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.read_tmux_session_environment_value",
        _read_tmux_env,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_live_agent_record_by_agent_id",
        lambda agent_id: SimpleNamespace(
            runtime=SimpleNamespace(
                manifest_path=str(manifest_path),
                agent_def_dir=str(agent_def_dir),
            )
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.load_session_manifest",
        lambda path: SimpleNamespace(path=Path(path), payload={"manifest": "payload"}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            backend="claude_headless",
            tool="claude",
            tmux_session_name="headless-session",
            agent_name="AGENTSYS-headless",
            agent_id="published-alpha",
        ),
    )

    def _attach_gateway(*, execution_mode_override: str | None = None) -> object:
        captured["execution_mode_override"] = execution_mode_override
        return SimpleNamespace(status="ok", detail="")

    controller = SimpleNamespace(
        attach_gateway=_attach_gateway,
        gateway_status=lambda: {"status": "local-attached"},
    )

    def _resume_runtime_session(*, agent_def_dir: Path, session_manifest_path: Path) -> object:
        captured["agent_def_dir"] = agent_def_dir
        captured["session_manifest_path"] = session_manifest_path
        return controller

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resume_runtime_session",
        _resume_runtime_session,
    )

    result = CliRunner().invoke(cli, ["agents", "gateway", "attach", "--foreground"])

    assert result.exit_code == 0, result.output
    assert captured["agent_def_dir"] == agent_def_dir
    assert captured["session_manifest_path"] == manifest_path
    assert captured["execution_mode_override"] == "tmux_auxiliary_window"
    assert json.loads(result.output) == {"status": "local-attached"}


def test_agents_relaunch_current_session_uses_manifest_first_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    agent_def_dir = (tmp_path / "agent-def").resolve()
    agent_def_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._require_current_tmux_session_name",
        lambda: "headless-session",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._resolve_current_session_manifest",
        lambda *, session_name: (
            captured.setdefault("session_name", session_name),
            SimpleNamespace(manifest_path=manifest_path, registry_record=None),
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._resolve_current_session_agent_def_dir",
        lambda *, session_name, registry_record: (
            captured.update(
                {"agent_def_dir_session_name": session_name, "registry_record": registry_record}
            )
            or agent_def_dir
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resume_runtime_session",
        lambda *, agent_def_dir, session_manifest_path: (
            captured.update(
                {
                    "agent_def_dir": agent_def_dir,
                    "session_manifest_path": session_manifest_path,
                }
            )
            or SimpleNamespace(
                agent_id="published-alpha",
                agent_identity="AGENTSYS-alpha",
                manifest_path=manifest_path,
                relaunch=lambda: SimpleNamespace(status="ok", detail="Runtime relaunched."),
            )
        ),
    )

    result = CliRunner().invoke(cli, ["agents", "relaunch"])

    assert result.exit_code == 0, result.output
    assert captured == {
        "session_name": "headless-session",
        "agent_def_dir_session_name": "headless-session",
        "registry_record": None,
        "agent_def_dir": agent_def_dir,
        "session_manifest_path": manifest_path,
    }
    assert json.loads(result.output) == {
        "success": True,
        "tracked_agent_id": "published-alpha",
        "detail": "Runtime relaunched.",
    }


def test_agents_relaunch_rejects_port_without_explicit_selector() -> None:
    result = CliRunner().invoke(cli, ["agents", "relaunch", "--port", "9889"])

    assert result.exit_code != 0
    assert (
        "`--port` is only supported with an explicit `--agent-id` or `--agent-name` relaunch target."
        in result.output
    )


def test_agents_relaunch_with_explicit_target_uses_managed_agent_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
        lambda **kwargs: (captured.setdefault("resolve_kwargs", kwargs), target)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.relaunch_managed_agent",
        lambda resolved_target: (
            captured.setdefault("target", resolved_target),
            {
                "success": True,
                "tracked_agent_id": "tracked-alpha",
                "detail": "Relaunched through managed authority.",
            },
        )[1],
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "relaunch", "--agent-id", "agent-123", "--port", "9889"],
    )

    assert result.exit_code == 0, result.output
    assert captured["resolve_kwargs"] == {
        "agent_id": "agent-123",
        "agent_name": None,
        "port": 9889,
    }
    assert captured["target"] is target
    assert json.loads(result.output) == {
        "success": True,
        "tracked_agent_id": "tracked-alpha",
        "detail": "Relaunched through managed authority.",
    }


def test_server_status_reports_no_server_running(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_unavailable(*, base_url: str) -> object:
        raise PairAuthorityConnectionError(
            base_url=base_url,
            cause=RuntimeError("connection refused"),
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.resolve_pair_authority_client",
        _raise_unavailable,
    )

    result = CliRunner().invoke(cli, ["server", "status"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {
        "api_base_url": "http://127.0.0.1:9889",
        "detail": "No supported Houmao pair authority is running.",
        "running": False,
    }


def test_server_start_defaults_to_detached_startup_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_start_detached(config: object) -> HoumaoDetachedServerStartResult:
        captured["config"] = config
        return HoumaoDetachedServerStartResult(
            success=True,
            running=True,
            api_base_url="http://127.0.0.1:9999",
            detail="Started houmao-server.",
            pid=123,
            server_root=str((tmp_path / "runtime").resolve()),
            reused_existing=False,
            log_paths=HoumaoServerStartLogPaths(
                stdout=str((tmp_path / "stdout.log").resolve()),
                stderr=str((tmp_path / "stderr.log").resolve()),
            ),
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.start_detached_server", _fake_start_detached
    )

    result = CliRunner().invoke(
        cli,
        [
            "server",
            "start",
            "--api-base-url",
            "http://127.0.0.1:9999",
            "--runtime-root",
            str((tmp_path / "runtime").resolve()),
            "--no-startup-child",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["running"] is True
    assert payload["mode"] == "background"
    assert payload["api_base_url"] == "http://127.0.0.1:9999"
    assert payload["pid"] == 123
    assert payload["reused_existing"] is False
    assert payload["log_paths"]["stdout"].endswith("stdout.log")
    assert captured["config"] is not None


def test_server_start_foreground_keeps_direct_run_server_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.start_detached_server",
        lambda config: (_ for _ in ()).throw(AssertionError("detached start should not run")),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.run_server",
        lambda **kwargs: run_calls.append(kwargs),
    )

    result = CliRunner().invoke(
        cli,
        [
            "server",
            "start",
            "--foreground",
            "--api-base-url",
            "http://127.0.0.1:9998",
            "--no-startup-child",
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.output == ""
    assert len(run_calls) == 1
    assert run_calls[0]["api_base_url"] == "http://127.0.0.1:9998"
    assert run_calls[0]["startup_child"] is False


def test_server_sessions_shutdown_all_uses_pair_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakePairClient()

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.require_houmao_server_pair",
        lambda *, base_url: client,
    )

    result = CliRunner().invoke(cli, ["server", "sessions", "shutdown", "--all"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert client.m_delete_session_calls == ["sess-a", "sess-b"]
    assert payload["results"] == [
        {"session": "sess-a", "success": True},
        {"session": "sess-b", "success": True},
    ]


def test_agents_launch_builds_and_starts_local_runtime_then_attaches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attach_calls: list[list[str]] = []
    captured: dict[str, object] = {}
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = SimpleNamespace(
        tool="codex",
        agent_def_dir=working_directory / "agents",
        role_name="gpu-kernel-coder",
        recipe=SimpleNamespace(
            tool="codex",
            skills=[],
            config_profile="default",
            credential_profile="default",
            launch_overrides=None,
            operator_prompt_mode="unattended",
            mailbox=None,
            default_agent_name="AGENTSYS-gpu",
        ),
        recipe_path=working_directory / "recipe.yaml",
    )
    controller = SimpleNamespace(
        manifest_path=working_directory / "runtime" / "manifest.json",
        agent_id="agent-1234",
        agent_identity="gpu",
        tmux_session_name="gpu-session",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (captured.setdefault("build_request", request), build_result)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (captured.setdefault("start_kwargs", kwargs), controller)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.subprocess.run",
        lambda args, **kwargs: (
            attach_calls.append(list(args)) or subprocess.CompletedProcess(args=args, returncode=0)
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--agent-name",
            "gpu",
            "--provider",
            "codex",
            "--session-name",
            "gpu-session",
            "--yolo",
        ],
    )

    assert result.exit_code == 0
    assert "Managed agent launch complete:" in result.output
    assert "agent_name=gpu" in result.output
    assert "agent_id=agent-1234" in result.output
    assert "tmux_session_name=gpu-session" in result.output
    assert f"manifest_path={controller.manifest_path}" in result.output
    assert captured["build_request"].operator_prompt_mode == "unattended"
    assert captured["build_request"].agent_name == "gpu"
    assert captured["build_request"].agent_id is None
    assert captured["start_kwargs"]["backend"] == "local_interactive"
    assert captured["start_kwargs"]["agent_name"] == "gpu"
    assert captured["start_kwargs"]["agent_id"] is None
    assert attach_calls == [["tmux", "attach-session", "-t", "gpu-session"]]


def test_agents_launch_headless_keeps_native_headless_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = SimpleNamespace(
        tool="claude",
        agent_def_dir=working_directory / "agents",
        role_name="researcher",
        recipe=SimpleNamespace(
            tool="claude",
            skills=[],
            config_profile="default",
            credential_profile="default",
            launch_overrides=None,
            operator_prompt_mode=None,
            mailbox=None,
            default_agent_name="AGENTSYS-claude",
        ),
        recipe_path=working_directory / "recipe.yaml",
    )
    controller = SimpleNamespace(
        manifest_path=working_directory / "runtime" / "manifest.json",
        agent_id="agent-claude",
        agent_identity="claude",
        tmux_session_name="claude-session",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (captured.setdefault("start_kwargs", kwargs), controller)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("tmux attach should not run")),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "researcher",
            "--agent-name",
            "claude",
            "--provider",
            "claude_code",
            "--headless",
            "--yolo",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["start_kwargs"]["backend"] == "claude_headless"


def test_agents_launch_interactive_reports_launch_policy_compatibility_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = SimpleNamespace(
        tool="claude",
        agent_def_dir=working_directory / "agents",
        role_name="researcher",
        recipe=SimpleNamespace(
            tool="claude",
            skills=[],
            config_profile="default",
            credential_profile="default",
            launch_overrides=None,
            operator_prompt_mode="unattended",
            mailbox=None,
            default_agent_name="AGENTSYS-claude",
        ),
        recipe_path=working_directory / "recipe.yaml",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (_ for _ in ()).throw(
            LaunchPolicyResolutionError(
                requested_operator_prompt_mode="unattended",
                tool="claude",
                policy_backend="raw_launch",
                detected_version="2.1.83",
                detail=(
                    "No compatible unattended launch strategy exists for tool='claude', "
                    "backend='raw_launch', version='2.1.83', "
                    "requested_operator_prompt_mode='unattended'."
                ),
            )
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "researcher",
            "--agent-name",
            "claude",
            "--provider",
            "claude_code",
            "--yolo",
        ],
    )

    assert result.exit_code != 0
    assert "runtime backend `local_interactive`" in result.output
    assert "provider startup did not begin" in result.output
    assert "requested_operator_prompt_mode='unattended'" in result.output
    assert "policy_backend='raw_launch'" in result.output
    assert "detected_version='2.1.83'" in result.output


def test_agents_launch_headless_reports_launch_policy_compatibility_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = SimpleNamespace(
        tool="claude",
        agent_def_dir=working_directory / "agents",
        role_name="researcher",
        recipe=SimpleNamespace(
            tool="claude",
            skills=[],
            config_profile="default",
            credential_profile="default",
            launch_overrides=None,
            operator_prompt_mode="unattended",
            mailbox=None,
            default_agent_name="AGENTSYS-claude",
        ),
        recipe_path=working_directory / "recipe.yaml",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (_ for _ in ()).throw(
            LaunchPolicyResolutionError(
                requested_operator_prompt_mode="unattended",
                tool="claude",
                policy_backend="claude_headless",
                detected_version="2.1.83",
                detail=(
                    "No compatible unattended launch strategy exists for tool='claude', "
                    "backend='claude_headless', version='2.1.83', "
                    "requested_operator_prompt_mode='unattended'."
                ),
            )
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "researcher",
            "--agent-name",
            "claude",
            "--provider",
            "claude_code",
            "--headless",
            "--yolo",
        ],
    )

    assert result.exit_code != 0
    assert "runtime backend `claude_headless`" in result.output
    assert "provider startup did not begin" in result.output
    assert "policy_backend='claude_headless'" in result.output
    assert "detected_version='2.1.83'" in result.output


def test_agents_launch_rejects_unsupported_provider() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--agent-name",
            "gpu",
            "--provider",
            "kiro_cli",
            "--yolo",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid provider `kiro_cli`." in result.output


def test_server_status_reports_health_and_current_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    class _HealthyClient:
        def __init__(self, base_url: str) -> None:
            self.m_base_url = base_url

        def health_extended(self) -> HoumaoHealthResponse:
            return HoumaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def current_instance(self) -> HoumaoCurrentInstance:
            return HoumaoCurrentInstance(
                pid=123,
                api_base_url=self.m_base_url,
                server_root="/tmp/houmao-server",
            )

        def list_sessions(self) -> list[_FakeSession]:
            return [_FakeSession("sess-a")]

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.resolve_pair_authority_client",
        lambda *, base_url: SimpleNamespace(
            client=_HealthyClient(base_url),
            health=PairAuthorityHealthProbe(status="ok", houmao_service="houmao-server"),
        ),
    )

    result = CliRunner().invoke(cli, ["server", "status", "--port", "9999"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["running"] is True
    assert payload["api_base_url"] == "http://127.0.0.1:9999"
    assert payload["active_session_count"] == 1


def test_server_status_accepts_passive_pair_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    class _PassiveClient:
        def __init__(self, base_url: str) -> None:
            self.m_base_url = base_url

        def current_instance(self) -> HoumaoCurrentInstance:
            return HoumaoCurrentInstance(
                pid=456,
                api_base_url=self.m_base_url,
                server_root="/tmp/houmao-passive-server",
            )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.resolve_pair_authority_client",
        lambda *, base_url: SimpleNamespace(
            client=_PassiveClient(base_url),
            health=PairAuthorityHealthProbe(status="ok", houmao_service="houmao-passive-server"),
        ),
    )

    result = CliRunner().invoke(cli, ["server", "status", "--port", "9891"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["running"] is True
    assert payload["api_base_url"] == "http://127.0.0.1:9891"
    assert payload["health"]["houmao_service"] == "houmao-passive-server"
    assert payload["active_session_count"] is None
    assert payload["active_sessions"] is None


def test_server_stop_accepts_passive_pair_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    class _PassiveClient:
        def shutdown_server(self) -> object:
            return SimpleNamespace(success=True)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.resolve_pair_authority_client",
        lambda *, base_url: SimpleNamespace(
            client=_PassiveClient(),
            health=PairAuthorityHealthProbe(status="ok", houmao_service="houmao-passive-server"),
        ),
    )

    result = CliRunner().invoke(cli, ["server", "stop", "--port", "9891"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {
        "api_base_url": "http://127.0.0.1:9891",
        "detail": "Shutdown request accepted.",
        "running": False,
        "success": True,
    }
