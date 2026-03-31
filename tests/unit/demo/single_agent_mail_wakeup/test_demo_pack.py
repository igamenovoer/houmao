from __future__ import annotations

from pathlib import Path

import pytest

from houmao.demo.single_agent_mail_wakeup import driver, reporting, runtime
from houmao.demo.single_agent_mail_wakeup.models import DemoState, DeliveryState, build_demo_layout


def test_build_demo_layout_includes_project_overlay_and_runtime_roots(tmp_path: Path) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs/claude")

    assert paths.project_dir == (tmp_path / "outputs/claude/project").resolve()
    assert paths.overlay_dir == (tmp_path / "outputs/claude/overlay").resolve()
    assert paths.runtime_root == (tmp_path / "outputs/claude/runtime").resolve()
    assert paths.registry_root == (tmp_path / "outputs/claude/registry").resolve()
    assert paths.jobs_root == (tmp_path / "outputs/claude/jobs").resolve()
    assert paths.control_dir == (tmp_path / "outputs/claude/control").resolve()


def test_build_demo_environment_exports_overlay_runtime_registry_and_jobs(tmp_path: Path) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs/codex")

    env = runtime.build_demo_environment(paths=paths, base_env={})

    assert env["HOUMAO_PROJECT_OVERLAY_DIR"] == str(paths.overlay_dir)
    assert env["AGENTSYS_AGENT_DEF_DIR"] == str((paths.overlay_dir / "agents").resolve())
    assert env["AGENTSYS_GLOBAL_RUNTIME_DIR"] == str(paths.runtime_root)
    assert env["AGENTSYS_GLOBAL_REGISTRY_DIR"] == str(paths.registry_root)
    assert env["AGENTSYS_LOCAL_JOBS_DIR"] == str(paths.jobs_root)


def test_import_project_auth_from_fixture_shapes_claude_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    fixture_root = repo_root / "fixtures/claude/kimi-coding"
    (fixture_root / "env").mkdir(parents=True)
    (fixture_root / "files").mkdir(parents=True)
    (fixture_root / "env/vars.env").write_text(
        "ANTHROPIC_API_KEY=sk-test\nANTHROPIC_BASE_URL=https://claude.example.test\n",
        encoding="utf-8",
    )
    (fixture_root / "files/claude_state.template.json").write_text("{}\n", encoding="utf-8")
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs/claude")
    paths.project_dir.mkdir(parents=True)

    captured: dict[str, object] = {}

    def fake_run_json_command(command: object, **kwargs: object) -> dict[str, object]:
        captured["command"] = command
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime, "run_json_command", fake_run_json_command)

    runtime.import_project_auth_from_fixture(
        paths=paths,
        env={},
        tool="claude",
        tool_parameters=type(
            "_Tool",
            (),
            {
                "auth_fixture_dir": Path("fixtures/claude/kimi-coding"),
                "auth_name": "kimi-coding",
            },
        )(),
        repo_root=repo_root,
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert command[:8] == [
        "pixi",
        "run",
        "houmao-mgr",
        "project",
        "agents",
        "tools",
        "claude",
        "auth",
    ]
    assert "--name" in command
    assert "kimi-coding" in command
    assert "--api-key" in command
    assert "sk-test" in command
    assert "--base-url" in command
    assert "https://claude.example.test" in command
    assert "--state-template-file" in command


def test_import_project_auth_from_fixture_shapes_codex_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    fixture_root = repo_root / "fixtures/codex/yunwu-openai"
    (fixture_root / "env").mkdir(parents=True)
    (fixture_root / "files").mkdir(parents=True)
    (fixture_root / "env/vars.env").write_text(
        "OPENAI_API_KEY=sk-openai\nOPENAI_BASE_URL=https://api.example.test/v1\nOPENAI_ORG_ID=org-demo\n",
        encoding="utf-8",
    )
    (fixture_root / "files/auth.json").write_text("{\"logged_in\": true}\n", encoding="utf-8")
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs/codex")
    paths.project_dir.mkdir(parents=True)

    captured: dict[str, object] = {}

    def fake_run_json_command(command: object, **kwargs: object) -> dict[str, object]:
        captured["command"] = command
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime, "run_json_command", fake_run_json_command)

    runtime.import_project_auth_from_fixture(
        paths=paths,
        env={},
        tool="codex",
        tool_parameters=type(
            "_Tool",
            (),
            {
                "auth_fixture_dir": Path("fixtures/codex/yunwu-openai"),
                "auth_name": "yunwu-openai",
            },
        )(),
        repo_root=repo_root,
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert "--api-key" in command
    assert "sk-openai" in command
    assert "--base-url" in command
    assert "https://api.example.test/v1" in command
    assert "--org-id" in command
    assert "org-demo" in command
    assert "--auth-json" in command


def test_driver_parser_accepts_supported_command_surface() -> None:
    parser = driver._build_parser()  # type: ignore[attr-defined]

    assert parser.parse_args(["start", "--tool", "claude"]).command == "start"
    assert parser.parse_args(["send"]).command == "send"
    assert parser.parse_args(["manual-send"]).command == "manual-send"
    assert parser.parse_args(["attach"]).command == "attach"
    assert parser.parse_args(["watch-gateway"]).command == "watch-gateway"
    assert parser.parse_args(["watch-gateway", "--follow"]).command == "watch-gateway"
    notifier_args = parser.parse_args(["notifier", "status"])
    assert notifier_args.command == "notifier"
    assert notifier_args.notifier_command == "status"
    notifier_on_args = parser.parse_args(["notifier", "on", "--seconds", "2"])
    assert notifier_on_args.notifier_command == "on"
    assert notifier_on_args.seconds == 2
    notifier_interval_args = parser.parse_args(["notifier", "set-interval", "--seconds", "5"])
    assert notifier_interval_args.notifier_command == "set-interval"
    assert notifier_interval_args.seconds == 5
    assert parser.parse_args(["inspect"]).command == "inspect"
    assert parser.parse_args(["verify"]).command == "verify"
    assert parser.parse_args(["stop"]).command == "stop"
    assert parser.parse_args(["auto", "--tool", "codex"]).command == "auto"
    assert parser.parse_args(["matrix"]).command == "matrix"


def test_attach_gateway_can_request_foreground_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs/claude")
    paths.project_dir.mkdir(parents=True)

    captured: dict[str, object] = {}

    def fake_run_json_command(command: object, **kwargs: object) -> dict[str, object]:
        captured["command"] = command
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime, "run_json_command", fake_run_json_command)

    runtime.attach_gateway(
        paths=paths,
        env={},
        agent_name="single-mail-claude-demo",
        timeout_seconds=30.0,
        foreground=True,
    )

    command = captured["command"]
    assert command == [
        "pixi",
        "run",
        "houmao-mgr",
        "agents",
        "gateway",
        "attach",
        "--agent-name",
        "single-mail-claude-demo",
        "--foreground",
    ]


