"""Integration coverage for the Houmao-server interactive demo CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import houmao.demo.houmao_server_interactive_full_pipeline_demo.cli as demo_cli
import houmao.demo.houmao_server_interactive_full_pipeline_demo.commands as demo_commands
from houmao.agents.realm_controller.boundary_models import HoumaoServerSectionV1
from houmao.server.models import (
    HoumaoHeadlessLaunchResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentRequestAcceptedResponse,
)


def _managed_snapshot(*, result: str, turn_index: int | None) -> demo_commands.ManagedAgentSnapshot:
    """Build one managed-agent snapshot for integration assertions."""

    return demo_commands.ManagedAgentSnapshot(
        tracked_agent_id="tracked-alice",
        transport="tui",
        tool="claude",
        session_name="alice",
        terminal_id="term-1",
        manifest_path="/tmp/runtime/sessions/houmao_server_rest/alice/manifest.json",
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


def test_cli_end_to_end_workflow_uses_demo_owned_server_state_and_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should drive start, inspect, prompt, verify, and stop end-to-end."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    agent_def_dir = (
        repo_root
        / "scripts"
        / "demo"
        / "houmao-server-interactive-full-pipeline-demo"
        / "agents"
    )
    fixture_agent_def_dir = repo_root / "tests" / "fixtures" / "agents"
    fixture_agent_def_dir.mkdir(parents=True, exist_ok=True)
    agent_def_dir.parent.mkdir(parents=True, exist_ok=True)
    agent_def_dir.symlink_to(Path("..") / ".." / ".." / "tests" / "fixtures" / "agents")

    calls: dict[str, list[str]] = {"submit_refs": [], "deleted_sessions": []}
    bundle_plan: list[dict[str, str]] = []

    def _fake_fetch_live_bundle(**kwargs: object) -> dict[str, str]:
        del kwargs
        if bundle_plan:
            return bundle_plan.pop(0)
        return {"state": "after", "detail": "after", "history": "after", "terminal": "after"}

    def _fake_managed_agent_snapshot(**kwargs: object) -> demo_commands.ManagedAgentSnapshot:
        state_payload = kwargs["state_response"]
        return (
            _managed_snapshot(result="none", turn_index=None)
            if state_payload == "before"
            else _managed_snapshot(result="success", turn_index=1)
        )

    def _fake_history_snapshot(payload: object) -> demo_commands.ManagedAgentHistorySnapshot:
        return _history_snapshot(count=0 if payload == "before" else 1)

    def _fake_terminal_snapshot(payload: object) -> demo_commands.TerminalSnapshot:
        return _terminal_snapshot(result="none" if payload == "before" else "success")

    class _FakeClient:
        def __init__(
            self,
            base_url: str,
            timeout_seconds: float = 5.0,
            create_timeout_seconds: float = 90.0,
        ) -> None:
            del base_url, timeout_seconds, create_timeout_seconds

        def submit_managed_agent_request(
            self, agent_ref: str, request_model: object
        ) -> HoumaoManagedAgentRequestAcceptedResponse:
            calls["submit_refs"].append(agent_ref)
            request_kind = getattr(request_model, "request_kind")
            return HoumaoManagedAgentRequestAcceptedResponse(
                success=True,
                tracked_agent_id="tracked-alice",
                request_id=f"mreq-{len(calls['submit_refs'])}",
                request_kind=request_kind,
                disposition="accepted",
                detail="accepted",
                headless_turn_id=None,
                headless_turn_index=None,
            )

        def stop_managed_agent(self, agent_ref: str) -> object:
            calls["deleted_sessions"].append(agent_ref)
            return type("StopResponse", (), {"success": True})()

        def delete_session(self, session_name: str) -> object:
            calls["deleted_sessions"].append(session_name)
            return type("DeleteResponse", (), {"success": True})()

    # Native headless launch mock - returns synchronously without polling
    def _fake_launch_native_session(
        *,
        client: object,
        provider: str,
        requested_session_name: str | None,
        workdir: Path,
        runtime_root: Path,
    ) -> HoumaoHeadlessLaunchResponse:
        session_name = requested_session_name or "alice"
        manifest_path = runtime_root / "sessions" / "houmao_server_rest" / session_name / "manifest.json"
        session_root = runtime_root / "sessions" / "houmao_server_rest" / session_name
        return HoumaoHeadlessLaunchResponse(
            success=True,
            detail="Native headless launch successful",
            tracked_agent_id="tracked-alice",
            identity=HoumaoManagedAgentIdentity(
                tracked_agent_id="tracked-alice",
                transport="tui",
                tool="claude",
                session_name=session_name,
                terminal_id="term-1",
                runtime_session_id=None,
                tmux_session_name=session_name,
                tmux_window_name="gpu-kernel-coder",
                manifest_path=str(manifest_path),
                session_root=str(session_root),
                agent_name=session_name,
                agent_id=f"AGENTSYS-{session_name}",
            ),
            manifest_path=str(manifest_path),
            session_root=str(session_root),
        )

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
        "_start_server_process",
        lambda **kwargs: type("Proc", (), {"pid": 4242})(),
    )
    monkeypatch.setattr(demo_commands, "_launch_native_session", _fake_launch_native_session)
    monkeypatch.setattr(
        demo_commands,
        "_load_manifest_bridge",
        lambda path: HoumaoServerSectionV1(
            api_base_url="http://127.0.0.1:19989",
            session_name="alice",
            terminal_id="term-1",
            parsing_mode="shadow_only",
            tmux_window_name="gpu-kernel-coder",
            turn_index=0,
        ),
    )
    monkeypatch.setattr(demo_commands, "HoumaoServerClient", _FakeClient)
    monkeypatch.setattr(demo_commands, "_fetch_live_bundle", _fake_fetch_live_bundle)
    monkeypatch.setattr(demo_commands, "_managed_agent_snapshot", _fake_managed_agent_snapshot)
    monkeypatch.setattr(demo_commands, "_history_snapshot", _fake_history_snapshot)
    monkeypatch.setattr(demo_commands, "_terminal_snapshot", _fake_terminal_snapshot)
    monkeypatch.setattr(
        demo_commands,
        "_dialog_tail_from_terminal_state",
        lambda **kwargs: "tail excerpt",
    )
    monkeypatch.setattr(
        demo_commands,
        "_wait_for_session_absent",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        demo_commands,
        "_best_effort_kill_tmux_session",
        lambda session_name: None,
    )
    monkeypatch.setattr(
        demo_commands,
        "_stop_server_process",
        lambda **kwargs: {"status": "stopped", "pid": 4242},
    )

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

    # Native launch uses session name directly (no cao- prefix)
    assert inspect_payload["managed_agent"]["tracked_agent_id"] == "tracked-alice"
    assert turn_payload["request_kind"] == "submit_prompt"
    assert verify_payload["status"] == "ok"
    assert verify_payload["accepted_prompt_count"] == 1
    assert report["current_managed_agent"]["last_turn_result"] == "success"
    assert state["agent_def_dir"] == str(agent_def_dir)
    assert state["active"] is False
    assert stop_payload["server_stop_status"] == "stopped"
    assert calls["submit_refs"] == ["alice"]
    assert calls["deleted_sessions"] == ["alice"]
