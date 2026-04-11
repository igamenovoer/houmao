from __future__ import annotations

import json
from pathlib import Path
import shutil
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.project.catalog import ProjectCatalog
from houmao.project.overlay import (
    PROJECT_OVERLAY_DISCOVERY_MODE_ENV_VAR,
    PROJECT_OVERLAY_DIR_ENV_VAR,
    bootstrap_project_overlay,
    bootstrap_project_overlay_at_root,
    require_project_overlay,
)
from houmao.server.models import (
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentListResponse,
)
from houmao.srv_ctrl.commands import main as command_main
from houmao.srv_ctrl.commands import project as project_commands
from houmao.srv_ctrl.commands import project_definitions
from houmao.srv_ctrl.commands import project_easy
from houmao.srv_ctrl.commands import project_launch_profiles
from houmao.srv_ctrl.commands import project_mailbox
from houmao.srv_ctrl.commands import project_tools
from houmao.srv_ctrl.commands.agents.core import emit_local_launch_completion
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


def _clone_setup_dir(repo_root: Path, *, tool: str, source: str, target: str) -> Path:
    """Clone one project-local setup directory for test coverage."""

    source_root = repo_root / ".houmao" / "agents" / "tools" / tool / "setups" / source
    target_root = repo_root / ".houmao" / "agents" / "tools" / tool / "setups" / target
    if source_root.is_dir():
        shutil.copytree(source_root, target_root)
        return target_root

    target_root.mkdir(parents=True, exist_ok=True)
    (target_root / "config.toml").write_text('model = "gpt-5.4"\n', encoding="utf-8")
    return target_root


def _make_claude_config_dir(root: Path, name: str, *, token_suffix: str) -> Path:
    """Create one Claude config-root fixture with vendor login state."""

    config_parent = (root / name).resolve()
    config_dir = (config_parent / ".claude").resolve()
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / ".credentials.json").write_text(
        json.dumps({"claudeAiOauth": {"accessToken": f"vendor-{token_suffix}"}}) + "\n",
        encoding="utf-8",
    )
    (config_parent / ".claude.json").write_text(
        json.dumps({"hasCompletedOnboarding": True, "numStartups": len(token_suffix)}) + "\n",
        encoding="utf-8",
    )
    return config_dir


def _project_auth_root(repo_root: Path, *, tool: str, name: str) -> Path:
    """Resolve one projected auth root from its operator-facing display name."""

    overlay = require_project_overlay(repo_root)
    profile = ProjectCatalog.from_overlay(overlay).load_auth_profile(tool=tool, name=name)
    return profile.resolved_projection_path(overlay)


def _create_codex_specialist(
    runner: CliRunner,
    *,
    name: str,
    credential: str,
    auth_json_path: Path,
) -> None:
    """Create one Codex-backed easy specialist for project command tests."""

    result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "specialist",
            "create",
            "--name",
            name,
            "--system-prompt",
            f"You are specialist {name}.",
            "--tool",
            "codex",
            "--credential",
            credential,
            "--api-key",
            "sk-openai",
            "--codex-auth-json",
            str(auth_json_path),
        ],
    )
    assert result.exit_code == 0, result.output


def _bootstrap_codex_researcher_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[CliRunner, Path, Path]:
    """Create one project overlay with a Codex researcher specialist."""

    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    _create_codex_specialist(
        runner,
        name="researcher",
        credential="work",
        auth_json_path=auth_json_path,
    )
    return runner, repo_root, auth_json_path


def test_project_help_mentions_agents_credentials_easy_and_mailbox() -> None:
    result = CliRunner().invoke(cli, ["project", "--help"])

    assert result.exit_code == 0
    assert "init" in result.output
    assert "status" in result.output
    assert "agents" in result.output
    assert "credentials" in result.output
    assert "easy" in result.output
    assert "mailbox" in result.output
    assert "agent-tools" not in result.output
    assert "project-overlay" in result.output.lower()


def test_project_module_remains_public_entrypoint() -> None:
    source = Path(project_commands.__file__).read_text(encoding="utf-8")

    assert project_commands.project_group.name == "project"
    assert project_commands.project_group.get_command(None, "agents") is not None
    assert project_commands.project_group.get_command(None, "credentials") is not None
    assert (
        project_commands.project_group.get_command(None, "easy") is project_easy.easy_project_group
    )
    assert (
        project_commands.project_group.get_command(None, "mailbox")
        is project_mailbox.project_mailbox_group
    )
    assert (
        project_commands.agents_project_group.get_command(None, "tools")
        is project_tools.project_tools_group
    )
    assert (
        project_commands.agents_project_group.get_command(None, "roles")
        is project_definitions.project_roles_group
    )
    assert (
        project_commands.agents_project_group.get_command(None, "presets")
        is project_definitions.project_presets_group
    )
    assert (
        project_commands.agents_project_group.get_command(None, "recipes")
        is project_definitions.project_recipes_group
    )
    assert (
        project_commands.agents_project_group.get_command(None, "launch-profiles")
        is project_launch_profiles.project_launch_profiles_group
    )
    assert "from .project import project_group" in Path(command_main.__file__).read_text(
        encoding="utf-8"
    )
    assert "def project_group" in source
    assert "def easy_project_group" not in source
    assert "def project_mailbox_group" not in source
    assert "def project_launch_profiles_group" not in source
    assert "def project_tools_group" not in source
    assert "def project_roles_group" not in source


def test_project_extracted_subgroup_help_surfaces() -> None:
    cases = [
        (
            ["project", "agents", "--help"],
            ("tools", "roles", "presets", "recipes", "launch-profiles"),
        ),
        (["project", "easy", "--help"], ("profile", "specialist", "instance")),
        (
            ["project", "mailbox", "--help"],
            ("init", "status", "register", "unregister", "accounts", "messages"),
        ),
    ]

    for args, expected_terms in cases:
        result = CliRunner().invoke(cli, [*args])

        assert result.exit_code == 0, result.output
        for expected in expected_terms:
            assert expected in result.output


def test_project_agents_tools_help_mentions_supported_tools() -> None:
    result = CliRunner().invoke(cli, ["project", "agents", "tools", "--help"])

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "codex" in result.output
    assert "gemini" in result.output


def test_project_credentials_help_mentions_supported_tools_and_verbs() -> None:
    group_result = CliRunner().invoke(cli, ["project", "credentials", "--help"])

    assert group_result.exit_code == 0
    assert "claude" in group_result.output
    assert "codex" in group_result.output
    assert "gemini" in group_result.output

    tool_result = CliRunner().invoke(cli, ["project", "credentials", "claude", "--help"])
    assert tool_result.exit_code == 0
    assert "list" in tool_result.output
    assert "get" in tool_result.output
    assert "add" in tool_result.output
    assert "set" in tool_result.output
    assert "login" in tool_result.output
    assert "rename" in tool_result.output
    assert "remove" in tool_result.output


def test_project_agents_tool_help_no_longer_mentions_auth() -> None:
    result = CliRunner().invoke(cli, ["project", "agents", "tools", "claude", "--help"])

    assert result.exit_code == 0
    assert "get" in result.output
    assert "setups" in result.output
    assert "auth" not in result.output