def test_capture_gateway_console_uses_authoritative_gateway_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs/claude")
    paths.project_dir.mkdir(parents=True)

    monkeypatch.setattr(
        runtime,
        "gateway_status",
        lambda **kwargs: {
            "tmux_session_name": "hm-single-mail-claude-demo",
            "gateway_tmux_window_index": 2,
        },
    )
    monkeypatch.setattr(
        runtime,
        "resolve_tmux_pane",
        lambda **kwargs: type("_Pane", (), {"pane_id": "%42"})(),
    )
    monkeypatch.setattr(
        runtime,
        "capture_tmux_pane",
        lambda **kwargs: "line-1\nline-2\nline-3\n",
    )

    payload = runtime.capture_gateway_console(
        paths=paths,
        env={},
        agent_name="single-mail-claude-demo",
        fallback_session_name="fallback-session",
        timeout_seconds=30.0,
        lines=2,
    )

    assert payload["session_name"] == "hm-single-mail-claude-demo"
    assert payload["window_index"] == "2"
    assert payload["pane_id"] == "%42"
    assert payload["text"] == "line-2\nline-3\n"


def test_report_contract_accepts_structural_project_mailbox_without_read_state(tmp_path: Path) -> None:
    output_root = (tmp_path / "outputs/claude").resolve()
    project_root = output_root / "project"
    overlay_root = output_root / "overlay"
    session_root = output_root / "runtime/session-1"
    output_file_path = project_root / "tmp/single-agent-mail-wakeup/processed-demo.md"
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    output_file_path.write_text("single-agent-mail-wakeup demo\n", encoding="utf-8")
    (project_root / "skills/mailbox").mkdir(parents=True, exist_ok=True)
    (project_root / ".houmao-demo-project.json").write_text("{}\n", encoding="utf-8")

    delivery = DeliveryState(
        delivery_index=1,
        subject="Single-agent mail wake-up demo demo",
        message_id="msg-20260331T000000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        thread_id="msg-20260331T000000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        created_at_utc="2026-03-31T00:00:00Z",
        staged_message_path=overlay_root / "mailbox/staging/message.md",
        payload_path=output_root / "deliveries/payloads/delivery-001.json",
        delivery_artifact_path=output_root / "deliveries/delivery-001.json",
        message_ref="filesystem:msg-20260331T000000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        unread_observed_at_utc="2026-03-31T00:00:02Z",
        completed_at_utc="2026-03-31T00:00:10Z",
        observation_source="manager_direct",
    )
    state = DemoState(
        created_at_utc="2026-03-31T00:00:00Z",
        repo_root=tmp_path.resolve(),
        output_root=output_root,
        selected_tool="claude",
        provider="claude_code",
        setup_name="default",
        run_id="single-agent-mail-wakeup-20260331T000000Z-demo",
        project_fixture=tmp_path / "fixture",
        project_workdir=project_root,
        overlay_root=overlay_root,
        agent_def_dir=overlay_root / "agents",
        specialist_name="single-mail-claude-demo",
        instance_name="single-mail-claude-demo",
        session_name="hm-single-mail-claude-demo",
        auth_bundle_name="kimi-coding",
        brain_manifest_path=session_root / "brain/manifest.json",
        brain_home_path=session_root / "brain/home",
        launch_helper_path=session_root / "brain/launch.sh",
        session_manifest_path=session_root / "manifest.json",
        session_root=session_root,
        tracked_agent_id="tracked-demo",
        agent_name="single-mail-claude-demo",
        agent_id="agent-demo",
        tmux_session_name="tmux-demo",
        mailbox_principal_id="single-mail-claude-demo",
        mailbox_address="single-mail-claude-demo@agents.localhost",
        operator_principal_id="operator",
        operator_address="operator@agents.localhost",
        gateway_root=session_root / "gateway",
        gateway_host="127.0.0.1",
        gateway_port=9911,
        notifier_interval_seconds=5,
        ready_timeout_seconds=180.0,
        output_timeout_seconds=180.0,
        output_file_path=output_file_path,
        output_file_expected_content="single-agent-mail-wakeup demo",
        deliveries=[delivery],
    )

    inspect_snapshot = {
        "gateway": {
            "status": {"gateway_health": "healthy"},
            "notifier": {"enabled": True},
            "audit_summary": {"has_enqueued": True, "has_poll_error": False},
            "queue_state": {"has_notifier_request": True, "has_completed_notifier_request": True},
        },
        "actor_mail": {
            "check": {
                "message_count": 1,
                "messages": [
                    {
                        "message_ref": "filesystem:msg-20260331T000000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        "unread": False,
                    }
                ],
            },
            "unread_check": {"unread_count": 0},
        },
        "project_mailbox": {
            "list": {
                "messages": [
                    {
                        "message_id": "msg-20260331T000000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        "projection_path": "mailboxes/single/inbox/message.md",
                        "canonical_path": "messages/msg-20260331T000000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.md",
                    }
                ]
            },
            "message": {
                "message": {
                    "message_id": "msg-20260331T000000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "projection_path": "mailboxes/single/inbox/message.md",
                    "canonical_path": "messages/msg-20260331T000000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.md",
                }
            },
        },
        "output_file": {
            "exists": True,
            "matches_expected_content": True,
            "modified_after_delivery": True,
        },
        "ownership": {
            "output_root_pack_local": True,
            "project_root_within_output_root": True,
            "overlay_root_within_output_root": True,
            "runtime_root_within_output_root": True,
            "output_file_within_project_root": True,
        },
        "project": {
            "visible_mailbox_skill_surface_present": True,
            "managed_project_metadata_present": True,
        },
        "specialist": {"launch": {"prompt_mode": "unattended"}},
        "instance": {"name": "single-mail-claude-demo"},
    }

    report = reporting.build_report_snapshot(state=state, inspect_snapshot=inspect_snapshot)

    assert report["outcome"]["status"] == "complete"
    reporting.validate_report_contract(report)
    assert report["structural_mailbox_evidence"]["delivered_message_visible"] is True


def test_sanitize_report_normalizes_delivery_subject_run_token() -> None:
    sanitized = reporting.sanitize_report(
        {
            "deliveries": [
                {
                    "subject": "Single-agent mail wake-up demo e72b254f",
                    "message_id": "msg-20260331T060421Z-f8a1b0ce96c44bebaa431c78141ac216",
                    "thread_id": "msg-20260331T060421Z-f8a1b0ce96c44bebaa431c78141ac216",
                }
            ]
        }
    )

    assert sanitized == {
        "deliveries": [
            {
                "subject": "Single-agent mail wake-up demo <RUN_ID>",
                "message_id": "<MESSAGE_ID>",
                "thread_id": "<THREAD_ID>",
            }
        ]
    }
