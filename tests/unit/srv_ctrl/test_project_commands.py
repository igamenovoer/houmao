from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from houmao.project.overlay import bootstrap_project_overlay
from houmao.srv_ctrl.commands.main import cli


def test_project_help_mentions_init_status_and_agent_tools() -> None:
    result = CliRunner().invoke(cli, ["project", "--help"])

    assert result.exit_code == 0
    assert "init" in result.output
    assert "status" in result.output
    assert "agent-tools" in result.output
    assert "credential" not in result.output
    assert "project-overlay" in result.output.lower()


def test_project_agent_tools_help_mentions_supported_tools() -> None:
    result = CliRunner().invoke(cli, ["project", "agent-tools", "--help"])

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "codex" in result.output
    assert "gemini" in result.output


def test_project_claude_auth_help_mentions_crud_verbs() -> None:
    result = CliRunner().invoke(cli, ["project", "agent-tools", "claude", "auth", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "add" in result.output
    assert "get" in result.output
    assert "set" in result.output
    assert "remove" in result.output


def test_project_init_bootstraps_local_overlay_without_touching_repo_root_gitignore(
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
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "codex"
        / "setups"
        / "default"
        / "config.toml"
    ).is_file()


def test_project_init_is_idempotent_and_preserves_existing_auth_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    first_result = runner.invoke(cli, ["project", "init"])
    assert first_result.exit_code == 0

    auth_env_path = (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "claude"
        / "auth"
        / "personal"
        / "env"
        / "vars.env"
    )
    auth_env_path.parent.mkdir(parents=True, exist_ok=True)
    auth_env_path.write_text("ANTHROPIC_API_KEY=keep-me\n", encoding="utf-8")

    second_result = runner.invoke(cli, ["project", "init"])

    assert second_result.exit_code == 0
    assert auth_env_path.read_text(encoding="utf-8") == "ANTHROPIC_API_KEY=keep-me\n"


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


def test_project_status_reports_missing_overlay_clearly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    workdir = (tmp_path / "workspace").resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workdir)

    result = runner.invoke(cli, ["project", "status"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["discovered"] is False
    assert payload["project_root"] is None
    assert payload["config_path"] is None
    assert payload["effective_agent_def_dir"] == str((workdir / ".agentsys" / "agents").resolve())
    assert payload["effective_agent_def_dir_source"] == "legacy_default"


def test_project_agent_tools_add_and_list_flow_for_supported_tools(
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

    claude_result = runner.invoke(
        cli,
        [
            "project",
            "agent-tools",
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
    )
    codex_result = runner.invoke(
        cli,
        [
            "project",
            "agent-tools",
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
    )
    gemini_result = runner.invoke(
        cli,
        [
            "project",
            "agent-tools",
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
    )

    assert claude_result.exit_code == 0
    assert codex_result.exit_code == 0
    assert gemini_result.exit_code == 0
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "claude"
        / "auth"
        / "work"
        / "env"
        / "vars.env"
    ).read_text(encoding="utf-8") == (
        "ANTHROPIC_API_KEY=sk-claude\n"
        "ANTHROPIC_BASE_URL=https://claude.example.test\n"
    )
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "codex"
        / "auth"
        / "personal"
        / "files"
        / "auth.json"
    ).read_text(encoding="utf-8") == '{"logged_in": true}\n'

    claude_list_result = runner.invoke(cli, ["project", "agent-tools", "claude", "auth", "list"])
    codex_list_result = runner.invoke(cli, ["project", "agent-tools", "codex", "auth", "list"])
    gemini_list_result = runner.invoke(cli, ["project", "agent-tools", "gemini", "auth", "list"])

    assert claude_list_result.exit_code == 0
    assert codex_list_result.exit_code == 0
    assert gemini_list_result.exit_code == 0
    assert json.loads(claude_list_result.output)["credentials"] == ["work"]
    assert json.loads(codex_list_result.output)["credentials"] == ["personal"]
    assert json.loads(gemini_list_result.output)["credentials"] == ["vertex"]


def test_project_agent_tools_claude_auth_get_set_and_remove_flow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    state_template_file = tmp_path / "claude-state.template.json"
    state_template_file.write_text('{"state": "template"}\n', encoding="utf-8")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    add_result = runner.invoke(
        cli,
        [
            "project",
            "agent-tools",
            "claude",
            "auth",
            "add",
            "--name",
            "work",
            "--api-key",
            "sk-claude",
            "--base-url",
            "https://claude.example.test",
            "--state-template-file",
            str(state_template_file),
        ],
    )

    assert add_result.exit_code == 0

    get_result = runner.invoke(
        cli,
        ["project", "agent-tools", "claude", "auth", "get", "--name", "work"],
    )

    assert get_result.exit_code == 0
    get_payload = json.loads(get_result.output)
    assert get_payload["env"]["ANTHROPIC_API_KEY"] == {"present": True, "redacted": True}
    assert get_payload["env"]["ANTHROPIC_BASE_URL"] == {
        "present": True,
        "value": "https://claude.example.test",
    }
    assert get_payload["files"]["claude_state.template.json"]["present"] is True

    set_result = runner.invoke(
        cli,
        [
            "project",
            "agent-tools",
            "claude",
            "auth",
            "set",
            "--name",
            "work",
            "--base-url",
            "https://proxy.example.test",
            "--clear-state-template-file",
        ],
    )

    assert set_result.exit_code == 0
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "claude"
        / "auth"
        / "work"
        / "env"
        / "vars.env"
    ).read_text(encoding="utf-8") == (
        "ANTHROPIC_API_KEY=sk-claude\n"
        "ANTHROPIC_BASE_URL=https://proxy.example.test\n"
    )
    assert not (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "claude"
        / "auth"
        / "work"
        / "files"
        / "claude_state.template.json"
    ).exists()

    clear_result = runner.invoke(
        cli,
        [
            "project",
            "agent-tools",
            "claude",
            "auth",
            "set",
            "--name",
            "work",
            "--clear-base-url",
        ],
    )

    assert clear_result.exit_code == 0
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "claude"
        / "auth"
        / "work"
        / "env"
        / "vars.env"
    ).read_text(encoding="utf-8") == "ANTHROPIC_API_KEY=sk-claude\n"

    remove_result = runner.invoke(
        cli,
        ["project", "agent-tools", "claude", "auth", "remove", "--name", "work"],
    )

    assert remove_result.exit_code == 0
    assert not (
        repo_root / ".houmao" / "agents" / "tools" / "claude" / "auth" / "work"
    ).exists()


def test_project_agent_tools_codex_set_allows_clear_only_updates(
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
                "agent-tools",
                "codex",
                "auth",
                "add",
                "--name",
                "personal",
                "--api-key",
                "sk-openai",
                "--auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    clear_result = runner.invoke(
        cli,
        [
            "project",
            "agent-tools",
            "codex",
            "auth",
            "set",
            "--name",
            "personal",
            "--clear-api-key",
            "--clear-auth-json",
        ],
    )

    assert clear_result.exit_code == 0
    assert (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "codex"
        / "auth"
        / "personal"
        / "env"
        / "vars.env"
    ).read_text(encoding="utf-8") == "\n"
    assert not (
        repo_root
        / ".houmao"
        / "agents"
        / "tools"
        / "codex"
        / "auth"
        / "personal"
        / "files"
        / "auth.json"
    ).exists()


def test_project_agent_tools_gemini_add_rejects_duplicate_names(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    gemini_oauth_creds = tmp_path / "gemini-oauth.json"
    gemini_oauth_creds.write_text('{"refresh_token": "token"}\n', encoding="utf-8")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    first_result = runner.invoke(
        cli,
        [
            "project",
            "agent-tools",
            "gemini",
            "auth",
            "add",
            "--name",
            "vertex",
            "--oauth-creds",
            str(gemini_oauth_creds),
        ],
    )
    duplicate_result = runner.invoke(
        cli,
        [
            "project",
            "agent-tools",
            "gemini",
            "auth",
            "add",
            "--name",
            "vertex",
            "--oauth-creds",
            str(gemini_oauth_creds),
        ],
    )

    assert first_result.exit_code == 0
    assert duplicate_result.exit_code != 0
    assert "already exists" in duplicate_result.output


def test_project_agent_tools_set_requires_existing_bundle(
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
            "agent-tools",
            "codex",
            "auth",
            "set",
            "--name",
            "missing",
            "--base-url",
            "https://proxy.example.test/v1",
        ],
    )

    assert result.exit_code != 0
    assert "Auth bundle not found" in result.output


def test_brains_build_uses_discovered_project_overlay_when_flag_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    nested_dir = repo_root / "subdir"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    captured_request: dict[str, object] = {}
    monkeypatch.chdir(nested_dir)

    def _fake_build_brain_home(request: object) -> object:
        captured_request["agent_def_dir"] = getattr(request, "agent_def_dir")
        return SimpleNamespace(
            home_id="brain-123",
            home_path=(repo_root / "runtime-home").resolve(),
            launch_helper_path=(repo_root / "launch.sh").resolve(),
            manifest_path=(repo_root / "manifest.yaml").resolve(),
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.brains.build_brain_home",
        _fake_build_brain_home,
    )

    result = runner.invoke(
        cli,
        [
            "brains",
            "build",
            "--tool",
            "claude",
            "--setup",
            "default",
            "--auth",
            "default",
            "--skill",
            "openspec-apply-change",
        ],
    )

    assert result.exit_code == 0
    assert captured_request["agent_def_dir"] == (repo_root / ".houmao" / "agents").resolve()