def test_project_agents_roles_help_mentions_verbs() -> None:
    result = CliRunner().invoke(cli, ["project", "agents", "roles", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "init" in result.output
    assert "set" in result.output
    assert "remove" in result.output
    assert "scaffold" not in result.output
    assert "presets" not in result.output


def test_project_agents_presets_help_mentions_verbs() -> None:
    result = CliRunner().invoke(cli, ["project", "agents", "presets", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "add" in result.output
    assert "set" in result.output
    assert "remove" in result.output


def test_project_agents_recipes_help_mentions_verbs() -> None:
    result = CliRunner().invoke(cli, ["project", "agents", "recipes", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "add" in result.output
    assert "set" in result.output
    assert "remove" in result.output
    assert "named recipes" in result.output


def test_project_agents_launch_profiles_help_mentions_verbs() -> None:
    result = CliRunner().invoke(cli, ["project", "agents", "launch-profiles", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "add" in result.output
    assert "set" in result.output
    assert "remove" in result.output
    assert ".houmao/agents/launch-profiles/" in result.output


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
    assert (repo_root / ".houmao" / "catalog.sqlite").is_file()
    assert (repo_root / ".houmao" / "content" / "prompts").is_dir()
    assert (repo_root / ".houmao" / "content" / "auth").is_dir()
    assert (repo_root / ".houmao" / "content" / "skills").is_dir()
    assert (repo_root / ".houmao" / "content" / "setups").is_dir()
    assert not (repo_root / ".houmao" / "agents").exists()
    assert not (repo_root / ".houmao" / "mailbox").exists()
    assert not (repo_root / ".houmao" / "easy").exists()


def test_project_init_uses_overlay_env_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    overlay_root = (tmp_path / "ci-overlay").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    root_gitignore = repo_root / ".gitignore"
    root_gitignore.write_text("existing-entry\n", encoding="utf-8")
    monkeypatch.chdir(repo_root)

    result = runner.invoke(
        cli,
        ["project", "init"],
        env={PROJECT_OVERLAY_DIR_ENV_VAR: str(overlay_root)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["overlay_root"] == str(overlay_root)
    assert root_gitignore.read_text(encoding="utf-8") == "existing-entry\n"
    assert (overlay_root / ".gitignore").read_text(encoding="utf-8") == "*\n"
    assert (overlay_root / "houmao-config.toml").is_file()
    assert (overlay_root / "catalog.sqlite").is_file()
    assert (overlay_root / "content" / "prompts").is_dir()


def test_project_init_rejects_relative_overlay_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(
        cli,
        ["project", "init"],
        env={PROJECT_OVERLAY_DIR_ENV_VAR: "relative/overlay"},
    )

    assert result.exit_code != 0
    assert "HOUMAO_PROJECT_OVERLAY_DIR" in result.output


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
    assert payload["overlay_root"] == str((repo_root / ".houmao").resolve())
    assert payload["overlay_root_source"] == "discovered"
    assert payload["overlay_discovery_mode"] == "ancestor"
    assert (
        payload["overlay_discovery_detail"]
        == "Ambient overlay discovery uses nearest-ancestor lookup within the Git boundary."
    )
    assert payload["config_path"] == str((repo_root / ".houmao" / "houmao-config.toml").resolve())
    assert payload["effective_agent_def_dir"] == str((repo_root / ".houmao" / "agents").resolve())
    assert payload["effective_agent_def_dir_source"] == "project_config"
    assert payload["project_mailbox_root"] == str((repo_root / ".houmao" / "mailbox").resolve())
    assert payload["project_runtime_root"] == str((repo_root / ".houmao" / "runtime").resolve())
    assert payload["project_jobs_root"] == str((repo_root / ".houmao" / "jobs").resolve())
    assert payload["project_easy_root"] == str((repo_root / ".houmao" / "easy").resolve())
    assert payload["would_bootstrap_overlay"] is False
    assert (
        payload["selected_overlay_detail"]
        == "Selected overlay root from nearest-ancestor project discovery."
    )
    assert (
        payload["overlay_bootstrap_detail"]
        == "Reused the selected project overlay without implicit bootstrap."
    )


def test_project_status_reports_env_selected_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    overlay_root = (tmp_path / "ci-overlay").resolve()
    nested_dir = repo_root / "nested" / "child"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay_at_root(overlay_root)
    monkeypatch.chdir(nested_dir)

    result = runner.invoke(
        cli,
        ["project", "status"],
        env={PROJECT_OVERLAY_DIR_ENV_VAR: str(overlay_root)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["discovered"] is True
    assert payload["overlay_root"] == str(overlay_root)
    assert payload["overlay_root_source"] == "env"
    assert payload["overlay_discovery_mode"] == "ancestor"
    assert payload["config_path"] == str((overlay_root / "houmao-config.toml").resolve())
    assert payload["effective_agent_def_dir"] == str((overlay_root / "agents").resolve())
    assert payload["effective_agent_def_dir_source"] == "project_config"
    assert payload["project_mailbox_root"] == str((overlay_root / "mailbox").resolve())


def test_project_status_reports_env_selected_overlay_even_in_cwd_only_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    overlay_root = (tmp_path / "ci-overlay").resolve()
    nested_dir = repo_root / "nested" / "child"
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    bootstrap_project_overlay_at_root(overlay_root)
    monkeypatch.chdir(nested_dir)

    result = runner.invoke(
        cli,
        ["project", "status"],
        env={
            PROJECT_OVERLAY_DIR_ENV_VAR: str(overlay_root),
            PROJECT_OVERLAY_DISCOVERY_MODE_ENV_VAR: "cwd_only",
        },
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["discovered"] is True
    assert payload["overlay_root"] == str(overlay_root)
    assert payload["overlay_root_source"] == "env"
    assert payload["overlay_discovery_mode"] == "cwd_only"
    assert payload["config_path"] == str((overlay_root / "houmao-config.toml").resolve())


def test_project_status_reports_missing_env_selected_overlay_clearly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    overlay_root = (tmp_path / "ci-overlay").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(
        cli,
        ["project", "status"],
        env={PROJECT_OVERLAY_DIR_ENV_VAR: str(overlay_root)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["discovered"] is False
    assert payload["project_root"] is None
    assert payload["overlay_root"] == str(overlay_root)
    assert payload["overlay_root_source"] == "env"
    assert payload["overlay_discovery_mode"] == "ancestor"
    assert payload["config_path"] is None
    assert payload["effective_agent_def_dir"] == str((overlay_root / "agents").resolve())
    assert payload["effective_agent_def_dir_source"] == "project_overlay_env"
    assert payload["project_runtime_root"] == str((overlay_root / "runtime").resolve())
    assert payload["project_jobs_root"] == str((overlay_root / "jobs").resolve())
    assert payload["project_mailbox_root"] == str((overlay_root / "mailbox").resolve())
    assert payload["project_easy_root"] == str((overlay_root / "easy").resolve())
    assert payload["would_bootstrap_overlay"] is True
    assert (
        payload["selected_overlay_detail"]
        == f"Selected overlay root from `HOUMAO_PROJECT_OVERLAY_DIR`. No project overlay exists yet at `{overlay_root}` for this invocation."
    )
    assert (
        payload["overlay_bootstrap_detail"]
        == "Project status used non-creating resolution and would bootstrap the selected overlay during a stateful project command."
    )


def test_project_status_reports_would_bootstrap_root_without_creating_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    nested_dir = (repo_root / "app").resolve()
    nested_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(nested_dir)

    result = runner.invoke(cli, ["project", "status"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    expected_overlay_root = (nested_dir / ".houmao").resolve()
    assert payload["discovered"] is False
    assert payload["overlay_root"] == str(expected_overlay_root)
    assert payload["overlay_discovery_mode"] == "ancestor"
    assert payload["project_runtime_root"] == str((expected_overlay_root / "runtime").resolve())
    assert payload["project_jobs_root"] == str((expected_overlay_root / "jobs").resolve())
    assert payload["project_mailbox_root"] == str((expected_overlay_root / "mailbox").resolve())
    assert payload["project_easy_root"] == str((expected_overlay_root / "easy").resolve())
    assert payload["would_bootstrap_overlay"] is True
    assert (
        payload["selected_overlay_detail"]
        == f"Selected overlay root from the default project-aware `<cwd>/.houmao` candidate. No project overlay exists yet at `{expected_overlay_root}` for this invocation."
    )
    assert (
        payload["overlay_bootstrap_detail"]
        == "Project status used non-creating resolution and would bootstrap the selected overlay during a stateful project command."
    )
    assert not expected_overlay_root.exists()


def test_project_status_reports_cwd_only_mode_against_cwd_overlay_candidate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    nested_dir = (repo_root / "app").resolve()
    nested_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    monkeypatch.chdir(nested_dir)

    result = runner.invoke(
        cli,
        ["project", "status"],
        env={PROJECT_OVERLAY_DISCOVERY_MODE_ENV_VAR: "cwd_only"},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    expected_overlay_root = (nested_dir / ".houmao").resolve()
    assert payload["discovered"] is False
    assert payload["overlay_root"] == str(expected_overlay_root)
    assert payload["overlay_root_source"] == "default"
    assert payload["overlay_discovery_mode"] == "cwd_only"
    assert (
        payload["overlay_discovery_detail"]
        == "Ambient overlay discovery is restricted to `<cwd>/.houmao/houmao-config.toml` for this invocation."
    )
    assert (
        payload["selected_overlay_detail"]
        == f"Selected overlay root from the cwd-local project-aware `<cwd>/.houmao` candidate. No project overlay exists yet at `{expected_overlay_root}` for this invocation."
    )


def test_project_credentials_add_bootstraps_missing_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "codex",
            "add",
            "--name",
            "personal",
            "--api-key",
            "sk-openai",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (repo_root / ".houmao" / "houmao-config.toml").is_file()
    assert (
        _project_auth_root(repo_root, tool="codex", name="personal") / "env" / "vars.env"
    ).is_file()


def test_project_agents_tool_get_fails_without_bootstrapping_missing_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli, ["project", "agents", "tools", "codex", "get"])

    assert result.exit_code != 0
    assert str((repo_root / ".houmao").resolve()) in result.output
    assert "uses non-creating resolution and did not bootstrap it" in result.output
    assert not (repo_root / ".houmao").exists()


def test_project_agents_role_init_bootstraps_missing_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli, ["project", "agents", "roles", "init", "--name", "researcher"])

    assert result.exit_code == 0, result.output
    assert (repo_root / ".houmao" / "houmao-config.toml").is_file()
    assert (
        repo_root / ".houmao" / "agents" / "roles" / "researcher" / "system-prompt.md"
    ).is_file()


def test_project_agents_role_list_fails_without_bootstrapping_missing_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli, ["project", "agents", "roles", "list"])

    assert result.exit_code != 0
    assert str((repo_root / ".houmao").resolve()) in result.output
    assert "uses non-creating resolution and did not bootstrap it" in result.output
    assert not (repo_root / ".houmao").exists()


def test_project_credentials_get_and_project_tool_setups_flow(
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
                "credentials",
                "claude",
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
                "credentials",
                "codex",
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
                "credentials",
                "gemini",
                "add",
                "--name",
                "vertex",
                "--api-key",
                "sk-gemini",
                "--base-url",
                "https://gemini.example.test",
                "--oauth-creds",
                str(gemini_oauth_creds),
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
        ["project", "credentials", "claude", "get", "--name", "work"],
    )
    assert get_auth_result.exit_code == 0
    get_auth_payload = json.loads(get_auth_result.output)
    assert get_auth_payload["env"]["ANTHROPIC_API_KEY"] == {"present": True, "redacted": True}
    assert get_auth_payload["env"]["ANTHROPIC_BASE_URL"] == {
        "present": True,
        "value": "https://claude.example.test",
    }

    gemini_get_result = runner.invoke(
        cli,
        ["project", "credentials", "gemini", "get", "--name", "vertex"],
    )
    assert gemini_get_result.exit_code == 0
    gemini_get_payload = json.loads(gemini_get_result.output)
    assert gemini_get_payload["env"]["GEMINI_API_KEY"] == {"present": True, "redacted": True}
    assert gemini_get_payload["env"]["GOOGLE_GEMINI_BASE_URL"] == {
        "present": True,
        "value": "https://gemini.example.test",
    }
    assert gemini_get_payload["files"]["oauth_creds.json"]["present"] is True

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
            "presets",
            "add",
            "--name",
            "researcher-claude-default",
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
            "presets",
            "get",
            "--name",
            "researcher-claude-default",
        ],
    )
    assert preset_get_result.exit_code == 0
    preset_payload = json.loads(preset_get_result.output)
    assert preset_payload["name"] == "researcher-claude-default"
    assert preset_payload["skills"] == ["notes"]
    assert preset_payload["auth"] == "default"
    assert preset_payload["launch"] == {"prompt_mode": "unattended"}

    role_get_result = runner.invoke(
        cli, ["project", "agents", "roles", "get", "--name", "researcher"]
    )
    assert role_get_result.exit_code == 0
    role_payload = json.loads(role_get_result.output)
    assert role_payload["system_prompt_exists"] is True
    assert "system_prompt_text" not in role_payload
    assert len(role_payload["recipes"]) == 1

    role_remove_result = runner.invoke(
        cli,
        ["project", "agents", "roles", "remove", "--name", "researcher"],
    )
    assert role_remove_result.exit_code != 0
    assert "still reference" in role_remove_result.output

    preset_remove_result = runner.invoke(
        cli,
        ["project", "agents", "presets", "remove", "--name", "researcher-claude-default"],
    )
    assert preset_remove_result.exit_code == 0

    role_remove_result = runner.invoke(
        cli, ["project", "agents", "roles", "remove", "--name", "researcher"]
    )
    assert role_remove_result.exit_code == 0
    assert not (repo_root / ".houmao" / "agents" / "roles" / "researcher").exists()


def test_project_agents_roles_get_include_prompt_reports_prompt_text_and_empty_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    init_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "roles",
            "init",
            "--name",
            "researcher",
            "--system-prompt",
            "Investigate failures carefully.",
        ],
    )
    assert init_result.exit_code == 0, init_result.output

    default_get_result = runner.invoke(
        cli,
        ["project", "agents", "roles", "get", "--name", "researcher"],
    )
    assert default_get_result.exit_code == 0, default_get_result.output
    default_payload = json.loads(default_get_result.output)
    assert "system_prompt_text" not in default_payload

    include_prompt_result = runner.invoke(
        cli,
        ["project", "agents", "roles", "get", "--name", "researcher", "--include-prompt"],
    )
    assert include_prompt_result.exit_code == 0, include_prompt_result.output
    include_prompt_payload = json.loads(include_prompt_result.output)
    assert include_prompt_payload["system_prompt_exists"] is True
    assert include_prompt_payload["system_prompt_text"] == "Investigate failures carefully."

    clear_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "roles",
            "set",
            "--name",
            "researcher",
            "--clear-system-prompt",
        ],
    )
    assert clear_result.exit_code == 0, clear_result.output

    promptless_get_result = runner.invoke(
        cli,
        ["project", "agents", "roles", "get", "--name", "researcher", "--include-prompt"],
    )
    assert promptless_get_result.exit_code == 0, promptless_get_result.output
    promptless_payload = json.loads(promptless_get_result.output)
    assert promptless_payload["system_prompt_exists"] is True
    assert promptless_payload["system_prompt_text"] == ""


def test_project_agents_presets_set_preserves_advanced_blocks(
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
            "init",
            "--name",
            "researcher",
        ],
    )
    assert result.exit_code == 0, result.output

    preset_path = repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    preset_path.write_text(
        "\n".join(
            [
                "role: researcher",
                "tool: codex",
                "setup: default",
                "skills:",
                "  - notes",
                "auth: default",
                "launch:",
                "  prompt_mode: unattended",
                "  env_records:",
                '    FEATURE_FLAG_X: "1"',
                "mailbox:",
                "  transport: none",
                "extra:",
                "  gateway:",
                "    host: 127.0.0.1",
                "    port: 43123",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "presets",
            "set",
            "--name",
            "researcher-codex-default",
            "--auth",
            "reviewer-creds",
            "--add-skill",
            "extra-notes",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["auth"] == "reviewer-creds"
    assert payload["skills"] == ["notes", "extra-notes"]
    assert payload["launch"] == {
        "prompt_mode": "unattended",
        "env_records": {"FEATURE_FLAG_X": "1"},
    }
    assert payload["mailbox"] == {"transport": "none"}
    assert payload["extra"] == {"gateway": {"host": "127.0.0.1", "port": 43123}}


def test_project_agents_recipes_add_and_set_support_unified_model_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    assert (
        runner.invoke(
            cli,
            ["project", "agents", "roles", "init", "--name", "researcher"],
        ).exit_code
        == 0
    )

    add_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "recipes",
            "add",
            "--name",
            "researcher-codex-default",
            "--role",
            "researcher",
            "--tool",
            "codex",
            "--model",
            "gpt-5.4",
            "--reasoning-level",
            "6",
        ],
    )

    assert add_result.exit_code == 0, add_result.output
    get_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "agents", "recipes", "get", "--name", "researcher-codex-default"],
        ).output
    )
    assert get_payload["launch"] == {
        "prompt_mode": "unattended",
        "model": {"name": "gpt-5.4", "reasoning": {"level": 6}},
    }

    set_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "recipes",
            "set",
            "--name",
            "researcher-codex-default",
            "--clear-model",
            "--reasoning-level",
            "4",
        ],
    )

    assert set_result.exit_code == 0, set_result.output
    set_payload = json.loads(set_result.output)
    assert set_payload["launch"] == {
        "prompt_mode": "unattended",
        "model": {"reasoning": {"level": 4}},
    }

    clear_reasoning_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "recipes",
            "set",
            "--name",
            "researcher-codex-default",
            "--clear-reasoning-level",
        ],
    )

    assert clear_reasoning_result.exit_code == 0, clear_reasoning_result.output
    clear_payload = json.loads(clear_reasoning_result.output)
    assert clear_payload["launch"] == {"prompt_mode": "unattended"}


def test_project_agents_recipes_add_rejects_negative_reasoning_level(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "agents",
                "roles",
                "init",
                "--name",
                "researcher",
                "--system-prompt",
                "Research carefully.",
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "recipes",
            "add",
            "--name",
            "researcher-codex-default",
            "--role",
            "researcher",
            "--tool",
            "codex",
            "--reasoning-level",
            "-1",
        ],
    )

    assert result.exit_code != 0
    assert "--reasoning-level" in result.output


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
        repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
    ).is_file()
    assert (
        _project_auth_root(repo_root, tool="codex", name="researcher-creds") / "files" / "auth.json"
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
    assert get_payload["preset_name"] == "researcher-codex-default"
    assert get_payload["tool"] == "codex"
    assert get_payload["credential"] == "researcher-creds"
    assert get_payload["skills"] == ["notes"]
    assert get_payload["launch"] == {"prompt_mode": "unattended"}

    remove_result = runner.invoke(
        cli, ["project", "easy", "specialist", "remove", "--name", "researcher"]
    )
    assert remove_result.exit_code == 0
    assert metadata_path.is_file()
    assert not (repo_root / ".houmao" / "agents" / "roles" / "researcher").exists()
    assert (repo_root / ".houmao" / "agents" / "skills" / "notes" / "SKILL.md").is_file()
    assert (
        _project_auth_root(repo_root, tool="codex", name="researcher-creds") / "files" / "auth.json"
    ).is_file()
    list_after_remove = runner.invoke(cli, ["project", "easy", "specialist", "list"])
    assert list_after_remove.exit_code == 0
    assert json.loads(list_after_remove.output)["specialists"] == []


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


def test_project_easy_specialist_list_fails_without_bootstrapping_missing_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli, ["project", "easy", "specialist", "list"])

    assert result.exit_code != 0
    assert str((repo_root / ".houmao").resolve()) in result.output
    assert "uses non-creating resolution and did not bootstrap it" in result.output
    assert not (repo_root / ".houmao").exists()


