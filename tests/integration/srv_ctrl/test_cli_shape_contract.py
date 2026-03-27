from __future__ import annotations

import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import click
import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller.agent_identity import AGENT_MANIFEST_PATH_ENV_VAR
from houmao.agents.realm_controller.backends.tmux_runtime import TmuxPaneRecord
from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
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
from houmao.agents.realm_controller.registry_storage import resolve_live_agent_record
from houmao.server.tui.process import PaneProcessInspection
from houmao.server.models import (
    HoumaoRecentTransition,
    HoumaoStabilityMetadata,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedDiagnostics,
    HoumaoTrackedLastTurn,
    HoumaoTrackedSessionIdentity,
    HoumaoTrackedSurface,
    HoumaoTrackedTurn,
)
from houmao.server.client import HoumaoServerClient
from houmao.srv_ctrl.commands.agents import core as agents_core
from houmao.srv_ctrl.commands.main import cli


def _source_repo_root() -> Path:
    """Return the tracked repository root."""

    return Path(__file__).resolve().parents[3]


def _pick_unused_loopback_port() -> int:
    """Return one likely-free loopback port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _python_subprocess_env() -> dict[str, str]:
    """Return subprocess env with repo `src/` added to `PYTHONPATH`."""

    repo_root = _source_repo_root()
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{repo_root / 'src'}:{env.get('PYTHONPATH', '')}"
    return env


def _write(path: Path, text: str) -> None:
    """Write one UTF-8 text file, creating parents first."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_role(agent_def_dir: Path) -> None:
    """Create one minimal role package."""

    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")


def _seed_brain_manifest(tmp_path: Path) -> Path:
    """Create one minimal launchable brain manifest."""

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
    return manifest_path.resolve()


class _FakeHeadlessSession:
    """Small fake tmux-backed headless backend for runtime integration tests."""

    m_relaunch_calls: list[str] = []

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

    @property
    def state(self) -> HeadlessSessionState:
        """Return persisted fake backend state."""

        return self.m_state

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        """Update the fake launch plan."""

        self.m_launch_plan = launch_plan

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        """Accept stop cleanup configuration without side effects."""

        del force_cleanup

    def send_prompt(self, prompt: str) -> list[object]:
        """Advance one fake turn."""

        del prompt
        self.m_state = replace(self.m_state, turn_index=self.m_state.turn_index + 1)
        return []

    def interrupt(self) -> SessionControlResult:
        """Return one successful interrupt result."""

        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
        """Return one successful terminate result."""

        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def close(self) -> None:
        """Close the fake backend."""

        return

    def relaunch(self) -> SessionControlResult:
        """Record one relaunch through the shared runtime primitive."""

        type(self).m_relaunch_calls.append(self.m_state.tmux_session_name or "unknown")
        return SessionControlResult(status="ok", action="relaunch", detail="relaunched")


class _FakeLocalInteractiveSession(_FakeHeadlessSession):
    """Small fake tmux-backed local interactive backend."""

    def __init__(self, *, tmux_session_name: str, launch_plan: LaunchPlan) -> None:
        super().__init__(tmux_session_name=tmux_session_name, launch_plan=launch_plan)
        self.backend = "local_interactive"
        self.m_state = HeadlessSessionState(
            session_id=None,
            turn_index=0,
            role_bootstrap_applied=True,
            working_directory=str(launch_plan.working_directory),
            tmux_session_name=tmux_session_name,
        )


def _sample_houmao_server_plan(tmp_path: Path) -> LaunchPlan:
    """Return one minimal `houmao_server_rest` launch plan for manifest-only tests."""

    return LaunchPlan(
        backend="houmao_server_rest",
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
            role_name="r",
            prompt="role prompt",
        ),
        metadata={},
    )


