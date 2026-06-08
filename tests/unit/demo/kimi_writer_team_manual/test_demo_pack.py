from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from houmao.demo.kimi_writer_team_manual import driver, runtime
from houmao.demo.kimi_writer_team_manual.models import build_demo_layout
from houmao.demo.kimi_writer_team_manual.store import load_demo_parameters


_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_PARAMETERS_PATH = (
    _WORKSPACE_ROOT / "scripts/demo/kimi-writer-team-manual/inputs/demo_parameters.json"
)


def _load_parameters() -> Any:
    """Load the tracked demo parameters."""

    return load_demo_parameters(_PARAMETERS_PATH)


def test_parameters_define_three_kimi_writer_team_members() -> None:
    parameters = _load_parameters()

    assert parameters.demo_id == "kimi-writer-team-manual"
    assert [member.agent_name for member in parameters.team] == [
        "alex-story",
        "alex-char",
        "alex-review",
    ]
    assert parameters.story_member.agent_name == "alex-story"
    assert parameters.member_by_agent_name("alex-char").mailbox_address == (
        "alex-char@houmao.localhost"
    )


def test_build_demo_layout_includes_project_overlay_and_runtime_roots(tmp_path: Path) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")

    assert paths.project_dir == (tmp_path / "outputs/project").resolve()
    assert paths.overlay_dir == (tmp_path / "outputs/overlay").resolve()
    assert paths.runtime_root == (tmp_path / "outputs/overlay/runtime").resolve()
    assert paths.registry_root == (tmp_path / "outputs/registry").resolve()
    assert paths.jobs_root == (tmp_path / "outputs/overlay/jobs").resolve()
    assert paths.mailbox_root == (tmp_path / "outputs/overlay/mailbox").resolve()


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


def test_kimi_credential_args_support_code_home(tmp_path: Path) -> None:
    code_home = tmp_path / "kimi-home"
    code_home.mkdir()

    args = runtime.build_kimi_credential_args(
        api_key=None,
        model_name=None,
        base_url=None,
        provider_type=None,
        code_base_url=None,
        code_oauth_host=None,
        oauth_host=None,
        disable_telemetry=False,
        code_home=code_home,
        config_toml=None,
        credential_json=None,
    )

    assert args == ["--code-home", str(code_home.resolve())]


def test_kimi_credential_args_require_one_source() -> None:
    with pytest.raises(runtime.DemoRuntimeError, match="Kimi credential input is required"):
        runtime.build_kimi_credential_args(
            api_key=None,
            model_name=None,
            base_url=None,
            provider_type=None,
            code_base_url=None,
            code_oauth_host=None,
            oauth_host=None,
            disable_telemetry=False,
            code_home=None,
            config_toml=None,
            credential_json=None,
        )


