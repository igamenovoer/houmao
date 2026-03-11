"""Unit tests for the interactive CAO demo workflow."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType

import pytest

import gig_agents.demo.cao_interactive_demo as interactive_demo
import gig_agents.demo.cao_interactive_demo.cao_server as demo_cao_server
import gig_agents.demo.cao_interactive_demo.cli as demo_cli
import gig_agents.demo.cao_interactive_demo.commands as demo_commands
import gig_agents.demo.cao_interactive_demo.models as demo_models
import gig_agents.demo.cao_interactive_demo.rendering as demo_rendering
import gig_agents.demo.cao_interactive_demo.runtime as demo_runtime
from gig_agents.demo.cao_interactive_demo import (
    FIXED_CAO_BASE_URL,
    CommandResult,
    DemoEnvironment,
    DemoPaths,
    DemoState,
    DemoWorkflowError,
    TurnRecord,
    inspect_demo,
    load_demo_state,
    load_turn_records,
    main,
    save_demo_state,
    send_turn,
    start_demo,
    stop_demo,
    verify_demo,
)
from gig_agents.demo.cao_interactive_demo.runtime import (
    _run_subprocess_command_with_wait_feedback,
)


def _make_paths(tmp_path: Path) -> DemoPaths:
    return DemoPaths.from_workspace_root(tmp_path / "workspace")


def _source_agent_def_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "agents"


def _seed_agent_def_dir(agent_def_dir: Path) -> None:
    if agent_def_dir.exists():
        shutil.rmtree(agent_def_dir)
    shutil.copytree(_source_agent_def_dir(), agent_def_dir)


def _make_env(
    tmp_path: Path,
    *,
    launcher_home_dir: Path | None = None,
    workdir: Path | None = None,
    yes_to_all: bool = False,
    provision_worktree: bool = False,
) -> DemoEnvironment:
    repo_root = tmp_path / "repo"
    agent_def_dir = repo_root / "tests" / "fixtures" / "agents"
    _seed_agent_def_dir(agent_def_dir)
    demo_base_root = repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo"
    return DemoEnvironment(
        repo_root=repo_root,
        demo_base_root=demo_base_root,
        current_run_root_path=demo_base_root / "current_run_root.txt",
        agent_def_dir=agent_def_dir,
        launcher_home_dir=launcher_home_dir or (tmp_path / "launcher-home"),
        workdir=workdir or repo_root,
        role_name="gpu-kernel-coder",
        timeout_seconds=30.0,
        yes_to_all=yes_to_all,
        provision_worktree=provision_worktree,
    )


def _seed_state(
    paths: DemoPaths,
    *,
    active: bool,
    agent_identity: str = "AGENTSYS-demo",
    launcher_home_dir: Path | None = None,
    terminal_log_path: str | None = None,
    turn_count: int = 0,
    tool: str = "claude",
    brain_recipe: str = "claude/gpu-kernel-coder-default",
) -> None:
    resolved_launcher_home_dir = launcher_home_dir or paths.workspace_root
    state = DemoState(
        active=active,
        agent_identity=agent_identity,
        tool=tool,
        variant_id=brain_recipe.replace("/", "-"),
        brain_recipe=brain_recipe,
        session_manifest=str(paths.runtime_root / "sessions" / "cao_rest" / "session.json"),
        session_name=agent_identity,
        tmux_target=agent_identity,
        terminal_id="term-001",
        terminal_log_path=terminal_log_path
        or str(
            resolved_launcher_home_dir
            / ".aws"
            / "cli-agent-orchestrator"
            / "logs"
            / "terminal"
            / "term-001.log"
        ),
        runtime_root=str(paths.runtime_root),
        workspace_dir=str(paths.workspace_root),
        brain_home=str(paths.runtime_root / "brains" / "home"),
        brain_manifest=str(paths.runtime_root / "brains" / "brain.json"),
        cao_base_url=FIXED_CAO_BASE_URL,
        cao_profile_store=str(
            resolved_launcher_home_dir / ".aws" / "cli-agent-orchestrator" / "agent-store"
        ),
        launcher_config_path=str(paths.launcher_config_path),
        updated_at="2026-03-06T00:00:00+00:00",
        turn_count=turn_count,
    )
    save_demo_state(paths.state_path, state)


def _turn_record(
    paths: DemoPaths,
    *,
    turn_index: int,
    agent_identity: str = "AGENTSYS-demo",
    response_text: str = "response",
) -> TurnRecord:
    return TurnRecord(
        turn_index=turn_index,
        agent_identity=agent_identity,
        prompt=f"prompt {turn_index}",
        started_at_utc=f"2026-03-06T00:00:0{turn_index}+00:00",
        completed_at_utc=f"2026-03-06T00:00:1{turn_index}+00:00",
        exit_status=0,
        response_text=response_text,
        events=[{"kind": "done", "message": response_text}],
        stdout_path=str(paths.turns_dir / f"turn-{turn_index:03d}.events.jsonl"),
        stderr_path=str(paths.turns_dir / f"turn-{turn_index:03d}.stderr.log"),
    )


def _patch_demo_tools_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(demo_rendering.shutil, "which", lambda _: "/usr/bin/fake")
    monkeypatch.setattr(demo_cao_server.shutil, "which", lambda _: "/usr/bin/fake")


def test_canonical_package_exports_are_explicit_and_resolve_to_owning_modules() -> None:
    resolved_exports = {name: getattr(interactive_demo, name) for name in interactive_demo.__all__}
    public_names = {
        name
        for name, value in interactive_demo.__dict__.items()
        if not name.startswith("_") and not isinstance(value, ModuleType)
    }

    assert set(interactive_demo.__all__) == public_names
    assert interactive_demo.DemoState is demo_models.DemoState
    assert interactive_demo.start_demo is demo_commands.start_demo
    assert resolved_exports["main"] is demo_cli.main
    assert interactive_demo.run_subprocess_command is demo_runtime.run_subprocess_command
    assert interactive_demo.FIXED_CAO_BASE_URL == demo_models.FIXED_CAO_BASE_URL


class FakeRunner:
    def __init__(self, tmp_path: Path) -> None:
        self.m_tmp_path = tmp_path
        self.m_calls: list[tuple[str, ...]] = []
        self.m_tmux_sessions: set[str] = set()
        self.m_last_built_tool = "claude"
        self.m_launcher_status_responses: list[tuple[int, dict[str, object]]] = [
            (
                2,
                {
                    "operation": "status",
                    "base_url": FIXED_CAO_BASE_URL,
                    "healthy": False,
                    "health_status": None,
                    "service": None,
                    "error": "connection refused",
                },
            )
        ]
        self.m_launcher_start_response: tuple[int, dict[str, object]] = (
            0,
            {
                "started_new_process": True,
                "reused_existing_process": False,
                "pid": 4242,
            },
        )
        self.m_launcher_stop_responses: list[tuple[int, dict[str, object]]] = [
            (
                0,
                {
                    "stopped": True,
                    "already_stopped": False,
                    "verification_passed": True,
                    "pid": 4242,
                    "signal_sent": "SIGTERM",
                },
            )
        ]

    @property
    def calls(self) -> list[tuple[str, ...]]:
        return list(self.m_calls)

    def __call__(
        self,
        command: list[str],
        cwd: Path,
        stdout_path: Path,
        stderr_path: Path,
        timeout_seconds: float,
    ) -> CommandResult:
        self.m_calls.append(tuple(command))
        stdout = ""
        stderr = ""
        returncode = 0

        if command[0] == "tmux":
            subcommand = command[1]
            session_name = command[-1]
            if subcommand == "has-session":
                returncode = 0 if session_name in self.m_tmux_sessions else 1
            elif subcommand == "kill-session":
                self.m_tmux_sessions.discard(session_name)
                returncode = 0
        elif command[0] == "git":
            worktree_path = Path(command[4])
            worktree_path.mkdir(parents=True, exist_ok=True)
            (worktree_path / ".git").write_text("gitdir: fake\n", encoding="utf-8")
        else:
            module = command[4]
            subcommand = command[5]

            if module == "gig_agents.cao.tools.cao_server_launcher":
                if subcommand == "status":
                    returncode, payload = self.m_launcher_status_responses.pop(0)
                    stdout = json.dumps(payload)
                elif subcommand == "start":
                    returncode, payload = self.m_launcher_start_response
                    stdout = json.dumps(payload)
                elif subcommand == "stop":
                    returncode, payload = self.m_launcher_stop_responses.pop(0)
                    stdout = json.dumps(payload)
            elif module == "gig_agents.agents.brain_launch_runtime":
                if subcommand == "build-brain":
                    runtime_root = Path(self._argument_value(command, "--runtime-root"))
                    recipe_path = Path(self._argument_value(command, "--recipe"))
                    self.m_last_built_tool = "codex" if "codex" in recipe_path.parts else "claude"
                    manifest_path = runtime_root / "brains" / "brain-manifest.json"
                    home_path = runtime_root / "brains" / "home"
                    manifest_path.parent.mkdir(parents=True, exist_ok=True)
                    manifest_path.write_text("{}", encoding="utf-8")
                    home_path.mkdir(parents=True, exist_ok=True)
                    stdout = json.dumps(
                        {
                            "home_id": "brain-home",
                            "home_path": str(home_path),
                            "manifest_path": str(manifest_path),
                            "launch_helper_path": str(home_path / "launch.py"),
                        }
                    )
                elif subcommand == "start-session":
                    runtime_root = Path(self._argument_value(command, "--runtime-root"))
                    session_manifest = (
                        runtime_root / "sessions" / "cao_rest" / "interactive-session.json"
                    )
                    session_manifest.parent.mkdir(parents=True, exist_ok=True)
                    agent_identity = self._argument_value(command, "--agent-identity")
                    session_manifest.write_text(
                        json.dumps(
                            {
                                "cao": {
                                    "session_name": agent_identity,
                                    "terminal_id": "term-123",
                                }
                            }
                        ),
                        encoding="utf-8",
                    )
                    stdout = json.dumps(
                        {
                            "session_manifest": str(session_manifest),
                            "agent_identity": agent_identity,
                            "tool": self.m_last_built_tool,
                        }
                    )
                elif subcommand == "send-prompt":
                    prompt = self._argument_value(command, "--prompt")
                    stdout = "\n".join(
                        [
                            json.dumps({"kind": "submitted", "message": "submitted"}),
                            json.dumps({"kind": "done", "message": f"echo: {prompt}"}),
                        ]
                    )
                elif subcommand == "stop-session":
                    stdout = json.dumps(
                        {
                            "status": "ok",
                            "action": "terminate",
                            "detail": "Deleted CAO terminal and session",
                        }
                    )

        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        return CommandResult(
            args=tuple(command),
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

    @staticmethod
    def _argument_value(command: list[str], flag: str) -> str:
        index = command.index(flag)
        return command[index + 1]


def test_start_demo_replaces_active_state_and_persists_new_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    _seed_state(paths, active=True, agent_identity="AGENTSYS-demo")
    env.current_run_root_path.parent.mkdir(parents=True, exist_ok=True)
    env.current_run_root_path.write_text(f"{paths.workspace_root}\n", encoding="utf-8")
    runner = FakeRunner(tmp_path)

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)

    payload = start_demo(
        paths=paths,
        env=env,
        agent_name_override="demo",
        brain_recipe_selector=None,
        run_command=runner,
    )

    state = load_demo_state(paths.state_path)
    assert state is not None
    assert state.active is True
    assert state.agent_identity == "AGENTSYS-demo"
    assert state.tool == "claude"
    assert state.variant_id == "claude-gpu-kernel-coder-default"
    assert state.brain_recipe == "claude/gpu-kernel-coder-default"
    assert state.cao_base_url == FIXED_CAO_BASE_URL
    assert state.terminal_log_path == str(
        env.launcher_home_dir
        / ".aws"
        / "cli-agent-orchestrator"
        / "logs"
        / "terminal"
        / "term-123.log"
    )
    assert payload["replaced_previous_agent_identity"] == "AGENTSYS-demo"

    stop_call = next(call for call in runner.calls if "stop-session" in call)
    assert stop_call[5] == "stop-session"
    assert "--agent-identity" in stop_call
    assert stop_call[stop_call.index("--agent-identity") + 1] == "AGENTSYS-demo"

    build_call = next(call for call in runner.calls if "build-brain" in call)
    assert build_call[build_call.index("--recipe") + 1].endswith(
        "tests/fixtures/agents/brains/brain-recipes/claude/gpu-kernel-coder-default.yaml"
    )

    start_call = next(call for call in runner.calls if "start-session" in call)
    assert start_call[start_call.index("--cao-base-url") + 1] == FIXED_CAO_BASE_URL
    assert start_call[start_call.index("--agent-identity") + 1] == "AGENTSYS-demo"


def test_start_demo_uses_recipe_default_name_when_agent_name_override_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)
    runner = FakeRunner(tmp_path)

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)

    payload = start_demo(
        paths=paths,
        env=env,
        agent_name_override=None,
        brain_recipe_selector="codex/gpu-kernel-coder-default",
        run_command=runner,
    )

    state = load_demo_state(paths.state_path)
    assert state is not None
    assert state.agent_identity == "AGENTSYS-cao-codex-demo"
    assert state.tool == "codex"
    assert state.variant_id == "codex-gpu-kernel-coder-default"
    assert state.brain_recipe == "codex/gpu-kernel-coder-default"
    assert payload["warnings"] == []


def test_start_demo_rejects_ambiguous_recipe_basename(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)

    with pytest.raises(
        DemoWorkflowError, match="Multiple brain recipes matched `gpu-kernel-coder-default`"
    ):
        start_demo(
            paths=paths,
            env=env,
            agent_name_override=None,
            brain_recipe_selector="gpu-kernel-coder-default",
            run_command=FakeRunner(tmp_path),
        )


def test_start_demo_replaces_stale_incompatible_local_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)
    paths.workspace_root.mkdir(parents=True, exist_ok=True)
    paths.state_path.write_text(
        json.dumps({"active": True, "agent_identity": "AGENTSYS-stale"}) + "\n",
        encoding="utf-8",
    )
    runner = FakeRunner(tmp_path)

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)

    start_demo(
        paths=paths,
        env=env,
        agent_name_override="demo",
        brain_recipe_selector=None,
        run_command=runner,
    )

    state = load_demo_state(paths.state_path)
    assert state is not None
    assert state.agent_identity == "AGENTSYS-demo"
    assert state.variant_id == "claude-gpu-kernel-coder-default"


def test_main_start_uses_repo_root_anchored_per_run_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _seed_agent_def_dir(repo_root / "tests" / "fixtures" / "agents")
    runner = FakeRunner(tmp_path)

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)
    monkeypatch.setattr(demo_cli, "_run_timestamp_slug", lambda: "20260309-120000-000000Z")

    exit_code = main(
        ["--repo-root", str(repo_root), "start", "--agent-name", "alice"],
        run_command=runner,
    )

    assert exit_code == 0

    workspace_root = (
        repo_root
        / "tmp"
        / "demo"
        / "cao-interactive-full-pipeline-demo"
        / "20260309-120000-000000Z"
    )
    state = load_demo_state(DemoPaths.from_workspace_root(workspace_root).state_path)
    assert state is not None
    assert Path(state.workspace_dir) == workspace_root
    assert state.brain_recipe == "claude/gpu-kernel-coder-default"
    assert (
        Path(state.cao_profile_store)
        == workspace_root / ".aws" / "cli-agent-orchestrator" / "agent-store"
    )
    assert Path(state.terminal_log_path) == (
        workspace_root / ".aws" / "cli-agent-orchestrator" / "logs" / "terminal" / "term-123.log"
    )

    current_run_root_path = (
        repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo" / "current_run_root.txt"
    )
    assert current_run_root_path.read_text(encoding="utf-8").strip() == str(workspace_root)

    worktree_call = next(call for call in runner.calls if call[:3] == ("git", "worktree", "add"))
    assert Path(worktree_call[4]) == workspace_root / "wktree"

    start_call = next(call for call in runner.calls if "start-session" in call)
    assert start_call[start_call.index("--workdir") + 1] == str(workspace_root / "wktree")
    assert start_call[start_call.index("--agent-def-dir") + 1] == str(
        repo_root / "tests" / "fixtures" / "agents"
    )


def test_main_start_emits_stderr_progress_and_human_readable_stdout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = tmp_path / "repo"
    _seed_agent_def_dir(repo_root / "tests" / "fixtures" / "agents")
    runner = FakeRunner(tmp_path)

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)
    monkeypatch.setattr(demo_cli, "_run_timestamp_slug", lambda: "20260309-120000-000000Z")

    exit_code = main(
        ["--repo-root", str(repo_root), "start", "--agent-name", "alice"],
        run_command=runner,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[interactive-demo:start]" not in captured.out
    assert "Interactive CAO Demo Started" in captured.out
    assert "Session Summary" in captured.out
    assert "agent_identity: AGENTSYS-alice" in captured.out
    assert "Commands" in captured.out
    assert "tmux_attach: tmux attach -t AGENTSYS-alice" in captured.out
    assert "Artifacts" in captured.out
    assert "[interactive-demo:start]" in captured.err
    assert "Preparing the interactive demo workspace." in captured.err
    assert "Ensuring local CAO availability" in captured.err
    assert "Building the interactive Claude runtime brain." in captured.err
    assert "Launching the interactive Claude session and waiting for readiness." in captured.err


def test_main_start_json_preserves_machine_readable_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = tmp_path / "repo"
    _seed_agent_def_dir(repo_root / "tests" / "fixtures" / "agents")
    runner = FakeRunner(tmp_path)

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)
    monkeypatch.setattr(demo_cli, "_run_timestamp_slug", lambda: "20260309-120000-000000Z")

    exit_code = main(
        ["--repo-root", str(repo_root), "start", "--agent-name", "alice", "--json"],
        run_command=runner,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["state"]["agent_identity"] == "AGENTSYS-alice"
    assert payload["state"]["tool"] == "claude"
    assert payload["state"]["variant_id"] == "claude-gpu-kernel-coder-default"
    assert "[interactive-demo:start]" not in captured.out
    assert "Interactive CAO Demo Started" not in captured.out
    assert "[interactive-demo:start]" in captured.err


def test_main_start_accepts_explicit_codex_recipe_selector(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _seed_agent_def_dir(repo_root / "tests" / "fixtures" / "agents")
    runner = FakeRunner(tmp_path)

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)
    monkeypatch.setattr(demo_cli, "_run_timestamp_slug", lambda: "20260309-120000-000000Z")

    exit_code = main(
        [
            "--repo-root",
            str(repo_root),
            "start",
            "--brain-recipe",
            "codex/gpu-kernel-coder-default",
            "--json",
        ],
        run_command=runner,
    )

    assert exit_code == 0
    workspace_root = (
        repo_root
        / "tmp"
        / "demo"
        / "cao-interactive-full-pipeline-demo"
        / "20260309-120000-000000Z"
    )
    state = load_demo_state(DemoPaths.from_workspace_root(workspace_root).state_path)
    assert state is not None
    assert state.tool == "codex"
    assert state.agent_identity == "AGENTSYS-cao-codex-demo"


def test_run_subprocess_command_with_wait_feedback_emits_recurring_heartbeats(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdout_path = tmp_path / "long-start.stdout"
    stderr_path = tmp_path / "long-start.stderr"

    result = _run_subprocess_command_with_wait_feedback(
        ["bash", "-lc", "sleep 0.28; printf 'ready'"],
        tmp_path,
        stdout_path,
        stderr_path,
        5.0,
        waiting_message=(
            "Still waiting for the interactive Claude session to launch and become ready for input."
        ),
        initial_delay_seconds=0.05,
        heartbeat_interval_seconds=0.05,
    )

    captured = capsys.readouterr()
    assert result.returncode == 0
    assert result.stdout == "ready"
    assert stdout_path.read_text(encoding="utf-8") == "ready"
    assert stderr_path.read_text(encoding="utf-8") == ""
    assert (
        captured.err.count(
            "Still waiting for the interactive Claude session to launch and become ready for input."
        )
        >= 2
    )


def test_start_demo_resets_previous_run_artifacts_and_stale_tmux(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    previous_paths = DemoPaths.from_workspace_root(tmp_path / "previous-run")
    previous_paths.turns_dir.mkdir(parents=True, exist_ok=True)
    previous_paths.report_path.write_text("{}", encoding="utf-8")
    (previous_paths.turns_dir / "turn-001.json").write_text("{}", encoding="utf-8")
    _seed_state(previous_paths, active=True, agent_identity="AGENTSYS-alice")

    next_paths = DemoPaths.from_workspace_root(tmp_path / "next-run")
    env = _make_env(
        tmp_path,
        launcher_home_dir=next_paths.workspace_root,
        workdir=next_paths.workspace_root / "wktree",
        provision_worktree=True,
    )
    env.current_run_root_path.parent.mkdir(parents=True, exist_ok=True)
    env.current_run_root_path.write_text(f"{previous_paths.workspace_root}\n", encoding="utf-8")
    runner = FakeRunner(tmp_path)
    runner.m_tmux_sessions.add("AGENTSYS-alice")

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)

    payload = start_demo(
        paths=next_paths,
        env=env,
        agent_name_override="alice",
        brain_recipe_selector=None,
        run_command=runner,
    )

    previous_state = load_demo_state(previous_paths.state_path)
    assert previous_state is not None
    assert previous_state.active is False
    assert payload["replaced_previous_agent_identity"] == "AGENTSYS-alice"
    assert not previous_paths.report_path.exists()
    assert list(previous_paths.turns_dir.glob("*.json")) == []
    assert any(call[:2] == ("tmux", "has-session") for call in runner.calls)
    assert any(call[:2] == ("tmux", "kill-session") for call in runner.calls)


def test_start_demo_replaces_verified_cao_server_with_yes_to_all(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path, yes_to_all=True)
    runner = FakeRunner(tmp_path)
    runner.m_launcher_status_responses = [
        (
            0,
            {
                "operation": "status",
                "base_url": FIXED_CAO_BASE_URL,
                "healthy": True,
                "health_status": "ok",
                "service": "cli-agent-orchestrator",
                "error": None,
            },
        )
    ]

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)
    monkeypatch.setattr(
        demo_cao_server,
        "_prompt_yes_no",
        lambda _: pytest.fail("unexpected confirmation prompt"),
    )

    start_demo(
        paths=paths,
        env=env,
        agent_name_override="demo",
        brain_recipe_selector=None,
        run_command=runner,
    )

    assert any(
        call[4] == "gig_agents.cao.tools.cao_server_launcher" and call[5] == "stop"
        for call in runner.calls
        if len(call) > 5
    )


def test_start_demo_verified_cao_replacement_stays_on_launcher_managed_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path, yes_to_all=True)
    runner = FakeRunner(tmp_path)
    runner.m_launcher_status_responses = [
        (
            0,
            {
                "operation": "status",
                "base_url": FIXED_CAO_BASE_URL,
                "healthy": True,
                "health_status": "ok",
                "service": "cli-agent-orchestrator",
                "error": None,
            },
        )
    ]

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_loopback_port_is_listening", lambda _: False)
    monkeypatch.setattr(
        demo_cao_server,
        "_find_listening_pids_for_port",
        lambda _: pytest.fail("unexpected procfs fallback for verified replacement"),
    )

    start_demo(
        paths=paths,
        env=env,
        agent_name_override="demo",
        brain_recipe_selector=None,
        run_command=runner,
    )

    assert any(
        call[4] == "gig_agents.cao.tools.cao_server_launcher" and call[5] == "stop"
        for call in runner.calls
        if len(call) > 5
    )


def test_start_demo_aborts_when_verified_cao_replacement_is_declined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)
    runner = FakeRunner(tmp_path)
    runner.m_launcher_status_responses = [
        (
            0,
            {
                "operation": "status",
                "base_url": FIXED_CAO_BASE_URL,
                "healthy": True,
                "health_status": "ok",
                "service": "cli-agent-orchestrator",
                "error": None,
            },
        )
    ]

    _patch_demo_tools_available(monkeypatch)
    monkeypatch.setattr(demo_cao_server, "_prompt_yes_no", lambda _: False)

    with pytest.raises(DemoWorkflowError, match="existing verified local `cao-server`"):
        start_demo(
            paths=paths,
            env=env,
            agent_name_override="demo",
            brain_recipe_selector=None,
            run_command=runner,
        )

    assert not paths.state_path.exists()


def test_start_demo_fails_when_existing_service_does_not_verify_as_cao_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)
    runner = FakeRunner(tmp_path)
    runner.m_launcher_status_responses = [
        (
            0,
            {
                "operation": "status",
                "base_url": FIXED_CAO_BASE_URL,
                "healthy": True,
                "health_status": "ok",
                "service": "other-service",
                "error": None,
            },
        )
    ]

    _patch_demo_tools_available(monkeypatch)

    with pytest.raises(DemoWorkflowError, match="did not verify as `cao-server`"):
        start_demo(
            paths=paths,
            env=env,
            agent_name_override="demo",
            brain_recipe_selector=None,
            run_command=runner,
        )


def test_find_pids_for_socket_inodes_skips_unreadable_proc_fd_directories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_exists = Path.exists
    original_iterdir = Path.iterdir

    def fake_exists(path: Path) -> bool:
        if str(path) in {"/proc/123/fd", "/proc/456/fd"}:
            return True
        return original_exists(path)

    def fake_iterdir(path: Path):
        if str(path) == "/proc":
            return iter((Path("/proc/123"), Path("/proc/456")))
        if str(path) == "/proc/123/fd":
            raise PermissionError("permission denied")
        if str(path) == "/proc/456/fd":
            return iter((Path("/proc/456/fd/7"),))
        return original_iterdir(path)

    def fake_readlink(path: str | Path) -> str:
        if str(path) == "/proc/456/fd/7":
            return "socket:[111]"
        raise OSError("missing")

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    monkeypatch.setattr(demo_cao_server.os, "readlink", fake_readlink)

    assert demo_cao_server._find_pids_for_socket_inodes({"111"}) == {456}


def test_send_turn_records_turn_artifact_and_updates_state(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)
    _seed_state(paths, active=True, turn_count=0)
    runner = FakeRunner(tmp_path)

    turn = send_turn(
        paths=paths,
        env=env,
        prompt="say hello",
        run_command=runner,
    )

    assert turn.turn_index == 1
    assert turn.response_text == "echo: say hello"

    state = load_demo_state(paths.state_path)
    assert state is not None
    assert state.turn_count == 1

    records = load_turn_records(paths.turns_dir)
    assert [record.turn_index for record in records] == [1]
    send_call = next(call for call in runner.calls if "send-prompt" in call)
    assert send_call[send_call.index("--agent-identity") + 1] == "AGENTSYS-demo"


def test_send_turn_succeeds_after_recovered_model_switch_history(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)
    _seed_state(paths, active=True, turn_count=3)
    paths.turns_dir.mkdir(parents=True, exist_ok=True)
    for turn_index in range(1, 4):
        record = _turn_record(paths, turn_index=turn_index)
        (paths.turns_dir / f"turn-{turn_index:03d}.json").write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def _runner(
        command: list[str],
        cwd: Path,
        stdout_path: Path,
        stderr_path: Path,
        timeout_seconds: float,
    ) -> CommandResult:
        del cwd, timeout_seconds
        stdout = "\n".join(
            [
                json.dumps({"kind": "submitted", "message": "submitted"}),
                json.dumps(
                    {
                        "kind": "done",
                        "message": "Yes, there is a claude.md file.",
                        "payload": {
                            "surface_assessment": {
                                "business_state": "idle",
                                "input_mode": "freeform",
                                "ui_context": "normal_prompt",
                                "evidence": ["SUPPORTED_OUTPUT_FAMILY", "IDLE_PROMPT_LINE"],
                            },
                            "dialog_projection": {
                                "dialog_text": (
                                    "/model\n"
                                    "Set model to Default (claude-sonnet-4-6)\n"
                                    "do we have claude.md\n"
                                    "Yes, there is a claude.md file."
                                )
                            },
                        },
                    }
                ),
            ]
        )
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return CommandResult(
            args=tuple(command),
            returncode=0,
            stdout=stdout,
            stderr="",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

    turn = send_turn(
        paths=paths,
        env=env,
        prompt="do we have claude.md",
        run_command=_runner,
    )

    assert turn.turn_index == 4
    assert turn.response_text == "Yes, there is a claude.md file."
    assert turn.events[-1]["payload"]["surface_assessment"]["ui_context"] == "normal_prompt"
    assert "/model" in turn.events[-1]["payload"]["dialog_projection"]["dialog_text"]

    state = load_demo_state(paths.state_path)
    assert state is not None
    assert state.agent_identity == "AGENTSYS-demo"
    assert state.turn_count == 4


def test_main_inspect_with_output_text_passes_requested_tail_chars(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "tests" / "fixtures" / "agents").mkdir(parents=True, exist_ok=True)
    demo_base_root = repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo"
    workspace_root = demo_base_root / "20260309-120000-000000Z"
    workspace_root.mkdir(parents=True, exist_ok=True)
    demo_base_root.mkdir(parents=True, exist_ok=True)
    (demo_base_root / "current_run_root.txt").write_text(
        f"{workspace_root}\n",
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    def _inspect_demo(
        *,
        paths: DemoPaths,
        as_json: bool,
        output_text_tail_chars: int | None = None,
    ) -> None:
        captured["paths"] = paths
        captured["as_json"] = as_json
        captured["output_text_tail_chars"] = output_text_tail_chars

    monkeypatch.setattr(demo_cli, "inspect_demo", _inspect_demo)

    exit_code = main(
        [
            "--repo-root",
            str(repo_root),
            "inspect",
            "--json",
            "--with-output-text",
            "42",
        ]
    )

    assert exit_code == 0
    assert isinstance(captured["paths"], DemoPaths)
    assert captured["as_json"] is True
    assert captured["output_text_tail_chars"] == 42
    assert captured["paths"].workspace_root == workspace_root


def test_inspect_demo_json_reports_live_state_and_clean_output_tail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _make_paths(tmp_path)
    launcher_home_dir = tmp_path / "launcher-home"
    _seed_state(
        paths,
        active=True,
        launcher_home_dir=launcher_home_dir,
        terminal_log_path="~/.aws/cli-agent-orchestrator/logs/terminal/term-001.log",
    )

    class FakeCaoRestClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.m_base_url = base_url
            self.m_timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> SimpleNamespace:
            assert terminal_id == "term-001"
            return SimpleNamespace(status=SimpleNamespace(value="processing"))

        def get_terminal_output(self, terminal_id: str, mode: str = "last") -> SimpleNamespace:
            assert terminal_id == "term-001"
            assert mode == "full"
            return SimpleNamespace(output="raw full output")

    class FakeShadowParserStack:
        def __init__(self, *, tool: str) -> None:
            assert tool == "claude"

        def parse_snapshot(self, scrollback: str, *, baseline_pos: int = 0) -> SimpleNamespace:
            assert scrollback == "raw full output"
            assert baseline_pos == 0
            return SimpleNamespace(
                surface_assessment=SimpleNamespace(availability="supported"),
                dialog_projection=SimpleNamespace(dialog_text="User: hi\nClaude: hello there"),
            )

    monkeypatch.setattr(demo_commands, "CaoRestClient", FakeCaoRestClient)
    monkeypatch.setattr(demo_runtime, "ShadowParserStack", FakeShadowParserStack)

    inspect_demo(paths=paths, as_json=True, output_text_tail_chars=11)

    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "claude"
    assert payload["variant_id"] == "claude-gpu-kernel-coder-default"
    assert payload["brain_recipe"] == "claude/gpu-kernel-coder-default"
    assert payload["tool_state"] == "processing"
    assert payload["output_text_tail"] == "hello there"
    assert payload["output_text_tail_chars_requested"] == 11
    assert payload["terminal_log_path"] == str(
        launcher_home_dir / ".aws" / "cli-agent-orchestrator" / "logs" / "terminal" / "term-001.log"
    )
    assert "output_text_tail_note" not in payload


def test_inspect_demo_uses_persisted_tool_for_shadow_parser_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _make_paths(tmp_path)
    _seed_state(
        paths,
        active=True,
        tool="codex",
        brain_recipe="codex/gpu-kernel-coder-default",
    )

    class FakeCaoRestClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.m_base_url = base_url
            self.m_timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> SimpleNamespace:
            return SimpleNamespace(status=SimpleNamespace(value="idle"))

        def get_terminal_output(self, terminal_id: str, mode: str = "last") -> SimpleNamespace:
            assert mode == "full"
            return SimpleNamespace(output="codex output")

    class FakeShadowParserStack:
        def __init__(self, *, tool: str) -> None:
            assert tool == "codex"

        def parse_snapshot(self, scrollback: str, *, baseline_pos: int = 0) -> SimpleNamespace:
            assert scrollback == "codex output"
            assert baseline_pos == 0
            return SimpleNamespace(
                surface_assessment=SimpleNamespace(availability="supported"),
                dialog_projection=SimpleNamespace(dialog_text="Codex says hello"),
            )

    monkeypatch.setattr(demo_commands, "CaoRestClient", FakeCaoRestClient)
    monkeypatch.setattr(demo_runtime, "ShadowParserStack", FakeShadowParserStack)

    inspect_demo(paths=paths, as_json=True, output_text_tail_chars=5)

    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "codex"
    assert payload["tool_state"] == "idle"
    assert payload["output_text_tail"] == "hello"


def test_inspect_demo_human_output_handles_live_lookup_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _make_paths(tmp_path)
    _seed_state(paths, active=True)

    class FailingCaoRestClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.m_base_url = base_url
            self.m_timeout_seconds = timeout_seconds

        def get_terminal(self, terminal_id: str) -> SimpleNamespace:
            raise RuntimeError(f"terminal lookup failed for {terminal_id}")

        def get_terminal_output(self, terminal_id: str, mode: str = "last") -> SimpleNamespace:
            raise RuntimeError(f"output lookup failed for {terminal_id} ({mode})")

    monkeypatch.setattr(demo_commands, "CaoRestClient", FailingCaoRestClient)

    inspect_demo(paths=paths, as_json=False, output_text_tail_chars=80)

    output = capsys.readouterr().out
    assert "Interactive CAO Demo Inspect" in output
    assert "Session Summary" in output
    assert "session_status: active" in output
    assert "tool_state: unknown" in output
    assert "Commands" in output
    assert "tmux_attach: tmux attach -t AGENTSYS-demo" in output
    assert (
        "terminal_log_tail: tail -f "
        f"{paths.workspace_root / '.aws' / 'cli-agent-orchestrator' / 'logs' / 'terminal' / 'term-001.log'}"
    ) in output
    assert "Output Text Tail (last 80 chars)" in output
    assert "clean projected Claude dialog tail unavailable" in output


def test_send_turn_fails_on_empty_response_but_still_writes_turn_artifact(
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)
    _seed_state(paths, active=True, turn_count=0)

    def _runner(
        command: list[str],
        cwd: Path,
        stdout_path: Path,
        stderr_path: Path,
        timeout_seconds: float,
    ) -> CommandResult:
        stdout = json.dumps({"kind": "done", "message": ""})
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return CommandResult(
            args=tuple(command),
            returncode=0,
            stdout=stdout,
            stderr="",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

    with pytest.raises(DemoWorkflowError, match="empty response"):
        send_turn(
            paths=paths,
            env=env,
            prompt="empty please",
            run_command=_runner,
        )

    records = load_turn_records(paths.turns_dir)
    assert len(records) == 1
    assert records[0].response_text == ""


def test_stop_demo_marks_state_inactive_when_session_is_missing(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    env = _make_env(tmp_path)
    _seed_state(paths, active=True)

    def _runner(
        command: list[str],
        cwd: Path,
        stdout_path: Path,
        stderr_path: Path,
        timeout_seconds: float,
    ) -> CommandResult:
        stderr = "error: Agent not found: tmux session `AGENTSYS-demo` does not exist."
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        return CommandResult(
            args=tuple(command),
            returncode=2,
            stdout="",
            stderr=stderr,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

    payload = stop_demo(
        paths=paths,
        env=env,
        run_command=_runner,
    )

    state = load_demo_state(paths.state_path)
    assert state is not None
    assert state.active is False
    assert payload["stop_result"]["stale_session_tolerated"] is True


def test_verify_demo_requires_reused_agent_identity_across_two_turns(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    _seed_state(paths, active=False, turn_count=2)
    paths.turns_dir.mkdir(parents=True, exist_ok=True)

    first = _turn_record(paths, turn_index=1, response_text="one")
    second = _turn_record(paths, turn_index=2, response_text="two")
    (paths.turns_dir / "turn-001.json").write_text(
        first.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    (paths.turns_dir / "turn-002.json").write_text(
        second.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    report = verify_demo(paths=paths)

    assert report.status == "ok"
    assert report.tool == "claude"
    assert report.variant_id == "claude-gpu-kernel-coder-default"
    assert report.brain_recipe == "claude/gpu-kernel-coder-default"
    assert report.turn_count == 2
    assert report.unique_agent_identity_count == 1
    assert report.terminal_id == "term-001"
    assert [turn.turn_index for turn in report.turns] == [1, 2]


def test_verify_demo_resolves_terminal_log_path_from_launcher_home(tmp_path: Path) -> None:
    paths = _make_paths(tmp_path)
    launcher_home_dir = tmp_path / "custom-launcher-home"
    _seed_state(
        paths,
        active=False,
        launcher_home_dir=launcher_home_dir,
        terminal_log_path="~/.aws/cli-agent-orchestrator/logs/terminal/term-001.log",
        turn_count=2,
    )
    paths.turns_dir.mkdir(parents=True, exist_ok=True)

    first = _turn_record(paths, turn_index=1, response_text="one")
    second = _turn_record(paths, turn_index=2, response_text="two")
    (paths.turns_dir / "turn-001.json").write_text(
        first.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    (paths.turns_dir / "turn-002.json").write_text(
        second.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    report = verify_demo(paths=paths)

    assert report.terminal_log_path == str(
        launcher_home_dir / ".aws" / "cli-agent-orchestrator" / "logs" / "terminal" / "term-001.log"
    )
