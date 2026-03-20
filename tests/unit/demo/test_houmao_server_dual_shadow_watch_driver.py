"""Unit tests for the Houmao-server dual shadow-watch demo driver."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import houmao.demo.houmao_server_dual_shadow_watch.driver as demo_driver
from houmao.demo.houmao_server_dual_shadow_watch.models import (
    AgentSessionState,
    DemoPaths,
    HoumaoServerDualShadowWatchState,
    MonitorSessionState,
    ServerProcessState,
    load_demo_state,
    save_demo_state,
)


def _repo_root() -> Path:
    """Return the repository root for this test module."""

    return Path(__file__).resolve().parents[3]


def _demo_state(tmp_path: Path) -> HoumaoServerDualShadowWatchState:
    """Return a representative persisted demo state."""

    return HoumaoServerDualShadowWatchState(
        schema_version=1,
        active=True,
        created_at_utc="2026-03-19T12:00:00+00:00",
        stopped_at_utc=None,
        repo_root="/repo",
        run_root="/repo/tmp/demo/houmao-server-dual-shadow-watch/demo-run",
        agent_def_dir="/repo/tests/fixtures/agents",
        project_fixture="/repo/tests/fixtures/dummy-projects/projection-demo-python",
        profile_path="/repo/scripts/demo/houmao-server-dual-shadow-watch/profiles/projection-demo.md",
        poll_interval_seconds=0.5,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
        server_start_timeout_seconds=20.0,
        launch_timeout_seconds=45.0,
        stop_timeout_seconds=20.0,
        server=ServerProcessState(
            api_base_url="http://127.0.0.1:19989",
            port=19989,
            runtime_root="/repo/tmp/demo/server/runtime",
            home_dir="/repo/tmp/demo/server/home",
            pid=4242,
            started_by_demo=True,
            stdout_log_path="/repo/tmp/demo/logs/houmao-server.stdout.log",
            stderr_log_path="/repo/tmp/demo/logs/houmao-server.stderr.log",
        ),
        agents={
            "claude": AgentSessionState(
                slot="claude",
                tool="claude",
                provider="claude_code",
                profile_name="projection-demo",
                session_name="cao-demo-claude",
                terminal_id="abcd1234",
                tmux_session_name="cao-demo-claude",
                workdir="/repo/tmp/demo/projects/claude",
                agent_name="cao-demo-claude",
                agent_id="AGENTSYS-cao-demo-claude",
                blueprint_path="/repo/tests/fixtures/agents/blueprints/projection-demo-claude.yaml",
                brain_recipe_path="/repo/tests/fixtures/agents/brains/brain-recipes/claude/projection-demo-default.yaml",
                role_name="projection-demo",
                config_profile="default",
                credential_profile="personal-a-default",
                brain_home_path="/repo/tmp/demo/runtime/homes/projection-demo-claude",
                brain_manifest_path="/repo/tmp/demo/runtime/manifests/projection-demo-claude.yaml",
                launch_helper_path="/repo/tmp/demo/runtime/homes/projection-demo-claude/launch.sh",
                session_manifest_path="/repo/tmp/demo/runtime/sessions/houmao_server_rest/cao-demo-claude/manifest.json",
                session_root="/repo/tmp/demo/runtime/sessions/houmao_server_rest/cao-demo-claude",
                launch_stdout_path="/repo/tmp/demo/logs/launch-claude.stdout.log",
                launch_stderr_path="/repo/tmp/demo/logs/launch-claude.stderr.log",
            )
        },
        monitor=MonitorSessionState(
            tmux_session_name="houmao-shadow-watch-monitor-demo-run",
            command=(
                "/usr/bin/python",
                "/repo/scripts/demo/houmao-server-dual-shadow-watch/scripts/watch_dashboard.py",
                "--state-file",
                "/repo/tmp/demo/houmao-server-dual-shadow-watch/demo-run/control/demo_state.json",
            ),
            samples_path="/repo/tmp/demo/houmao-server-dual-shadow-watch/demo-run/monitor/samples.ndjson",
            transitions_path="/repo/tmp/demo/houmao-server-dual-shadow-watch/demo-run/monitor/transitions.ndjson",
            dashboard_log_path="/repo/tmp/demo/houmao-server-dual-shadow-watch/demo-run/logs/monitor-dashboard.log",
        ),
    )


def test_demo_paths_resolve_expected_layout() -> None:
    """The demo layout should derive deterministic subpaths from one run root."""

    repo_root = Path("/repo-root")
    run_root = Path("/repo-root/tmp/demo/houmao-server-dual-shadow-watch/demo-run")

    paths = DemoPaths.from_run_root(repo_root=repo_root, run_root=run_root)

    assert paths.control_dir == run_root / "control"
    assert paths.runtime_root == run_root / "runtime"
    assert paths.registry_root == run_root / "registry"
    assert paths.jobs_root == run_root / "jobs"
    assert paths.server_home_dir == run_root / "server" / "home"
    assert paths.server_runtime_root == run_root / "server" / "runtime"
    assert paths.claude_project_dir == run_root / "projects" / "claude"
    assert paths.codex_project_dir == run_root / "projects" / "codex"
    assert paths.monitor_dir == run_root / "monitor"
    assert paths.state_path == run_root / "control" / "demo_state.json"
    assert paths.preflight_report_path == run_root / "control" / "preflight.json"
    assert paths.current_run_root_path == (
        repo_root / "tmp" / "demo" / "houmao-server-dual-shadow-watch" / "current_run_root.txt"
    )


def test_install_projection_profile_targets_public_pair_port(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Profile installs should target the public Houmao pair port, not a hidden child home."""

    captured: dict[str, object] = {}
    profile_path = tmp_path / "projection-demo.md"
    profile_path.write_text("# projection-demo\n", encoding="utf-8")
    stdout_path = tmp_path / "install.stdout.log"
    stderr_path = tmp_path / "install.stderr.log"

    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured["args"] = args[0]
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(demo_driver.subprocess, "run", _fake_run)

    demo_driver._install_projection_profile(
        api_base_url="http://127.0.0.1:19989",
        profile_path=profile_path,
        provider="codex",
        env={"HOME": "/demo/server/home"},
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )

    assert captured["args"] == [
        demo_driver.sys.executable,
        "-m",
        "houmao.srv_ctrl",
        "install",
        str(profile_path),
        "--provider",
        "codex",
        "--port",
        "19989",
    ]
    assert captured["env"] == {"HOME": "/demo/server/home"}


