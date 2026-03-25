from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.models import LaunchPlan, SessionControlResult
from houmao.agents.realm_controller.registry_storage import resolve_live_agent_record
from houmao.server.client import HoumaoServerClient
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


def _install_fake_headless_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch runtime backend creation to use the fake headless backend."""

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


def _start_houmao_mgr_server(*, api_base_url: str, runtime_root: Path) -> subprocess.Popen[str]:
    """Start `houmao-mgr server start` in a detached subprocess."""

    repo_root = _source_repo_root()
    return subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "from houmao.srv_ctrl.commands.main import main; "
                "import sys; "
                "raise SystemExit(main(sys.argv[1:]))"
            ),
            "server",
            "start",
            "--api-base-url",
            api_base_url,
            "--runtime-root",
            str(runtime_root),
            "--no-startup-child",
        ],
        cwd=repo_root,
        env=_python_subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_for_server_ready(
    *,
    api_base_url: str,
    process: subprocess.Popen[str],
    timeout_seconds: float = 10.0,
) -> None:
    """Wait until the server health route responds or fail with subprocess logs."""

    client = HoumaoServerClient(api_base_url, timeout_seconds=0.5)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise AssertionError(
                "houmao-mgr server start exited before becoming healthy.\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )
        try:
            health = client.health_extended()
        except Exception:
            time.sleep(0.1)
            continue
        if health.houmao_service == "houmao-server":
            return
        time.sleep(0.1)
    process.kill()
    stdout, stderr = process.communicate(timeout=1)
    raise AssertionError(
        f"Timed out waiting for houmao-server health.\nstdout:\n{stdout}\nstderr:\n{stderr}"
    )


def test_houmao_mgr_agents_launch_supports_registry_first_local_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """`agents launch` should publish registry state and later resolve local control from it."""

    agent_def_dir = tmp_path / "agent-def"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    _install_fake_headless_runtime(monkeypatch)

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
        lambda *, session_name: session_name == "AGENTSYS-gpu",
    )

    runner = CliRunner()

    launch_result = runner.invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu",
            "--provider",
            "claude_code",
            "--headless",
            "--yolo",
        ],
    )

    assert launch_result.exit_code == 0, launch_result.output
    assert "Managed agent launch complete:" in launch_result.output
    assert resolve_live_agent_record("AGENTSYS-gpu") is not None

    list_result = runner.invoke(cli, ["agents", "list"])
    assert list_result.exit_code == 0, list_result.output
    list_payload = json.loads(list_result.output)
    assert [item["agent_name"] for item in list_payload["agents"]] == ["AGENTSYS-gpu"]

    state_result = runner.invoke(cli, ["agents", "state", "AGENTSYS-gpu"])
    assert state_result.exit_code == 0, state_result.output
    state_payload = json.loads(state_result.output)
    assert state_payload["identity"]["transport"] == "headless"
    assert state_payload["identity"]["agent_name"] == "AGENTSYS-gpu"
    assert state_payload["availability"] == "available"

    stop_result = runner.invoke(cli, ["agents", "stop", "AGENTSYS-gpu"])
    assert stop_result.exit_code == 0, stop_result.output
    stop_payload = json.loads(stop_result.output)
    assert stop_payload["success"] is True
    assert resolve_live_agent_record("AGENTSYS-gpu") is None


def test_houmao_mgr_server_commands_cover_live_lifecycle_and_empty_sessions(
    tmp_path: Path,
) -> None:
    """`server` commands should manage one live `houmao-server` process end to end."""

    port = _pick_unused_loopback_port()
    api_base_url = f"http://127.0.0.1:{port}"
    runtime_root = (tmp_path / "runtime").resolve()
    process = _start_houmao_mgr_server(api_base_url=api_base_url, runtime_root=runtime_root)
    try:
        _wait_for_server_ready(api_base_url=api_base_url, process=process)

        runner = CliRunner()

        status_result = runner.invoke(cli, ["server", "status", "--port", str(port)])
        assert status_result.exit_code == 0, status_result.output
        status_payload = json.loads(status_result.output)
        assert status_payload["running"] is True
        assert status_payload["api_base_url"] == api_base_url
        assert status_payload["active_session_count"] == 0

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

        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