class _FakeSingleSessionTrackingRuntime:
    """Small fake tracker used by local interactive CLI integration tests."""

    def __init__(self, *, identity: HoumaoTrackedSessionIdentity, **_: object) -> None:
        self.m_identity = identity

    def refresh_once(self) -> HoumaoTerminalStateResponse:
        """Return one ready tracked-state sample."""

        return HoumaoTerminalStateResponse(
            terminal_id="abcd1234",
            tracked_session=self.m_identity,
            diagnostics=HoumaoTrackedDiagnostics(
                availability="available",
                transport_state="tmux_up",
                process_state="tui_up",
                parse_status="parsed",
            ),
            probe_snapshot=None,
            parsed_surface=None,
            surface=HoumaoTrackedSurface(
                accepting_input="yes",
                editing_input="no",
                ready_posture="yes",
            ),
            turn=HoumaoTrackedTurn(phase="ready"),
            last_turn=HoumaoTrackedLastTurn(
                result="none",
                source="none",
                updated_at_utc="2026-01-01T00:00:00+00:00",
            ),
            stability=HoumaoStabilityMetadata(
                signature="ready",
                stable=True,
                stable_for_seconds=2.0,
                stable_since_utc="2026-01-01T00:00:00+00:00",
            ),
            recent_transitions=[],
        )

    def history(self, *, limit: int) -> HoumaoTerminalHistoryResponse:
        """Return one bounded tracked history payload."""

        del limit
        return HoumaoTerminalHistoryResponse(
            terminal_id="abcd1234",
            tracked_session_id=self.m_identity.tracked_session_id,
            entries=[
                HoumaoRecentTransition(
                    recorded_at_utc="2026-01-01T00:00:00+00:00",
                    summary="ready",
                    diagnostics_availability="available",
                    turn_phase="ready",
                    last_turn_result="none",
                    last_turn_source="none",
                    transport_state="tmux_up",
                    process_state="tui_up",
                    parse_status="parsed",
                )
            ],
        )