def test_project_easy_specialist_create_can_persist_as_is_opt_out(
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
            "--no-unattended",
        ],
    )

    assert create_result.exit_code == 0, create_result.output
    create_payload = json.loads(create_result.output)
    preset_path = Path(create_payload["generated"]["preset"])
    preset_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "easy", "specialist", "get", "--name", "reviewer"],
        ).output
    )

    assert yaml.safe_load(preset_path.read_text(encoding="utf-8"))["launch"] == {
        "prompt_mode": "as_is"
    }
    assert preset_payload["launch"] == {"prompt_mode": "as_is"}


def test_project_credentials_gemini_set_preserves_api_key_when_updating_base_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    add_result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "gemini",
            "add",
            "--name",
            "proxy",
            "--api-key",
            "sk-gemini",
            "--base-url",
            "https://gemini.example.test",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    env_file = _project_auth_root(repo_root, tool="gemini", name="proxy") / "env" / "vars.env"
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "GEMINI_API_KEY=sk-gemini",
        "GOOGLE_GEMINI_BASE_URL=https://gemini.example.test",
    ]

    set_result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "gemini",
            "set",
            "--name",
            "proxy",
            "--base-url",
            "https://gemini-alt.example.test",
        ],
    )
    assert set_result.exit_code == 0, set_result.output
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "GEMINI_API_KEY=sk-gemini",
        "GOOGLE_GEMINI_BASE_URL=https://gemini-alt.example.test",
    ]

    clear_result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "gemini",
            "set",
            "--name",
            "proxy",
            "--clear-base-url",
        ],
    )
    assert clear_result.exit_code == 0, clear_result.output
    assert env_file.read_text(encoding="utf-8").splitlines() == ["GEMINI_API_KEY=sk-gemini"]


def test_project_credentials_gemini_add_supports_oauth_only_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    oauth_creds = tmp_path / "oauth_creds.json"
    oauth_creds.write_text('{"refresh_token": "token"}\n', encoding="utf-8")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "gemini",
            "add",
            "--name",
            "personal",
            "--oauth-creds",
            str(oauth_creds),
        ],
    )

    assert result.exit_code == 0, result.output
    oauth_bundle_file = (
        _project_auth_root(repo_root, tool="gemini", name="personal") / "files" / "oauth_creds.json"
    )
    assert oauth_bundle_file.is_file()
    assert oauth_bundle_file.read_text(encoding="utf-8") == '{"refresh_token": "token"}\n'


def test_project_credentials_claude_add_supports_oauth_only_bundle(
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
            "credentials",
            "claude",
            "add",
            "--name",
            "oauth-only",
            "--oauth-token",
            "oauth-token-123",
            "--base-url",
            "https://claude.example.test",
        ],
    )

    assert result.exit_code == 0, result.output
    env_file = _project_auth_root(repo_root, tool="claude", name="oauth-only") / "env" / "vars.env"
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "CLAUDE_CODE_OAUTH_TOKEN=oauth-token-123",
        "ANTHROPIC_BASE_URL=https://claude.example.test",
    ]

    get_result = runner.invoke(
        cli,
        ["project", "credentials", "claude", "get", "--name", "oauth-only"],
    )
    assert get_result.exit_code == 0, get_result.output
    payload = json.loads(get_result.output)
    assert payload["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == {"present": True, "redacted": True}
    assert payload["env"]["ANTHROPIC_BASE_URL"] == {
        "present": True,
        "value": "https://claude.example.test",
    }


def test_project_credentials_claude_set_refreshes_config_dir_import_without_clearing_other_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    template_path = tmp_path / "claude-state-template.json"
    template_path.write_text('{"custom": {"keep": true}}\n', encoding="utf-8")
    config_dir_a = _make_claude_config_dir(tmp_path, "vendor-a", token_suffix="alpha")
    config_dir_b = _make_claude_config_dir(tmp_path, "vendor-b", token_suffix="beta")
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0

    add_result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "claude",
            "add",
            "--name",
            "vendor-login",
            "--oauth-token",
            "oauth-token-123",
            "--base-url",
            "https://claude.example.test",
            "--state-template-file",
            str(template_path),
            "--config-dir",
            str(config_dir_a),
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    auth_root = _project_auth_root(repo_root, tool="claude", name="vendor-login")
    files_root = auth_root / "files"
    assert json.loads((files_root / ".credentials.json").read_text(encoding="utf-8")) == {
        "claudeAiOauth": {"accessToken": "vendor-alpha"}
    }
    assert json.loads((files_root / ".claude.json").read_text(encoding="utf-8")) == {
        "hasCompletedOnboarding": True,
        "numStartups": 5,
    }
    assert json.loads((files_root / "claude_state.template.json").read_text(encoding="utf-8")) == {
        "custom": {"keep": True}
    }

    set_result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "claude",
            "set",
            "--name",
            "vendor-login",
            "--config-dir",
            str(config_dir_b),
            "--model",
            "claude-sonnet-4-5",
        ],
    )
    assert set_result.exit_code == 0, set_result.output

    assert json.loads((files_root / ".credentials.json").read_text(encoding="utf-8")) == {
        "claudeAiOauth": {"accessToken": "vendor-beta"}
    }
    assert json.loads((files_root / ".claude.json").read_text(encoding="utf-8")) == {
        "hasCompletedOnboarding": True,
        "numStartups": 4,
    }
    assert json.loads((files_root / "claude_state.template.json").read_text(encoding="utf-8")) == {
        "custom": {"keep": True}
    }
    env_file = auth_root / "env" / "vars.env"
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "CLAUDE_CODE_OAUTH_TOKEN=oauth-token-123",
        "ANTHROPIC_BASE_URL=https://claude.example.test",
        "ANTHROPIC_MODEL=claude-sonnet-4-5",
    ]

    get_result = runner.invoke(
        cli,
        ["project", "credentials", "claude", "get", "--name", "vendor-login"],
    )
    assert get_result.exit_code == 0, get_result.output
    payload = json.loads(get_result.output)
    assert payload["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == {"present": True, "redacted": True}
    assert payload["files"][".credentials.json"]["present"] is True
    assert payload["files"][".claude.json"]["present"] is True
    assert "vendor-alpha" not in get_result.output
    assert "vendor-beta" not in get_result.output

    clear_result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "claude",
            "set",
            "--name",
            "vendor-login",
            "--clear-config-dir",
        ],
    )
    assert clear_result.exit_code == 0, clear_result.output
    assert not (files_root / ".credentials.json").exists()
    assert not (files_root / ".claude.json").exists()
    assert (files_root / "claude_state.template.json").is_file()


