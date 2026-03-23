"""Unit tests for the standalone dual shadow-watch demo driver."""

from __future__ import annotations

import subprocess
from pathlib import Path

import houmao.demo.cao_dual_shadow_watch.driver as demo_driver
from houmao.demo.cao_dual_shadow_watch.models import (
    AgentSessionState,
    DemoLauncherState,
    DemoPaths,
    DualShadowWatchDemoState,
    MonitorSessionState,
    load_demo_state,
    save_demo_state,
)


def _repo_root() -> Path:
    """Return the repository root for this test module."""

    return Path(__file__).resolve().parents[3]


def test_demo_paths_resolve_expected_layout() -> None:
    """The demo layout should derive deterministic subpaths from one run root."""

    repo_root = Path("/repo-root")
    run_root = Path("/repo-root/tmp/demo/cao-dual-shadow-watch/demo-run")

    paths = DemoPaths.from_run_root(repo_root=repo_root, run_root=run_root)

    assert paths.control_dir == run_root / "control"
    assert paths.runtime_root == run_root / "runtime"
    assert paths.projects_dir == run_root / "projects"
    assert paths.claude_project_dir == run_root / "projects" / "claude"
    assert paths.codex_project_dir == run_root / "projects" / "codex"
    assert paths.monitor_dir == run_root / "monitor"
    assert paths.state_path == run_root / "control" / "demo_state.json"
    assert paths.launcher_config_path == run_root / "control" / "cao-server-launcher.toml"
    assert paths.current_run_root_path == (
        repo_root / "tmp" / "demo" / "cao-dual-shadow-watch" / "current_run_root.txt"
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


def test_demo_state_round_trip_preserves_shadow_only_contract(tmp_path: Path) -> None:
    """Persisted demo state should round-trip with the expected shadow posture."""

    state_path = tmp_path / "demo_state.json"
    state = DualShadowWatchDemoState(
        schema_version=1,
        active=True,
        created_at_utc="2026-03-18T12:00:00+00:00",
        stopped_at_utc=None,
        repo_root="/repo",
        run_root="/repo/tmp/demo/cao-dual-shadow-watch/demo-run",
        agent_def_dir="/repo/tests/fixtures/agents",
        project_fixture="/repo/tests/fixtures/dummy-projects/projection-demo-python",
        parsing_mode="shadow_only",
        poll_interval_seconds=0.5,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
        launcher=DemoLauncherState(
            config_path="/repo/tmp/demo/control/cao-server-launcher.toml",
            base_url="http://localhost:9889",
            runtime_root="/repo/tmp/demo/runtime",
            home_dir="/tmp/cao-home",
            profile_store="/tmp/cao-home/.aws/cli-agent-orchestrator/agent-store",
            started_new_process=True,
            reused_existing_process=False,
            artifact_dir="/repo/tmp/demo/runtime/cao_servers/localhost-9889/launcher",
            log_file="/repo/tmp/demo/runtime/cao_servers/localhost-9889/launcher/cao-server.log",
            ownership_file="/repo/tmp/demo/runtime/cao_servers/localhost-9889/launcher/ownership.json",
        ),
        agents={
            "claude": AgentSessionState(
                slot="claude",
                tool="claude",
                blueprint_path="/repo/tests/fixtures/agents/blueprints/projection-demo-claude.yaml",
                brain_recipe_path="/repo/tests/fixtures/agents/brains/brain-recipes/claude/projection-demo-default.yaml",
                role_name="projection-demo",
                workdir="/repo/tmp/demo/projects/claude",
                brain_home_path="/repo/tmp/demo/runtime/homes/claude/demo-home",
                brain_manifest_path="/repo/tmp/demo/runtime/manifests/claude/demo-home.json",
                launch_helper_path="/repo/tmp/demo/runtime/homes/claude/demo-home/launch.sh",
                session_manifest_path="/repo/tmp/demo/runtime/sessions/cao_rest/demo-session/manifest.json",
                agent_identity="projection-demo-claude",
                agent_id="AGENTSYS-projection-demo-claude",
                tmux_session_name="AGENTSYS-projection-demo-claude",
                cao_session_name="AGENTSYS-projection-demo-claude",
                terminal_id="term-claude",
                parsing_mode="shadow_only",
            ),
            "codex": AgentSessionState(
                slot="codex",
                tool="codex",
                blueprint_path="/repo/tests/fixtures/agents/blueprints/projection-demo-codex.yaml",
                brain_recipe_path="/repo/tests/fixtures/agents/brains/brain-recipes/codex/projection-demo-default.yaml",
                role_name="projection-demo",
                workdir="/repo/tmp/demo/projects/codex",
                brain_home_path="/repo/tmp/demo/runtime/homes/codex/demo-home",
                brain_manifest_path="/repo/tmp/demo/runtime/manifests/codex/demo-home.json",
                launch_helper_path="/repo/tmp/demo/runtime/homes/codex/demo-home/launch.sh",
                session_manifest_path="/repo/tmp/demo/runtime/sessions/cao_rest/demo-session-2/manifest.json",
                agent_identity="projection-demo-codex",
                agent_id="AGENTSYS-projection-demo-codex",
                tmux_session_name="AGENTSYS-projection-demo-codex",
                cao_session_name="AGENTSYS-projection-demo-codex",
                terminal_id="term-codex",
                parsing_mode="shadow_only",
            ),
        },
        monitor=MonitorSessionState(
            tmux_session_name="houmao-shadow-watch-monitor-120000",
            command=(
                "/usr/bin/python",
                "/repo/scripts/demo/cao-dual-shadow-watch/scripts/watch_dashboard.py",
                "--state-file",
                "/repo/tmp/demo/cao-dual-shadow-watch/demo-run/control/demo_state.json",
            ),
            samples_path="/repo/tmp/demo/cao-dual-shadow-watch/demo-run/monitor/samples.ndjson",
            transitions_path="/repo/tmp/demo/cao-dual-shadow-watch/demo-run/monitor/transitions.ndjson",
            dashboard_log_path="/repo/tmp/demo/cao-dual-shadow-watch/demo-run/logs/monitor-dashboard.log",
        ),
    )

    save_demo_state(state_path, state)
    loaded = load_demo_state(state_path)

    assert loaded.parsing_mode == "shadow_only"
    assert loaded.poll_interval_seconds == 0.5
    assert loaded.agents["claude"].terminal_id == "term-claude"
    assert loaded.monitor.tmux_session_name == "houmao-shadow-watch-monitor-120000"
