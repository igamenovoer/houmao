"""Unit tests for the interactive CAO full-pipeline demo workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gig_agents.demo.cao_interactive_full_pipeline_demo import (
    FIXED_CAO_BASE_URL,
    CommandResult,
    DemoEnvironment,
    DemoPaths,
    DemoState,
    DemoWorkflowError,
    TurnRecord,
    load_demo_state,
    load_turn_records,
    save_demo_state,
    send_turn,
    start_demo,
    stop_demo,
    verify_demo,
)


def _make_paths(tmp_path: Path) -> DemoPaths:
    return DemoPaths.from_workspace_root(tmp_path / "workspace")


def _make_env(tmp_path: Path) -> DemoEnvironment:
    repo_root = tmp_path / "repo"
    agent_def_dir = repo_root / "tests" / "fixtures" / "agents"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    return DemoEnvironment(
        repo_root=repo_root,
        agent_def_dir=agent_def_dir,
        launcher_home_dir=tmp_path / "launcher-home",
        workdir=repo_root,
        role_name="gpu-kernel-coder",
        config_profile="default",
        credential_profile="personal-a-default",
        skills=("openspec-apply-change",),
        timeout_seconds=30.0,
    )


def _seed_state(
    paths: DemoPaths,
    *,
    active: bool,
    agent_identity: str = "AGENTSYS-demo",
    turn_count: int = 0,
) -> None:
    state = DemoState(
        active=active,
        agent_identity=agent_identity,
        session_manifest=str(paths.runtime_root / "sessions" / "cao_rest" / "session.json"),
        session_name=agent_identity,
        tmux_target=agent_identity,
        terminal_id="term-001",
        terminal_log_path="~/.aws/cli-agent-orchestrator/logs/terminal/term-001.log",
        runtime_root=str(paths.runtime_root),
        workspace_dir=str(paths.workspace_root),
        brain_home=str(paths.runtime_root / "brains" / "home"),
        brain_manifest=str(paths.runtime_root / "brains" / "brain.json"),
        cao_base_url=FIXED_CAO_BASE_URL,
        cao_profile_store=str(paths.workspace_root / ".aws" / "cli-agent-orchestrator" / "agent-store"),
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


class FakeRunner:
    def __init__(self, tmp_path: Path) -> None:
        self.m_tmp_path = tmp_path
        self.m_calls: list[tuple[str, ...]] = []

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
        module = command[4]
        subcommand = command[5]

        if module == "gig_agents.cao.tools.cao_server_launcher":
            if subcommand == "status":
                returncode = 1
            elif subcommand == "start":
                stdout = json.dumps(
                    {
                        "started_new_process": True,
                        "reused_existing_process": False,
                        "pid": 4242,
                    }
                )
        elif module == "gig_agents.agents.brain_launch_runtime":
            if subcommand == "build-brain":
                runtime_root = Path(self._argument_value(command, "--runtime-root"))
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
                session_manifest = runtime_root / "sessions" / "cao_rest" / "interactive-session.json"
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
    _seed_state(paths, active=True, agent_identity="AGENTSYS-old")
    runner = FakeRunner(tmp_path)

    monkeypatch.setattr(
        "gig_agents.demo.cao_interactive_full_pipeline_demo.shutil.which",
        lambda _: "/usr/bin/fake",
    )

    payload = start_demo(
        paths=paths,
        env=env,
        agent_name="demo",
        run_command=runner,
    )

    state = load_demo_state(paths.state_path)
    assert state is not None
    assert state.active is True
    assert state.agent_identity == "AGENTSYS-demo"
    assert state.cao_base_url == FIXED_CAO_BASE_URL
    assert payload["replaced_previous_agent_identity"] == "AGENTSYS-old"

    stop_call = next(call for call in runner.calls if "stop-session" in call)
    assert stop_call[5] == "stop-session"
    assert "--agent-identity" in stop_call
    assert stop_call[stop_call.index("--agent-identity") + 1] == "AGENTSYS-old"

    start_call = next(call for call in runner.calls if "start-session" in call)
    assert start_call[start_call.index("--cao-base-url") + 1] == FIXED_CAO_BASE_URL
    assert start_call[start_call.index("--agent-identity") + 1] == "AGENTSYS-demo"


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
    assert report.turn_count == 2
    assert report.unique_agent_identity_count == 1
    assert [turn.turn_index for turn in report.turns] == [1, 2]
