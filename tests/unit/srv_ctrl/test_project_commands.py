from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from houmao.project.overlay import bootstrap_project_overlay
from houmao.server.models import HoumaoManagedAgentIdentity, HoumaoManagedAgentListResponse
from houmao.srv_ctrl.commands.main import cli


def _make_skill_dir(root: Path, name: str) -> Path:
    """Create one reusable skill directory fixture."""

    skill_root = (root / name).resolve()
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text(
        f"# {name}\n\nReusable instructions for `{name}`.\n",
        encoding="utf-8",
    )
    return skill_root


def test_project_help_mentions_agents_easy_and_mailbox() -> None:
    result = CliRunner().invoke(cli, ["project", "--help"])

    assert result.exit_code == 0
    assert "init" in result.output
    assert "status" in result.output
    assert "agents" in result.output
    assert "easy" in result.output
    assert "mailbox" in result.output
    assert "agent-tools" not in result.output
    assert "project-overlay" in result.output.lower()


def test_project_agents_tools_help_mentions_supported_tools() -> None:
    result = CliRunner().invoke(cli, ["project", "agents", "tools", "--help"])

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "codex" in result.output
    assert "gemini" in result.output


def test_project_agents_roles_help_mentions_verbs() -> None:
    result = CliRunner().invoke(cli, ["project", "agents", "roles", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "init" in result.output
    assert "scaffold" in result.output
    assert "remove" in result.output
    assert "presets" in result.output


def test_project_init_bootstraps_local_overlay_without_optional_mailbox_or_easy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    root_gitignore = repo_root / ".gitignore"
    root_gitignore.write_text("existing-entry\n", encoding="utf-8")
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli, ["project", "init"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["project_root"] == str(repo_root.resolve())
    assert root_gitignore.read_text(encoding="utf-8") == "existing-entry\n"
    assert (repo_root / ".houmao" / ".gitignore").read_text(encoding="utf-8") == "*\n"
    assert (repo_root / ".houmao" / "houmao-config.toml").is_file()
    assert (repo_root / ".houmao" / "agents" / "skills").is_dir()
    assert (repo_root / ".houmao" / "agents" / "roles").is_dir()
    assert (repo_root / ".houmao" / "agents" / "compatibility-profiles").is_dir()
    assert (repo_root / ".houmao" / "agents" / "tools" / "claude" / "adapter.yaml").is_file()
    assert (
        repo_root / ".houmao" / "agents" / "tools" / "codex" / "setups" / "default" / "config.toml"
    ).is_file()
    assert not (repo_root / ".houmao" / "mailbox").exists()
    assert not (repo_root / ".houmao" / "easy").exists()


def test_project_status_reports_discovered_overlay_from_nested_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    nested_dir = repo_root / "nested" / "child"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    monkeypatch.chdir(nested_dir)

    result = runner.invoke(cli, ["project", "status"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["discovered"] is True
    assert payload["project_root"] == str(repo_root)
    assert payload["config_path"] == str((repo_root / ".houmao" / "houmao-config.toml").resolve())
    assert payload["effective_agent_def_dir"] == str((repo_root / ".houmao" / "agents").resolve())
    assert payload["effective_agent_def_dir_source"] == "project_config"
    assert payload["project_mailbox_root"] == str((repo_root / ".houmao" / "mailbox").resolve())


def test_project_agents_tools_auth_get_and_setups_flow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    codex_auth_json = tmp_path / "codex-auth.json"
    codex_auth_json.write_text('{"logged_in": true}\n', encoding="utf-8")
    gemini_oauth_creds = tmp_path / "gemini-oauth.json"
    gemini_oauth_creds.write_text('{"refresh_token": "token"}\n', encoding="utf-8")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    assert (
        runner.invoke(
            cli,
            [
                "project",
                "agents",
                "tools",
                "claude",
                "auth",
                "add",
                "--name",
                "work",
                "--api-key",
                "sk-claude",
                "--base-url",
                "https://claude.example.test",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "agents",
                "tools",
                "codex",
                "auth",
                "add",
                "--name",
                "personal",
                "--api-key",
                "sk-openai",
                "--auth-json",
                str(codex_auth_json),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "agents",
                "tools",
                "gemini",
                "auth",
                "add",
                "--name",
                "vertex",
                "--api-key",
                "sk-gemini",
                "--oauth-creds",
                str(gemini_oauth_creds),
                "--use-vertex-ai",
            ],
        ).exit_code
        == 0
    )

    claude_get_result = runner.invoke(cli, ["project", "agents", "tools", "claude", "get"])
    assert claude_get_result.exit_code == 0
    claude_get_payload = json.loads(claude_get_result.output)
    assert claude_get_payload["tool"] == "claude"
    assert "default" in claude_get_payload["setups"]
    assert claude_get_payload["auth_bundles"] == ["work"]

    add_setup_result = runner.invoke(
        cli,
        ["project", "agents", "tools", "claude", "setups", "add", "--name", "research"],
    )
    assert add_setup_result.exit_code == 0
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "claude"
        / "setups"
        / "research"
        / "settings.json"
    ).is_file()

    get_setup_result = runner.invoke(
        cli,
        ["project", "agents", "tools", "claude", "setups", "get", "--name", "research"],
    )
    assert get_setup_result.exit_code == 0
    assert "settings.json" in json.loads(get_setup_result.output)["files"]

    get_auth_result = runner.invoke(
        cli,
        ["project", "agents", "tools", "claude", "auth", "get", "--name", "work"],
    )
    assert get_auth_result.exit_code == 0
    get_auth_payload = json.loads(get_auth_result.output)
    assert get_auth_payload["env"]["ANTHROPIC_API_KEY"] == {"present": True, "redacted": True}
    assert get_auth_payload["env"]["ANTHROPIC_BASE_URL"] == {
        "present": True,
        "value": "https://claude.example.test",
    }

    remove_setup_result = runner.invoke(
        cli,
        ["project", "agents", "tools", "claude", "setups", "remove", "--name", "research"],
    )
    assert remove_setup_result.exit_code == 0
    assert not (
        repo_root / ".houmao" / "agents" / "tools" / "claude" / "setups" / "research"
    ).exists()


def test_project_agents_roles_init_list_get_and_presets_flow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    init_result = runner.invoke(cli, ["project", "agents", "roles", "init", "--name", "researcher"])
    assert init_result.exit_code == 0
    assert (
        repo_root / ".houmao" / "agents" / "roles" / "researcher" / "system-prompt.md"
    ).is_file()

    list_result = runner.invoke(cli, ["project", "agents", "roles", "list"])
    assert list_result.exit_code == 0
    listed_roles = {item["name"] for item in json.loads(list_result.output)["roles"]}
    assert "researcher" in listed_roles

    preset_add_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "roles",
            "presets",
            "add",
            "--role",
            "researcher",
            "--tool",
            "claude",
            "--auth",
            "default",
            "--skill",
            "notes",
            "--prompt-mode",
            "unattended",
        ],
    )
    assert preset_add_result.exit_code == 0

    preset_get_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "roles",
            "presets",
            "get",
            "--role",
            "researcher",
            "--tool",
            "claude",
        ],
    )
    assert preset_get_result.exit_code == 0
    preset_payload = json.loads(preset_get_result.output)
    assert preset_payload["skills"] == ["notes"]
    assert preset_payload["auth"] == "default"
    assert preset_payload["launch"] == {"prompt_mode": "unattended"}

    role_get_result = runner.invoke(
        cli, ["project", "agents", "roles", "get", "--name", "researcher"]
    )
    assert role_get_result.exit_code == 0
    role_payload = json.loads(role_get_result.output)
    assert role_payload["system_prompt_exists"] is True
    assert len(role_payload["presets"]) == 1

    preset_remove_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "roles",
            "presets",
            "remove",
            "--role",
            "researcher",
            "--tool",
            "claude",
        ],
    )
    assert preset_remove_result.exit_code == 0

    role_remove_result = runner.invoke(
        cli, ["project", "agents", "roles", "remove", "--name", "researcher"]
    )
    assert role_remove_result.exit_code == 0
    assert not (repo_root / ".houmao" / "agents" / "roles" / "researcher").exists()