def test_project_credentials_rename_preserves_identity_and_updates_launch_profile_display_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    assert (
        runner.invoke(
            cli,
            ["project", "agents", "roles", "init", "--name", "reviewer"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "agents",
                "recipes",
                "add",
                "--name",
                "reviewer-codex-default",
                "--role",
                "reviewer",
                "--tool",
                "codex",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "credentials",
                "codex",
                "add",
                "--name",
                "work",
                "--api-key",
                "sk-openai",
            ],
        ).exit_code
        == 0
    )

    initial_auth_result = runner.invoke(
        cli,
        ["project", "credentials", "codex", "get", "--name", "work"],
    )
    assert initial_auth_result.exit_code == 0, initial_auth_result.output
    initial_auth_payload = json.loads(initial_auth_result.output)
    initial_projection_path = Path(initial_auth_payload["path"])
    assert initial_projection_path.is_dir()

    add_profile_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "add",
            "--name",
            "reviewer-default",
            "--recipe",
            "reviewer-codex-default",
            "--auth",
            "work",
        ],
    )
    assert add_profile_result.exit_code == 0, add_profile_result.output

    rename_result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "codex",
            "rename",
            "--name",
            "work",
            "--to",
            "breakglass",
        ],
    )
    assert rename_result.exit_code == 0, rename_result.output
    rename_payload = json.loads(rename_result.output)
    assert rename_payload["previous_name"] == "work"
    assert rename_payload["name"] == "breakglass"
    assert rename_payload["bundle_ref"] == initial_auth_payload["bundle_ref"]
    assert Path(rename_payload["path"]) == initial_projection_path
    assert initial_projection_path.is_dir()

    old_auth_result = runner.invoke(
        cli,
        ["project", "credentials", "codex", "get", "--name", "work"],
    )
    assert old_auth_result.exit_code != 0

    renamed_auth_result = runner.invoke(
        cli,
        ["project", "credentials", "codex", "get", "--name", "breakglass"],
    )
    assert renamed_auth_result.exit_code == 0, renamed_auth_result.output
    renamed_auth_payload = json.loads(renamed_auth_result.output)
    assert renamed_auth_payload["bundle_ref"] == initial_auth_payload["bundle_ref"]
    assert Path(renamed_auth_payload["path"]) == initial_projection_path

    launch_profile_result = runner.invoke(
        cli,
        ["project", "agents", "launch-profiles", "get", "--name", "reviewer-default"],
    )
    assert launch_profile_result.exit_code == 0, launch_profile_result.output
    launch_profile_payload = json.loads(launch_profile_result.output)
    assert launch_profile_payload["defaults"]["auth"] == "breakglass"


def test_project_easy_specialist_get_derives_current_auth_display_name_after_credential_rename(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
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
    )
    assert create_result.exit_code == 0, create_result.output

    initial_auth_result = runner.invoke(
        cli,
        ["project", "credentials", "codex", "get", "--name", "work"],
    )
    assert initial_auth_result.exit_code == 0, initial_auth_result.output
    initial_auth_payload = json.loads(initial_auth_result.output)

    rename_result = runner.invoke(
        cli,
        [
            "project",
            "credentials",
            "codex",
            "rename",
            "--name",
            "work",
            "--to",
            "breakglass",
        ],
    )
    assert rename_result.exit_code == 0, rename_result.output
    rename_payload = json.loads(rename_result.output)
    assert rename_payload["bundle_ref"] == initial_auth_payload["bundle_ref"]

    specialist_result = runner.invoke(
        cli,
        ["project", "easy", "specialist", "get", "--name", "researcher"],
    )
    assert specialist_result.exit_code == 0, specialist_result.output
    specialist_payload = json.loads(specialist_result.output)
    assert specialist_payload["credential"] == "breakglass"

    recipe_result = runner.invoke(
        cli,
        ["project", "agents", "recipes", "get", "--name", "researcher-codex-default"],
    )
    assert recipe_result.exit_code == 0, recipe_result.output
    recipe_payload = json.loads(recipe_result.output)
    assert recipe_payload["auth"] == "breakglass"


def test_project_easy_specialist_create_supports_claude_oauth_token_lane(
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
            "claude-reviewer",
            "--tool",
            "claude",
            "--system-prompt",
            "You review code with Claude.",
            "--claude-oauth-token",
            "oauth-token-123",
        ],
    )

    assert result.exit_code == 0, result.output
    env_file = (
        _project_auth_root(repo_root, tool="claude", name="claude-reviewer-creds")
        / "env"
        / "vars.env"
    )
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "CLAUDE_CODE_OAUTH_TOKEN=oauth-token-123"
    ]
    specialist_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "easy", "specialist", "get", "--name", "claude-reviewer"],
        ).output
    )
    assert specialist_payload["tool"] == "claude"
    assert specialist_payload["launch"] == {"prompt_mode": "unattended"}


def test_project_easy_specialist_create_supports_claude_config_dir_lane_without_state_template(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    config_dir = _make_claude_config_dir(tmp_path, "vendor-specialist", token_suffix="gamma")
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
            "claude-imported",
            "--tool",
            "claude",
            "--system-prompt",
            "You use imported Claude vendor auth.",
            "--claude-config-dir",
            str(config_dir),
            "--claude-model",
            "claude-sonnet-4-5",
        ],
    )

    assert result.exit_code == 0, result.output
    auth_root = _project_auth_root(repo_root, tool="claude", name="claude-imported-creds")
    assert json.loads((auth_root / "files" / ".credentials.json").read_text(encoding="utf-8")) == {
        "claudeAiOauth": {"accessToken": "vendor-gamma"}
    }
    assert json.loads((auth_root / "files" / ".claude.json").read_text(encoding="utf-8")) == {
        "hasCompletedOnboarding": True,
        "numStartups": 5,
    }
    assert not (auth_root / "files" / "claude_state.template.json").exists()
    assert (auth_root / "env" / "vars.env").read_text(encoding="utf-8").strip() == ""

    specialist_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "easy", "specialist", "get", "--name", "claude-imported"],
        ).output
    )
    assert specialist_payload["tool"] == "claude"
    assert specialist_payload["credential"] == "claude-imported-creds"
    assert specialist_payload["launch"] == {
        "prompt_mode": "unattended",
        "model": {"name": "claude-sonnet-4-5"},
    }


def test_project_easy_specialist_create_persists_unified_model_config(
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

    result = runner.invoke(
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
            "--system-prompt",
            "You review code precisely.",
            "--api-key",
            "sk-openai",
            "--codex-auth-json",
            str(auth_json_path),
            "--model",
            "gpt-5.4",
            "--reasoning-level",
            "6",
        ],
    )

    assert result.exit_code == 0, result.output
    preset_path = repo_root / ".houmao" / "agents" / "presets" / "reviewer-codex-default.yaml"
    assert yaml.safe_load(preset_path.read_text(encoding="utf-8"))["launch"] == {
        "prompt_mode": "unattended",
        "model": {"name": "gpt-5.4", "reasoning": {"level": 6}},
    }
    specialist_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "easy", "specialist", "get", "--name", "reviewer"],
        ).output
    )
    assert specialist_payload["launch"] == {
        "prompt_mode": "unattended",
        "model": {"name": "gpt-5.4", "reasoning": {"level": 6}},
    }


def test_project_easy_specialist_create_supports_gemini_base_url_and_oauth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    oauth_creds = tmp_path / "oauth_creds.json"
    oauth_creds.write_text('{"refresh_token": "token"}\n', encoding="utf-8")
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
            "gemini-reviewer",
            "--tool",
            "gemini",
            "--system-prompt",
            "You are a Gemini reviewer.",
            "--api-key",
            "sk-gemini",
            "--base-url",
            "https://gemini.example.test",
            "--gemini-oauth-creds",
            str(oauth_creds),
        ],
    )

    assert result.exit_code == 0, result.output
    env_file = (
        _project_auth_root(repo_root, tool="gemini", name="gemini-reviewer-creds")
        / "env"
        / "vars.env"
    )
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "GEMINI_API_KEY=sk-gemini",
        "GOOGLE_GEMINI_BASE_URL=https://gemini.example.test",
    ]
    assert (
        _project_auth_root(repo_root, tool="gemini", name="gemini-reviewer-creds")
        / "files"
        / "oauth_creds.json"
    ).is_file()
    specialist_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "easy", "specialist", "get", "--name", "gemini-reviewer"],
        ).output
    )
    assert specialist_payload["tool"] == "gemini"
    assert specialist_payload["launch"] == {"prompt_mode": "unattended"}


def test_project_easy_specialist_create_gemini_no_unattended_persists_as_is(
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
            "gemini-reviewer",
            "--tool",
            "gemini",
            "--system-prompt",
            "You are a Gemini reviewer.",
            "--api-key",
            "sk-gemini",
            "--no-unattended",
        ],
    )

    assert result.exit_code == 0, result.output
    specialist_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "easy", "specialist", "get", "--name", "gemini-reviewer"],
        ).output
    )
    assert specialist_payload["launch"] == {"prompt_mode": "as_is"}


def test_project_easy_specialist_create_prompts_before_replacing_existing_specialist(
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
                "--tool",
                "codex",
                "--system-prompt",
                "Initial prompt",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
                "--with-skill",
                str(skill_dir),
                "--no-unattended",
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: True,
    )

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
            "Replacement prompt",
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    prompt_path = repo_root / ".houmao" / "agents" / "roles" / "researcher" / "system-prompt.md"
    preset_path = repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
    assert prompt_path.read_text(encoding="utf-8") == "Replacement prompt\n"
    assert yaml.safe_load(preset_path.read_text(encoding="utf-8"))["launch"] == {
        "prompt_mode": "unattended"
    }
    assert (
        _project_auth_root(repo_root, tool="codex", name="researcher-creds") / "files" / "auth.json"
    ).is_file()
    assert (repo_root / ".houmao" / "agents" / "skills" / "notes" / "SKILL.md").is_file()


def test_project_easy_specialist_create_noninteractive_conflict_requires_yes(
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
                "--tool",
                "codex",
                "--system-prompt",
                "Initial prompt",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: False,
    )

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
            "Replacement prompt",
        ],
    )

    assert result.exit_code != 0
    assert "Rerun with `--yes`" in result.output
    prompt_path = repo_root / ".houmao" / "agents" / "roles" / "researcher" / "system-prompt.md"
    assert prompt_path.read_text(encoding="utf-8") == "Initial prompt\n"


def test_project_easy_specialist_create_yes_replaces_existing_specialist(
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
                "--tool",
                "codex",
                "--system-prompt",
                "Initial prompt",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
                "--with-skill",
                str(skill_dir),
                "--no-unattended",
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: False,
    )

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
            "Replacement prompt",
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.output
    prompt_path = repo_root / ".houmao" / "agents" / "roles" / "researcher" / "system-prompt.md"
    preset_path = repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
    assert prompt_path.read_text(encoding="utf-8") == "Replacement prompt\n"
    assert yaml.safe_load(preset_path.read_text(encoding="utf-8"))["launch"] == {
        "prompt_mode": "unattended"
    }
    assert (
        _project_auth_root(repo_root, tool="codex", name="researcher-creds") / "files" / "auth.json"
    ).is_file()
    assert (repo_root / ".houmao" / "agents" / "skills" / "notes" / "SKILL.md").is_file()


def test_project_easy_specialist_create_persists_env_records(
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
            "researcher",
            "--tool",
            "codex",
            "--api-key",
            "sk-openai",
            "--codex-auth-json",
            str(auth_json_path),
            "--env-set",
            "OPENAI_MODEL=gpt-5.4",
            "--env-set",
            "FEATURE_FLAG_X=1",
        ],
    )

    assert create_result.exit_code == 0, create_result.output
    create_payload = json.loads(create_result.output)
    preset_path = Path(create_payload["generated"]["preset"])
    preset_payload = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
    specialist_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "easy", "specialist", "get", "--name", "researcher"],
        ).output
    )

    assert preset_payload["launch"] == {
        "prompt_mode": "unattended",
        "env_records": {
            "OPENAI_MODEL": "gpt-5.4",
            "FEATURE_FLAG_X": "1",
        },
    }
    assert specialist_payload["launch"] == preset_payload["launch"]


