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


def test_child_cao_home_dir_resolves_expected_layout() -> None:
    """Profile installs should target the child CAO home used by delegated launch."""

    repo_root = Path("/repo-root")
    run_root = Path("/repo-root/tmp/demo/houmao-server-dual-shadow-watch/demo-run")
    paths = DemoPaths.from_run_root(repo_root=repo_root, run_root=run_root)

    child_home = demo_driver._child_cao_home_dir(
        api_base_url="http://127.0.0.1:19989",
        paths=paths,
    )

    assert child_home == (
        run_root
        / "server"
        / "runtime"
        / "houmao_servers"
        / "127.0.0.1-19989"
        / "child_cao"
        / "runtime"
        / "cao_servers"
        / "127.0.0.1-19990"
        / "home"
    )


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
    state = HoumaoServerDualShadowWatchState(
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

    save_demo_state(state_path, state)
    loaded = load_demo_state(state_path)

    assert loaded.server.api_base_url == "http://127.0.0.1:19989"
    assert loaded.agents["claude"].provider == "claude_code"
    assert loaded.monitor.tmux_session_name == "houmao-shadow-watch-monitor-demo-run"


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