def test_provision_project_fixture_initializes_standalone_git_repo(tmp_path: Path) -> None:
    """Provisioning should copy the fixture and create a fresh standalone git repo."""

    fixture_path = _repo_root() / "tests" / "fixtures" / "dummy-projects" / "projection-demo-python"
    project_workdir = tmp_path / "project"

    demo_driver._provision_project_fixture(
        fixture_path=fixture_path,
        project_workdir=project_workdir,
    )

    assert (project_workdir / "pyproject.toml").is_file()
    assert (project_workdir / ".git").exists()
    top_level = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=project_workdir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert Path(top_level).resolve() == project_workdir.resolve()


def test_demo_state_round_trip_preserves_houmao_server_contract(tmp_path: Path) -> None:
    """Persisted demo state should round-trip with the expected server-owned posture."""

    state_path = tmp_path / "demo_state.json"
    state = _demo_state(tmp_path)

    save_demo_state(state_path, state)
    loaded = load_demo_state(state_path)

    assert loaded.server.api_base_url == "http://127.0.0.1:19989"
    assert loaded.agents["claude"].provider == "claude_code"
    assert loaded.monitor.tmux_session_name == "houmao-shadow-watch-monitor-demo-run"


def test_inspect_demo_reports_monitor_cadence_separately_from_server_posture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Inspect output should group monitor cadence separately from server timing posture."""

    del tmp_path
    state = _demo_state(Path("/unused"))

    class _PayloadDouble:
        def __init__(self, payload: dict[str, object]) -> None:
            self.m_payload = payload

        def model_dump(self, mode: str = "json") -> dict[str, object]:
            del mode
            return self.m_payload

    class _ClientDouble:
        def __init__(self, base_url: str, timeout_seconds: float = 3.0) -> None:
            del base_url, timeout_seconds

        def get_session(self, session_name: str) -> _PayloadDouble:
            return _PayloadDouble({"session_name": session_name, "status": "ready"})

        def terminal_state(self, terminal_id: str) -> _PayloadDouble:
            return _PayloadDouble(
                {
                    "terminal_id": terminal_id,
                    "turn": {"phase": "ready"},
                    "surface": {"ready_posture": "yes"},
                    "stability": {"stable": False, "stable_for_seconds": 0.7},
                }
            )

    monkeypatch.setattr(demo_driver, "_load_selected_demo_state", lambda **kwargs: state)
    monkeypatch.setattr(demo_driver, "_server_health_payload", lambda base_url: {"ok": True})
    monkeypatch.setattr(
        demo_driver,
        "_tmux_session_exists",
        lambda session_name: session_name == state.monitor.tmux_session_name,
    )
    monkeypatch.setattr(demo_driver, "HoumaoServerClient", _ClientDouble)

    payload = demo_driver.inspect_demo(
        repo_root=Path("/repo"),
        run_root=Path("/repo/tmp/demo/houmao-server-dual-shadow-watch/demo-run"),
        json_output=True,
    )

    assert "poll_interval_seconds" not in payload
    assert payload["monitor"]["poll_interval_seconds"] == 0.5
    assert payload["server"]["timing_posture"] == {
        "stability_threshold_seconds": 1.0,
        "completion_stability_seconds": 1.0,
        "unknown_to_stalled_timeout_seconds": 30.0,
    }
    assert payload["server"]["healthy"] == {"ok": True}
    assert payload["agents"]["claude"]["tracked_state"]["stability"]["stable"] is False


def test_wait_for_session_registration_times_out() -> None:
    """Session registration waits should fail explicitly instead of hanging."""

    class _ClientDouble:
        def get_session(self, session_name: str) -> dict[str, object]:
            raise RuntimeError(f"missing: {session_name}")

    with pytest.raises(demo_driver.HoumaoServerDualShadowWatchError, match="timed out waiting"):
        demo_driver._wait_for_session_registration(
            client=_ClientDouble(),  # type: ignore[arg-type]
            session_name="cao-demo-codex",
            timeout_seconds=0.01,
        )


def test_preflight_reports_missing_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Preflight should fail fast when required command surfaces are unavailable."""

    monkeypatch.setattr(
        demo_driver,
        "_command_check_payload",
        lambda name: {"ok": name == "git", "path": f"/usr/bin/{name}" if name == "git" else None},
    )
    monkeypatch.setattr(
        demo_driver,
        "_resolve_lane_preflight",
        lambda **kwargs: demo_driver.LanePreflight(
            slot=str(kwargs["slot"]),
            tool=str(kwargs["slot"]),
            provider="codex" if kwargs["slot"] == "codex" else "claude_code",
            blueprint_path=tmp_path / "blueprint.yaml",
            brain_recipe_path=tmp_path / "recipe.yaml",
            role_name="projection-demo",
            config_profile="default",
            credential_profile="personal-a-default",
            config_profile_dir=tmp_path / "config",
            credential_profile_dir=tmp_path / "creds",
            credential_env_path=tmp_path / "creds" / "env" / "vars.env",
            required_credential_paths=(),
            optional_credential_paths=(),
            selected_allowlisted_env={},
            selected_allowlisted_env_keys=(),
            launch_executable="/usr/bin/fake-tool",
            home_selector_env_var="FAKE_HOME",
        ),
    )

    payload = demo_driver.preflight_demo(
        repo_root=_repo_root(),
        run_root=tmp_path / "demo-run",
        agent_def_dir=tmp_path / "missing-agents",
        project_fixture=tmp_path / "missing-fixture",
        profile_path=tmp_path / "missing-profile.md",
        port=19989,
        json_output=True,
    )

    assert payload["ok"] is False
    assert any("missing required executable `pixi`" in blocker for blocker in payload["blockers"])
