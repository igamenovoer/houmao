from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.demo.single_agent_gateway_wakeup_headless import driver, reporting, runtime
from houmao.demo.single_agent_gateway_wakeup_headless.models import (
    DemoState,
    DeliveryState,
    build_demo_layout,
    load_demo_parameters,
)


def test_build_demo_layout_includes_project_overlay_and_runtime_roots(tmp_path: Path) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")

    assert paths.project_dir == (tmp_path / "outputs/project").resolve()
    assert paths.overlay_dir == (tmp_path / "outputs/overlay").resolve()
    assert paths.runtime_root == (tmp_path / "outputs/overlay/runtime").resolve()
    assert paths.registry_root == (tmp_path / "outputs/registry").resolve()
    assert paths.jobs_root == (tmp_path / "outputs/overlay/jobs").resolve()
    assert paths.control_dir == (tmp_path / "outputs/control").resolve()


def test_build_demo_environment_exports_overlay_and_registry_and_clears_root_overrides(
    tmp_path: Path,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")

    env = runtime.build_demo_environment(
        paths=paths,
        base_env={
            "HOUMAO_AGENT_DEF_DIR": "/tmp/legacy-agents",
            "HOUMAO_GLOBAL_RUNTIME_DIR": "/tmp/legacy-runtime",
            "HOUMAO_GLOBAL_MAILBOX_DIR": "/tmp/legacy-mailbox",
            "HOUMAO_LOCAL_JOBS_DIR": "/tmp/legacy-jobs",
            "HOUMAO_JOB_DIR": "/tmp/legacy-job-dir",
        },
    )

    assert env["HOUMAO_PROJECT_OVERLAY_DIR"] == str(paths.overlay_dir)
    assert env["HOUMAO_GLOBAL_REGISTRY_DIR"] == str(paths.registry_root)
    assert "HOUMAO_AGENT_DEF_DIR" not in env
    assert "HOUMAO_GLOBAL_RUNTIME_DIR" not in env
    assert "HOUMAO_GLOBAL_MAILBOX_DIR" not in env
    assert "HOUMAO_LOCAL_JOBS_DIR" not in env
    assert "HOUMAO_JOB_DIR" not in env


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
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
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
    assert command[:9] == [
        "pixi",
        "run",
        "houmao-mgr",
        "--print-json",
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
    (fixture_root / "files/auth.json").write_text('{"logged_in": true}\n', encoding="utf-8")
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
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


def test_import_project_auth_from_fixture_shapes_gemini_oauth_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    fixture_root = repo_root / "fixtures/gemini/personal-a-default"
    (fixture_root / "env").mkdir(parents=True)
    (fixture_root / "files").mkdir(parents=True)
    (fixture_root / "env/vars.env").write_text("GOOGLE_GENAI_USE_GCA=true\n", encoding="utf-8")
    (fixture_root / "files/oauth_creds.json").write_text(
        '{"refresh_token": "token"}\n',
        encoding="utf-8",
    )
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
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
        tool="gemini",
        tool_parameters=type(
            "_Tool",
            (),
            {
                "auth_fixture_dir": Path("fixtures/gemini/personal-a-default"),
                "auth_name": "personal-a-default",
            },
        )(),
        repo_root=repo_root,
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert command[:9] == [
        "pixi",
        "run",
        "houmao-mgr",
        "--print-json",
        "project",
        "agents",
        "tools",
        "gemini",
        "auth",
    ]
    assert "--name" in command
    assert "personal-a-default" in command
    assert "--oauth-creds" in command
    assert str((fixture_root / "files/oauth_creds.json").resolve()) in command


def test_import_project_auth_from_fixture_shapes_gemini_api_key_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    fixture_root = repo_root / "fixtures/gemini/api-key-a-default"
    (fixture_root / "env").mkdir(parents=True)
    (fixture_root / "files").mkdir(parents=True)
    (fixture_root / "env/vars.env").write_text(
        "GEMINI_API_KEY=sk-gemini\nGOOGLE_GEMINI_BASE_URL=https://gemini.example.test\n",
        encoding="utf-8",
    )
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
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
        tool="gemini",
        tool_parameters=type(
            "_Tool",
            (),
            {
                "auth_fixture_dir": Path("fixtures/gemini/api-key-a-default"),
                "auth_name": "api-key-a-default",
            },
        )(),
        repo_root=repo_root,
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert "--api-key" in command
    assert "sk-gemini" in command
    assert "--base-url" in command
    assert "https://gemini.example.test" in command


def test_import_project_auth_from_fixture_reuses_existing_bundle_with_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    fixture_root = repo_root / "fixtures/codex/yunwu-openai"
    (fixture_root / "env").mkdir(parents=True)
    (fixture_root / "files").mkdir(parents=True)
    (fixture_root / "env/vars.env").write_text(
        "OPENAI_API_KEY=sk-openai\nOPENAI_BASE_URL=https://api.example.test/v1\n",
        encoding="utf-8",
    )
    (fixture_root / "files/auth.json").write_text('{"logged_in": true}\n', encoding="utf-8")
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.project_dir.mkdir(parents=True)
    (paths.overlay_dir / "agents/tools/codex/auth/yunwu-openai").mkdir(parents=True, exist_ok=True)

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
    assert command[8] == "auth"
    assert command[9] == "set"


def test_driver_parser_accepts_supported_command_surface() -> None:
    parser = driver._build_parser()  # type: ignore[attr-defined]

    assert parser.parse_args(["start", "--tool", "claude"]).command == "start"
    assert parser.parse_args(["start", "--tool", "gemini"]).command == "start"
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
    assert parser.parse_args(["auto", "--tool", "gemini"]).command == "auto"
    assert parser.parse_args(["matrix"]).command == "matrix"


def test_tracked_demo_parameters_include_gemini_lane() -> None:
    parameters = load_demo_parameters(
        Path("scripts/demo/single-agent-gateway-wakeup-headless/inputs/demo_parameters.json")
    )

    assert set(parameters.tools.keys()) == {"claude", "codex", "gemini"}
    gemini = parameters.tool_parameters(tool="gemini")
    assert gemini.provider == "gemini_cli"
    assert gemini.auth_name == "personal-a-default"


def test_command_matrix_runs_all_supported_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    tool_calls: list[str] = []

    def fake_run_auto(**kwargs: object) -> None:
        tool = str(kwargs["tool"])
        paths = kwargs["paths"]
        tool_calls.append(tool)
        paths.control_dir.mkdir(parents=True, exist_ok=True)
        paths.report_path.write_text("{}\n", encoding="utf-8")
        paths.sanitized_report_path.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(driver, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(driver, "_load_parameters", lambda args, repo_root: object())
    monkeypatch.setattr(
        driver,
        "_resolve_paths",
        lambda args, repo_root, tool: build_demo_layout(demo_output_dir=tmp_path / f"outputs-{tool}"),
    )
    monkeypatch.setattr(driver, "_run_auto", fake_run_auto)

    args = driver._build_parser().parse_args(["matrix"])
    exit_code = driver._command_matrix(args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert tool_calls == ["claude", "codex", "gemini"]
    assert [item["tool"] for item in payload["results"]] == ["claude", "codex", "gemini"]


def test_attach_gateway_can_request_foreground_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
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
        "--print-json",
        "agents",
        "gateway",
        "attach",
        "--agent-name",
        "single-mail-claude-demo",
        "--foreground",
    ]


def test_launch_instance_uses_headless_project_easy_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.project_dir.mkdir(parents=True)

    captured: dict[str, object] = {}

    def fake_run_command(command: object, **kwargs: object) -> runtime.CommandResult:
        captured["command"] = command
        captured.update(kwargs)
        return runtime.CommandResult(
            args=tuple(str(part) for part in command),
            returncode=0,
            stdout='{"manifest_path": "/tmp/demo-manifest.json"}\n',
            stderr="",
            stdout_path=paths.logs_dir / "instance-launch.stdout",
            stderr_path=paths.logs_dir / "instance-launch.stderr",
        )

    monkeypatch.setattr(runtime, "run_command", fake_run_command)

    payload = runtime.launch_instance(
        paths=paths,
        env={},
        specialist_name="single-headless-mail-codex",
        instance_name="single-headless-mail-codex-demo",
        session_name="hm-single-headless-mail-codex-demo",
        mail_root=(paths.overlay_dir / "mailbox").resolve(),
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert command == [
        "pixi",
        "run",
        "houmao-mgr",
        "--print-json",
        "project",
        "easy",
        "instance",
        "launch",
        "--specialist",
        "single-headless-mail-codex",
        "--name",
        "single-headless-mail-codex-demo",
        "--session-name",
        "hm-single-headless-mail-codex-demo",
        "--headless",
        "--yolo",
        "--mail-transport",
        "filesystem",
        "--mail-root",
        str((paths.overlay_dir / "mailbox").resolve()),
    ]
    assert payload["manifest_path"] == "/tmp/demo-manifest.json"


def test_capture_gateway_console_uses_authoritative_gateway_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
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
        fallback_window_index=None,
        timeout_seconds=30.0,
        lines=2,
    )

    assert payload["session_name"] == "hm-single-mail-claude-demo"
    assert payload["window_index"] == "2"
    assert payload["pane_id"] == "%42"
    assert payload["text"] == "line-2\nline-3\n"


def test_capture_gateway_console_uses_persisted_window_index_when_status_omits_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.project_dir.mkdir(parents=True)

    resolved: dict[str, object] = {}
    monkeypatch.setattr(
        runtime,
        "gateway_status",
        lambda **kwargs: {
            "tmux_session_name": "hm-single-headless-mail-codex-demo",
            "gateway_tmux_window_index": None,
        },
    )

    def fake_resolve_tmux_pane(**kwargs: object) -> object:
        resolved.update(kwargs)
        return type("_Pane", (), {"pane_id": "%77"})()

    monkeypatch.setattr(runtime, "resolve_tmux_pane", fake_resolve_tmux_pane)
    monkeypatch.setattr(runtime, "capture_tmux_pane", lambda **kwargs: "gateway-line\n")

    payload = runtime.capture_gateway_console(
        paths=paths,
        env={},
        agent_name="single-headless-mail-codex-demo",
        fallback_session_name="hm-single-headless-mail-codex-demo",
        fallback_window_index="7",
        timeout_seconds=30.0,
        lines=10,
    )

    assert resolved["session_name"] == "hm-single-headless-mail-codex-demo"
    assert resolved["window_index"] == "7"
    assert payload["window_index"] == "7"
    assert payload["pane_id"] == "%77"


def test_collect_headless_runtime_snapshot_reads_latest_turn_artifacts(tmp_path: Path) -> None:
    output_root = (tmp_path / "outputs").resolve()
    project_root = output_root / "project"
    overlay_root = output_root / "overlay"
    session_root = output_root / "runtime/session-1"
    manifest_path = session_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}\n", encoding="utf-8")
    turn_dir = session_root / "manifest.turn-artifacts" / "turn-0001"
    turn_dir.mkdir(parents=True, exist_ok=True)
    (turn_dir / "stdout.jsonl").write_text('{"kind":"turn.completed"}\n', encoding="utf-8")
    (turn_dir / "exitcode").write_text("0\n", encoding="utf-8")

    state = DemoState(
        created_at_utc="2026-03-31T00:00:00Z",
        repo_root=tmp_path.resolve(),
        output_root=output_root,
        selected_tool="claude",
        provider="claude_code",
        setup_name="default",
        run_id="single-agent-gateway-wakeup-headless-20260331T000000Z-demo",
        project_fixture=tmp_path / "fixture",
        project_workdir=project_root,
        overlay_root=overlay_root,
        agent_def_dir=overlay_root / "agents",
        specialist_name="single-headless-mail-claude",
        instance_name="single-headless-mail-claude-demo",
        session_name="hm-single-headless-mail-claude-demo",
        auth_bundle_name="kimi-coding",
        brain_manifest_path=session_root / "brain/manifest.json",
        brain_home_path=session_root / "brain/home",
        launch_helper_path=session_root / "brain/launch.sh",
        session_manifest_path=manifest_path,
        session_root=session_root,
        tracked_agent_id="tracked-demo",
        agent_name="single-headless-mail-claude-demo",
        agent_id="agent-demo",
        tmux_session_name="tmux-demo",
        mailbox_principal_id="single-headless-mail-claude-demo",
        mailbox_address="single-headless-mail-claude-demo@agents.localhost",
        operator_principal_id="operator",
        operator_address="operator@agents.localhost",
        gateway_root=session_root / "gateway",
        gateway_host="127.0.0.1",
        gateway_port=9911,
        notifier_interval_seconds=5,
        ready_timeout_seconds=180.0,
        output_timeout_seconds=180.0,
        output_file_path=project_root / "tmp/output.md",
        output_file_expected_content="expected",
        deliveries=[],
    )

    snapshot = reporting.collect_headless_runtime_snapshot(
        state=state,
        agent_show={
            "detail": {
                "transport": "headless",
                "runtime_resumable": True,
                "tmux_session_live": True,
                "can_accept_prompt_now": True,
                "interruptible": False,
                "last_turn": {
                    "result": "success",
                    "turn_id": "turn-0001",
                    "turn_index": 1,
                },
                "last_turn_status": "completed",
                "last_turn_completed_at_utc": "2026-03-31T00:00:10Z",
                "last_turn_completion_source": "process_exit",
                "last_turn_returncode": 0,
                "last_turn_history_summary": "turn-0001 completed",
                "last_turn_error": None,
            }
        },
        agent_state={"last_turn": {"result": "success", "turn_id": "turn-0001", "turn_index": 1}},
    )

    assert snapshot["detail_transport"] == "headless"
    assert snapshot["last_turn_status"] == "completed"
    assert snapshot["turn_artifacts_root_present"] is True
    assert snapshot["latest_turn_dir_present"] is True
    assert snapshot["latest_turn_stdout_present"] is True
    assert snapshot["latest_turn_stdout_non_empty"] is True
    assert snapshot["latest_turn_exitcode_present"] is True


def test_report_contract_accepts_structural_project_mailbox_without_read_state(
    tmp_path: Path,
) -> None:
    output_root = (tmp_path / "outputs").resolve()
    project_root = output_root / "project"
    overlay_root = output_root / "overlay"
    session_root = output_root / "runtime/session-1"
    output_file_path = project_root / "tmp/single-agent-gateway-wakeup-headless/processed-demo.md"
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    output_file_path.write_text("single-agent-gateway-wakeup-headless demo\n", encoding="utf-8")
    (project_root / "skills/mailbox").mkdir(parents=True, exist_ok=True)
    (project_root / ".houmao-demo-project.json").write_text("{}\n", encoding="utf-8")

    delivery = DeliveryState(
        delivery_index=1,
        subject="Single-agent gateway wake-up headless demo e72b254f",
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
        run_id="single-agent-gateway-wakeup-headless-20260331T000000Z-e72b254f",
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
        gateway_tmux_session_name="tmux-demo",
        gateway_tmux_window_index="2",
        notifier_interval_seconds=5,
        ready_timeout_seconds=180.0,
        output_timeout_seconds=180.0,
        output_file_path=output_file_path,
        output_file_expected_content="single-agent-gateway-wakeup-headless demo",
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
        "managed_agent": {
            "headless": {
                "detail_transport": "headless",
                "detail_runtime_resumable": True,
                "detail_tmux_session_live": True,
                "detail_can_accept_prompt_now": True,
                "last_turn_result": "success",
                "last_turn_status": "completed",
                "last_turn_completed_at_utc": "2026-03-31T00:00:10Z",
                "last_turn_completion_source": "process_exit",
                "last_turn_returncode": 0,
                "turn_artifacts_root_present": True,
                "latest_turn_dir_present": True,
                "latest_turn_stdout_present": True,
                "latest_turn_stdout_non_empty": True,
                "latest_turn_exitcode_present": True,
            }
        },
        "specialist": {"launch": {"prompt_mode": "unattended"}},
        "instance": {"name": "single-mail-claude-demo"},
    }

    report = reporting.build_report_snapshot(state=state, inspect_snapshot=inspect_snapshot)

    assert report["outcome"]["status"] == "complete"
    reporting.validate_report_contract(report)
    assert report["headless_runtime_evidence"]["last_turn_status"] == "completed"
    assert report["structural_mailbox_evidence"]["delivered_message_visible"] is True
    expected_report_path = (
        Path(__file__).resolve().parents[4]
        / "scripts/demo/single-agent-gateway-wakeup-headless/expected_report/report.json"
    )
    assert reporting.sanitize_report(report) == json.loads(
        expected_report_path.read_text(encoding="utf-8")
    )


def test_sanitize_report_normalizes_delivery_subject_run_token() -> None:
    sanitized = reporting.sanitize_report(
        {
            "deliveries": [
                {
                    "subject": "Single-agent gateway wake-up headless demo e72b254f",
                    "message_id": "msg-20260331T060421Z-f8a1b0ce96c44bebaa431c78141ac216",
                    "thread_id": "msg-20260331T060421Z-f8a1b0ce96c44bebaa431c78141ac216",
                }
            ]
        }
    )

    assert sanitized == {
        "deliveries": [
            {
                "subject": "Single-agent gateway wake-up headless demo <RUN_ID>",
                "message_id": "<MESSAGE_ID>",
                "thread_id": "<THREAD_ID>",
            }
        ]
    }


def test_followup_command_omits_output_override_for_default_root(tmp_path: Path) -> None:
    repo_root = tmp_path.resolve()
    paths = build_demo_layout(
        demo_output_dir=repo_root / "scripts/demo/single-agent-gateway-wakeup-headless/outputs"
    )

    attach_command = driver._followup_command(  # type: ignore[attr-defined]
        paths=paths, command="attach", repo_root=repo_root
    )
    notifier_command = driver._followup_command(  # type: ignore[attr-defined]
        paths=paths, command="notifier status", repo_root=repo_root
    )

    assert attach_command == "scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh attach"
    assert (
        notifier_command
        == "scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier status"
    )


def test_followup_command_includes_output_override_for_non_default_root(tmp_path: Path) -> None:
    repo_root = tmp_path.resolve()
    paths = build_demo_layout(
        demo_output_dir=repo_root
        / "scripts/demo/single-agent-gateway-wakeup-headless/custom-outputs"
    )

    notifier_command = driver._followup_command(  # type: ignore[attr-defined]
        paths=paths, command="notifier status", repo_root=repo_root
    )

    assert notifier_command == (
        "scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier "
        f"--demo-output-dir {paths.output_root} status"
    )


def test_prepare_output_root_preserves_overlay_specialist_state_and_resets_ephemeral_dirs(
    tmp_path: Path,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")

    persistent_paths = (
        paths.overlay_dir / "agents/roles/single-mail-claude/system-prompt.md",
        paths.overlay_dir / "content/prompts/demo.md",
        paths.overlay_dir / "easy/specialists/single-mail-claude.toml",
        paths.overlay_dir / "houmao-config.toml",
        paths.overlay_dir / "catalog.sqlite",
    )
    for path in persistent_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("keep\n", encoding="utf-8")

    ephemeral_dirs = (
        paths.project_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.jobs_root,
        paths.logs_dir,
        paths.deliveries_dir,
        paths.evidence_dir,
        paths.control_dir,
        paths.overlay_dir / "mailbox/staging",
    )
    for directory in ephemeral_dirs:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "marker.txt").write_text("remove\n", encoding="utf-8")

    runtime.prepare_output_root(paths=paths, allow_reprovision=True)

    for path in persistent_paths:
        assert path.is_file()
    assert not (paths.overlay_dir / "mailbox").exists()
    assert not paths.project_dir.exists()
    for directory in (
        paths.runtime_root,
        paths.registry_root,
        paths.jobs_root,
        paths.logs_dir,
        paths.deliveries_dir,
        paths.evidence_dir,
        paths.control_dir,
    ):
        assert directory.is_dir()
        assert not (directory / "marker.txt").exists()


def test_ensure_specialist_reuses_existing_specialist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.control_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        runtime,
        "get_specialist",
        lambda **kwargs: {"name": "single-mail-codex", "launch": {"prompt_mode": "unattended"}},
    )

    create_calls: list[object] = []

    def fake_create_specialist(**kwargs: object) -> dict[str, object]:
        create_calls.append(kwargs)
        return {"created": True}

    monkeypatch.setattr(runtime, "create_specialist", fake_create_specialist)

    payload = runtime.ensure_specialist(
        paths=paths,
        env={},
        specialist_name="single-mail-codex",
        tool="codex",
        tool_parameters=type(
            "_Tool",
            (),
            {
                "setup": "yunwu-openai",
                "auth_name": "yunwu-openai",
            },
        )(),
        system_prompt_file=tmp_path / "prompt.md",
        timeout_seconds=30.0,
    )

    assert payload["name"] == "single-mail-codex"
    assert create_calls == []
    assert paths.specialist_create_path.is_file()