def test_project_easy_specialist_create_persists_non_default_setup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    _clone_setup_dir(repo_root, tool="codex", source="default", target="yunwu-openai")

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
            "--setup",
            "yunwu-openai",
            "--api-key",
            "sk-openai",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    specialist_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "easy", "specialist", "get", "--name", "researcher"],
        ).output
    )

    assert payload["setup"] == "yunwu-openai"
    assert payload["generated"]["preset"].endswith("/researcher-codex-yunwu-openai.yaml")
    assert specialist_payload["setup"] == "yunwu-openai"
    assert specialist_payload["generated"]["preset"].endswith("/researcher-codex-yunwu-openai.yaml")


@pytest.mark.parametrize("tool_name", ["claude", "codex", "gemini"])
def test_project_easy_specialist_create_persists_default_setup_for_supported_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tool_name: str,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / f"repo-{tool_name}").resolve()
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
            tool_name,
            "--api-key",
            "sk-openai",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    assert payload["setup"] == "default"
    assert payload["generated"]["preset"].endswith(f"/researcher-{tool_name}-default.yaml")


def test_project_easy_instance_launch_rejects_gemini_without_headless(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
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
                "gemini-reviewer",
                "--tool",
                "gemini",
                "--system-prompt",
                "You are a Gemini reviewer.",
                "--api-key",
                "sk-gemini",
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
            "gemini-reviewer",
            "--name",
            "gemini-reviewer-1",
        ],
    )

    assert result.exit_code != 0
    assert "Gemini specialists are currently headless-only" in result.output


def test_project_easy_instance_launch_rejects_removed_yolo_flag(tmp_path: Path) -> None:
    runner = CliRunner()

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
            "--yolo",
        ],
    )

    assert result.exit_code != 0
    assert "No such option: --yolo" in result.output


def test_project_easy_instance_launch_uses_stored_specialist_setup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    assert runner.invoke(cli, ["project", "init"]).exit_code == 0
    _clone_setup_dir(repo_root, tool="codex", source="default", target="yunwu-openai")
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
                "--tool",
                "codex",
                "--setup",
                "yunwu-openai",
                "--api-key",
                "sk-openai",
            ],
        ).exit_code
        == 0
    )

    shutil.rmtree(repo_root / ".houmao" / "agents" / "roles" / "researcher")
    captured: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> SimpleNamespace:
        preset_path = (
            repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-yunwu-openai.yaml"
        )
        assert preset_path.is_file()
        assert not (
            repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
        ).exists()
        captured.update(kwargs)
        manifest_path = (tmp_path / "manifest.json").resolve()
        manifest_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            agent_identity=kwargs["agent_name"],
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _fake_launch,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
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
            "--headless",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["agents"] == str(
        repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-yunwu-openai.yaml"
    )


def test_project_easy_specialist_create_rejects_credential_owned_env_names(
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
            "--api-key",
            "sk-openai",
            "--codex-auth-json",
            str(auth_json_path),
            "--env-set",
            "OPENAI_API_KEY=other",
        ],
    )

    assert result.exit_code != 0
    assert "belongs to credential env" in result.output


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


def test_project_agents_launch_profiles_crud_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
    shared_memory_dir = (repo_root.parent / "shared" / "alice-memory").resolve()
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
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "credentials",
                "codex",
                "add",
                "--name",
                "alice-creds",
                "--api-key",
                "sk-openai",
                "--auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    add_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "add",
            "--name",
            "alice",
            "--recipe",
            "researcher-codex-default",
            "--agent-name",
            "alice",
            "--agent-id",
            "agent-alice",
            "--workdir",
            "/repos/alice",
            "--auth",
            "alice-creds",
            "--memory-dir",
            "../shared/alice-memory",
            "--model",
            "gpt-5.4-mini",
            "--reasoning-level",
            "4",
            "--prompt-mode",
            "unattended",
            "--env-set",
            "PROJECT_CONTEXT=alice",
            "--mail-transport",
            "filesystem",
            "--mail-principal-id",
            "alice",
            "--mail-address",
            "alice@agents.localhost",
            "--mail-root",
            "/mail-root",
            "--gateway-port",
            "9011",
            "--prompt-overlay-mode",
            "append",
            "--prompt-overlay-text",
            "Prefer Alice repository conventions.",
        ],
    )

    assert add_result.exit_code == 0, add_result.output
    add_payload = json.loads(add_result.output)
    assert add_payload["profile_lane"] == "launch-profile"
    assert add_payload["recipe"] == "researcher-codex-default"
    assert add_payload["defaults"] == {
        "agent_name": "alice",
        "agent_id": "agent-alice",
        "workdir": "/repos/alice",
        "auth": "alice-creds",
        "memory_binding": "exact",
        "memory_dir": str(shared_memory_dir),
        "model": {"name": "gpt-5.4-mini", "reasoning": {"level": 4}},
        "prompt_mode": "unattended",
        "env": {"PROJECT_CONTEXT": "alice"},
        "mailbox": {
            "transport": "filesystem",
            "principal_id": "alice",
            "address": "alice@agents.localhost",
            "filesystem_root": "/mail-root",
        },
        "posture": {
            "gateway_auto_attach": True,
            "gateway_host": "127.0.0.1",
            "gateway_port": 9011,
        },
        "managed_header": "inherit",
        "prompt_overlay": {
            "mode": "append",
            "present": True,
        },
    }
    assert (repo_root / ".houmao" / "agents" / "launch-profiles" / "alice.yaml").is_file()

    get_result = runner.invoke(
        cli, ["project", "agents", "launch-profiles", "get", "--name", "alice"]
    )
    assert get_result.exit_code == 0, get_result.output
    get_payload = json.loads(get_result.output)
    assert get_payload["source"] == {
        "kind": "recipe",
        "name": "researcher-codex-default",
        "exists": True,
        "path": str(
            (
                repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
            ).resolve()
        ),
        "recipe": "researcher-codex-default",
        "recipe_path": str(
            (
                repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
            ).resolve()
        ),
        "tool": "codex",
        "provider": "codex",
        "role_name": "researcher",
    }

    list_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "list",
            "--recipe",
            "researcher-codex-default",
            "--tool",
            "codex",
        ],
    )
    assert list_result.exit_code == 0, list_result.output
    list_payload = json.loads(list_result.output)
    assert [item["name"] for item in list_payload["launch_profiles"]] == ["alice"]

    assert (
        runner.invoke(
            cli,
            [
                "project",
                "credentials",
                "codex",
                "add",
                "--name",
                "reviewer-creds",
                "--api-key",
                "sk-openai",
                "--auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    set_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "set",
            "--name",
            "alice",
            "--auth",
            "reviewer-creds",
            "--clear-model",
        ],
    )
    assert set_result.exit_code == 0, set_result.output
    set_payload = json.loads(set_result.output)
    assert set_payload["defaults"]["auth"] == "reviewer-creds"
    assert set_payload["defaults"]["memory_binding"] == "exact"
    assert set_payload["defaults"]["memory_dir"] == str(shared_memory_dir)
    assert set_payload["defaults"]["model"] == {"reasoning": {"level": 4}}
    assert set_payload["defaults"]["mailbox"]["transport"] == "filesystem"
    assert set_payload["defaults"]["prompt_overlay"]["present"] is True

    remove_result = runner.invoke(
        cli, ["project", "agents", "launch-profiles", "remove", "--name", "alice"]
    )
    assert remove_result.exit_code == 0, remove_result.output
    remove_payload = json.loads(remove_result.output)
    assert remove_payload["removed"] is True
    assert not (repo_root / ".houmao" / "agents" / "launch-profiles" / "alice.yaml").exists()
    assert (
        repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
    ).is_file()


def test_project_easy_profile_crud_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
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
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "credentials",
                "codex",
                "add",
                "--name",
                "alice-creds",
                "--api-key",
                "sk-openai",
                "--auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )
    create_result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "profile",
            "create",
            "--name",
            "alice",
            "--specialist",
            "researcher",
            "--agent-name",
            "alice",
            "--workdir",
            "/repos/alice",
            "--auth",
            "alice-creds",
            "--no-memory-dir",
            "--model",
            "gpt-5.4-mini",
            "--reasoning-level",
            "4",
            "--prompt-overlay-mode",
            "replace",
            "--prompt-overlay-text",
            "Operate only on Alice-owned repositories.",
        ],
    )

    assert create_result.exit_code == 0, create_result.output
    create_payload = json.loads(create_result.output)
    assert create_payload["profile_lane"] == "easy-profile"
    assert create_payload["specialist"] == "researcher"
    assert create_payload["defaults"]["agent_name"] == "alice"
    assert create_payload["defaults"]["memory_binding"] == "disabled"
    assert create_payload["defaults"]["memory_dir"] is None
    assert create_payload["defaults"]["model"] == {
        "name": "gpt-5.4-mini",
        "reasoning": {"level": 4},
    }
    assert create_payload["defaults"]["managed_header"] == "inherit"
    assert create_payload["defaults"]["prompt_overlay"] == {
        "mode": "replace",
        "present": True,
    }

    list_result = runner.invoke(cli, ["project", "easy", "profile", "list"])
    assert list_result.exit_code == 0, list_result.output
    list_payload = json.loads(list_result.output)
    assert [item["name"] for item in list_payload["profiles"]] == ["alice"]

    get_result = runner.invoke(cli, ["project", "easy", "profile", "get", "--name", "alice"])
    assert get_result.exit_code == 0, get_result.output
    get_payload = json.loads(get_result.output)
    assert get_payload["profile_lane"] == "easy-profile"
    assert get_payload["specialist"] == "researcher"
    assert get_payload["defaults"]["auth"] == "alice-creds"

    remove_result = runner.invoke(cli, ["project", "easy", "profile", "remove", "--name", "alice"])
    assert remove_result.exit_code == 0, remove_result.output
    remove_payload = json.loads(remove_result.output)
    assert remove_payload["removed"] is True
    assert (
        runner.invoke(
            cli,
            ["project", "easy", "specialist", "get", "--name", "researcher"],
        ).exit_code
        == 0
    )