def test_project_agents_roles_scaffold_creates_complete_starter_slice(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "roles",
            "scaffold",
            "--name",
            "researcher",
            "--tool",
            "claude",
            "--tool",
            "codex",
            "--auth",
            "default",
            "--skill",
            "notes",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (
        repo_root / ".houmao" / "agents" / "roles" / "researcher" / "system-prompt.md"
    ).is_file()
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "roles"
        / "researcher"
        / "presets"
        / "claude"
        / "default.yaml"
    ).is_file()
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "roles"
        / "researcher"
        / "presets"
        / "codex"
        / "default.yaml"
    ).is_file()
    assert (repo_root / ".houmao" / "agents" / "skills" / "notes" / "SKILL.md").is_file()
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "claude"
        / "auth"
        / "default"
        / "env"
        / "vars.env"
    ).is_file()
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "codex"
        / "auth"
        / "default"
        / "env"
        / "vars.env"
    ).is_file()


def test_project_easy_specialist_create_list_get_and_remove_preserves_shared_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = tmp_path / "auth.json"
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
    skill_dir = _make_skill_dir(tmp_path, "notes")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    create_result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "specialist",
            "create",
            "--name",
            "researcher",
            "--system-prompt",
            "You are a precise repo researcher.",
            "--tool",
            "codex",
            "--credential",
            "work",
            "--api-key",
            "sk-openai",
            "--codex-auth-json",
            str(auth_json_path),
            "--with-skill",
            str(skill_dir),
        ],
    )

    assert create_result.exit_code == 0, create_result.output
    create_payload = json.loads(create_result.output)
    metadata_path = Path(create_payload["metadata_path"])
    assert metadata_path.is_file()
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "roles"
        / "researcher"
        / "presets"
        / "codex"
        / "default.yaml"
    ).is_file()
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "codex"
        / "auth"
        / "work"
        / "files"
        / "auth.json"
    ).is_file()
    assert (repo_root / ".houmao" / "agents" / "skills" / "notes" / "SKILL.md").is_file()

    list_result = runner.invoke(cli, ["project", "easy", "specialist", "list"])
    assert list_result.exit_code == 0
    assert [item["name"] for item in json.loads(list_result.output)["specialists"]] == [
        "researcher"
    ]

    get_result = runner.invoke(
        cli, ["project", "easy", "specialist", "get", "--name", "researcher"]
    )
    assert get_result.exit_code == 0
    get_payload = json.loads(get_result.output)
    assert get_payload["tool"] == "codex"
    assert get_payload["credential"] == "work"
    assert get_payload["skills"] == ["notes"]

    remove_result = runner.invoke(
        cli, ["project", "easy", "specialist", "remove", "--name", "researcher"]
    )
    assert remove_result.exit_code == 0
    assert not metadata_path.exists()
    assert not (repo_root / ".houmao" / "agents" / "roles" / "researcher").exists()
    assert (repo_root / ".houmao" / "agents" / "skills" / "notes" / "SKILL.md").is_file()
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "codex"
        / "auth"
        / "work"
        / "files"
        / "auth.json"
    ).is_file()


