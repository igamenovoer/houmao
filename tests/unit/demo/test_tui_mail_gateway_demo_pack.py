"""Unit tests for the TUI mail gateway demo pack."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import houmao.demo.tui_mail_gateway_demo_pack.driver as demo_driver
import houmao.demo.tui_mail_gateway_demo_pack.runtime as demo_runtime
from houmao.agents.brain_builder import BuildResult
from houmao.demo.tui_mail_gateway_demo_pack.models import (
    DemoState,
    TurnState,
    build_demo_layout,
    default_demo_output_dir,
    load_demo_parameters,
    load_demo_state,
    save_demo_state,
)


PACK_DIR = Path(__file__).resolve().parents[3] / "scripts" / "demo" / "tui-mail-gateway-demo-pack"


def _repo_root() -> Path:
    """Return the repository root for this test module."""

    return Path(__file__).resolve().parents[3]


def _make_state(
    paths, *, tool: str = "codex", active: bool = True, turns: list[TurnState] | None = None
) -> DemoState:
    """Create one representative persisted demo state."""

    for directory in (
        paths.control_dir,
        paths.logs_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.mailbox_root,
        paths.jobs_root,
        paths.deliveries_dir,
        paths.project_dir,
        paths.evidence_dir,
        paths.cao_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return DemoState(
        active=active,
        created_at_utc="2026-03-23T18:00:00+00:00",
        stopped_at_utc=None if active else "2026-03-23T18:10:00+00:00",
        repo_root=_repo_root(),
        output_root=paths.output_root,
        selected_tool=tool,
        run_id="tui-mail-gateway-20260323T180000Z-deadbeef",
        agent_def_dir=_repo_root() / "tests" / "fixtures" / "agents",
        project_fixture=_repo_root()
        / "tests"
        / "fixtures"
        / "dummy-projects"
        / "mailbox-demo-python",
        project_workdir=paths.project_dir,
        blueprint_path=_repo_root()
        / "tests"
        / "fixtures"
        / "agents"
        / "blueprints"
        / f"mailbox-demo-{tool}.yaml",
        brain_manifest_path=paths.runtime_root / "manifests" / "brain.json",
        brain_home_path=paths.runtime_root / "homes" / tool,
        launch_helper_path=paths.runtime_root / "homes" / tool / "launch.sh",
        session_manifest_path=paths.runtime_root / "sessions" / "demo" / "manifest.json",
        session_root=paths.runtime_root / "sessions" / "demo",
        agent_identity=f"AGENTSYS-tui-mail-gateway-{tool}",
        agent_name=f"AGENTSYS-tui-mail-gateway-{tool}",
        agent_id=f"agent-{tool}",
        tmux_session_name=f"tmux-{tool}",
        terminal_id="terminal-1",
        mailbox_principal_id=f"AGENTSYS-tui-mail-gateway-{tool}",
        mailbox_address=f"AGENTSYS-tui-mail-gateway-{tool}@agents.localhost",
        gateway_root=paths.runtime_root / "sessions" / "demo" / "gateway",
        gateway_host="127.0.0.1",
        gateway_port=43123,
        cao_base_url="http://127.0.0.1:9889",
        cao_profile_store=paths.cao_home_dir / ".aws" / "cli-agent-orchestrator" / "agent-store",
        launcher_config_path=paths.launcher_config_path,
        cadence_seconds=5,
        turn_limit=3,
        drive_timeout_seconds=60,
        notifier_interval_seconds=1,
        turns=list(turns or []),
    )


def test_tracked_parameters_and_default_output_roots_match_the_documented_contract() -> None:
    """The tracked inputs should expose the documented tool and drive defaults."""

    parameters = load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")

    assert parameters.project_fixture == Path("tests/fixtures/dummy-projects/mailbox-demo-python")
    assert parameters.tools["claude"].blueprint == Path(
        "tests/fixtures/agents/roles/mailbox-demo/presets/claude/default.yaml"
    )
    assert parameters.tools["codex"].blueprint == Path(
        "tests/fixtures/agents/roles/mailbox-demo/presets/codex/default.yaml"
    )
    assert parameters.drive.cadence_seconds == 5
    assert parameters.drive.turn_limit == 3
    assert (
        default_demo_output_dir(repo_root=_repo_root(), tool="claude")
        == (
            _repo_root() / "scripts" / "demo" / "tui-mail-gateway-demo-pack" / "outputs" / "claude"
        ).resolve()
    )


def test_start_demo_persists_selected_tool_and_output_root_containment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup should require a selected tool and redirect owned state under one output root."""

    parameters = load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    override_agent_def_dir = tmp_path / "custom-agents"
    override_agent_def_dir.mkdir()

    recorded: dict[str, object] = {}

    monkeypatch.setenv("AGENT_DEF_DIR", str(override_agent_def_dir))
    monkeypatch.setattr(
        demo_driver,
        "start_cao_service",
        lambda *, repo_root, paths, cao_base_url, timeout_seconds: {
            "base_url": cao_base_url,
            "healthy": True,
        },
    )
    monkeypatch.setattr(
        demo_driver,
        "resolve_demo_preset_launch",
        lambda *, agent_def_dir, preset_path: SimpleNamespace(role_name="mailbox-demo"),
    )

    def fake_build_brain(*, repo_root, paths, agent_def_dir, blueprint_path, env, timeout_seconds):
        recorded["agent_def_dir"] = agent_def_dir
        recorded["blueprint_path"] = blueprint_path
        recorded["env"] = dict(env)
        del repo_root, timeout_seconds
        return BuildResult(
            home_id="demo-home",
            home_path=paths.runtime_root / "homes" / "codex",
            manifest_path=paths.runtime_root / "manifests" / "brain.json",
            launch_helper_path=paths.runtime_root / "homes" / "codex" / "launch.sh",
            launch_preview="launch",
            manifest={},
        )

    monkeypatch.setattr(demo_driver, "build_brain", fake_build_brain)
    monkeypatch.setattr(
        demo_driver,
        "provision_project_workdir",
        lambda *, project_fixture, project_dir, allow_reprovision, build_result: project_dir,
    )
    monkeypatch.setattr(
        demo_driver,
        "start_mailbox_session",
        lambda **kwargs: {
            "session_manifest": str(paths.runtime_root / "sessions" / "demo" / "manifest.json"),
            "tool": "codex",
            "backend": "local_interactive",
        },
    )
    monkeypatch.setattr(
        demo_driver,
        "attach_gateway",
        lambda **kwargs: {
            "gateway_root": str(paths.runtime_root / "sessions" / "demo" / "gateway"),
            "gateway_host": "127.0.0.1",
            "gateway_port": 43123,
        },
    )
    monkeypatch.setattr(
        demo_driver,
        "load_session_details",
        lambda **kwargs: {
            "agent_identity": "AGENTSYS-tui-mail-gateway-codex",
            "agent_name": "AGENTSYS-tui-mail-gateway-codex",
            "agent_id": "agent-codex",
            "tmux_session_name": "tmux-codex",
            "terminal_id": "terminal-1",
            "session_root": paths.runtime_root / "sessions" / "demo",
        },
    )
    monkeypatch.setattr(demo_driver, "enable_notifier", lambda *, state: {"enabled": True})

    state = demo_driver._start_demo(
        repo_root=_repo_root(),
        paths=paths,
        parameters=parameters,
        tool="codex",
    )
    loaded = load_demo_state(paths.state_path)

    assert state.selected_tool == "codex"
    assert loaded.selected_tool == "codex"
    assert loaded.agent_def_dir == override_agent_def_dir.resolve()
    assert str(recorded["blueprint_path"]).endswith("roles/mailbox-demo/presets/codex/default.yaml")
    env = recorded["env"]
    assert env["AGENTSYS_GLOBAL_RUNTIME_DIR"] == str(paths.runtime_root)
    assert env["AGENTSYS_GLOBAL_REGISTRY_DIR"] == str(paths.registry_root)
    assert env["AGENTSYS_GLOBAL_MAILBOX_DIR"] == str(paths.mailbox_root)
    assert env["AGENTSYS_LOCAL_JOBS_DIR"] == str(paths.jobs_root)
    assert loaded.project_workdir == paths.project_dir.resolve()
    assert loaded.output_root == paths.output_root.resolve()


