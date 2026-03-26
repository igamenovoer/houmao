"""Integration coverage for the interactive full-pipeline demo CLI."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import houmao.demo.houmao_server_interactive_full_pipeline_demo.cli as demo_cli
import houmao.demo.houmao_server_interactive_full_pipeline_demo.commands as demo_commands
from houmao.demo.houmao_server_interactive_full_pipeline_demo.models import DemoRequestRecord


def _managed_snapshot(*, result: str, turn_index: int | None) -> demo_commands.ManagedAgentSnapshot:
    """Build one managed-agent snapshot for integration assertions."""

    return demo_commands.ManagedAgentSnapshot(
        tracked_agent_id="tracked-alice",
        transport="tui",
        tool="claude",
        session_name="alice",
        terminal_id="term-1",
        manifest_path="/tmp/runtime/sessions/local_interactive/session-1/manifest.json",
        availability="available",
        turn_phase="ready",
        active_turn_id=None,
        last_turn_result=result,
        last_turn_id=None if turn_index is None else f"turn-{turn_index}",
        last_turn_index=turn_index,
        last_turn_updated_at_utc=None if turn_index is None else "2026-03-24T12:00:05+00:00",
        detail_transport="tui",
        terminal_state_route="/houmao/terminals/term-1/state",
        terminal_history_route="/houmao/terminals/term-1/history",
        parsed_surface_present=True,
        ready_posture="yes",
        stable=True,
        stable_for_seconds=1.0,
        can_accept_prompt_now=None,
        interruptible=None,
        diagnostic_count=0,
        gateway_queue_depth=None,
    )


def _history_snapshot(*, count: int) -> demo_commands.ManagedAgentHistorySnapshot:
    """Build one managed-agent history snapshot for integration assertions."""

    return demo_commands.ManagedAgentHistorySnapshot(
        entry_count=count,
        latest_recorded_at_utc="2026-03-24T12:00:05+00:00" if count else None,
        latest_summary="Turn completed." if count else None,
        latest_turn_phase="ready" if count else None,
        latest_last_turn_result="success" if count else None,
    )


def _terminal_snapshot(*, result: str) -> demo_commands.TerminalSnapshot:
    """Build one tracked-terminal snapshot for integration assertions."""

    return demo_commands.TerminalSnapshot(
        terminal_id="term-1",
        parser_family="shadow",
        availability="available",
        business_state="ready",
        input_mode="command",
        ui_context="conversation",
        parsed_surface_present=True,
        ready_posture="yes",
        turn_phase="ready",
        last_turn_result=result,
        stable=True,
        stable_for_seconds=1.0,
        recent_transition_count=2,
        probe_captured_text_length=80,
    )


def test_cli_end_to_end_workflow_uses_local_managed_agent_state_and_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should drive start, inspect, prompt, verify, and stop end-to-end."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    agent_def_dir = (
        repo_root / "scripts" / "demo" / "houmao-server-interactive-full-pipeline-demo" / "agents"
    )
    fixture_agent_def_dir = repo_root / "tests" / "fixtures" / "agents"
    fixture_agent_def_dir.mkdir(parents=True, exist_ok=True)
    agent_def_dir.parent.mkdir(parents=True, exist_ok=True)
    agent_def_dir.symlink_to(Path("..") / ".." / ".." / "tests" / "fixtures" / "agents")

    bundle_plan: list[dict[str, str]] = []
    request_counter = {"count": 0}

    monkeypatch.setattr(
        demo_commands,
        "_cleanup_existing_state_for_startup",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        demo_commands,
        "_provision_default_worktree",
        lambda **kwargs: (
            kwargs["paths"].workdir.mkdir(parents=True, exist_ok=True),
            (kwargs["paths"].workdir / ".git").write_text("gitdir: fake\n", encoding="utf-8"),
        ),
    )
    monkeypatch.setattr(
        demo_commands,
        "resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            agent_def_dir=agent_def_dir,
            tool="claude",
            role_name="coder",
            recipe=SimpleNamespace(
                tool="claude",
                skills=["demo-skill"],
                config_profile="default",
                credential_profile="default",
                launch_overrides=None,
                operator_prompt_mode=None,
                mailbox=None,
            ),
            recipe_path=agent_def_dir / "brains" / "brain-recipes" / "claude" / "demo.yaml",
        ),
    )
    monkeypatch.setattr(
        demo_commands,
        "build_brain_home",
        lambda request: SimpleNamespace(
            manifest_path=request.runtime_root / "brains" / "demo-home" / "manifest.json"
        ),
    )
    monkeypatch.setattr(
        demo_commands,
        "start_runtime_session",
        lambda **kwargs: SimpleNamespace(
            agent_identity=kwargs["agent_name"],
            agent_id="agent-id-alice",
            tmux_session_name=kwargs["tmux_session_name"] or "tmux-alice",
            manifest_path=kwargs["runtime_root"]
            / "sessions"
            / "local_interactive"
            / "session-1"
            / "manifest.json",
            launch_plan=SimpleNamespace(tool="claude"),
        ),
    )
    monkeypatch.setattr(demo_commands, "_wait_for_controller_launch_readiness", lambda **kwargs: None)
    monkeypatch.setattr(
        demo_commands,
        "_resolve_local_target",
        lambda state: SimpleNamespace(identity=SimpleNamespace(tracked_agent_id="tracked-alice")),
    )
    monkeypatch.setattr(
        demo_commands,
        "_fetch_live_bundle",
        lambda **kwargs: bundle_plan.pop(0),
    )
    monkeypatch.setattr(
        demo_commands,
        "_fetch_live_bundle_from_target",
        lambda **kwargs: bundle_plan.pop(0),
    )
    monkeypatch.setattr(demo_commands, "_managed_agent_snapshot", lambda **kwargs: (
        _managed_snapshot(result="none", turn_index=None)
        if kwargs["state_response"] == "before"
        else _managed_snapshot(result="success", turn_index=1)
    ))
    monkeypatch.setattr(
        demo_commands,
        "_history_snapshot",
        lambda payload: _history_snapshot(count=0 if payload == "before" else 1),
    )
    monkeypatch.setattr(
        demo_commands,
        "_terminal_snapshot",
        lambda payload: _terminal_snapshot(result="none" if payload == "before" else "success"),
    )
    monkeypatch.setattr(
        demo_commands,
        "_dialog_tail_from_terminal_state",
        lambda **kwargs: "tail excerpt",
    )

    def _fake_submit_request_record(**kwargs: object) -> DemoRequestRecord:
        request_counter["count"] += 1
        return DemoRequestRecord(
            request_id=f"mreq-{request_counter['count']}",
            request_kind=str(kwargs["request_kind"]),  # type: ignore[arg-type]
            tracked_agent_id="tracked-alice",
            detail="accepted",
            success=True,
            disposition="accepted" if kwargs["request_kind"] == "submit_prompt" else "action",
        )

    monkeypatch.setattr(demo_commands, "_submit_request_record", _fake_submit_request_record)
    monkeypatch.setattr(
        demo_commands,
        "_resume_local_controller",
        lambda state: SimpleNamespace(
            stop=lambda force_cleanup: SimpleNamespace(status="ok", detail="stopped")
        ),
    )
    monkeypatch.setattr(demo_commands, "_best_effort_kill_tmux_session", lambda session_name: None)
    monkeypatch.setattr(demo_commands, "_best_effort_cleanup_session_root", lambda session_root: None)

    assert (
        demo_cli.main(["--repo-root", str(repo_root), "start", "--session-name", "alice", "--json"])
        == 0
    )
    start_payload = json.loads(capsys.readouterr().out)
    workspace_root = Path(start_payload["state"]["workspace_dir"])

    bundle_plan[:] = [
        {"state": "after", "detail": "after", "history": "after", "terminal": "after"}
    ]
    assert demo_cli.main(["--repo-root", str(repo_root), "inspect", "--json"]) == 0
    inspect_payload = json.loads(capsys.readouterr().out)

    bundle_plan[:] = [
        {"state": "before", "detail": "before", "history": "before", "terminal": "before"},
        {"state": "after", "detail": "after", "history": "after", "terminal": "after"},
    ]
    assert demo_cli.main(["--repo-root", str(repo_root), "send-turn", "--prompt", "hello"]) == 0
    turn_payload = json.loads(capsys.readouterr().out)

    bundle_plan[:] = [
        {"state": "after", "detail": "after", "history": "after", "terminal": "after"}
    ]
    assert demo_cli.main(["--repo-root", str(repo_root), "verify"]) == 0
    verify_payload = json.loads(capsys.readouterr().out)

    assert demo_cli.main(["--repo-root", str(repo_root), "stop"]) == 0
    stop_payload = json.loads(capsys.readouterr().out)

    report = json.loads((workspace_root / "report.json").read_text(encoding="utf-8"))
    state = json.loads((workspace_root / "state.json").read_text(encoding="utf-8"))

    assert start_payload["state"]["agent_name"] == "alice"
    assert inspect_payload["managed_agent"]["tracked_agent_id"] == "tracked-alice"
    assert turn_payload["request_kind"] == "submit_prompt"
    assert turn_payload["request"]["request_id"] == "mreq-1"
    assert verify_payload["status"] == "ok"
    assert verify_payload["accepted_prompt_count"] == 1
    assert report["current_managed_agent"]["last_turn_result"] == "success"
    assert state["agent_def_dir"] == str(agent_def_dir)
    assert state["active"] is False
    assert stop_payload["stop_status"] == "stopped"