def test_project_easy_specialist_launch_derives_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = tmp_path / "auth.json"
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
    skill_dir = _make_skill_dir(tmp_path, "notes")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "easy",
                "specialist",
                "create",
                "--name",
                "researcher",
                "--system-prompt",
                "You are a precise repo researcher.",
                "--tool",
                "codex",
                "--credential",
                "work",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
                "--with-skill",
                str(skill_dir),
            ],
        ).exit_code
        == 0
    )

    captured: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.launch_agents_command",
        SimpleNamespace(callback=_fake_launch),
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "specialist",
            "launch",
            "--name",
            "researcher",
            "--instance",
            "repo-research-1",
            "--headless",
            "--yolo",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["agents"] == "researcher"
    assert captured["agent_name"] == "repo-research-1"
    assert captured["provider"] == "codex"
    assert captured["headless"] is True


def test_project_easy_instance_list_and_get_use_runtime_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = tmp_path / "auth.json"
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
    skill_dir = _make_skill_dir(tmp_path, "notes")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "easy",
                "specialist",
                "create",
                "--name",
                "researcher",
                "--system-prompt",
                "You are a precise repo researcher.",
                "--tool",
                "codex",
                "--credential",
                "work",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
                "--with-skill",
                str(skill_dir),
            ],
        ).exit_code
        == 0
    )

    manifest_path = (tmp_path / "manifest.json").resolve()
    manifest_path.write_text("{}\n", encoding="utf-8")
    identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-researcher",
        transport="headless",
        tool="codex",
        session_name=None,
        terminal_id=None,
        runtime_session_id="runtime-session-1",
        tmux_session_name=None,
        tmux_window_name=None,
        manifest_path=str(manifest_path),
        session_root=str((tmp_path / "runtime").resolve()),
        agent_name="repo-research-1",
        agent_id="agent-123",
    )
    manifest_payload = {
        "role_name": "researcher",
        "tool": "codex",
        "runtime": {
            "agent_def_dir": str((repo_root / ".houmao" / "agents").resolve()),
        },
    }

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.list_managed_agents",
        lambda *, port=None: HoumaoManagedAgentListResponse(agents=[identity]),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.resolve_managed_agent_target",
        lambda **kwargs: SimpleNamespace(identity=identity),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project._load_manifest_payload",
        lambda path: manifest_payload,
    )

    list_result = runner.invoke(cli, ["project", "easy", "instance", "list"])
    assert list_result.exit_code == 0
    list_payload = json.loads(list_result.output)
    assert len(list_payload["instances"]) == 1
    assert list_payload["instances"][0]["specialist"] == "researcher"
    assert list_payload["instances"][0]["tool"] == "codex"

    get_result = runner.invoke(
        cli, ["project", "easy", "instance", "get", "--name", "repo-research-1"]
    )
    assert get_result.exit_code == 0
    get_payload = json.loads(get_result.output)
    assert get_payload["specialist"] == "researcher"
    assert get_payload["agent_id"] == "agent-123"
    assert get_payload["manifest_path"] == str(manifest_path)