def _install_fake_tmux_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch runtime backend creation to use fake tmux-backed backends."""

    tmux_envs: dict[str, dict[str, str]] = {}

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: (
            _FakeLocalInteractiveSession
            if kwargs["launch_plan"].backend == "local_interactive"
            else _FakeHeadlessSession
        )(
            tmux_session_name=str(
                kwargs.get("agent_identity")
                or kwargs["resume_state"].backend_state["tmux_session_name"]
            ),
            launch_plan=kwargs["launch_plan"],
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.has_tmux_session_shared",
        lambda *, session_name: SimpleNamespace(returncode=0 if session_name else 1),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda *, session_name, env_vars: tmux_envs.setdefault(session_name, {}).update(env_vars),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.unset_tmux_session_environment_shared",
        lambda *, session_name, variable_names: [
            tmux_envs.setdefault(session_name, {}).pop(name, None) for name in variable_names
        ],
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: tmux_envs.get(session_name, {}).get(variable_name),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.SingleSessionTrackingRuntime",
        _FakeSingleSessionTrackingRuntime,
    )


def _run_houmao_mgr_command(*args: str) -> subprocess.CompletedProcess[str]:
    """Run one `houmao-mgr` subprocess through the package module entrypoint."""

    repo_root = _source_repo_root()
    return subprocess.run(
        [sys.executable, "-m", "houmao.srv_ctrl", *args],
        cwd=repo_root,
        env=_python_subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def _wait_for_server_ready(
    *,
    api_base_url: str,
    timeout_seconds: float = 10.0,
) -> dict[str, object]:
    """Wait until the server health and current-instance routes respond."""

    client = HoumaoServerClient(api_base_url, timeout_seconds=0.5)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            health = client.health_extended()
            current_instance = client.current_instance().model_dump(mode="json")
        except Exception:
            time.sleep(0.1)
            continue
        if health.houmao_service == "houmao-server":
            return current_instance
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for houmao-server health at {api_base_url}.")


def _wait_for_server_stop(*, api_base_url: str, timeout_seconds: float = 10.0) -> None:
    """Wait until the target server no longer responds."""

    client = HoumaoServerClient(api_base_url, timeout_seconds=0.5)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            client.health_extended()
        except Exception:
            return
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for houmao-server shutdown at {api_base_url}.")


def _run_houmao_mgr_server_start(
    *,
    api_base_url: str,
    runtime_root: Path,
) -> subprocess.CompletedProcess[str]:
    """Run `houmao-mgr server start` and capture its detached-start result."""

    return _run_houmao_mgr_command(
        "server",
        "start",
        "--api-base-url",
        api_base_url,
        "--runtime-root",
        str(runtime_root),
        "--no-startup-child",
    )


class _BlockingHealthHandler(BaseHTTPRequestHandler):
    """Small HTTP server that occupies the requested port without Houmao routes."""

    def do_GET(self) -> None:  # noqa: N802
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"not found")

    def log_message(self, format: str, *args: object) -> None:
        del format, args
        return


def test_houmao_mgr_agents_launch_supports_registry_first_local_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """`agents launch` should publish registry state and later resolve local control from it."""

    agent_def_dir = tmp_path / "agent-def"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    _install_fake_tmux_runtime(monkeypatch)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root.resolve()))
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            tool="claude",
            agent_def_dir=agent_def_dir.resolve(),
            role_name="r",
            recipe=SimpleNamespace(
                tool="claude",
                skills=[],
                config_profile="default",
                credential_profile="default",
                launch_overrides=None,
                operator_prompt_mode=None,
                mailbox=None,
                default_agent_name="gpu",
            ),
            recipe_path=(tmp_path / "recipe.yaml").resolve(),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: SimpleNamespace(manifest_path=brain_manifest_path),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.tmux_session_exists",
        lambda *, session_name: session_name.startswith("gpu-"),
    )

    runner = CliRunner()

    launch_result = runner.invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu",
            "--agent-name",
            "gpu",
            "--provider",
            "claude_code",
            "--headless",
            "--yolo",
        ],
    )

    assert launch_result.exit_code == 0, launch_result.output
    assert "Managed agent launch complete:" in launch_result.output
    assert resolve_live_agent_record("gpu") is not None

    list_result = runner.invoke(cli, ["agents", "list"])
    assert list_result.exit_code == 0, list_result.output
    list_payload = json.loads(list_result.output)
    assert [item["agent_name"] for item in list_payload["agents"]] == ["gpu"]

    state_result = runner.invoke(cli, ["agents", "state", "--agent-name", "gpu"])
    assert state_result.exit_code == 0, state_result.output
    state_payload = json.loads(state_result.output)
    assert state_payload["identity"]["transport"] == "headless"
    assert state_payload["identity"]["agent_name"] == "gpu"
    assert state_payload["availability"] == "available"

    stop_result = runner.invoke(cli, ["agents", "stop", "--agent-name", "gpu"])
    assert stop_result.exit_code == 0, stop_result.output
    stop_payload = json.loads(stop_result.output)
    assert stop_payload["success"] is True
    assert resolve_live_agent_record("gpu") is None


def test_houmao_mgr_agents_launch_supports_registry_first_local_interactive_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Default `agents launch` should publish and resolve local interactive TUI control."""

    agent_def_dir = tmp_path / "agent-def"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    _install_fake_tmux_runtime(monkeypatch)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root.resolve()))
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            tool="claude",
            agent_def_dir=agent_def_dir.resolve(),
            role_name="r",
            recipe=SimpleNamespace(
                tool="claude",
                skills=[],
                config_profile="default",
                credential_profile="default",
                launch_overrides=None,
                operator_prompt_mode=None,
                mailbox=None,
                default_agent_name="gpu",
            ),
            recipe_path=(tmp_path / "recipe.yaml").resolve(),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: SimpleNamespace(manifest_path=brain_manifest_path),
    )

    runner = CliRunner()

    launch_result = runner.invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu",
            "--agent-name",
            "gpu",
            "--provider",
            "claude_code",
            "--yolo",
        ],
    )

    assert launch_result.exit_code == 0, launch_result.output
    assert "Managed agent launch complete:" in launch_result.output
    assert "terminal_handoff=skipped_non_interactive" in launch_result.output
    assert "attach_command=tmux attach-session -t AGENTSYS-gpu-" in launch_result.output
    record = resolve_live_agent_record("gpu")
    assert record is not None
    assert record.identity.backend == "local_interactive"

    state_result = runner.invoke(cli, ["agents", "state", "--agent-name", "gpu"])
    assert state_result.exit_code == 0, state_result.output
    state_payload = json.loads(state_result.output)
    assert state_payload["identity"]["transport"] == "tui"
    assert state_payload["identity"]["terminal_id"] == "abcd1234"
    assert state_payload["availability"] == "available"

    stop_result = runner.invoke(cli, ["agents", "stop", "--agent-name", "gpu"])
    assert stop_result.exit_code == 0, stop_result.output
    stop_payload = json.loads(stop_result.output)
    assert stop_payload["success"] is True
    assert resolve_live_agent_record("gpu") is None