def test_project_easy_profile_set_patches_defaults_and_preserves_prompt_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, repo_root, auth_json_path = _bootstrap_codex_researcher_project(
        monkeypatch,
        tmp_path,
    )

    assert (
        runner.invoke(
            cli,
            [
                "project",
                "credentials",
                "codex",
                "add",
                "--name",
                "reviewer-creds",
                "--api-key",
                "sk-openai",
                "--auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )
    create_result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "profile",
            "create",
            "--name",
            "alice",
            "--specialist",
            "researcher",
            "--workdir",
            "/repos/alice",
            "--auth",
            "work",
            "--mail-transport",
            "filesystem",
            "--mail-principal-id",
            "alice",
            "--mail-address",
            "alice@agents.localhost",
            "--mail-root",
            "/mail-root",
            "--prompt-overlay-mode",
            "append",
            "--prompt-overlay-text",
            "Prefer Alice repository conventions.",
        ],
    )
    assert create_result.exit_code == 0, create_result.output

    set_result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "profile",
            "set",
            "--name",
            "alice",
            "--workdir",
            "/repos/alice-next",
            "--auth",
            "reviewer-creds",
        ],
    )

    assert set_result.exit_code == 0, set_result.output
    set_payload = json.loads(set_result.output)
    assert set_payload["defaults"]["workdir"] == "/repos/alice-next"
    assert set_payload["defaults"]["auth"] == "reviewer-creds"
    assert set_payload["defaults"]["mailbox"]["transport"] == "filesystem"
    assert set_payload["defaults"]["prompt_overlay"] == {
        "mode": "append",
        "present": True,
    }

    projection = yaml.safe_load(
        (repo_root / ".houmao" / "agents" / "launch-profiles" / "alice.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert projection["defaults"]["workdir"] == "/repos/alice-next"
    assert projection["defaults"]["prompt_overlay"] == {
        "mode": "append",
        "text": "Prefer Alice repository conventions.",
    }


def test_project_easy_profile_create_yes_replaces_and_clears_omitted_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, repo_root, auth_json_path = _bootstrap_codex_researcher_project(
        monkeypatch,
        tmp_path,
    )
    _create_codex_specialist(
        runner,
        name="reviewer-v2",
        credential="work-v2",
        auth_json_path=auth_json_path,
    )
    create_result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "profile",
            "create",
            "--name",
            "alice",
            "--specialist",
            "researcher",
            "--workdir",
            "/repos/alice",
            "--mail-transport",
            "filesystem",
            "--mail-principal-id",
            "alice",
            "--mail-address",
            "alice@agents.localhost",
            "--mail-root",
            "/mail-root",
            "--prompt-overlay-mode",
            "replace",
            "--prompt-overlay-text",
            "Operate only on Alice-owned repositories.",
        ],
    )
    assert create_result.exit_code == 0, create_result.output

    replace_result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "profile",
            "create",
            "--name",
            "alice",
            "--specialist",
            "reviewer-v2",
            "--workdir",
            "/repos/alice-v2",
            "--yes",
        ],
    )

    assert replace_result.exit_code == 0, replace_result.output
    replace_payload = json.loads(replace_result.output)
    assert replace_payload["specialist"] == "reviewer-v2"
    assert replace_payload["defaults"]["workdir"] == "/repos/alice-v2"
    assert "mailbox" not in replace_payload["defaults"]
    assert "prompt_overlay" not in replace_payload["defaults"]

    projection = yaml.safe_load(
        (repo_root / ".houmao" / "agents" / "launch-profiles" / "alice.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert projection["source"] == {"kind": "specialist", "name": "reviewer-v2"}
    assert projection["defaults"]["workdir"] == "/repos/alice-v2"
    assert "mailbox" not in projection["defaults"]
    assert "prompt_overlay" not in projection["defaults"]


def test_project_launch_profile_add_yes_replaces_and_clears_omitted_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, repo_root, auth_json_path = _bootstrap_codex_researcher_project(
        monkeypatch,
        tmp_path,
    )
    _create_codex_specialist(
        runner,
        name="reviewer-v2",
        credential="work-v2",
        auth_json_path=auth_json_path,
    )
    add_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "add",
            "--name",
            "alice",
            "--recipe",
            "researcher-codex-default",
            "--workdir",
            "/repos/alice",
            "--mail-transport",
            "filesystem",
            "--mail-principal-id",
            "alice",
            "--mail-address",
            "alice@agents.localhost",
            "--mail-root",
            "/mail-root",
            "--prompt-overlay-mode",
            "append",
            "--prompt-overlay-text",
            "Prefer Alice repository conventions.",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    replace_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "add",
            "--name",
            "alice",
            "--recipe",
            "reviewer-v2-codex-default",
            "--workdir",
            "/repos/alice-v2",
            "--yes",
        ],
    )

    assert replace_result.exit_code == 0, replace_result.output
    replace_payload = json.loads(replace_result.output)
    assert replace_payload["recipe"] == "reviewer-v2-codex-default"
    assert replace_payload["defaults"]["workdir"] == "/repos/alice-v2"
    assert "mailbox" not in replace_payload["defaults"]
    assert "prompt_overlay" not in replace_payload["defaults"]

    projection = yaml.safe_load(
        (repo_root / ".houmao" / "agents" / "launch-profiles" / "alice.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert projection["source"] == {"kind": "recipe", "name": "reviewer-v2-codex-default"}
    assert projection["defaults"]["workdir"] == "/repos/alice-v2"
    assert "mailbox" not in projection["defaults"]
    assert "prompt_overlay" not in projection["defaults"]


def test_project_launch_profile_replacement_requires_yes_noninteractive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, repo_root, _auth_json_path = _bootstrap_codex_researcher_project(
        monkeypatch,
        tmp_path,
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "easy",
                "profile",
                "create",
                "--name",
                "alice",
                "--specialist",
                "researcher",
                "--workdir",
                "/repos/alice",
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
                "launch-profiles",
                "add",
                "--name",
                "nightly",
                "--recipe",
                "researcher-codex-default",
                "--workdir",
                "/repos/nightly",
            ],
        ).exit_code
        == 0
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.common.has_interactive_terminal",
        lambda *streams: False,
    )

    easy_result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "profile",
            "create",
            "--name",
            "alice",
            "--specialist",
            "researcher",
            "--workdir",
            "/repos/alice-v2",
        ],
    )
    explicit_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "add",
            "--name",
            "nightly",
            "--recipe",
            "researcher-codex-default",
            "--workdir",
            "/repos/nightly-v2",
        ],
    )

    assert easy_result.exit_code != 0
    assert "Rerun with `--yes`" in easy_result.output
    assert explicit_result.exit_code != 0
    assert "Rerun with `--yes`" in explicit_result.output
    easy_payload = json.loads(
        runner.invoke(cli, ["project", "easy", "profile", "get", "--name", "alice"]).output
    )
    explicit_payload = json.loads(
        runner.invoke(
            cli,
            ["project", "agents", "launch-profiles", "get", "--name", "nightly"],
        ).output
    )
    assert easy_payload["defaults"]["workdir"] == "/repos/alice"
    assert explicit_payload["defaults"]["workdir"] == "/repos/nightly"
    assert (repo_root / ".houmao" / "agents" / "launch-profiles" / "alice.yaml").is_file()


def test_project_launch_profile_replacement_rejects_cross_lane_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, _repo_root, _auth_json_path = _bootstrap_codex_researcher_project(
        monkeypatch,
        tmp_path,
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "easy",
                "profile",
                "create",
                "--name",
                "alice",
                "--specialist",
                "researcher",
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
                "launch-profiles",
                "add",
                "--name",
                "nightly",
                "--recipe",
                "researcher-codex-default",
            ],
        ).exit_code
        == 0
    )

    explicit_over_easy_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "add",
            "--name",
            "alice",
            "--recipe",
            "researcher-codex-default",
            "--yes",
        ],
    )
    easy_over_explicit_result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "profile",
            "create",
            "--name",
            "nightly",
            "--specialist",
            "researcher",
            "--yes",
        ],
    )

    assert explicit_over_easy_result.exit_code != 0
    assert "not an available `launch-profile` definition" in explicit_over_easy_result.output
    assert easy_over_explicit_result.exit_code != 0
    assert "not an available `easy-profile` definition" in easy_over_explicit_result.output
    assert (
        json.loads(
            runner.invoke(cli, ["project", "easy", "profile", "get", "--name", "alice"]).output
        )["profile_lane"]
        == "easy-profile"
    )
    assert (
        json.loads(
            runner.invoke(
                cli,
                ["project", "agents", "launch-profiles", "get", "--name", "nightly"],
            ).output
        )["profile_lane"]
        == "launch-profile"
    )


def test_project_easy_profile_set_without_updates_fails_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, _repo_root, _auth_json_path = _bootstrap_codex_researcher_project(
        monkeypatch,
        tmp_path,
    )
    create_result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "profile",
            "create",
            "--name",
            "alice",
            "--specialist",
            "researcher",
            "--workdir",
            "/repos/alice",
            "--prompt-overlay-mode",
            "append",
            "--prompt-overlay-text",
            "Prefer Alice repository conventions.",
        ],
    )
    assert create_result.exit_code == 0, create_result.output
    before_result = runner.invoke(cli, ["project", "easy", "profile", "get", "--name", "alice"])
    assert before_result.exit_code == 0, before_result.output

    set_result = runner.invoke(cli, ["project", "easy", "profile", "set", "--name", "alice"])
    after_result = runner.invoke(cli, ["project", "easy", "profile", "get", "--name", "alice"])

    assert set_result.exit_code != 0
    assert "No launch-profile updates were requested" in set_result.output
    assert after_result.exit_code == 0, after_result.output
    assert json.loads(after_result.output) == json.loads(before_result.output)


def test_project_launch_profile_set_can_disable_and_clear_memory_binding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
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
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "credentials",
                "codex",
                "add",
                "--name",
                "alice-creds",
                "--api-key",
                "sk-openai",
                "--auth-json",
                str(auth_json_path),
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
                "launch-profiles",
                "add",
                "--name",
                "alice",
                "--recipe",
                "researcher-codex-default",
                "--memory-dir",
                str((tmp_path / "shared" / "alice-memory").resolve()),
            ],
        ).exit_code
        == 0
    )

    disabled_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "set",
            "--name",
            "alice",
            "--no-memory-dir",
        ],
    )

    assert disabled_result.exit_code == 0, disabled_result.output
    disabled_payload = json.loads(disabled_result.output)
    assert disabled_payload["defaults"]["memory_binding"] == "disabled"
    assert disabled_payload["defaults"]["memory_dir"] is None

    cleared_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "set",
            "--name",
            "alice",
            "--clear-memory-dir",
        ],
    )

    assert cleared_result.exit_code == 0, cleared_result.output
    cleared_payload = json.loads(cleared_result.output)
    assert cleared_payload["defaults"]["memory_binding"] == "inherit"
    assert cleared_payload["defaults"]["memory_dir"] is None


def test_project_easy_instance_launch_uses_profile_defaults_and_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    profile_workdir = (tmp_path / "profile-workdir").resolve()
    runtime_workdir = (tmp_path / "runtime-workdir").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    profile_workdir.mkdir(parents=True, exist_ok=True)
    runtime_workdir.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
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
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "credentials",
                "codex",
                "add",
                "--name",
                "alice-creds",
                "--api-key",
                "sk-openai",
                "--auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "easy",
                "profile",
                "create",
                "--name",
                "alice",
                "--specialist",
                "researcher",
                "--agent-name",
                "alice",
                "--workdir",
                str(profile_workdir),
                "--auth",
                "alice-creds",
                "--memory-dir",
                str((tmp_path / "profile-memory").resolve()),
                "--model",
                "gpt-5.4-mini",
                "--reasoning-level",
                "4",
                "--mail-transport",
                "filesystem",
                "--mail-principal-id",
                "alice",
                "--mail-address",
                "alice@agents.localhost",
                "--mail-root",
                "/shared-mail-root",
                "--headless",
                "--no-gateway",
                "--prompt-overlay-mode",
                "append",
                "--prompt-overlay-text",
                "Prefer Alice repository conventions.",
            ],
        ).exit_code
        == 0
    )

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        lambda **kwargs: (
            captured.update(kwargs)
            or SimpleNamespace(
                agent_identity=kwargs["agent_name"],
                agent_id="agent-123",
                tmux_session_name="HOUMAO-alice",
                manifest_path=(tmp_path / "manifest.json").resolve(),
            )
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "instance",
            "launch",
            "--profile",
            "alice",
            "--auth",
            "breakglass",
            "--workdir",
            str(runtime_workdir),
            "--model",
            "gpt-5.4-nano",
            "--reasoning-level",
            "12",
            "--no-headless",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["agents"] == str(
        repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
    )
    assert captured["agent_name"] == "alice"
    assert captured["auth"] == "breakglass"
    assert captured["working_directory"] == runtime_workdir
    assert captured["memory_dir"] is None
    assert captured["no_memory_dir"] is False
    assert captured["launch_profile_memory_dir"] == str((tmp_path / "profile-memory").resolve())
    assert captured["launch_profile_memory_disabled"] is False
    assert captured["provider"] == "codex"
    assert captured["headless"] is False
    assert captured["gateway_auto_attach"] is False
    assert captured["launch_profile_model_config"].name == "gpt-5.4-mini"
    assert captured["launch_profile_model_config"].reasoning.level == 4
    assert captured["direct_model_config"].name == "gpt-5.4-nano"
    assert captured["direct_model_config"].reasoning.level == 12
    assert captured["prompt_overlay_mode"] == "append"
    assert captured["prompt_overlay_text"] == "Prefer Alice repository conventions."
    assert captured["launch_profile_provenance"] == {
        "name": "alice",
        "lane": "easy_profile",
        "source_kind": "specialist",
        "source_name": "researcher",
        "recipe_name": "researcher-codex-default",
        "prompt_overlay": {
            "mode": "append",
            "present": True,
        },
    }
    assert captured["declared_mailbox"].transport == "filesystem"
    assert captured["declared_mailbox"].filesystem_root == "/shared-mail-root"


def test_project_launch_profile_set_can_clear_managed_header_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
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

    add_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "add",
            "--name",
            "alice",
            "--recipe",
            "researcher-codex-default",
            "--no-managed-header",
        ],
    )
    assert add_result.exit_code == 0, add_result.output
    assert json.loads(add_result.output)["defaults"]["managed_header"] == "disabled"

    set_result = runner.invoke(
        cli,
        [
            "project",
            "agents",
            "launch-profiles",
            "set",
            "--name",
            "alice",
            "--clear-managed-header",
        ],
    )
    assert set_result.exit_code == 0, set_result.output
    assert json.loads(set_result.output)["defaults"]["managed_header"] == "inherit"


