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
    assert not (repo_root / ".houmao" / "agents" / "compatibility-profiles").exists()
    assert (repo_root / ".houmao" / "agents" / "tools" / "claude" / "adapter.yaml").is_file()
    assert (
        repo_root / ".houmao" / "agents" / "tools" / "codex" / "setups" / "default" / "config.toml"
    ).is_file()
    assert not (repo_root / ".houmao" / "mailbox").exists()
    assert not (repo_root / ".houmao" / "easy").exists()


def test_project_init_can_opt_into_compatibility_profiles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli, ["project", "init", "--with-compatibility-profiles"])

    assert result.exit_code == 0
    assert (repo_root / ".houmao" / "agents" / "compatibility-profiles").is_dir()


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
        / "researcher-creds"
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
    assert get_payload["credential"] == "researcher-creds"
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
        / "researcher-creds"
        / "files"
        / "auth.json"
    ).is_file()


def test_project_easy_specialist_create_allows_promptless_specialist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = tmp_path / "auth.json"
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
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
            "reviewer",
            "--tool",
            "codex",
            "--api-key",
            "sk-openai",
            "--codex-auth-json",
            str(auth_json_path),
        ],
    )

    assert create_result.exit_code == 0, create_result.output
    create_payload = json.loads(create_result.output)
    assert create_payload["credential"] == "reviewer-creds"
    prompt_path = repo_root / ".houmao" / "agents" / "roles" / "reviewer" / "system-prompt.md"
    assert prompt_path.is_file()
    assert prompt_path.read_text(encoding="utf-8") == ""


def test_project_easy_specialist_create_fails_when_default_bundle_is_missing(
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
            "easy",
            "specialist",
            "create",
            "--name",
            "researcher",
            "--tool",
            "codex",
            "--system-prompt",
            "You are a precise repo researcher.",
        ],
    )

    assert result.exit_code != 0
    assert "researcher-creds" in result.output


def test_project_easy_instance_launch_derives_provider_and_mailbox_flags(
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
    emitted: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        manifest_path = (tmp_path / "manifest.json").resolve()
        manifest_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            agent_identity=kwargs["agent_name"],
            agent_id="agent-123",
            tmux_session_name="AGENTSYS-repo-research-1",
            manifest_path=manifest_path,
        )

    def _fake_emit(**kwargs: object) -> None:
        emitted.update(kwargs)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.launch_managed_agent_locally",
        _fake_launch,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.emit_local_launch_completion",
        _fake_emit,
    )

    mail_root = (tmp_path / "mail-root").resolve()
    private_mailbox_dir = (tmp_path / "private-mailbox").resolve()
    result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "instance",
            "launch",
            "--specialist",
            "researcher",
            "--name",
            "repo-research-1",
            "--headless",
            "--yolo",
            "--mail-transport",
            "filesystem",
            "--mail-root",
            str(mail_root),
            "--mail-account-dir",
            str(private_mailbox_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["agents"] == "researcher"
    assert captured["agent_name"] == "repo-research-1"
    assert captured["provider"] == "codex"
    assert captured["headless"] is True
    assert captured["mailbox_transport"] == "filesystem"
    assert captured["mailbox_root"] == mail_root
    assert captured["mailbox_account_dir"] == private_mailbox_dir
    assert emitted["agent_name"] == "repo-research-1"
    assert emitted["headless"] is True


def test_project_easy_instance_launch_requires_specialist_and_name(tmp_path: Path) -> None:
    runner = CliRunner()

    missing_specialist = runner.invoke(
        cli,
        ["project", "easy", "instance", "launch", "--name", "repo-research-1"],
    )
    assert missing_specialist.exit_code != 0
    assert "Missing option '--specialist'" in missing_specialist.output

    missing_name = runner.invoke(
        cli,
        ["project", "easy", "instance", "launch", "--specialist", "researcher"],
    )
    assert missing_name.exit_code != 0
    assert "Missing option '--name'" in missing_name.output


def test_project_easy_instance_launch_rejects_email_transport(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = tmp_path / "auth.json"
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
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
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "instance",
            "launch",
            "--specialist",
            "researcher",
            "--name",
            "repo-research-1",
            "--mail-transport",
            "email",
        ],
    )

    assert result.exit_code != 0
    assert "not implemented yet" in result.output


