from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.agents.system_skills import (
    SYSTEM_SKILL_SET_AGENT_INSTANCE,
    SYSTEM_SKILL_STATE_SCHEMA_VERSION,
    SYSTEM_SKILL_SET_MAILBOX_FULL,
    SYSTEM_SKILL_SET_USER_CONTROL,
    SystemSkillCatalogError,
    SystemSkillInstallError,
    install_system_skills_for_home,
    load_system_skill_catalog,
    load_system_skill_catalog_from_paths,
    load_system_skill_install_state,
    resolve_auto_install_skill_selection,
    resolve_system_skill_selection,
    system_skill_state_path_for_home,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _packaged_catalog_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "src/houmao/agents/assets/system_skills/catalog.schema.json"
    )


def test_load_system_skill_catalog_reports_named_sets_and_auto_install_defaults() -> None:
    catalog = load_system_skill_catalog()

    assert catalog.schema_version == 1
    assert tuple(catalog.skills.keys()) == (
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-email-via-filesystem",
        "houmao-email-via-stalwart",
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
        "houmao-manage-agent-instance",
    )
    assert tuple(catalog.sets.keys()) == (
        "mailbox-core",
        "mailbox-full",
        "user-control",
        "agent-instance",
    )
    assert catalog.auto_install.managed_launch_sets == (
        SYSTEM_SKILL_SET_MAILBOX_FULL,
        SYSTEM_SKILL_SET_USER_CONTROL,
    )
    assert catalog.auto_install.managed_join_sets == (
        SYSTEM_SKILL_SET_MAILBOX_FULL,
        SYSTEM_SKILL_SET_USER_CONTROL,
    )
    assert catalog.auto_install.cli_default_sets == (
        SYSTEM_SKILL_SET_MAILBOX_FULL,
        SYSTEM_SKILL_SET_USER_CONTROL,
        SYSTEM_SKILL_SET_AGENT_INSTANCE,
    )


def test_resolve_system_skill_selection_dedupes_sets_and_explicit_skills() -> None:
    catalog = load_system_skill_catalog()

    resolved = resolve_system_skill_selection(
        catalog,
        set_names=("mailbox-core", "mailbox-full", "user-control"),
        skill_names=("houmao-email-via-filesystem", "houmao-manage-specialist"),
    )

    assert resolved == (
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-email-via-filesystem",
        "houmao-email-via-stalwart",
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
    )
    assert resolve_auto_install_skill_selection(catalog, kind="managed_launch") == resolved


def test_resolve_system_skill_selection_cli_default_includes_agent_instance_skill() -> None:
    catalog = load_system_skill_catalog()

    resolved = resolve_auto_install_skill_selection(catalog, kind="cli_default")

    assert resolved == (
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-email-via-filesystem",
        "houmao-email-via-stalwart",
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
        "houmao-manage-agent-instance",
    )