def test_houmao_mgr_agents_relaunch_supports_registry_first_local_headless_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """`agents relaunch` should reuse registry-first local headless authority."""

    agent_def_dir = tmp_path / "agent-def"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    _install_fake_tmux_runtime(monkeypatch)
    _FakeHeadlessSession.m_relaunch_calls = []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root.resolve()))
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            tool="claude",
            agent_def_dir=agent_def_dir.resolve(),
            role_name="r",
            recipe=SimpleNamespace(
                tool="claude",
                skills=[],
                config_profile="default",
                credential_profile="default",
                launch_overrides=None,
                operator_prompt_mode=None,
                mailbox=None,
                default_agent_name="gpu",
            ),
            recipe_path=(tmp_path / "recipe.yaml").resolve(),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: SimpleNamespace(manifest_path=brain_manifest_path),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.tmux_session_exists",
        lambda *, session_name: session_name.startswith("gpu-"),
    )

    runner = CliRunner()
    launch_result = runner.invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu",
            "--agent-name",
            "gpu",
            "--provider",
            "claude_code",
            "--headless",
            "--yolo",
        ],
    )
    assert launch_result.exit_code == 0, launch_result.output

    relaunch_result = runner.invoke(cli, ["agents", "relaunch", "--agent-name", "gpu"])

    assert relaunch_result.exit_code == 0, relaunch_result.output
    relaunch_payload = json.loads(relaunch_result.output)
    assert relaunch_payload["success"] is True
    assert relaunch_payload["detail"] == "relaunched"
    assert len(_FakeHeadlessSession.m_relaunch_calls) == 1


def test_houmao_mgr_agents_mailbox_register_updates_local_headless_registry_and_mail_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "agent-def"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    _install_fake_tmux_runtime(monkeypatch)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root.resolve()))
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            tool="claude",
            agent_def_dir=agent_def_dir.resolve(),
            role_name="r",
            recipe=SimpleNamespace(
                tool="claude",
                skills=[],
                config_profile="default",
                credential_profile="default",
                launch_overrides=None,
                operator_prompt_mode=None,
                mailbox=None,
                default_agent_name="gpu",
            ),
            recipe_path=(tmp_path / "recipe.yaml").resolve(),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: SimpleNamespace(manifest_path=brain_manifest_path),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.tmux_session_exists",
        lambda *, session_name: session_name.startswith("gpu-"),
    )

    runner = CliRunner()
    launch_result = runner.invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu",
            "--agent-name",
            "gpu",
            "--provider",
            "claude_code",
            "--headless",
            "--yolo",
        ],
    )
    assert launch_result.exit_code == 0, launch_result.output

    mailbox_root = (tmp_path / "shared-mail").resolve()
    register_result = runner.invoke(
        cli,
        [
            "agents",
            "mailbox",
            "register",
            "--agent-name",
            "gpu",
            "--mailbox-root",
            str(mailbox_root),
        ],
    )
    assert register_result.exit_code == 0, register_result.output
    register_payload = json.loads(register_result.output)
    assert register_payload["activation_state"] == "active"
    assert register_payload["address"] == "AGENTSYS-gpu@agents.localhost"
    assert register_payload["mailbox_root"] == str(mailbox_root)

    status_result = runner.invoke(cli, ["agents", "mailbox", "status", "--agent-name", "gpu"])
    assert status_result.exit_code == 0, status_result.output
    status_payload = json.loads(status_result.output)
    assert status_payload["registered"] is True
    assert status_payload["activation_state"] == "active"
    assert status_payload["runtime_mailbox_enabled"] is True

    record = resolve_live_agent_record("gpu")
    assert record is not None
    assert record.mailbox is not None
    assert record.mailbox.address == "AGENTSYS-gpu@agents.localhost"

    mail_status_result = runner.invoke(cli, ["agents", "mail", "status", "--agent-name", "gpu"])
    assert mail_status_result.exit_code == 0, mail_status_result.output
    mail_status_payload = json.loads(mail_status_result.output)
    assert mail_status_payload["transport"] == "filesystem"

    unregister_result = runner.invoke(
        cli,
        ["agents", "mailbox", "unregister", "--agent-name", "gpu"],
    )
    assert unregister_result.exit_code == 0, unregister_result.output
    unregister_payload = json.loads(unregister_result.output)
    assert unregister_payload["activation_state"] == "active"

    record = resolve_live_agent_record("gpu")
    assert record is not None
    assert record.mailbox is None

    post_unregister_mail_status = runner.invoke(
        cli,
        ["agents", "mail", "status", "--agent-name", "gpu"],
    )
    assert post_unregister_mail_status.exit_code != 0
    assert "not mailbox-enabled" in post_unregister_mail_status.output