def test_project_easy_instance_launch_filesystem_in_root_requires_mail_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = tmp_path / "auth.json"
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
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
            ],
        ).exit_code
        == 0
    )

    missing_root = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "instance",
            "launch",
            "--specialist",
            "researcher",
            "--name",
            "repo-research-1",
            "--mail-transport",
            "filesystem",
        ],
    )
    assert missing_root.exit_code != 0
    assert "requires `--mail-root`" in missing_root.output

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.launch_managed_agent_locally",
        lambda **kwargs: (
            captured.update(kwargs)
            or SimpleNamespace(
                agent_identity=kwargs["agent_name"],
                agent_id="agent-123",
                tmux_session_name="AGENTSYS-repo-research-1",
                manifest_path=(tmp_path / "manifest.json").resolve(),
            )
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.emit_local_launch_completion",
        lambda **kwargs: None,
    )

    mail_root = (tmp_path / "mail-root").resolve()
    success = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "instance",
            "launch",
            "--specialist",
            "researcher",
            "--name",
            "repo-research-1",
            "--headless",
            "--yolo",
            "--mail-transport",
            "filesystem",
            "--mail-root",
            str(mail_root),
        ],
    )

    assert success.exit_code == 0, success.output
    assert captured["mailbox_transport"] == "filesystem"
    assert captured["mailbox_root"] == mail_root
    assert captured["mailbox_account_dir"] is None


def test_project_easy_instance_stop_checks_overlay_and_delegates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

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
    target = SimpleNamespace(identity=identity)
    stop_calls: list[object] = []

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.resolve_managed_agent_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project._load_manifest_payload",
        lambda path: {
            "runtime": {"agent_def_dir": str((repo_root / ".houmao" / "agents").resolve())}
        },
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.stop_managed_agent",
        lambda resolved_target: (
            stop_calls.append(resolved_target)
            or {"success": True, "agent_name": resolved_target.identity.agent_name}
        ),
    )

    result = runner.invoke(
        cli, ["project", "easy", "instance", "stop", "--name", "repo-research-1"]
    )

    assert result.exit_code == 0, result.output
    assert stop_calls == [target]
    assert json.loads(result.output) == {"success": True, "agent_name": "repo-research-1"}


def test_project_easy_instance_stop_rejects_instances_from_other_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

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
    target = SimpleNamespace(identity=identity)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project.resolve_managed_agent_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project._load_manifest_payload",
        lambda path: {
            "runtime": {"agent_def_dir": str((tmp_path / "other" / ".houmao" / "agents").resolve())}
        },
    )

    result = runner.invoke(
        cli, ["project", "easy", "instance", "stop", "--name", "repo-research-1"]
    )

    assert result.exit_code != 0
    assert "does not belong to the discovered project overlay" in result.output


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
        "launch_plan": {
            "mailbox": {
                "transport": "filesystem",
                "principal_id": "AGENTSYS-repo-research-1",
                "address": "AGENTSYS-repo-research-1@agents.localhost",
                "filesystem_root": str((tmp_path / "mail-root").resolve()),
                "mailbox_kind": "symlink",
                "mailbox_path": str((tmp_path / "private-mailboxes" / "repo-research-1").resolve()),
                "bindings_version": "2026-03-29T12:00:00Z",
            }
        },
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
    assert list_payload["instances"][0]["mailbox"] == {
        "transport": "filesystem",
        "principal_id": "AGENTSYS-repo-research-1",
        "address": "AGENTSYS-repo-research-1@agents.localhost",
        "mailbox_root": str((tmp_path / "mail-root").resolve()),
        "mailbox_kind": "symlink",
        "mailbox_dir": str((tmp_path / "private-mailboxes" / "repo-research-1").resolve()),
        "bindings_version": "2026-03-29T12:00:00Z",
    }

    get_result = runner.invoke(
        cli, ["project", "easy", "instance", "get", "--name", "repo-research-1"]
    )
    assert get_result.exit_code == 0
    get_payload = json.loads(get_result.output)
    assert get_payload["specialist"] == "researcher"
    assert get_payload["agent_id"] == "agent-123"
    assert get_payload["manifest_path"] == str(manifest_path)
    assert get_payload["mailbox"] == {
        "transport": "filesystem",
        "principal_id": "AGENTSYS-repo-research-1",
        "address": "AGENTSYS-repo-research-1@agents.localhost",
        "mailbox_root": str((tmp_path / "mail-root").resolve()),
        "mailbox_kind": "symlink",
        "mailbox_dir": str((tmp_path / "private-mailboxes" / "repo-research-1").resolve()),
        "bindings_version": "2026-03-29T12:00:00Z",
    }