def test_kimi_auth_bundle_shapes_credential_args(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    (bundle / "env").mkdir(parents=True)
    (bundle / "files/credentials").mkdir(parents=True)
    (bundle / "env/vars.env").write_text(
        "KIMI_MODEL_API_KEY=sk-kimi\n"
        "KIMI_MODEL_NAME=kimi-k2\n"
        "KIMI_MODEL_BASE_URL=https://kimi.example.test\n"
        "KIMI_DISABLE_TELEMETRY=true\n",
        encoding="utf-8",
    )
    (bundle / "files/config.toml").write_text("[demo]\n", encoding="utf-8")
    (bundle / "files/credentials/kimi-code.json").write_text("{}\n", encoding="utf-8")

    args, source = runtime.build_kimi_credential_args_from_bundle(bundle_dir=bundle)

    assert source == f"auth-bundle:{bundle}"
    assert "--api-key" in args
    assert "sk-kimi" in args
    assert "--model-name" in args
    assert "kimi-k2" in args
    assert "--base-url" in args
    assert "https://kimi.example.test" in args
    assert "--disable-telemetry" in args
    assert "--config-toml" in args
    assert "--credential-json" in args


def test_driver_parser_accepts_manual_command_surface() -> None:
    parser = driver._build_parser()  # type: ignore[attr-defined]

    assert parser.parse_args(["start", "--api-key", "sk-test"]).command == "start"
    assert parser.parse_args(["attach", "--agent", "alex-char"]).command == "attach"
    assert parser.parse_args(["prompt-start", "--chapters", "1"]).command == "prompt-start"
    assert (
        parser.parse_args(
            [
                "send-mail",
                "--from-agent",
                "alex-story",
                "--to-agent",
                "alex-char",
                "--subject",
                "s",
                "--body-content",
                "b",
            ]
        ).command
        == "send-mail"
    )
    notifier_args = parser.parse_args(["notifier", "--agent", "alex-story", "status"])
    assert notifier_args.command == "notifier"
    assert notifier_args.notifier_command == "status"
    assert parser.parse_args(["status"]).command == "status"
    assert parser.parse_args(["inspect"]).command == "inspect"
    assert parser.parse_args(["stop"]).command == "stop"


def test_create_specialist_uses_kimi_tui_for_story_and_core_system_skills(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.project_dir.mkdir(parents=True)
    member = _load_parameters().story_member
    captured: dict[str, Any] = {}

    def fake_run_json_command(command: list[str], **kwargs: object) -> dict[str, Any]:
        captured["command"] = command
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime, "run_json_command", fake_run_json_command)

    runtime.create_specialist(
        paths=paths,
        env={},
        member=member,
        credential_name="writer-team-kimi",
        setup_name="default",
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert command[:8] == [
        "pixi",
        "run",
        "houmao-mgr",
        "--print-json",
        "project",
        "specialist",
        "create",
        "--name",
    ]
    assert "--tool" in command
    assert "kimi" in command
    assert "--no-unattended" in command
    assert "--system-skills-mode" in command
    assert "replace" in command
    assert "--system-skill-set" in command
    assert "core" in command


def test_create_specialist_uses_unattended_default_for_reviewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.project_dir.mkdir(parents=True)
    member = _load_parameters().member_by_agent_name("alex-review")
    captured: dict[str, Any] = {}

    def fake_run_json_command(command: list[str], **kwargs: object) -> dict[str, Any]:
        captured["command"] = command
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime, "run_json_command", fake_run_json_command)

    runtime.create_specialist(
        paths=paths,
        env={},
        member=member,
        credential_name="writer-team-kimi",
        setup_name="default",
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert "--no-unattended" not in command


def test_create_profile_uses_mailbox_and_story_as_is_prompt_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.project_dir.mkdir(parents=True)
    member = _load_parameters().story_member
    captured: dict[str, Any] = {}

    def fake_run_json_command(command: list[str], **kwargs: object) -> dict[str, Any]:
        captured["command"] = command
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime, "run_json_command", fake_run_json_command)

    runtime.create_profile(
        paths=paths,
        env={},
        member=member,
        credential_name="writer-team-kimi",
        notifier_appendix_text="process mail",
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert "--prompt-mode" in command
    assert "as_is" in command
    assert "--mail-transport" in command
    assert "filesystem" in command
    assert "--mail-root" in command
    assert str(paths.mailbox_root) in command
    assert "--mail-principal-id" in command
    assert "HOUMAO-alex-story" in command
    assert "--mail-address" in command
    assert "alex-story@houmao.localhost" in command


def test_create_profile_uses_reviewer_unattended_prompt_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.project_dir.mkdir(parents=True)
    member = _load_parameters().member_by_agent_name("alex-review")
    captured: dict[str, Any] = {}

    def fake_run_json_command(command: list[str], **kwargs: object) -> dict[str, Any]:
        captured["command"] = command
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime, "run_json_command", fake_run_json_command)

    runtime.create_profile(
        paths=paths,
        env={},
        member=member,
        credential_name="writer-team-kimi",
        notifier_appendix_text="process mail",
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert "--prompt-mode" in command
    assert "unattended" in command


def test_launch_agent_uses_tui_gateway_background_for_story(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.project_dir.mkdir(parents=True)
    member = _load_parameters().story_member
    captured: dict[str, Any] = {}

    def fake_run_json_command(command: list[str], **kwargs: object) -> dict[str, Any]:
        captured["command"] = command
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime, "run_json_command", fake_run_json_command)

    runtime.launch_agent(
        paths=paths,
        env={},
        member=member,
        session_name="kimi-writer-alex-story-demo",
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert "--profile" in command
    assert "alex-story" in command
    assert "--headless" not in command
    assert "--gateway-background" in command


def test_launch_agent_uses_headless_gateway_background_for_reviewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    paths.project_dir.mkdir(parents=True)
    member = _load_parameters().member_by_agent_name("alex-review")
    captured: dict[str, Any] = {}

    def fake_run_json_command(command: list[str], **kwargs: object) -> dict[str, Any]:
        captured["command"] = command
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime, "run_json_command", fake_run_json_command)

    runtime.launch_agent(
        paths=paths,
        env={},
        member=member,
        session_name="kimi-writer-alex-review-demo",
        timeout_seconds=30.0,
    )

    command = captured["command"]
    assert "--profile" in command
    assert "alex-review" in command
    assert "--headless" in command
    assert "--gateway-background" in command


def test_render_start_charter_replaces_run_id_and_chapter_count() -> None:
    rendered = driver.render_start_charter(
        "Run `__RUN_ID__`; chapters `__CHAPTER_COUNT__`; all __CHAPTER_COUNT_WORD__",
        run_id="kimi-writer-team-demo",
        chapter_count=3,
    )

    assert "kimi-writer-team-demo" in rendered
    assert "`3`" in rendered
    assert "all 3" in rendered


def test_supported_demo_index_mentions_kimi_writer_team() -> None:
    demo_readme = (_WORKSPACE_ROOT / "scripts/demo/README.md").read_text(encoding="utf-8")

    assert "kimi-writer-team-manual/" in demo_readme
    assert "three Kimi Code TUI agents" in demo_readme