def test_houmao_mgr_agents_mailbox_register_refreshes_local_interactive_live_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "agent-def"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    _install_fake_tmux_runtime(monkeypatch)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTSYS_GLOBAL_REGISTRY_DIR", str(registry_root.resolve()))
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            tool="claude",
            agent_def_dir=agent_def_dir.resolve(),
            role_name="r",
            recipe=SimpleNamespace(
                tool="claude",
                skills=[],
                config_profile="default",
                credential_profile="default",
                launch_overrides=None,
                operator_prompt_mode=None,
                mailbox=None,
                default_agent_name="gpu",
            ),
            recipe_path=(tmp_path / "recipe.yaml").resolve(),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: SimpleNamespace(manifest_path=brain_manifest_path),
    )

    runner = CliRunner()
    launch_result = runner.invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu",
            "--agent-name",
            "gpu",
            "--provider",
            "claude_code",
            "--yolo",
        ],
    )
    assert launch_result.exit_code == 0, launch_result.output

    register_result = runner.invoke(
        cli,
        [
            "agents",
            "mailbox",
            "register",
            "--agent-name",
            "gpu",
            "--mailbox-root",
            str((tmp_path / "shared-mail").resolve()),
        ],
    )
    assert register_result.exit_code == 0, register_result.output
    register_payload = json.loads(register_result.output)
    assert register_payload["activation_state"] == "active"
    assert register_payload["relaunch_required"] is False

    mailbox_status_result = runner.invoke(
        cli,
        ["agents", "mailbox", "status", "--agent-name", "gpu"],
    )
    assert mailbox_status_result.exit_code == 0, mailbox_status_result.output
    mailbox_status_payload = json.loads(mailbox_status_result.output)
    assert mailbox_status_payload["activation_state"] == "active"
    assert mailbox_status_payload["runtime_mailbox_enabled"] is True

    mail_status_result = runner.invoke(cli, ["agents", "mail", "status", "--agent-name", "gpu"])
    assert mail_status_result.exit_code == 0, mail_status_result.output
    mail_status_payload = json.loads(mail_status_result.output)
    assert mail_status_payload["transport"] == "filesystem"