def test_load_system_skill_catalog_rejects_unknown_set_member(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.toml"
    _write(
        catalog_path,
        """
schema_version = 1

[skills.houmao-email-via-agent-gateway]
asset_subpath = "houmao-email-via-agent-gateway"

[sets.mailbox-core]
skills = ["houmao-email-via-agent-gateway", "houmao-missing"]

[auto_install]
managed_launch_sets = ["mailbox-core"]
managed_join_sets = ["mailbox-core"]
cli_default_sets = ["mailbox-core"]
""".strip()
        + "\n",
    )

    with pytest.raises(
        SystemSkillCatalogError,
        match="references unknown system skill `houmao-missing`",
    ):
        load_system_skill_catalog_from_paths(
            catalog_path=catalog_path,
            schema_path=_packaged_catalog_schema_path(),
        )


def test_install_system_skills_for_home_records_state_and_preserves_user_content(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    user_skill_path = home_path / "skills/custom-user-skill/SKILL.md"
    _write(user_skill_path, "custom user skill\n")

    result = install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        set_names=("mailbox-core", "user-control"),
        skill_names=("houmao-email-via-filesystem",),
    )

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    manage_specialist_path = home_path / "skills/houmao-manage-specialist/SKILL.md"
    manage_specialist_actions = home_path / "skills/houmao-manage-specialist/actions"
    manage_specialist_references = home_path / "skills/houmao-manage-specialist/references"
    manage_credentials_path = home_path / "skills/houmao-manage-credentials/SKILL.md"
    manage_credentials_actions = home_path / "skills/houmao-manage-credentials/actions"
    manage_agent_definition_path = home_path / "skills/houmao-manage-agent-definition/SKILL.md"
    manage_agent_definition_agents = home_path / "skills/houmao-manage-agent-definition/agents"
    manage_agent_definition_actions = home_path / "skills/houmao-manage-agent-definition/actions"

    assert result.resolved_skill_names == (
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
        "houmao-email-via-filesystem",
    )
    assert state is not None
    assert tuple(record.name for record in state.installed_skills) == result.resolved_skill_names
    assert user_skill_path.is_file()
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-email-via-agent-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-email-via-filesystem/SKILL.md").is_file()
    assert manage_specialist_path.is_file()
    assert manage_credentials_path.is_file()
    assert manage_agent_definition_path.is_file()
    manage_specialist_skill = manage_specialist_path.read_text(encoding="utf-8")
    manage_credentials_skill = manage_credentials_path.read_text(encoding="utf-8")
    manage_agent_definition_skill = manage_agent_definition_path.read_text(encoding="utf-8")
    create_action_path = manage_specialist_actions / "create.md"
    list_action_path = manage_specialist_actions / "list.md"
    get_action_path = manage_specialist_actions / "get.md"
    remove_action_path = manage_specialist_actions / "remove.md"
    create_action = create_action_path.read_text(encoding="utf-8")
    credentials_list_action_path = manage_credentials_actions / "list.md"
    credentials_get_action_path = manage_credentials_actions / "get.md"
    credentials_add_action_path = manage_credentials_actions / "add.md"
    credentials_set_action_path = manage_credentials_actions / "set.md"
    credentials_remove_action_path = manage_credentials_actions / "remove.md"
    definition_create_action_path = manage_agent_definition_actions / "create.md"
    definition_list_action_path = manage_agent_definition_actions / "list.md"
    definition_get_action_path = manage_agent_definition_actions / "get.md"
    definition_set_action_path = manage_agent_definition_actions / "set.md"
    definition_remove_action_path = manage_agent_definition_actions / "remove.md"
    credentials_get_action = credentials_get_action_path.read_text(encoding="utf-8")
    credentials_set_action = credentials_set_action_path.read_text(encoding="utf-8")
    definition_get_action = definition_get_action_path.read_text(encoding="utf-8")
    definition_set_action = definition_set_action_path.read_text(encoding="utf-8")
    assert ".venv/bin/houmao-mgr" in manage_specialist_skill
    assert "pixi run houmao-mgr" in manage_specialist_skill
    assert "uv run houmao-mgr" in manage_specialist_skill
    assert "globally installed `houmao-mgr` from uv tools" in manage_specialist_skill
    assert "actions/create.md" in manage_specialist_skill
    assert "actions/list.md" in manage_specialist_skill
    assert "actions/get.md" in manage_specialist_skill
    assert "actions/remove.md" in manage_specialist_skill
    assert "project easy instance launch" in manage_specialist_skill
    assert "Explicit Auth Mode" in create_action
    assert "Env Lookup Mode" in create_action
    assert "Directory Scan Mode" in create_action
    assert "auto credentials" in create_action
    assert "No Discovery Mode" in create_action
    assert "references/claude-credential-lookup.md" in create_action
    assert "references/codex-credential-lookup.md" in create_action
    assert "references/gemini-credential-lookup.md" in create_action
    assert "--claude-oauth-token" in create_action
    assert "--claude-config-dir" in create_action
    assert "optional bootstrap state" in create_action
    assert "not a credential-providing method" in create_action
    assert "do not scan env vars, directories, repo-local tool homes" in create_action
    assert "tests/fixtures/agents" not in create_action
    assert ".venv/bin/houmao-mgr" in manage_credentials_skill
    assert "pixi run houmao-mgr" in manage_credentials_skill
    assert "uv run houmao-mgr" in manage_credentials_skill
    assert "actions/list.md" in manage_credentials_skill
    assert "actions/get.md" in manage_credentials_skill
    assert "actions/add.md" in manage_credentials_skill
    assert "actions/set.md" in manage_credentials_skill
    assert "actions/remove.md" in manage_credentials_skill
    assert "project agents tools <tool> auth ..." in manage_credentials_skill
    assert "Do not print raw secret values" in manage_credentials_skill
    assert credentials_list_action_path.is_file()
    assert credentials_get_action_path.is_file()
    assert credentials_add_action_path.is_file()
    assert credentials_set_action_path.is_file()
    assert credentials_remove_action_path.is_file()
    assert "project agents tools <tool> auth get --name <name>" in credentials_get_action
    assert "Do not bypass `auth get`" in credentials_get_action
    assert "Do not invent unsupported clear flags" in credentials_set_action
    assert (
        "Do not continue with set when the user has not provided any explicit supported change"
        in credentials_set_action
    )
    assert ".venv/bin/houmao-mgr" in manage_agent_definition_skill
    assert "pixi run houmao-mgr" in manage_agent_definition_skill
    assert "uv run houmao-mgr" in manage_agent_definition_skill
    assert "actions/create.md" in manage_agent_definition_skill
    assert "actions/list.md" in manage_agent_definition_skill
    assert "actions/get.md" in manage_agent_definition_skill
    assert "actions/set.md" in manage_agent_definition_skill
    assert "actions/remove.md" in manage_agent_definition_skill
    assert "project agents roles list|get|init|set|remove" in manage_agent_definition_skill
    assert "project agents presets list|get|add|set|remove" in manage_agent_definition_skill
    assert "houmao-manage-credentials" in manage_agent_definition_skill
    assert "project agents roles scaffold" in manage_agent_definition_skill
    assert "project agents roles presets ..." in manage_agent_definition_skill
    assert "direct hand-editing under `.houmao/agents/`" in manage_agent_definition_skill
    assert (manage_agent_definition_agents / "openai.yaml").is_file()
    assert definition_create_action_path.is_file()
    assert definition_list_action_path.is_file()
    assert definition_get_action_path.is_file()
    assert definition_set_action_path.is_file()
    assert definition_remove_action_path.is_file()
    assert "project agents roles init --name <role>" in definition_create_action_path.read_text(
        encoding="utf-8"
    )
    assert (
        "project agents presets add --name <preset> --role <role> --tool <tool>"
        in definition_create_action_path.read_text(encoding="utf-8")
    )
    assert "project agents roles list" in definition_list_action_path.read_text(encoding="utf-8")
    assert "project agents presets list" in definition_list_action_path.read_text(encoding="utf-8")
    assert "project agents roles get --name <role> --include-prompt" in definition_get_action
    assert "project agents presets get --name <preset>" in definition_get_action
    assert "project agents roles set --name <role>" in definition_set_action
    assert "project agents presets set --name <preset>" in definition_set_action
    assert "--clear-auth" in definition_set_action
    assert "houmao-manage-credentials" in definition_set_action
    assert "project agents roles remove --name <role>" in definition_remove_action_path.read_text(
        encoding="utf-8"
    )
    assert (
        "project agents presets remove --name <preset>"
        in definition_remove_action_path.read_text(encoding="utf-8")
    )
    assert list_action_path.is_file()
    assert get_action_path.is_file()
    assert remove_action_path.is_file()

    claude_reference_path = manage_specialist_references / "claude-credential-lookup.md"
    codex_reference_path = manage_specialist_references / "codex-credential-lookup.md"
    gemini_reference_path = manage_specialist_references / "gemini-credential-lookup.md"
    assert claude_reference_path.is_file()
    assert codex_reference_path.is_file()
    assert gemini_reference_path.is_file()

    claude_reference = claude_reference_path.read_text(encoding="utf-8")
    codex_reference = codex_reference_path.read_text(encoding="utf-8")
    gemini_reference = gemini_reference_path.read_text(encoding="utf-8")

    assert "CLAUDE_CONFIG_DIR" in claude_reference
    assert "~/.claude" in claude_reference
    assert "apiKeyHelper" in claude_reference
    assert "CLAUDE_CODE_OAUTH_TOKEN" in claude_reference
    assert "--claude-oauth-token" in claude_reference
    assert "--claude-config-dir" in claude_reference
    assert ".credentials.json" in claude_reference
    assert "optional bootstrap state" in claude_reference
    assert "not itself a credential-providing method" in claude_reference
    assert (
        "do not treat `.credentials.json` or `~/.claude.json` as directly importable specialist inputs"
        not in claude_reference
    )
    assert "tests/fixtures/agents" not in claude_reference

    assert "CODEX_HOME" in codex_reference
    assert "auth.json" in codex_reference
    assert "requires_openai_auth = false" in codex_reference
    assert 'wire_api = "responses"' in codex_reference
    assert "tests/fixtures/agents" not in codex_reference

    assert "GEMINI_CLI_HOME" in gemini_reference
    assert "oauth_creds.json" in gemini_reference
    assert "GOOGLE_APPLICATION_CREDENTIALS" in gemini_reference
    assert "tests/fixtures/agents" not in gemini_reference


def test_install_system_skills_for_home_cli_default_includes_agent_instance_skill(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()

    result = install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        use_cli_default=True,
    )

    manage_agent_instance_path = home_path / "skills/houmao-manage-agent-instance/SKILL.md"
    manage_agent_instance_actions = home_path / "skills/houmao-manage-agent-instance/actions"

    assert result.selected_set_names == (
        "mailbox-full",
        "user-control",
        "agent-instance",
    )
    assert result.resolved_skill_names == (
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-email-via-filesystem",
        "houmao-email-via-stalwart",
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
        "houmao-manage-agent-instance",
    )
    assert (home_path / "skills/houmao-manage-credentials/SKILL.md").is_file()
    assert (home_path / "skills/houmao-manage-agent-definition/SKILL.md").is_file()
    assert manage_agent_instance_path.is_file()
    manage_agent_instance_skill = manage_agent_instance_path.read_text(encoding="utf-8")
    launch_action_path = manage_agent_instance_actions / "launch.md"
    join_action_path = manage_agent_instance_actions / "join.md"
    list_action_path = manage_agent_instance_actions / "list.md"
    stop_action_path = manage_agent_instance_actions / "stop.md"
    cleanup_action_path = manage_agent_instance_actions / "cleanup.md"
    launch_action = launch_action_path.read_text(encoding="utf-8")
    cleanup_action = cleanup_action_path.read_text(encoding="utf-8")

    assert "actions/launch.md" in manage_agent_instance_skill
    assert "actions/join.md" in manage_agent_instance_skill
    assert "actions/list.md" in manage_agent_instance_skill
    assert "actions/stop.md" in manage_agent_instance_skill
    assert "actions/cleanup.md" in manage_agent_instance_skill
    assert "project easy specialist create" in manage_agent_instance_skill
    assert "agents cleanup mailbox" in manage_agent_instance_skill
    assert launch_action_path.is_file()
    assert join_action_path.is_file()
    assert list_action_path.is_file()
    assert stop_action_path.is_file()
    assert cleanup_action_path.is_file()
    assert "agents launch" in launch_action
    assert "project easy instance launch" in launch_action
    assert "--mail-transport" in launch_action
    assert "agents cleanup session" in cleanup_action
    assert "agents cleanup logs" in cleanup_action
    assert "admin cleanup runtime" in cleanup_action


def test_install_system_skills_for_home_rejects_non_owned_collision(tmp_path: Path) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    conflicting_skill_path = home_path / "skills/houmao-email-via-agent-gateway/SKILL.md"
    _write(conflicting_skill_path, "user-authored collision\n")

    with pytest.raises(
        SystemSkillInstallError,
        match="Refusing to overwrite non-owned system-skill path",
    ):
        install_system_skills_for_home(
            tool="codex",
            home_path=home_path,
            skill_names=("houmao-email-via-agent-gateway",),
        )


def test_install_system_skills_for_home_migrates_previous_owned_family_paths(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    _write(
        home_path / "skills/mailbox/houmao-process-emails-via-gateway/SKILL.md",
        "old mailbox path\n",
    )
    _write(
        home_path / "skills/project/houmao-create-specialist/SKILL.md",
        "old project path\n",
    )
    state_path = system_skill_state_path_for_home(home_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": SYSTEM_SKILL_STATE_SCHEMA_VERSION,
                "tool": "codex",
                "installed_at": "2026-04-05T00:00:00Z",
                "installed_skills": [
                    {
                        "name": "houmao-process-emails-via-gateway",
                        "asset_subpath": "mailbox/houmao-process-emails-via-gateway",
                        "projected_relative_dir": "skills/mailbox/houmao-process-emails-via-gateway",
                        "content_digest": "old-mailbox",
                    },
                    {
                        "name": "houmao-create-specialist",
                        "asset_subpath": "project/houmao-create-specialist",
                        "projected_relative_dir": "skills/project/houmao-create-specialist",
                        "content_digest": "old-project",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        skill_names=("houmao-process-emails-via-gateway", "houmao-manage-specialist"),
    )

    assert result.projected_relative_dirs == (
        "skills/houmao-process-emails-via-gateway",
        "skills/houmao-manage-specialist",
    )
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-manage-specialist/SKILL.md").is_file()
    assert not (home_path / "skills/mailbox/houmao-process-emails-via-gateway").exists()
    assert not (home_path / "skills/project/houmao-create-specialist").exists()
    assert not (home_path / "skills/mailbox").exists()
    assert not (home_path / "skills/project").exists()

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    assert state is not None
    assert tuple(record.projected_relative_dir for record in state.installed_skills) == (
        "skills/houmao-process-emails-via-gateway",
        "skills/houmao-manage-specialist",
    )
    assert tuple(record.name for record in state.installed_skills) == (
        "houmao-process-emails-via-gateway",
        "houmao-manage-specialist",
    )


def test_install_system_skills_for_home_migrates_renamed_specialist_owned_path(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    _write(
        home_path / "skills/houmao-create-specialist/SKILL.md",
        "old flat project-easy path\n",
    )
    state_path = system_skill_state_path_for_home(home_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": SYSTEM_SKILL_STATE_SCHEMA_VERSION,
                "tool": "codex",
                "installed_at": "2026-04-05T00:00:00Z",
                "installed_skills": [
                    {
                        "name": "houmao-create-specialist",
                        "asset_subpath": "houmao-create-specialist",
                        "projected_relative_dir": "skills/houmao-create-specialist",
                        "content_digest": "old-flat-project",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        skill_names=("houmao-manage-specialist",),
    )

    assert result.projected_relative_dirs == ("skills/houmao-manage-specialist",)
    assert (home_path / "skills/houmao-manage-specialist/SKILL.md").is_file()
    assert not (home_path / "skills/houmao-create-specialist").exists()

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    assert state is not None
    assert tuple(record.name for record in state.installed_skills) == ("houmao-manage-specialist",)
    assert tuple(record.projected_relative_dir for record in state.installed_skills) == (
        "skills/houmao-manage-specialist",
    )
