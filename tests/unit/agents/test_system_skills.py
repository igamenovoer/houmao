from __future__ import annotations

import json
from pathlib import Path

import pytest

import houmao.agents.system_skills as system_skills_module
from houmao.agents.system_skills import (
    SYSTEM_SKILL_SET_AGENT_GATEWAY,
    SYSTEM_SKILL_SET_AGENT_MESSAGING,
    SYSTEM_SKILL_SET_AGENT_INSTANCE,
    SYSTEM_SKILL_SET_MAILBOX_FULL,
    SYSTEM_SKILL_SET_USER_CONTROL,
    SYSTEM_SKILL_STATE_SCHEMA_VERSION,
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


def _packaged_skill_asset_root(skill_name: str) -> Path:
    return (
        Path(__file__).resolve().parents[3] / "src/houmao/agents/assets/system_skills" / skill_name
    ).resolve()


def test_load_system_skill_catalog_reports_named_sets_and_auto_install_defaults() -> None:
    catalog = load_system_skill_catalog()

    assert catalog.schema_version == 1
    assert tuple(catalog.skills.keys()) == (
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
        "houmao-mailbox-mgr",
        "houmao-specialist-mgr",
        "houmao-credential-mgr",
        "houmao-agent-definition",
        "houmao-agent-instance",
        "houmao-agent-messaging",
        "houmao-agent-gateway",
    )
    assert tuple(catalog.sets.keys()) == (
        "mailbox-core",
        "mailbox-full",
        "user-control",
        "agent-instance",
        "agent-messaging",
        "agent-gateway",
    )
    assert catalog.auto_install.managed_launch_sets == (
        SYSTEM_SKILL_SET_MAILBOX_FULL,
        SYSTEM_SKILL_SET_USER_CONTROL,
        SYSTEM_SKILL_SET_AGENT_MESSAGING,
        SYSTEM_SKILL_SET_AGENT_GATEWAY,
    )
    assert catalog.auto_install.managed_join_sets == (
        SYSTEM_SKILL_SET_MAILBOX_FULL,
        SYSTEM_SKILL_SET_USER_CONTROL,
        SYSTEM_SKILL_SET_AGENT_MESSAGING,
        SYSTEM_SKILL_SET_AGENT_GATEWAY,
    )
    assert catalog.auto_install.cli_default_sets == (
        SYSTEM_SKILL_SET_MAILBOX_FULL,
        SYSTEM_SKILL_SET_USER_CONTROL,
        SYSTEM_SKILL_SET_AGENT_INSTANCE,
        SYSTEM_SKILL_SET_AGENT_MESSAGING,
        SYSTEM_SKILL_SET_AGENT_GATEWAY,
    )


def test_resolve_system_skill_selection_dedupes_sets_and_explicit_skills() -> None:
    catalog = load_system_skill_catalog()

    resolved = resolve_system_skill_selection(
        catalog,
        set_names=(
            "mailbox-core",
            "mailbox-full",
            "user-control",
            "agent-messaging",
            "agent-gateway",
        ),
        skill_names=("houmao-agent-email-comms", "houmao-specialist-mgr"),
    )

    assert resolved == (
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
        "houmao-mailbox-mgr",
        "houmao-specialist-mgr",
        "houmao-credential-mgr",
        "houmao-agent-definition",
        "houmao-agent-messaging",
        "houmao-agent-gateway",
    )
    assert resolve_auto_install_skill_selection(catalog, kind="managed_launch") == resolved


def test_resolve_system_skill_selection_cli_default_includes_agent_instance_messaging_and_gateway_skills() -> (
    None
):
    catalog = load_system_skill_catalog()

    resolved = resolve_auto_install_skill_selection(catalog, kind="cli_default")

    assert resolved == (
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
        "houmao-mailbox-mgr",
        "houmao-specialist-mgr",
        "houmao-credential-mgr",
        "houmao-agent-definition",
        "houmao-agent-instance",
        "houmao-agent-messaging",
        "houmao-agent-gateway",
    )


def test_load_system_skill_catalog_rejects_unknown_set_member(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.toml"
    _write(
        catalog_path,
        """
schema_version = 1

[skills.houmao-agent-email-comms]
asset_subpath = "houmao-agent-email-comms"

[sets.mailbox-core]
skills = ["houmao-agent-email-comms", "houmao-missing"]

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
        skill_names=("houmao-agent-email-comms",),
    )

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    manage_specialist_path = home_path / "skills/houmao-specialist-mgr/SKILL.md"
    manage_specialist_actions = home_path / "skills/houmao-specialist-mgr/actions"
    manage_specialist_references = home_path / "skills/houmao-specialist-mgr/references"
    manage_credentials_path = home_path / "skills/houmao-credential-mgr/SKILL.md"
    manage_credentials_actions = home_path / "skills/houmao-credential-mgr/actions"
    manage_agent_definition_path = home_path / "skills/houmao-agent-definition/SKILL.md"
    manage_agent_definition_agents = home_path / "skills/houmao-agent-definition/agents"
    manage_agent_definition_actions = home_path / "skills/houmao-agent-definition/actions"

    assert result.resolved_skill_names == (
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
        "houmao-specialist-mgr",
        "houmao-credential-mgr",
        "houmao-agent-definition",
    )
    assert state is not None
    assert state.schema_version == SYSTEM_SKILL_STATE_SCHEMA_VERSION
    assert tuple(record.name for record in state.installed_skills) == result.resolved_skill_names
    assert tuple(record.projection_mode for record in state.installed_skills) == (
        "copy",
        "copy",
        "copy",
        "copy",
        "copy",
    )
    assert user_skill_path.is_file()
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-email-comms/SKILL.md").is_file()
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
    launch_action_path = manage_specialist_actions / "launch.md"
    stop_action_path = manage_specialist_actions / "stop.md"
    create_action = create_action_path.read_text(encoding="utf-8")
    list_action = list_action_path.read_text(encoding="utf-8")
    get_action = get_action_path.read_text(encoding="utf-8")
    remove_action = remove_action_path.read_text(encoding="utf-8")
    launch_action = launch_action_path.read_text(encoding="utf-8")
    stop_action = stop_action_path.read_text(encoding="utf-8")
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
    assert "command -v houmao-mgr" in manage_specialist_skill
    assert "uv tool run --from houmao houmao-mgr" in manage_specialist_skill
    assert ".venv/bin/houmao-mgr" in manage_specialist_skill
    assert "pixi run houmao-mgr" in manage_specialist_skill
    assert "uv run houmao-mgr" in manage_specialist_skill
    assert "user explicitly asks for a specific launcher" in manage_specialist_skill
    assert "actions/create.md" in manage_specialist_skill
    assert "actions/list.md" in manage_specialist_skill
    assert "actions/get.md" in manage_specialist_skill
    assert "actions/remove.md" in manage_specialist_skill
    assert "actions/launch.md" in manage_specialist_skill
    assert "create profile" in manage_specialist_skill
    assert "list profiles" in manage_specialist_skill
    assert "get profile" in manage_specialist_skill
    assert "remove profile" in manage_specialist_skill
    assert "Explicit Auth Mode" in create_action
    assert "project easy profile create" in create_action
    assert "--prompt-overlay-mode append|replace" in create_action
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
    assert "project easy profile list" in list_action
    assert "Use the `houmao-mgr` launcher already chosen by the top-level skill." in list_action
    assert "<chosen houmao-mgr launcher>" in list_action
    assert "project easy profile get --name <name>" in get_action
    assert "project easy profile remove --name <name>" in remove_action
    assert "project easy instance launch --profile <profile>" in launch_action
    assert "project easy profile get --name <profile>" in launch_action
    assert "whether it was launched from a specialist or from an easy profile" in stop_action
    assert "command -v houmao-mgr" in manage_credentials_skill
    assert "uv tool run --from houmao houmao-mgr" in manage_credentials_skill
    assert ".venv/bin/houmao-mgr" in manage_credentials_skill
    assert "pixi run houmao-mgr" in manage_credentials_skill
    assert "uv run houmao-mgr" in manage_credentials_skill
    assert "actions/list.md" in manage_credentials_skill
    assert "actions/get.md" in manage_credentials_skill
    assert "actions/add.md" in manage_credentials_skill
    assert "actions/set.md" in manage_credentials_skill
    assert "actions/remove.md" in manage_credentials_skill
    assert "project agents tools <tool> auth ..." in manage_credentials_skill
    assert "project easy profile ..." in manage_credentials_skill
    assert "project agents launch-profiles ..." in manage_credentials_skill
    assert (
        "Do not treat changing an easy profile or explicit launch profile `--auth` override"
        in manage_credentials_skill
    )
    assert "Do not print raw secret values" in manage_credentials_skill
    assert credentials_list_action_path.is_file()
    assert credentials_get_action_path.is_file()
    assert credentials_add_action_path.is_file()
    assert credentials_set_action_path.is_file()
    assert credentials_remove_action_path.is_file()
    assert "Use the `houmao-mgr` launcher already chosen by the top-level skill." in credentials_get_action
    assert "<chosen houmao-mgr launcher>" in credentials_get_action
    assert "project agents tools <tool> auth get --name <name>" in credentials_get_action
    assert "Do not bypass `auth get`" in credentials_get_action
    assert (
        "stored easy-profile or explicit launch-profile `--auth` override" in credentials_get_action
    )
    assert "Do not invent unsupported clear flags" in credentials_set_action
    assert (
        "stored easy-profile or explicit launch-profile `--auth` override change"
        in credentials_set_action
    )
    assert (
        "Do not continue with set when the user has not provided any explicit supported change"
        in credentials_set_action
    )
    assert "command -v houmao-mgr" in manage_agent_definition_skill
    assert "uv tool run --from houmao houmao-mgr" in manage_agent_definition_skill
    assert ".venv/bin/houmao-mgr" in manage_agent_definition_skill
    assert "pixi run houmao-mgr" in manage_agent_definition_skill
    assert "uv run houmao-mgr" in manage_agent_definition_skill
    assert "actions/create.md" in manage_agent_definition_skill
    assert "actions/list.md" in manage_agent_definition_skill
    assert "actions/get.md" in manage_agent_definition_skill
    assert "actions/set.md" in manage_agent_definition_skill
    assert "actions/remove.md" in manage_agent_definition_skill
    assert "project agents roles list|get|init|set|remove" in manage_agent_definition_skill
    assert "project agents recipes list|get|add|set|remove" in manage_agent_definition_skill
    assert "project agents presets list|get|add|set|remove" in manage_agent_definition_skill
    assert "houmao-credential-mgr" in manage_agent_definition_skill
    assert "project agents roles scaffold" in manage_agent_definition_skill
    assert "project agents roles presets ..." in manage_agent_definition_skill
    assert "direct hand-editing under `.houmao/agents/`" in manage_agent_definition_skill
    assert (manage_agent_definition_agents / "openai.yaml").is_file()
    assert definition_create_action_path.is_file()
    assert definition_list_action_path.is_file()
    assert definition_get_action_path.is_file()
    assert definition_set_action_path.is_file()
    assert definition_remove_action_path.is_file()
    assert "Use the `houmao-mgr` launcher already chosen by the top-level skill." in definition_get_action
    assert "<chosen houmao-mgr launcher>" in definition_get_action
    assert "project agents roles init --name <role>" in definition_create_action_path.read_text(
        encoding="utf-8"
    )
    assert (
        "project agents recipes add --name <recipe> --role <role> --tool <tool>"
        in definition_create_action_path.read_text(encoding="utf-8")
    )
    assert "project agents roles list" in definition_list_action_path.read_text(encoding="utf-8")
    assert "project agents recipes list" in definition_list_action_path.read_text(encoding="utf-8")
    assert "project agents roles get --name <role> --include-prompt" in definition_get_action
    assert "project agents recipes get --name <recipe>" in definition_get_action
    assert "project agents roles set --name <role>" in definition_set_action
    assert "project agents recipes set --name <recipe>" in definition_set_action
    assert "--clear-auth" in definition_set_action
    assert "houmao-credential-mgr" in definition_set_action
    assert "project agents roles remove --name <role>" in definition_remove_action_path.read_text(
        encoding="utf-8"
    )
    assert (
        "project agents recipes remove --name <recipe>"
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


def test_install_system_skills_for_home_cli_default_includes_agent_instance_messaging_and_gateway_skills(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()

    result = install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        use_cli_default=True,
    )

    manage_agent_instance_path = home_path / "skills/houmao-agent-instance/SKILL.md"
    manage_agent_instance_actions = home_path / "skills/houmao-agent-instance/actions"
    mailbox_mgr_path = home_path / "skills/houmao-mailbox-mgr/SKILL.md"
    mailbox_mgr_actions = home_path / "skills/houmao-mailbox-mgr/actions"
    mailbox_mgr_references = home_path / "skills/houmao-mailbox-mgr/references"
    agent_messaging_path = home_path / "skills/houmao-agent-messaging/SKILL.md"
    agent_messaging_actions = home_path / "skills/houmao-agent-messaging/actions"
    agent_messaging_references = home_path / "skills/houmao-agent-messaging/references"
    agent_gateway_path = home_path / "skills/houmao-agent-gateway/SKILL.md"
    agent_gateway_actions = home_path / "skills/houmao-agent-gateway/actions"
    agent_gateway_references = home_path / "skills/houmao-agent-gateway/references"

    assert result.selected_set_names == (
        "mailbox-full",
        "user-control",
        "agent-instance",
        "agent-messaging",
        "agent-gateway",
    )
    assert result.projection_mode == "copy"
    assert result.resolved_skill_names == (
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
        "houmao-mailbox-mgr",
        "houmao-specialist-mgr",
        "houmao-credential-mgr",
        "houmao-agent-definition",
        "houmao-agent-instance",
        "houmao-agent-messaging",
        "houmao-agent-gateway",
    )
    assert (home_path / "skills/houmao-credential-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-definition/SKILL.md").is_file()
    assert mailbox_mgr_path.is_file()
    assert manage_agent_instance_path.is_file()
    assert agent_messaging_path.is_file()
    assert agent_gateway_path.is_file()
    mailbox_mgr_skill = mailbox_mgr_path.read_text(encoding="utf-8")
    manage_agent_instance_skill = manage_agent_instance_path.read_text(encoding="utf-8")
    agent_messaging_skill = agent_messaging_path.read_text(encoding="utf-8")
    agent_gateway_skill = agent_gateway_path.read_text(encoding="utf-8")
    launch_action_path = manage_agent_instance_actions / "launch.md"
    join_action_path = manage_agent_instance_actions / "join.md"
    list_action_path = manage_agent_instance_actions / "list.md"
    stop_action_path = manage_agent_instance_actions / "stop.md"
    relaunch_action_path = manage_agent_instance_actions / "relaunch.md"
    cleanup_action_path = manage_agent_instance_actions / "cleanup.md"
    launch_action = launch_action_path.read_text(encoding="utf-8")
    relaunch_action = relaunch_action_path.read_text(encoding="utf-8")
    cleanup_action = cleanup_action_path.read_text(encoding="utf-8")
    discover_action_path = agent_messaging_actions / "discover.md"
    prompt_action_path = agent_messaging_actions / "prompt.md"
    interrupt_action_path = agent_messaging_actions / "interrupt.md"
    gateway_queue_action_path = agent_messaging_actions / "gateway-queue.md"
    send_keys_action_path = agent_messaging_actions / "send-keys.md"
    mail_action_path = agent_messaging_actions / "mail.md"
    reset_context_action_path = agent_messaging_actions / "reset-context.md"
    intent_matrix_reference_path = agent_messaging_references / "intent-matrix.md"
    managed_agent_http_reference_path = agent_messaging_references / "managed-agent-http.md"
    gateway_lifecycle_action_path = agent_gateway_actions / "lifecycle.md"
    gateway_discover_action_path = agent_gateway_actions / "discover.md"
    gateway_services_action_path = agent_gateway_actions / "gateway-services.md"
    gateway_wakeups_action_path = agent_gateway_actions / "wakeups.md"
    gateway_mail_notifier_action_path = agent_gateway_actions / "mail-notifier.md"
    gateway_scope_reference_path = agent_gateway_references / "scope-and-routing.md"
    gateway_http_reference_path = agent_gateway_references / "http-surface.md"
    mailbox_init_action_path = mailbox_mgr_actions / "init.md"
    mailbox_register_action_path = mailbox_mgr_actions / "register.md"
    mailbox_messages_get_action_path = mailbox_mgr_actions / "messages-get.md"
    mailbox_agent_binding_register_action_path = mailbox_mgr_actions / "agent-binding-register.md"
    mailbox_root_reference_path = mailbox_mgr_references / "root-selection.md"
    mailbox_mode_reference_path = mailbox_mgr_references / "mode-vocabulary.md"
    mailbox_structural_reference_path = mailbox_mgr_references / "structural-vs-actor-state.md"
    mailbox_stalwart_reference_path = mailbox_mgr_references / "stalwart-boundary.md"
    discover_action = discover_action_path.read_text(encoding="utf-8")
    reset_context_action = reset_context_action_path.read_text(encoding="utf-8")
    mail_action = mail_action_path.read_text(encoding="utf-8")
    gateway_discover_action = gateway_discover_action_path.read_text(encoding="utf-8")
    gateway_wakeups_action = gateway_wakeups_action_path.read_text(encoding="utf-8")
    gateway_http_reference = gateway_http_reference_path.read_text(encoding="utf-8")

    assert "actions/init.md" in mailbox_mgr_skill
    assert "actions/register.md" in mailbox_mgr_skill
    assert "actions/agent-binding-register.md" in mailbox_mgr_skill
    assert "references/root-selection.md" in mailbox_mgr_skill
    assert "command -v houmao-mgr" in mailbox_mgr_skill
    assert "uv tool run --from houmao houmao-mgr" in mailbox_mgr_skill
    assert "houmao-mgr mailbox ..." in mailbox_mgr_skill
    assert "houmao-mgr project mailbox ..." in mailbox_mgr_skill
    assert "houmao-mgr agents mailbox ..." in mailbox_mgr_skill
    assert mailbox_init_action_path.is_file()
    assert mailbox_register_action_path.is_file()
    assert mailbox_messages_get_action_path.is_file()
    assert mailbox_agent_binding_register_action_path.is_file()
    assert mailbox_root_reference_path.is_file()
    assert mailbox_mode_reference_path.is_file()
    assert mailbox_structural_reference_path.is_file()
    assert mailbox_stalwart_reference_path.is_file()
    assert "Use the `houmao-mgr` launcher already chosen by the top-level skill." in mailbox_init_action_path.read_text(
        encoding="utf-8"
    )
    assert "<chosen houmao-mgr launcher>" in mailbox_init_action_path.read_text(encoding="utf-8")
    assert "actions/launch.md" in manage_agent_instance_skill
    assert "actions/join.md" in manage_agent_instance_skill
    assert "actions/list.md" in manage_agent_instance_skill
    assert "actions/stop.md" in manage_agent_instance_skill
    assert "actions/relaunch.md" in manage_agent_instance_skill
    assert "actions/cleanup.md" in manage_agent_instance_skill
    assert "project easy specialist create" in manage_agent_instance_skill
    assert "agents cleanup mailbox" in manage_agent_instance_skill
    assert "agents relaunch" in manage_agent_instance_skill
    assert launch_action_path.is_file()
    assert join_action_path.is_file()
    assert list_action_path.is_file()
    assert stop_action_path.is_file()
    assert relaunch_action_path.is_file()
    assert cleanup_action_path.is_file()
    assert "command -v houmao-mgr" in manage_agent_instance_skill
    assert "uv tool run --from houmao houmao-mgr" in manage_agent_instance_skill
    assert "agents launch" in launch_action
    assert "--launch-profile" in launch_action
    assert "launch-profile-backed" in launch_action
    assert "project easy instance launch" in launch_action
    assert "--mail-transport" in launch_action
    assert "agents relaunch --agent-name" in relaunch_action
    assert "current-session relaunch" in relaunch_action
    assert "Do not reinterpret a relaunch request as `agents launch`" in relaunch_action
    assert "agents cleanup session" in cleanup_action
    assert "agents cleanup logs" in cleanup_action
    assert "admin cleanup runtime" in cleanup_action
    assert "actions/discover.md" in agent_messaging_skill
    assert "actions/prompt.md" in agent_messaging_skill
    assert "actions/interrupt.md" in agent_messaging_skill
    assert "actions/gateway-queue.md" in agent_messaging_skill
    assert "actions/send-keys.md" in agent_messaging_skill
    assert "actions/mail.md" in agent_messaging_skill
    assert "actions/reset-context.md" in agent_messaging_skill
    assert "houmao-mgr agents prompt" in agent_messaging_skill
    assert "command -v houmao-mgr" in agent_messaging_skill
    assert "uv tool run --from houmao houmao-mgr" in agent_messaging_skill
    assert discover_action_path.is_file()
    assert prompt_action_path.is_file()
    assert interrupt_action_path.is_file()
    assert gateway_queue_action_path.is_file()
    assert send_keys_action_path.is_file()
    assert mail_action_path.is_file()
    assert reset_context_action_path.is_file()
    assert intent_matrix_reference_path.is_file()
    assert managed_agent_http_reference_path.is_file()
    assert "Use the `houmao-mgr` launcher already chosen by the top-level skill." in discover_action
    assert "<chosen houmao-mgr launcher>" in discover_action
    assert "actions/lifecycle.md" in agent_gateway_skill
    assert "actions/discover.md" in agent_gateway_skill
    assert "actions/gateway-services.md" in agent_gateway_skill
    assert "actions/wakeups.md" in agent_gateway_skill
    assert "actions/mail-notifier.md" in agent_gateway_skill
    assert "HOUMAO_MANIFEST_PATH" in agent_gateway_skill
    assert "HOUMAO_GATEWAY_ATTACH_PATH" in agent_gateway_skill
    assert "houmao-mgr agents gateway attach|detach|status" in agent_gateway_skill
    assert "command -v houmao-mgr" in agent_gateway_skill
    assert "uv tool run --from houmao houmao-mgr" in agent_gateway_skill
    assert gateway_lifecycle_action_path.is_file()
    assert gateway_discover_action_path.is_file()
    assert gateway_services_action_path.is_file()
    assert gateway_wakeups_action_path.is_file()
    assert gateway_mail_notifier_action_path.is_file()
    assert gateway_scope_reference_path.is_file()
    assert gateway_http_reference_path.is_file()
    assert "HOUMAO_AGENT_ID" in gateway_discover_action
    assert "Use the `houmao-mgr` launcher already chosen by the top-level skill." in gateway_discover_action
    assert "<chosen houmao-mgr launcher>" in gateway_discover_action
    assert "agents mail resolve-live" in gateway_discover_action
    assert "/v1/wakeups" in gateway_wakeups_action
    assert "gateway stop or restart" in gateway_wakeups_action
    assert "process-local in-memory state" in gateway_wakeups_action
    assert "/houmao/agents/{agent_ref}/gateway/wakeups" in gateway_http_reference
    assert "POST /houmao/agents/{agent_ref}/gateway/control/prompt" in reset_context_action
    assert 'chat_session.mode = "new"' in reset_context_action
    assert "houmao-process-emails-via-gateway" in mail_action
    assert "houmao-agent-email-comms" in mail_action


def test_install_system_skills_for_home_supports_explicit_symlink_projection(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()

    result = install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        skill_names=("houmao-specialist-mgr",),
        projection_mode="symlink",
    )

    installed_skill_dir = home_path / "skills/houmao-specialist-mgr"
    state = load_system_skill_install_state(tool="codex", home_path=home_path)

    assert result.projection_mode == "symlink"
    assert installed_skill_dir.is_symlink()
    assert installed_skill_dir.readlink().is_absolute()
    assert installed_skill_dir.readlink() == _packaged_skill_asset_root("houmao-specialist-mgr")
    assert (installed_skill_dir / "SKILL.md").is_file()
    assert state is not None
    assert tuple(record.name for record in state.installed_skills) == ("houmao-specialist-mgr",)
    assert tuple(record.projection_mode for record in state.installed_skills) == ("symlink",)


def test_install_system_skills_for_home_rejects_symlink_projection_without_filesystem_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()

    def _raise_no_filesystem_root(asset_subpath: str) -> Path:
        raise SystemSkillInstallError(
            f"Packaged system-skill assets for `{asset_subpath}` are not filesystem-backed."
        )

    monkeypatch.setattr(
        system_skills_module,
        "_packaged_skill_filesystem_root",
        _raise_no_filesystem_root,
    )

    with pytest.raises(SystemSkillInstallError, match="not filesystem-backed"):
        install_system_skills_for_home(
            tool="codex",
            home_path=home_path,
            skill_names=("houmao-specialist-mgr",),
            projection_mode="symlink",
        )


def test_install_system_skills_for_home_reinstalls_between_copy_and_symlink_modes(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    installed_skill_dir = home_path / "skills/houmao-specialist-mgr"

    install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        skill_names=("houmao-specialist-mgr",),
    )
    assert installed_skill_dir.is_dir()
    assert not installed_skill_dir.is_symlink()

    install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        skill_names=("houmao-specialist-mgr",),
        projection_mode="symlink",
    )
    assert installed_skill_dir.is_symlink()
    assert installed_skill_dir.readlink() == _packaged_skill_asset_root("houmao-specialist-mgr")
    assert (installed_skill_dir / "SKILL.md").is_file()

    install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        skill_names=("houmao-specialist-mgr",),
        projection_mode="copy",
    )
    assert installed_skill_dir.is_dir()
    assert not installed_skill_dir.is_symlink()
    assert (installed_skill_dir / "SKILL.md").is_file()

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    assert state is not None
    assert tuple(record.name for record in state.installed_skills) == ("houmao-specialist-mgr",)
    assert tuple(record.projection_mode for record in state.installed_skills) == ("copy",)


def test_install_system_skills_for_home_rejects_non_owned_collision(tmp_path: Path) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    conflicting_skill_path = home_path / "skills/houmao-agent-email-comms/SKILL.md"
    _write(conflicting_skill_path, "user-authored collision\n")

    with pytest.raises(
        SystemSkillInstallError,
        match="Refusing to overwrite non-owned system-skill path",
    ):
        install_system_skills_for_home(
            tool="codex",
            home_path=home_path,
            skill_names=("houmao-agent-email-comms",),
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
                "schema_version": 1,
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
        skill_names=("houmao-process-emails-via-gateway", "houmao-specialist-mgr"),
    )

    assert result.projected_relative_dirs == (
        "skills/houmao-process-emails-via-gateway",
        "skills/houmao-specialist-mgr",
    )
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert not (home_path / "skills/mailbox/houmao-process-emails-via-gateway").exists()
    assert not (home_path / "skills/project/houmao-create-specialist").exists()
    assert not (home_path / "skills/mailbox").exists()
    assert not (home_path / "skills/project").exists()

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    assert state is not None
    assert tuple(record.projected_relative_dir for record in state.installed_skills) == (
        "skills/houmao-process-emails-via-gateway",
        "skills/houmao-specialist-mgr",
    )
    assert tuple(record.name for record in state.installed_skills) == (
        "houmao-process-emails-via-gateway",
        "houmao-specialist-mgr",
    )
    assert tuple(record.projection_mode for record in state.installed_skills) == ("copy", "copy")


def test_install_system_skills_for_home_migrates_legacy_gemini_owned_paths_for_recorded_skills(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "gemini-home").resolve()
    _write(
        home_path / ".agents/skills/houmao-specialist-mgr/SKILL.md",
        "old specialist path\n",
    )
    _write(
        home_path / ".agents/skills/houmao-agent-instance/SKILL.md",
        "old agent-instance path\n",
    )
    state_path = system_skill_state_path_for_home(home_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": SYSTEM_SKILL_STATE_SCHEMA_VERSION,
                "tool": "gemini",
                "installed_at": "2026-04-05T00:00:00Z",
                "installed_skills": [
                    {
                        "name": "houmao-specialist-mgr",
                        "asset_subpath": "houmao-specialist-mgr",
                        "projected_relative_dir": ".agents/skills/houmao-specialist-mgr",
                        "projection_mode": "copy",
                        "content_digest": "old-specialist",
                    },
                    {
                        "name": "houmao-agent-instance",
                        "asset_subpath": "houmao-agent-instance",
                        "projected_relative_dir": ".agents/skills/houmao-agent-instance",
                        "projection_mode": "copy",
                        "content_digest": "old-agent-instance",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = install_system_skills_for_home(
        tool="gemini",
        home_path=home_path,
        skill_names=("houmao-specialist-mgr",),
    )

    assert result.projected_relative_dirs == (".gemini/skills/houmao-specialist-mgr",)
    assert (home_path / ".gemini/skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert (home_path / ".gemini/skills/houmao-agent-instance/SKILL.md").is_file()
    assert not (home_path / ".agents/skills/houmao-specialist-mgr").exists()
    assert not (home_path / ".agents/skills/houmao-agent-instance").exists()
    assert not (home_path / ".agents/skills").exists()

    state = load_system_skill_install_state(tool="gemini", home_path=home_path)
    assert state is not None
    assert tuple(record.name for record in state.installed_skills) == (
        "houmao-specialist-mgr",
        "houmao-agent-instance",
    )
    assert tuple(record.projected_relative_dir for record in state.installed_skills) == (
        ".gemini/skills/houmao-specialist-mgr",
        ".gemini/skills/houmao-agent-instance",
    )
    assert tuple(record.projection_mode for record in state.installed_skills) == ("copy", "copy")


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
                "schema_version": 1,
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
        skill_names=("houmao-specialist-mgr",),
    )

    assert result.projected_relative_dirs == ("skills/houmao-specialist-mgr",)
    assert (home_path / "skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert not (home_path / "skills/houmao-create-specialist").exists()

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    assert state is not None
    assert tuple(record.name for record in state.installed_skills) == ("houmao-specialist-mgr",)
    assert tuple(record.projected_relative_dir for record in state.installed_skills) == (
        "skills/houmao-specialist-mgr",
    )
    assert tuple(record.projection_mode for record in state.installed_skills) == ("copy",)


@pytest.mark.parametrize(
    ("legacy_name", "current_name"),
    [
        ("houmao-manage-specialist", "houmao-specialist-mgr"),
        ("houmao-manage-credentials", "houmao-credential-mgr"),
        ("houmao-manage-agent-definition", "houmao-agent-definition"),
        ("houmao-manage-agent-instance", "houmao-agent-instance"),
    ],
)
def test_install_system_skills_for_home_migrates_superseded_current_skill_owned_path(
    tmp_path: Path,
    legacy_name: str,
    current_name: str,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    _write(
        home_path / f"skills/{legacy_name}/SKILL.md",
        "old flat skill path\n",
    )
    state_path = system_skill_state_path_for_home(home_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": SYSTEM_SKILL_STATE_SCHEMA_VERSION,
                "tool": "codex",
                "installed_at": "2026-04-08T00:00:00Z",
                "installed_skills": [
                    {
                        "name": legacy_name,
                        "asset_subpath": legacy_name,
                        "projected_relative_dir": f"skills/{legacy_name}",
                        "projection_mode": "copy",
                        "content_digest": "old-flat-skill",
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
        skill_names=(current_name,),
    )

    assert result.projected_relative_dirs == (f"skills/{current_name}",)
    assert (home_path / f"skills/{current_name}/SKILL.md").is_file()
    assert not (home_path / f"skills/{legacy_name}").exists()

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    assert state is not None
    assert tuple(record.name for record in state.installed_skills) == (current_name,)
    assert tuple(record.projected_relative_dir for record in state.installed_skills) == (
        f"skills/{current_name}",
    )
    assert tuple(record.projection_mode for record in state.installed_skills) == ("copy",)