def test_project_easy_instance_launch_forwards_managed_header_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
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
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "easy",
                "profile",
                "create",
                "--name",
                "alice",
                "--specialist",
                "researcher",
                "--managed-header",
            ],
        ).exit_code
        == 0
    )

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        lambda **kwargs: (
            captured.update(kwargs)
            or SimpleNamespace(
                agent_identity="alice",
                agent_id="agent-123",
                tmux_session_name="HOUMAO-alice",
                manifest_path=(tmp_path / "manifest.json").resolve(),
            )
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "instance",
            "launch",
            "--profile",
            "alice",
            "--name",
            "alice",
            "--no-managed-header",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["managed_header_override"] is False
    assert captured["launch_profile_managed_header_policy"] == "enabled"


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
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        )

    def _fake_emit(**kwargs: object) -> None:
        emitted.update(kwargs)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _fake_launch,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
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
            "--mail-transport",
            "filesystem",
            "--mail-root",
            str(mail_root),
            "--mail-account-dir",
            str(private_mailbox_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["agents"] == str(
        repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
    )
    assert captured["agent_name"] == "repo-research-1"
    assert captured["provider"] == "codex"
    assert captured["headless"] is True
    assert captured["gateway_auto_attach"] is True
    assert captured["gateway_host"] == "127.0.0.1"
    assert captured["gateway_port"] == 0
    assert captured["gateway_execution_mode"] == "tmux_auxiliary_window"
    assert captured["mailbox_transport"] == "filesystem"
    assert captured["mailbox_root"] == mail_root
    assert captured["mailbox_account_dir"] == private_mailbox_dir
    assert emitted["agent_name"] == "repo-research-1"
    assert emitted["headless"] is True


def test_project_easy_instance_launch_keeps_selected_overlay_when_workdir_points_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    runtime_workdir = (tmp_path / "runtime-workdir").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    runtime_workdir.mkdir(parents=True, exist_ok=True)
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
                "--tool",
                "codex",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    captured: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        manifest_path = (tmp_path / "manifest.json").resolve()
        manifest_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            agent_identity=kwargs["agent_name"],
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _fake_launch,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
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
            "--headless",
            "--workdir",
            str(runtime_workdir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["working_directory"] == runtime_workdir
    assert captured["source_working_directory"] == repo_root
    assert captured["source_agent_def_dir"] == (repo_root / ".houmao" / "agents").resolve()
    assert captured["agents"] == str(
        repo_root / ".houmao" / "agents" / "presets" / "researcher-codex-default.yaml"
    )


def test_project_easy_instance_launch_help_exposes_workdir() -> None:
    result = CliRunner().invoke(cli, ["project", "easy", "instance", "launch", "--help"])

    assert result.exit_code == 0, result.output
    assert "--workdir DIRECTORY" in result.output
    assert "--no-gateway" in result.output
    assert "--gateway-port INTEGER RANGE" in result.output
    assert "--gateway-background" in result.output


def test_project_easy_instance_launch_no_gateway_opt_out(
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
                "--tool",
                "codex",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    captured: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        manifest_path = (tmp_path / "manifest.json").resolve()
        manifest_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            agent_identity=kwargs["agent_name"],
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _fake_launch,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
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
            "--headless",
            "--no-gateway",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["gateway_auto_attach"] is False
    assert captured["gateway_host"] is None
    assert captured["gateway_port"] is None
    assert captured["gateway_execution_mode"] is None


def test_project_easy_instance_launch_gateway_port_override(
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
                "--tool",
                "codex",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    captured: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        manifest_path = (tmp_path / "manifest.json").resolve()
        manifest_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            agent_identity=kwargs["agent_name"],
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _fake_launch,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
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
            "--headless",
            "--gateway-port",
            "43123",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["gateway_auto_attach"] is True
    assert captured["gateway_host"] == "127.0.0.1"
    assert captured["gateway_port"] == 43123
    assert captured["gateway_execution_mode"] == "tmux_auxiliary_window"


def test_project_easy_instance_launch_gateway_background_override(
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
                "--tool",
                "codex",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    captured: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        manifest_path = (tmp_path / "manifest.json").resolve()
        manifest_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            agent_identity=kwargs["agent_name"],
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _fake_launch,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
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
            "--headless",
            "--gateway-background",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["gateway_auto_attach"] is True
    assert captured["gateway_host"] == "127.0.0.1"
    assert captured["gateway_port"] == 0
    assert captured["gateway_execution_mode"] == "detached_process"


def test_project_easy_instance_launch_gateway_background_override_forces_attach_when_easy_profile_defaults_disable_gateway(
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
                "--tool",
                "codex",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "project",
                "easy",
                "profile",
                "create",
                "--name",
                "alice",
                "--specialist",
                "researcher",
                "--no-gateway",
            ],
        ).exit_code
        == 0
    )

    captured: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        manifest_path = (tmp_path / "manifest.json").resolve()
        manifest_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            agent_identity=kwargs["agent_name"],
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _fake_launch,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "instance",
            "launch",
            "--profile",
            "alice",
            "--name",
            "repo-research-1",
            "--headless",
            "--gateway-background",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["gateway_auto_attach"] is True
    assert captured["gateway_host"] == "127.0.0.1"
    assert captured["gateway_port"] == 0
    assert captured["gateway_execution_mode"] == "detached_process"


def test_project_easy_instance_launch_resolves_one_off_env_set(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = tmp_path / "auth.json"
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")

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
                "--tool",
                "codex",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    captured: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        manifest_path = (tmp_path / "manifest.json").resolve()
        manifest_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            agent_identity=kwargs["agent_name"],
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _fake_launch,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
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
            "--headless",
            "--env-set",
            "FEATURE_FLAG_X=1",
            "--env-set",
            "OPENAI_BASE_URL",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["launch_env_overrides"] == {
        "FEATURE_FLAG_X": "1",
        "OPENAI_BASE_URL": "https://example.invalid/v1",
    }


def test_project_easy_instance_launch_rejects_conflicting_gateway_flags(
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
                "--tool",
                "codex",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    launch_called = False

    def _unexpected_launch(**kwargs: object) -> SimpleNamespace:
        nonlocal launch_called
        launch_called = True
        return SimpleNamespace()

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _unexpected_launch,
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
            "--headless",
            "--no-gateway",
            "--gateway-port",
            "43123",
        ],
    )

    assert result.exit_code != 0
    assert "`--no-gateway` and `--gateway-port` cannot be combined" in result.output
    assert launch_called is False


def test_project_easy_instance_launch_rejects_no_gateway_with_gateway_background(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
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
                "--tool",
                "codex",
                "--api-key",
                "sk-openai",
                "--codex-auth-json",
                str(auth_json_path),
            ],
        ).exit_code
        == 0
    )

    launch_called = False

    def _unexpected_launch(**kwargs: object) -> SimpleNamespace:
        del kwargs
        nonlocal launch_called
        launch_called = True
        return SimpleNamespace()

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        _unexpected_launch,
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
            "--headless",
            "--no-gateway",
            "--gateway-background",
        ],
    )

    assert result.exit_code != 0
    assert "`--no-gateway` and `--gateway-background` cannot be combined" in result.output
    assert launch_called is False


def test_emit_local_launch_completion_reports_gateway_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    manifest_path.write_text("{}\n", encoding="utf-8")
    emitted: list[dict[str, object]] = []

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.emit",
        lambda payload, **kwargs: emitted.append(dict(payload)),
    )

    launch_result = SimpleNamespace(
        controller=SimpleNamespace(
            agent_identity="repo-research-1",
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
            gateway_host="127.0.0.1",
            gateway_port=43123,
            gateway_auto_attach_error=None,
            gateway_status=lambda: GatewayStatusV1(
                attach_identity="agent-123",
                backend="local_interactive",
                tmux_session_name="HOUMAO-repo-research-1",
                gateway_health="healthy",
                managed_agent_connectivity="connected",
                managed_agent_recovery="idle",
                request_admission="open",
                terminal_surface_eligibility="ready",
                active_execution="idle",
                execution_mode="tmux_auxiliary_window",
                queue_depth=0,
                gateway_host="127.0.0.1",
                gateway_port=43123,
                gateway_tmux_window_id="@2",
                gateway_tmux_window_index="2",
                managed_agent_instance_epoch=1,
            ),
        ),
        runtime_root=(tmp_path / "runtime").resolve(),
        runtime_root_detail="runtime-root-detail",
        jobs_root=(tmp_path / "jobs").resolve(),
        jobs_root_detail="jobs-root-detail",
        mailbox_root=(tmp_path / "mailbox").resolve(),
        mailbox_root_detail="mailbox-root-detail",
        overlay_root=(tmp_path / "overlay").resolve(),
        overlay_root_detail="overlay-root-detail",
        project_overlay_bootstrapped=False,
        overlay_bootstrap_detail="overlay-bootstrap-detail",
    )

    emit_local_launch_completion(
        launch_result=launch_result,
        agent_name="repo-research-1",
        session_name="HOUMAO-repo-research-1",
        headless=True,
    )

    assert emitted == [
        {
            "status": "Managed agent launch complete",
            "agent_name": "repo-research-1",
            "agent_id": "agent-123",
            "tmux_session_name": "HOUMAO-repo-research-1",
            "manifest_path": str(manifest_path),
            "runtime_root": str((tmp_path / "runtime").resolve()),
            "runtime_root_detail": "runtime-root-detail",
            "jobs_root": str((tmp_path / "jobs").resolve()),
            "jobs_root_detail": "jobs-root-detail",
            "memory_dir": None,
            "mailbox_root": str((tmp_path / "mailbox").resolve()),
            "mailbox_root_detail": "mailbox-root-detail",
            "overlay_root": str((tmp_path / "overlay").resolve()),
            "overlay_root_detail": "overlay-root-detail",
            "project_overlay_bootstrapped": False,
            "overlay_bootstrap_detail": "overlay-bootstrap-detail",
            "gateway_host": "127.0.0.1",
            "gateway_port": 43123,
            "gateway_execution_mode": "tmux_auxiliary_window",
            "gateway_tmux_window_index": "2",
        }
    ]