def test_houmao_mgr_agents_gateway_attach_supports_manifest_first_current_session_pair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Current-session pair attach should resolve from `manifest.json` without gateway pointers."""

    manifest_path = default_manifest_path(tmp_path, "houmao_server_rest", "pair-session-1")
    agent_def_dir = (tmp_path / "agent-def").resolve()
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_sample_houmao_server_plan(tmp_path),
            role_name="r",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="AGENTSYS-pair",
            agent_id="agent-pair-1",
            tmux_session_name="AGENTSYS-pair",
            session_id="pair-session-1",
            agent_def_dir=agent_def_dir,
            backend_state={
                "api_base_url": "http://127.0.0.1:9890",
                "session_name": "cao-gpu",
                "terminal_id": "term-123",
                "parsing_mode": "shadow_only",
                "tmux_window_name": "developer-1",
            },
        )
    )
    write_session_manifest(manifest_path, payload)

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="AGENTSYS-pair\n",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: (
            str(manifest_path)
            if session_name == "AGENTSYS-pair" and variable_name == AGENT_MANIFEST_PATH_ENV_VAR
            else None
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.require_houmao_server_pair",
        lambda base_url: (
            captured.setdefault("base_url", base_url),
            SimpleNamespace(
                attach_managed_agent_gateway=lambda agent_ref: (
                    captured.setdefault("agent_ref", agent_ref),
                    {
                        "gateway_health": "healthy",
                        "managed_agent_connectivity": "connected",
                        "managed_agent_recovery": "idle",
                        "request_admission": "open",
                        "active_execution": "idle",
                        "queue_depth": 0,
                        "gateway_host": "127.0.0.1",
                        "gateway_port": 43123,
                    },
                )[1]
            ),
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_identity",
        lambda client, agent_ref: SimpleNamespace(transport="tui", session_name=agent_ref),
    )

    result = CliRunner().invoke(cli, ["agents", "gateway", "attach"])

    assert result.exit_code == 0, result.output
    assert captured == {
        "base_url": "http://127.0.0.1:9890",
        "agent_ref": "cao-gpu",
    }
    assert json.loads(result.output) == {
        "gateway_health": "healthy",
        "managed_agent_connectivity": "connected",
        "managed_agent_recovery": "idle",
        "request_admission": "open",
        "active_execution": "idle",
        "queue_depth": 0,
        "gateway_host": "127.0.0.1",
        "gateway_port": 43123,
    }


def test_houmao_mgr_agents_help_retires_history_command() -> None:
    """`agents --help` should not advertise the retired history surface."""

    runner = CliRunner()

    help_result = runner.invoke(cli, ["agents", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "history" not in help_result.output

    history_result = runner.invoke(cli, ["agents", "history", "--help"])
    assert history_result.exit_code != 0
    assert "No such command 'history'" in history_result.output


def test_houmao_mgr_server_commands_cover_live_lifecycle_and_empty_sessions(
    tmp_path: Path,
) -> None:
    """`server` commands should manage one live `houmao-server` process end to end."""

    port = _pick_unused_loopback_port()
    api_base_url = f"http://127.0.0.1:{port}"
    runtime_root = (tmp_path / "runtime").resolve()
    start_result = _run_houmao_mgr_server_start(
        api_base_url=api_base_url, runtime_root=runtime_root
    )
    assert start_result.returncode == 0, start_result.stderr
    start_payload = json.loads(start_result.stdout)
    assert start_payload["success"] is True
    assert start_payload["running"] is True
    assert start_payload["mode"] == "background"
    assert start_payload["api_base_url"] == api_base_url
    assert start_payload["reused_existing"] is False
    assert start_payload["log_paths"]["stdout"].endswith("houmao-server.stdout.log")
    live_instance = _wait_for_server_ready(api_base_url=api_base_url)
    assert start_payload["current_instance"]["pid"] == live_instance["pid"]

    runner = CliRunner()

    status_result = runner.invoke(cli, ["server", "status", "--port", str(port)])
    assert status_result.exit_code == 0, status_result.output
    status_payload = json.loads(status_result.output)
    assert status_payload["running"] is True
    assert status_payload["api_base_url"] == api_base_url
    assert status_payload["active_session_count"] == 0

    reuse_result = _run_houmao_mgr_server_start(
        api_base_url=api_base_url, runtime_root=runtime_root
    )
    assert reuse_result.returncode == 0, reuse_result.stderr
    reuse_payload = json.loads(reuse_result.stdout)
    assert reuse_payload["success"] is True
    assert reuse_payload["reused_existing"] is True
    assert reuse_payload["pid"] == live_instance["pid"]

    sessions_result = runner.invoke(cli, ["server", "sessions", "list", "--port", str(port)])
    assert sessions_result.exit_code == 0, sessions_result.output
    assert json.loads(sessions_result.output) == {"sessions": []}

    shutdown_all_result = runner.invoke(
        cli,
        ["server", "sessions", "shutdown", "--all", "--port", str(port)],
    )
    assert shutdown_all_result.exit_code == 0, shutdown_all_result.output
    assert json.loads(shutdown_all_result.output) == {
        "detail": "No server sessions found to shutdown.",
        "success": True,
    }

    stop_result = runner.invoke(cli, ["server", "stop", "--port", str(port)])
    assert stop_result.exit_code == 0, stop_result.output
    stop_payload = json.loads(stop_result.output)
    assert stop_payload["success"] is True
    assert stop_payload["api_base_url"] == api_base_url
    _wait_for_server_stop(api_base_url=api_base_url)


def test_houmao_mgr_server_start_reports_unsuccessful_detached_start(
    tmp_path: Path,
) -> None:
    """Detached `server start` should report a failed start result when the child exits early."""

    port = _pick_unused_loopback_port()
    api_base_url = f"http://127.0.0.1:{port}"
    runtime_root = (tmp_path / "runtime").resolve()
    blocker = ThreadingHTTPServer(("127.0.0.1", port), _BlockingHealthHandler)
    worker = threading.Thread(target=blocker.serve_forever, daemon=True)
    worker.start()
    try:
        result = _run_houmao_mgr_server_start(api_base_url=api_base_url, runtime_root=runtime_root)
    finally:
        blocker.shutdown()
        blocker.server_close()
        worker.join(timeout=5)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert payload["running"] is False
    assert payload["mode"] == "background"
    assert payload["api_base_url"] == api_base_url
    assert payload["log_paths"]["stderr"].endswith("houmao-server.stderr.log")
    assert Path(payload["log_paths"]["stderr"]).exists()
    assert payload["exit_code"] is not None
    assert "exited before becoming healthy" in payload["detail"]


def _sample_join_pane(*, pane_pid: int = 321, window_name: str = "manual") -> TmuxPaneRecord:
    return TmuxPaneRecord(
        pane_id="%1",
        session_name="join-sess",
        window_id="@1",
        window_index="0",
        window_name=window_name,
        pane_index="0",
        pane_active=True,
        pane_dead=False,
        pane_pid=pane_pid,
    )


def test_houmao_mgr_agents_join_tui_auto_detects_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(agents_core, "_require_current_tmux_session_name", lambda: "join-sess")
    monkeypatch.setattr(agents_core, "list_tmux_panes", lambda session_name: (_sample_join_pane(),))
    monkeypatch.setattr(agents_core, "_detect_join_provider", lambda pane_pid: "codex")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        return subprocess.CompletedProcess(
            args=["tmux"],
            returncode=0,
            stdout="/tmp/project\n",
            stderr="",
        )

    monkeypatch.setattr(agents_core.subprocess, "run", fake_run)

    def fake_materialize_joined_launch(**kwargs: object) -> agents_core.JoinedSessionArtifacts:
        captured.update(kwargs)
        return agents_core.JoinedSessionArtifacts(
            manifest_path=Path("/tmp/runtime/manifest.json"),
            session_root=Path("/tmp/runtime"),
            agent_name="coder",
            agent_id="agent-1",
        )

    monkeypatch.setattr(agents_core, "materialize_joined_launch", fake_materialize_joined_launch)

    result = CliRunner().invoke(cli, ["agents", "join", "--agent-name", "coder"])

    assert result.exit_code == 0, result.output
    assert captured["provider"] == "codex"
    assert captured["headless"] is False
    assert captured["tmux_session_name"] == "join-sess"
    assert captured["tmux_window_name"] == "manual"
    assert captured["working_directory"] == Path("/tmp/project")
    assert "Managed agent join complete:" in result.output
    assert "provider=codex" in result.output


def test_houmao_mgr_agents_join_headless_last_resume(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(agents_core, "_require_current_tmux_session_name", lambda: "join-sess")
    monkeypatch.setattr(agents_core, "list_tmux_panes", lambda session_name: (_sample_join_pane(),))
    monkeypatch.setattr(agents_core, "_detect_join_provider", lambda pane_pid: None)
    monkeypatch.setattr(
        agents_core.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["tmux"], returncode=0, stdout="/tmp/project\n", stderr=""
        ),
    )

    def fake_materialize_joined_launch(**kwargs: object) -> agents_core.JoinedSessionArtifacts:
        captured.update(kwargs)
        return agents_core.JoinedSessionArtifacts(
            manifest_path=Path("/tmp/runtime/manifest.json"),
            session_root=Path("/tmp/runtime"),
            agent_name="reviewer",
            agent_id="agent-2",
        )

    monkeypatch.setattr(agents_core, "materialize_joined_launch", fake_materialize_joined_launch)

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "join",
            "--headless",
            "--agent-name",
            "reviewer",
            "--provider",
            "codex",
            "--launch-args",
            "exec",
            "--launch-args=--json",
            "--resume-id",
            "last",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["headless"] is True
    assert captured["provider"] == "codex"
    assert captured["launch_args"] == ("exec", "--json")
    resume_selection = captured["resume_selection"]
    assert isinstance(resume_selection, agents_core.HeadlessResumeSelection)
    assert resume_selection.kind == "last"


def test_houmao_mgr_agents_join_rejects_provider_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agents_core, "_require_current_tmux_session_name", lambda: "join-sess")
    monkeypatch.setattr(agents_core, "list_tmux_panes", lambda session_name: (_sample_join_pane(),))
    monkeypatch.setattr(agents_core, "_detect_join_provider", lambda pane_pid: "codex")
    monkeypatch.setattr(
        agents_core.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["tmux"], returncode=0, stdout="/tmp/project\n", stderr=""
        ),
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "join", "--agent-name", "coder", "--provider", "claude_code"],
    )

    assert result.exit_code != 0
    assert "does not match detected provider `codex`" in result.output


def test_houmao_mgr_agents_join_requires_tmux(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_current_session() -> str:
        raise click.ClickException(
            "Current-session attach must be run from inside the target tmux session."
        )

    monkeypatch.setattr(agents_core, "_require_current_tmux_session_name", fail_current_session)

    result = CliRunner().invoke(cli, ["agents", "join", "--agent-name", "coder"])

    assert result.exit_code != 0
    assert "inside the target tmux session" in result.output


def test_houmao_mgr_agents_join_rejects_blank_resume_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agents_core, "_require_current_tmux_session_name", lambda: "join-sess")
    monkeypatch.setattr(agents_core, "list_tmux_panes", lambda session_name: (_sample_join_pane(),))
    monkeypatch.setattr(agents_core, "_detect_join_provider", lambda pane_pid: None)
    monkeypatch.setattr(
        agents_core.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["tmux"], returncode=0, stdout="/tmp/project\n", stderr=""
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "join",
            "--headless",
            "--agent-name",
            "reviewer",
            "--provider",
            "codex",
            "--launch-args",
            "exec",
            "--launch-args=--json",
            "--resume-id",
            "",
        ],
    )

    assert result.exit_code != 0
    assert "`--resume-id` must not be blank" in result.output


def test_detect_join_provider_supports_gemini_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeInspector:
        def inspect(self, *, tool: str, pane_pid: int | None) -> PaneProcessInspection:
            del pane_pid
            if tool == "gemini":
                return PaneProcessInspection(
                    process_state="tui_up",
                    matched_process_names=("gemini",),
                    matched_processes=(),
                )
            return PaneProcessInspection(
                process_state="tui_down",
                matched_process_names=(),
                matched_processes=(),
            )

    monkeypatch.setattr(
        agents_core, "PaneProcessInspector", lambda supported_processes: _FakeInspector()
    )

    assert agents_core._detect_join_provider(123) == "gemini_cli"