def test_drive_loop_honors_unread_gate_and_captures_turn_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive should inject only when unread is clear and persist per-turn evidence."""

    parameters = load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    state = _make_state(paths, tool="codex", active=True)
    save_demo_state(paths.state_path, state)

    delivered_ids: list[str] = []
    snapshots = iter(
        [
            {"state_source": "gateway", "message_count": 0, "unread_count": 1, "messages": []},
            {"state_source": "gateway", "message_count": 0, "unread_count": 0, "messages": []},
            {
                "state_source": "gateway",
                "message_count": 1,
                "unread_count": 1,
                "messages": [{"message_ref": "msg-1", "unread": True}],
            },
            {
                "state_source": "gateway",
                "message_count": 1,
                "unread_count": 0,
                "messages": [{"message_ref": "msg-1", "unread": False}],
            },
            {
                "state_source": "gateway",
                "message_count": 2,
                "unread_count": 1,
                "messages": [
                    {"message_ref": "msg-1", "unread": False},
                    {"message_ref": "msg-2", "unread": True},
                ],
            },
            {
                "state_source": "gateway",
                "message_count": 2,
                "unread_count": 0,
                "messages": [
                    {"message_ref": "msg-1", "unread": False},
                    {"message_ref": "msg-2", "unread": False},
                ],
            },
            {
                "state_source": "gateway",
                "message_count": 3,
                "unread_count": 1,
                "messages": [
                    {"message_ref": "msg-1", "unread": False},
                    {"message_ref": "msg-2", "unread": False},
                    {"message_ref": "msg-3", "unread": True},
                ],
            },
            {
                "state_source": "gateway",
                "message_count": 3,
                "unread_count": 0,
                "messages": [
                    {"message_ref": "msg-1", "unread": False},
                    {"message_ref": "msg-2", "unread": False},
                    {"message_ref": "msg-3", "unread": False},
                ],
            },
        ]
    )
    monkeypatch.setattr(demo_driver, "collect_mailbox_snapshot", lambda state: next(snapshots))
    monkeypatch.setattr(
        demo_driver,
        "collect_gateway_status",
        lambda state: {
            "request_admission": "open",
            "active_execution": "idle",
            "queue_depth": 0,
        },
    )

    def fake_deliver_turn_message(*, repo_root, paths, parameters, state, turn_index):
        del repo_root, paths, parameters, state
        message_id = f"msg-{turn_index}"
        delivered_ids.append(message_id)
        return TurnState(
            turn_index=turn_index,
            template_path=PACK_DIR / "inputs" / f"turn-{turn_index}.md",
            subject=f"turn {turn_index}",
            message_id=message_id,
            thread_id="thread-1",
            staged_message_path=tmp_path / f"staged-{turn_index}.md",
            payload_path=tmp_path / f"payload-{turn_index}.json",
            delivery_artifact_path=tmp_path / f"delivery-{turn_index}.json",
            delivered_at_utc="2026-03-23T18:00:00+00:00",
        )

    monkeypatch.setattr(demo_driver, "deliver_turn_message", fake_deliver_turn_message)

    def fake_capture_turn_evidence(*, paths, state, turn):
        del state
        snapshot_path = paths.evidence_dir / f"turn-{turn.turn_index:03d}.txt"
        tail_path = paths.evidence_dir / f"turn-{turn.turn_index:03d}.tail.txt"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text("snapshot\n", encoding="utf-8")
        tail_path.write_text("tail\n", encoding="utf-8")
        return turn.model_copy(
            update={
                "evidence_snapshot_path": snapshot_path,
                "evidence_tail_path": tail_path,
                "evidence_collected_at_utc": "2026-03-23T18:00:05+00:00",
            }
        )

    monkeypatch.setattr(demo_driver, "capture_turn_evidence", fake_capture_turn_evidence)
    monkeypatch.setattr(demo_driver.time, "sleep", lambda _: None)

    updated = demo_driver._drive_demo(
        repo_root=_repo_root(),
        paths=paths,
        parameters=parameters,
        timeout_seconds=30,
    )

    assert delivered_ids == ["msg-1", "msg-2", "msg-3"]
    assert updated.delivery_count == 3
    assert updated.processed_turn_count == 3
    assert all(turn.evidence_snapshot_path is not None for turn in updated.turns)
    assert all(turn.evidence_tail_path is not None for turn in updated.turns)


def test_verify_builds_the_sanitized_report_contract(tmp_path: Path) -> None:
    """Verify should write the expected sanitized report for a successful run."""

    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    turns = [
        TurnState(
            turn_index=index,
            template_path=PACK_DIR / "inputs" / f"turn-{index}.md",
            subject=f"turn {index}",
            message_id=f"msg-{index}",
            thread_id="thread-1",
            staged_message_path=tmp_path / f"staged-{index}.md",
            payload_path=tmp_path / f"payload-{index}.json",
            delivery_artifact_path=tmp_path / f"delivery-{index}.json",
            delivered_at_utc="2026-03-23T18:00:00+00:00",
            unread_observed_at_utc="2026-03-23T18:00:01+00:00",
            read_observed_at_utc="2026-03-23T18:00:02+00:00",
            mailbox_state_source="gateway",
            evidence_snapshot_path=tmp_path / f"snapshot-{index}.txt",
            evidence_tail_path=tmp_path / f"tail-{index}.txt",
            evidence_collected_at_utc="2026-03-23T18:00:03+00:00",
        )
        for index in (1, 2, 3)
    ]
    state = _make_state(paths, tool="codex", active=True, turns=turns)
    save_demo_state(paths.state_path, state)
    expected_path = tmp_path / "expected-report.json"

    def fake_inspect_demo(*, paths):
        del paths
        return {
            "mailbox": {
                "state_source": "gateway",
                "message_count": 3,
                "unread_count": 0,
                "messages": [],
            },
            "gateway": {
                "notifier": {"enabled": True},
                "audit_summary": {
                    "row_count": 5,
                    "enqueued_mail_work": True,
                    "poll_errors_present": False,
                    "last_outcome": "enqueued",
                },
            },
        }

    original_inspect = demo_driver._inspect_demo
    demo_driver._inspect_demo = fake_inspect_demo
    try:
        demo_driver._verify_demo(
            repo_root=_repo_root(),
            paths=paths,
            expected_report=str(expected_path),
            snapshot=True,
        )
        demo_driver._verify_demo(
            repo_root=_repo_root(),
            paths=paths,
            expected_report=str(expected_path),
            snapshot=False,
        )
    finally:
        demo_driver._inspect_demo = original_inspect

    sanitized = json.loads(paths.sanitized_report_path.read_text(encoding="utf-8"))
    assert sanitized["config"]["selected_tool"] == "<TOOL>"
    assert sanitized["counts"]["processed_turns"] == 3
    assert sanitized["human_review_evidence"]["snapshot_count"] == 3
    assert "turn 1" not in json.dumps(sanitized)


def test_resolve_paths_without_tool_reuses_the_only_existing_default_state(tmp_path: Path) -> None:
    """Stepwise commands should reuse persisted state without repeating `--tool`."""

    codex_output = default_demo_output_dir(repo_root=tmp_path, tool="codex")
    paths = build_demo_layout(demo_output_dir=codex_output)
    save_demo_state(paths.state_path, _make_state(paths, tool="codex", active=True))

    resolved = demo_driver._resolve_paths(
        argparse_namespace := type("Args", (), {"demo_output_dir": None})(),
        repo_root=tmp_path,
        tool=None,
    )

    assert resolved.output_root == codex_output.resolve()
    del argparse_namespace


def test_stop_is_idempotent_and_preserves_existing_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stop should be repeatable and keep existing run artifacts on disk."""

    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    evidence_file = paths.evidence_dir / "turn-001" / "tmux-pane.txt"
    evidence_file.parent.mkdir(parents=True, exist_ok=True)
    evidence_file.write_text("snapshot\n", encoding="utf-8")
    save_demo_state(paths.state_path, _make_state(paths, tool="codex", active=True))

    monkeypatch.setattr(demo_driver, "collect_notifier_status", lambda state: {"enabled": True})
    monkeypatch.setattr(demo_runtime, "disable_notifier", lambda *, state: {"enabled": False})
    monkeypatch.setattr(
        demo_driver,
        "stop_session",
        lambda *, repo_root, paths, state, timeout_seconds: {"status": "ok"},
    )
    monkeypatch.setattr(
        demo_driver,
        "stop_cao_service",
        lambda *, repo_root, paths, timeout_seconds: {"status": "ok"},
    )

    first = demo_driver._stop_demo(repo_root=_repo_root(), paths=paths)
    second = demo_driver._stop_demo(repo_root=_repo_root(), paths=paths)
    updated = load_demo_state(paths.state_path)

    assert first["already_stopped"] is False
    assert second["already_stopped"] is True
    assert updated.active is False
    assert evidence_file.is_file()