def test_emit_local_launch_completion_reports_gateway_attach_failure_and_exits_two(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    manifest_path.write_text("{}\n", encoding="utf-8")
    emitted: list[dict[str, object]] = []

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.emit",
        lambda payload, **kwargs: emitted.append(dict(payload)),
    )

    launch_result = SimpleNamespace(
        controller=SimpleNamespace(
            agent_identity="repo-research-1",
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
            gateway_host=None,
            gateway_port=None,
            gateway_auto_attach_error="bind failure",
        ),
        runtime_root=(tmp_path / "runtime").resolve(),
        runtime_root_detail="runtime-root-detail",
        jobs_root=(tmp_path / "jobs").resolve(),
        jobs_root_detail="jobs-root-detail",
        mailbox_root=(tmp_path / "mailbox").resolve(),
        mailbox_root_detail="mailbox-root-detail",
        overlay_root=(tmp_path / "overlay").resolve(),
        overlay_root_detail="overlay-root-detail",
        project_overlay_bootstrapped=False,
        overlay_bootstrap_detail="overlay-bootstrap-detail",
    )

    with pytest.raises(SystemExit) as exc_info:
        emit_local_launch_completion(
            launch_result=launch_result,
            agent_name="repo-research-1",
            session_name="HOUMAO-repo-research-1",
            headless=True,
        )

    assert exc_info.value.code == 2
    assert emitted == [
        {
            "status": "Managed agent launch complete",
            "agent_name": "repo-research-1",
            "agent_id": "agent-123",
            "tmux_session_name": "HOUMAO-repo-research-1",
            "manifest_path": str(manifest_path),
            "runtime_root": str((tmp_path / "runtime").resolve()),
            "runtime_root_detail": "runtime-root-detail",
            "jobs_root": str((tmp_path / "jobs").resolve()),
            "jobs_root_detail": "jobs-root-detail",
            "memory_dir": None,
            "mailbox_root": str((tmp_path / "mailbox").resolve()),
            "mailbox_root_detail": "mailbox-root-detail",
            "overlay_root": str((tmp_path / "overlay").resolve()),
            "overlay_root_detail": "overlay-root-detail",
            "project_overlay_bootstrapped": False,
            "overlay_bootstrap_detail": "overlay-bootstrap-detail",
            "gateway_auto_attach_error": "bind failure",
        }
    ]


def test_project_easy_instance_launch_requires_specialist_and_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    auth_json_path = (tmp_path / "auth.json").resolve()
    auth_json_path.write_text('{"logged_in": true}\n', encoding="utf-8")
    monkeypatch.chdir(repo_root)

    missing_specialist = runner.invoke(
        cli,
        ["project", "easy", "instance", "launch", "--name", "repo-research-1"],
    )
    assert missing_specialist.exit_code != 0
    assert "Provide exactly one of `--specialist` or `--profile`." in missing_specialist.output

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

    missing_name = runner.invoke(
        cli,
        ["project", "easy", "instance", "launch", "--specialist", "researcher"],
    )
    assert missing_name.exit_code != 0
    assert "`project easy instance launch --specialist` requires `--name`." in missing_name.output


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
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        lambda **kwargs: (
            captured.update(kwargs)
            or SimpleNamespace(
                agent_identity=kwargs["agent_name"],
                agent_id="agent-123",
                tmux_session_name="HOUMAO-repo-research-1",
                manifest_path=(tmp_path / "manifest.json").resolve(),
            )
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
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


def test_project_easy_instance_launch_bare_force_forwards_keep_stale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    overlay = SimpleNamespace(project_root=tmp_path.resolve())
    preset_path = (tmp_path / "preset.yaml").resolve()
    preset_path.write_text("role: researcher\n", encoding="utf-8")
    source_agent_def_dir = (tmp_path / "agents").resolve()
    source_agent_def_dir.mkdir(parents=True, exist_ok=True)
    captured: dict[str, object] = {}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy._ensure_project_overlay",
        lambda: overlay,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy._load_specialist_or_click",
        lambda **kwargs: SimpleNamespace(
            tool="codex",
            provider="codex",
            resolved_preset_path=lambda project_overlay: preset_path,
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.materialize_project_agent_catalog_projection",
        lambda project_overlay: source_agent_def_dir,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        lambda **kwargs: (
            captured.update(kwargs)
            or SimpleNamespace(
                agent_identity=kwargs["agent_name"],
                agent_id="agent-123",
                tmux_session_name="repo-research-1",
                manifest_path=(tmp_path / "manifest.json").resolve(),
            )
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
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
            "--headless",
            "--force",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["force_mode"] == "keep-stale"


def test_project_easy_instance_launch_profile_forwards_clean_force_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    overlay = SimpleNamespace(project_root=tmp_path.resolve())
    preset_path = (tmp_path / "preset.yaml").resolve()
    preset_path.write_text("role: researcher\n", encoding="utf-8")
    source_agent_def_dir = (tmp_path / "agents").resolve()
    source_agent_def_dir.mkdir(parents=True, exist_ok=True)
    specialist = SimpleNamespace(
        tool="codex",
        provider="codex",
        resolved_preset_path=lambda project_overlay: preset_path,
    )
    resolved_profile = SimpleNamespace(
        specialist=specialist,
        source_exists=True,
        recipe_name="researcher",
        prompt_overlay_text=None,
        entry=SimpleNamespace(
            name="alice",
            profile_lane="easy_profile",
            source_kind="specialist",
            source_name="researcher",
            mailbox_payload=None,
            operator_prompt_mode=None,
            env_payload={},
            model_name=None,
            reasoning_level=None,
            managed_header_policy="inherit",
            prompt_overlay_mode=None,
            posture_payload={"headless": True},
            managed_agent_name="profile-agent",
            auth_name=None,
            workdir=None,
            memory_dir=None,
            memory_disabled=False,
        ),
    )
    captured: dict[str, object] = {}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy._ensure_project_overlay",
        lambda: overlay,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy._load_launch_profile_or_click",
        lambda **kwargs: resolved_profile,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.materialize_project_agent_catalog_projection",
        lambda project_overlay: source_agent_def_dir,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.launch_managed_agent_locally",
        lambda **kwargs: (
            captured.update(kwargs)
            or SimpleNamespace(
                agent_identity=kwargs["agent_name"],
                agent_id="agent-123",
                tmux_session_name="profile-agent",
                manifest_path=(tmp_path / "manifest.json").resolve(),
            )
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.emit_local_launch_completion",
        lambda **kwargs: None,
    )

    result = runner.invoke(
        cli,
        [
            "project",
            "easy",
            "instance",
            "launch",
            "--profile",
            "alice",
            "--force",
            "clean",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["force_mode"] == "clean"


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
        "houmao.srv_ctrl.commands.project_easy.resolve_managed_agent_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy._load_manifest_payload",
        lambda path: {
            "runtime": {"agent_def_dir": str((repo_root / ".houmao" / "agents").resolve())}
        },
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.stop_managed_agent",
        lambda resolved_target: (
            stop_calls.append(resolved_target)
            or HoumaoManagedAgentActionResponse(
                success=True,
                tracked_agent_id=resolved_target.identity.tracked_agent_id,
                detail=f"Stopped {resolved_target.identity.agent_name}",
            )
        ),
    )

    result = runner.invoke(
        cli, ["project", "easy", "instance", "stop", "--name", "repo-research-1"]
    )

    assert result.exit_code == 0, result.output
    assert stop_calls == [target]
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["tracked_agent_id"] == "tracked-researcher"
    assert payload["detail"] == "Stopped repo-research-1"
    assert payload["selected_overlay_root"] == str((repo_root / ".houmao").resolve())
    assert (
        payload["selected_overlay_detail"]
        == "Selected overlay root from nearest-ancestor project discovery."
    )


def test_project_easy_instance_stop_fails_without_bootstrapping_missing_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    result = runner.invoke(
        cli, ["project", "easy", "instance", "stop", "--name", "repo-research-1"]
    )

    assert result.exit_code != 0
    assert str((repo_root / ".houmao").resolve()) in result.output
    assert "uses non-creating resolution and did not bootstrap it" in result.output
    assert not (repo_root / ".houmao").exists()


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
        "houmao.srv_ctrl.commands.project_easy.resolve_managed_agent_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy._load_manifest_payload",
        lambda path: {
            "runtime": {"agent_def_dir": str((tmp_path / "other" / ".houmao" / "agents").resolve())}
        },
    )

    result = runner.invoke(
        cli, ["project", "easy", "instance", "stop", "--name", "repo-research-1"]
    )

    assert result.exit_code != 0
    assert "does not belong to the selected project overlay" in result.output


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
            "metadata": {
                "launch_overrides": {
                    "construction_provenance": {
                        "launch_profile": {
                            "name": "alice",
                            "lane": "easy_profile",
                            "source_kind": "specialist",
                            "source_name": "researcher",
                            "recipe_name": "researcher-codex-default",
                            "prompt_overlay": {
                                "mode": "append",
                                "present": True,
                            },
                        }
                    }
                }
            },
            "mailbox": {
                "transport": "filesystem",
                "principal_id": "HOUMAO-repo-research-1",
                "address": "HOUMAO-repo-research-1@agents.localhost",
                "filesystem_root": str((tmp_path / "mail-root").resolve()),
                "mailbox_kind": "symlink",
                "mailbox_path": str((tmp_path / "private-mailboxes" / "repo-research-1").resolve()),
                "bindings_version": "2026-03-29T12:00:00Z",
            },
        },
        "runtime": {
            "agent_def_dir": str((repo_root / ".houmao" / "agents").resolve()),
            "memory_dir": str((tmp_path / "memory" / "agents" / "repo-research-1").resolve()),
        },
    }

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_common.list_managed_agents",
        lambda *, port=None: HoumaoManagedAgentListResponse(agents=[identity]),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy.resolve_managed_agent_target",
        lambda **kwargs: SimpleNamespace(identity=identity),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_common._load_manifest_payload",
        lambda path: manifest_payload,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.project_easy._load_manifest_payload",
        lambda path: manifest_payload,
    )

    list_result = runner.invoke(cli, ["project", "easy", "instance", "list"])
    assert list_result.exit_code == 0
    list_payload = json.loads(list_result.output)
    assert len(list_payload["instances"]) == 1
    assert list_payload["instances"][0]["specialist"] == "researcher"
    assert list_payload["instances"][0]["easy_profile"] == "alice"
    assert list_payload["instances"][0]["tool"] == "codex"
    assert list_payload["instances"][0]["memory_dir"] == str(
        (tmp_path / "memory" / "agents" / "repo-research-1").resolve()
    )
    assert list_payload["instances"][0]["mailbox"] == {
        "transport": "filesystem",
        "principal_id": "HOUMAO-repo-research-1",
        "address": "HOUMAO-repo-research-1@agents.localhost",
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
    assert get_payload["easy_profile"] == "alice"
    assert get_payload["agent_id"] == "agent-123"
    assert get_payload["manifest_path"] == str(manifest_path)
    assert get_payload["memory_dir"] == str(
        (tmp_path / "memory" / "agents" / "repo-research-1").resolve()
    )
    assert get_payload["mailbox"] == {
        "transport": "filesystem",
        "principal_id": "HOUMAO-repo-research-1",
        "address": "HOUMAO-repo-research-1@agents.localhost",
        "mailbox_root": str((tmp_path / "mail-root").resolve()),
        "mailbox_kind": "symlink",
        "mailbox_dir": str((tmp_path / "private-mailboxes" / "repo-research-1").resolve()),
        "bindings_version": "2026-03-29T12:00:00Z",
    }
