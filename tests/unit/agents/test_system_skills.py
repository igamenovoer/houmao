from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import houmao.agents.system_skills as system_skills_module
from houmao.agents.system_skills import (
    SYSTEM_SKILL_SET_ALL,
    SYSTEM_SKILL_SET_CORE,
    SYSTEM_SKILL_UTILS_LLM_WIKI,
    SYSTEM_SKILL_UTILS_WORKSPACE_MGR,
    SystemSkillCatalogError,
    SystemSkillInstallError,
    discover_installed_system_skills,
    install_system_skills_for_home,
    load_system_skill_catalog,
    load_system_skill_catalog_from_paths,
    resolve_auto_install_skill_selection,
    resolve_system_skill_selection,
    uninstall_system_skills_for_home,
)

CORE_SYSTEM_SKILLS = (
    "houmao-process-emails-via-gateway",
    "houmao-agent-email-comms",
    "houmao-mailbox-mgr",
    "houmao-memory-mgr",
    "houmao-adv-usage-pattern",
    "houmao-touring",
    "houmao-project-mgr",
    "houmao-specialist-mgr",
    "houmao-credential-mgr",
    "houmao-agent-definition",
    "houmao-agent-loop-pairwise",
    "houmao-agent-loop-pairwise-v2",
    "houmao-agent-loop-generic",
    "houmao-agent-instance",
    "houmao-agent-inspect",
    "houmao-agent-messaging",
    "houmao-agent-gateway",
)
ALL_SYSTEM_SKILLS = (
    *CORE_SYSTEM_SKILLS,
    SYSTEM_SKILL_UTILS_LLM_WIKI,
    SYSTEM_SKILL_UTILS_WORKSPACE_MGR,
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


def _obsolete_system_skill_state_path(home_path: Path) -> Path:
    return (home_path.resolve() / ".houmao/system-skills/install-state.json").resolve()


def _assert_no_install_state_written(home_path: Path) -> None:
    assert not _obsolete_system_skill_state_path(home_path).exists()


def test_load_system_skill_catalog_reports_named_sets_and_auto_install_defaults() -> None:
    catalog = load_system_skill_catalog()

    assert catalog.schema_version == 1
    assert tuple(catalog.skills.keys()) == (
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
        "houmao-adv-usage-pattern",
        "houmao-utils-llm-wiki",
        "houmao-utils-workspace-mgr",
        "houmao-touring",
        "houmao-mailbox-mgr",
        "houmao-memory-mgr",
        "houmao-project-mgr",
        "houmao-specialist-mgr",
        "houmao-credential-mgr",
        "houmao-agent-definition",
        "houmao-agent-loop-pairwise",
        "houmao-agent-loop-pairwise-v2",
        "houmao-agent-loop-generic",
        "houmao-agent-instance",
        "houmao-agent-inspect",
        "houmao-agent-messaging",
        "houmao-agent-gateway",
    )
    assert tuple(catalog.sets.keys()) == (
        SYSTEM_SKILL_SET_CORE,
        SYSTEM_SKILL_SET_ALL,
    )
    assert catalog.sets[SYSTEM_SKILL_SET_CORE].skill_names == CORE_SYSTEM_SKILLS
    assert catalog.sets[SYSTEM_SKILL_SET_ALL].skill_names == ALL_SYSTEM_SKILLS
    assert catalog.auto_install.managed_launch_sets == (SYSTEM_SKILL_SET_CORE,)
    assert catalog.auto_install.managed_join_sets == (SYSTEM_SKILL_SET_CORE,)
    assert catalog.auto_install.cli_default_sets == (SYSTEM_SKILL_SET_ALL,)


def test_resolve_system_skill_selection_dedupes_sets_and_explicit_skills() -> None:
    catalog = load_system_skill_catalog()

    resolved = resolve_system_skill_selection(
        catalog,
        set_names=(SYSTEM_SKILL_SET_CORE,),
        skill_names=("houmao-agent-email-comms", "houmao-specialist-mgr"),
    )

    assert resolved == CORE_SYSTEM_SKILLS
    assert resolve_auto_install_skill_selection(catalog, kind="managed_launch") == resolved


def test_resolve_system_skill_selection_all_adds_utilities_to_core() -> None:
    catalog = load_system_skill_catalog()

    resolved = resolve_system_skill_selection(
        catalog,
        set_names=(SYSTEM_SKILL_SET_ALL,),
    )

    assert resolved == ALL_SYSTEM_SKILLS
    assert SYSTEM_SKILL_SET_ALL not in catalog.auto_install.managed_launch_sets
    assert SYSTEM_SKILL_SET_ALL not in catalog.auto_install.managed_join_sets
    assert catalog.auto_install.cli_default_sets == (SYSTEM_SKILL_SET_ALL,)


def test_resolve_system_skill_selection_cli_default_includes_agent_instance_messaging_and_gateway_skills() -> (
    None
):
    catalog = load_system_skill_catalog()

    resolved = resolve_auto_install_skill_selection(catalog, kind="cli_default")

    assert resolved == ALL_SYSTEM_SKILLS


def test_packaged_installable_sets_are_closed_over_internal_skill_routing() -> None:
    catalog = load_system_skill_catalog()
    skill_name_pattern = re.compile(
        r"(?<![A-Za-z0-9_])("
        + "|".join(re.escape(name) for name in sorted(catalog.skills, key=len, reverse=True))
        + r")(?![A-Za-z0-9_])"
    )
    asset_root = Path(__file__).resolve().parents[3] / "src/houmao/agents/assets/system_skills"

    for set_name, set_record in catalog.sets.items():
        installed = set(set_record.skill_names)
        for skill_name in set_record.skill_names:
            skill_root = asset_root / catalog.skills[skill_name].asset_subpath
            for markdown_path in skill_root.rglob("*.md"):
                refs = set(skill_name_pattern.findall(markdown_path.read_text(encoding="utf-8")))
                refs.discard(skill_name)
                missing = refs - installed
                assert not missing, (
                    f"set `{set_name}` installs `{skill_name}` but "
                    f"{markdown_path.relative_to(skill_root)} references missing skills "
                    f"{sorted(missing)}"
                )


def test_houmao_utils_llm_wiki_packaged_asset_shape() -> None:
    skill_root = _packaged_skill_asset_root(SYSTEM_SKILL_UTILS_LLM_WIKI)
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")

    assert (skill_root / "SKILL.md").is_file()
    assert (skill_root / "references").is_dir()
    assert (skill_root / "scripts").is_dir()
    assert (skill_root / "subskills").is_dir()
    assert (skill_root / "viewer").is_dir()
    assert (skill_root / "viewer/audit-shared/package.json").is_file()
    assert (skill_root / "viewer/web/package.json").is_file()
    assert not list(skill_root.rglob("node_modules"))
    assert not list(skill_root.rglob("dist"))
    assert "name: houmao-utils-llm-wiki" in skill_text
    assert "python3 scripts/scaffold.py" in skill_text
    assert "Authored by" not in skill_text
    assert "Karpathy" not in skill_text


def test_houmao_utils_workspace_mgr_packaged_asset_shape() -> None:
    skill_root = _packaged_skill_asset_root(SYSTEM_SKILL_UTILS_WORKSPACE_MGR)
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    in_repo_text = (skill_root / "subskills/in-repo-workspace.md").read_text(encoding="utf-8")

    assert (skill_root / "SKILL.md").is_file()
    assert (skill_root / "subskills/in-repo-workspace.md").is_file()
    assert (skill_root / "subskills/out-of-repo-workspace.md").is_file()
    assert "name: houmao-utils-workspace-mgr" in skill_text
    assert "seeded-worktree" in skill_text
    assert "Plan Mode" in skill_text
    assert "Execute Mode" in skill_text
    assert "For `in-repo`, the default planned launch cwd is `<repo-root>`" in skill_text
    assert "For `in-repo` memo seeds" in skill_text
    assert "discover local-state symlink candidates recursively" in skill_text
    assert "reachable `.pixi/` directories, at any depth" in skill_text
    assert "explicitly local-only files or directories whose basename does not start with `.`" in (
        skill_text
    )
    assert "`.pixi/` is the only default dot-prefixed exception" in skill_text
    assert "`.hidden-parent/.pixi/` is skipped" in skill_text
    assert "Do not follow symlinked directories" in skill_text
    assert "skip if Git tracks any files under the source subtree" in skill_text
    assert "The repo root is the shared visibility surface." in in_repo_text
    assert "The per-agent `repo/` worktree is the safe mutation surface" in in_repo_text
    assert "recursive local-state symlink decisions" in in_repo_text
    assert "hidden-path skips, symlink traversal skips, and tracked-content conflict skips" in (
        in_repo_text
    )
    assert "| `<repo-root>/houmao-ws/<agent-name>/kb/**` | yes | yes | yes | no |" in (in_repo_text)
    assert "Update launch profiles so each agent cwd points at `<repo-root>`." in in_repo_text


def test_load_system_skill_catalog_rejects_unknown_set_member(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.toml"
    _write(
        catalog_path,
        """
schema_version = 1

[skills.houmao-agent-email-comms]
asset_subpath = "houmao-agent-email-comms"

[sets.core]
skills = ["houmao-agent-email-comms", "houmao-missing"]

[auto_install]
managed_launch_sets = ["core"]
managed_join_sets = ["core"]
cli_default_sets = ["core"]
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


def test_install_system_skills_for_home_projects_selected_skills_and_preserves_user_content(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    user_skill_path = home_path / "skills/custom-user-skill/SKILL.md"
    _write(user_skill_path, "custom user skill\n")

    result = install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        set_names=(SYSTEM_SKILL_SET_CORE,),
        skill_names=("houmao-agent-email-comms",),
    )

    installed_records = discover_installed_system_skills(tool="codex", home_path=home_path)
    project_mgr_path = home_path / "skills/houmao-project-mgr/SKILL.md"
    project_mgr_actions = home_path / "skills/houmao-project-mgr/actions"
    project_mgr_references = home_path / "skills/houmao-project-mgr/references"
    manage_specialist_path = home_path / "skills/houmao-specialist-mgr/SKILL.md"
    manage_specialist_actions = home_path / "skills/houmao-specialist-mgr/actions"
    manage_specialist_references = home_path / "skills/houmao-specialist-mgr/references"
    manage_credentials_path = home_path / "skills/houmao-credential-mgr/SKILL.md"
    manage_credentials_actions = home_path / "skills/houmao-credential-mgr/actions"
    manage_agent_definition_path = home_path / "skills/houmao-agent-definition/SKILL.md"
    manage_agent_definition_agents = home_path / "skills/houmao-agent-definition/agents"
    manage_agent_definition_actions = home_path / "skills/houmao-agent-definition/actions"
    pairwise_loop_skill_path = home_path / "skills/houmao-agent-loop-pairwise/SKILL.md"
    pairwise_loop_authoring = home_path / "skills/houmao-agent-loop-pairwise/authoring"
    pairwise_loop_prestart = home_path / "skills/houmao-agent-loop-pairwise/prestart"
    pairwise_loop_operating = home_path / "skills/houmao-agent-loop-pairwise/operating"
    pairwise_loop_v2_skill_path = home_path / "skills/houmao-agent-loop-pairwise-v2/SKILL.md"
    pairwise_loop_v2_authoring = home_path / "skills/houmao-agent-loop-pairwise-v2/authoring"
    pairwise_loop_v2_prestart = home_path / "skills/houmao-agent-loop-pairwise-v2/prestart"
    pairwise_loop_v2_operating = home_path / "skills/houmao-agent-loop-pairwise-v2/operating"
    relay_loop_skill_path = home_path / "skills/houmao-agent-loop-generic/SKILL.md"
    relay_loop_authoring = home_path / "skills/houmao-agent-loop-generic/authoring"
    relay_loop_operating = home_path / "skills/houmao-agent-loop-generic/operating"

    assert result.selected_set_names == (SYSTEM_SKILL_SET_CORE,)
    assert result.resolved_skill_names == CORE_SYSTEM_SKILLS
    assert set(record.name for record in installed_records) == set(result.resolved_skill_names)
    assert tuple(record.projection_mode for record in installed_records) == ("copy",) * len(
        CORE_SYSTEM_SKILLS
    )
    _assert_no_install_state_written(home_path)
    assert user_skill_path.is_file()
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-email-comms/SKILL.md").is_file()
    assert project_mgr_path.is_file()
    assert manage_specialist_path.is_file()
    assert manage_credentials_path.is_file()
    assert manage_agent_definition_path.is_file()
    assert pairwise_loop_skill_path.is_file()
    assert (pairwise_loop_authoring / "formulate-loop-plan.md").is_file()
    assert not pairwise_loop_prestart.exists()
    assert (pairwise_loop_operating / "start.md").is_file()
    assert (pairwise_loop_operating / "status.md").is_file()
    assert (pairwise_loop_operating / "stop.md").is_file()
    assert not (pairwise_loop_operating / "peek.md").exists()
    assert pairwise_loop_v2_skill_path.is_file()
    assert (pairwise_loop_v2_authoring / "formulate-loop-plan.md").is_file()
    assert (pairwise_loop_v2_prestart / "prepare-run.md").is_file()
    assert (pairwise_loop_v2_operating / "start.md").is_file()
    assert (pairwise_loop_v2_operating / "peek.md").is_file()
    assert (pairwise_loop_v2_operating / "hard-kill.md").is_file()
    assert relay_loop_skill_path.is_file()
    assert (relay_loop_authoring / "formulate-loop-plan.md").is_file()
    assert (relay_loop_operating / "start.md").is_file()
    project_mgr_skill = project_mgr_path.read_text(encoding="utf-8")
    manage_specialist_skill = manage_specialist_path.read_text(encoding="utf-8")
    manage_credentials_skill = manage_credentials_path.read_text(encoding="utf-8")
    manage_agent_definition_skill = manage_agent_definition_path.read_text(encoding="utf-8")
    pairwise_loop_skill = pairwise_loop_skill_path.read_text(encoding="utf-8")
    pairwise_loop_v2_skill = pairwise_loop_v2_skill_path.read_text(encoding="utf-8")
    pairwise_loop_v2_prepare_run = (pairwise_loop_v2_prestart / "prepare-run.md").read_text(
        encoding="utf-8"
    )
    pairwise_loop_v2_start = (pairwise_loop_v2_operating / "start.md").read_text(
        encoding="utf-8"
    )
    relay_loop_skill = relay_loop_skill_path.read_text(encoding="utf-8")
    project_init_action_path = project_mgr_actions / "init.md"
    project_status_action_path = project_mgr_actions / "status.md"
    project_launch_profiles_action_path = project_mgr_actions / "launch-profiles.md"
    project_easy_instances_action_path = project_mgr_actions / "easy-instances.md"
    project_overlay_reference_path = project_mgr_references / "overlay-resolution.md"
    project_layout_reference_path = project_mgr_references / "project-layout.md"
    project_effects_reference_path = project_mgr_references / "project-aware-effects.md"
    project_routing_reference_path = project_mgr_references / "routing-boundaries.md"
    create_action_path = manage_specialist_actions / "create.md"
    list_action_path = manage_specialist_actions / "list.md"
    get_action_path = manage_specialist_actions / "get.md"
    remove_action_path = manage_specialist_actions / "remove.md"
    launch_action_path = manage_specialist_actions / "launch.md"
    stop_action_path = manage_specialist_actions / "stop.md"
    project_init_action = project_init_action_path.read_text(encoding="utf-8")
    project_status_action = project_status_action_path.read_text(encoding="utf-8")
    project_launch_profiles_action = project_launch_profiles_action_path.read_text(encoding="utf-8")
    project_easy_instances_action = project_easy_instances_action_path.read_text(encoding="utf-8")
    project_overlay_reference = project_overlay_reference_path.read_text(encoding="utf-8")
    project_layout_reference = project_layout_reference_path.read_text(encoding="utf-8")
    project_effects_reference = project_effects_reference_path.read_text(encoding="utf-8")
    project_routing_reference = project_routing_reference_path.read_text(encoding="utf-8")
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
    assert "command -v houmao-mgr" in project_mgr_skill
    assert "uv tool run --from houmao houmao-mgr" in project_mgr_skill
    assert ".venv/bin/houmao-mgr" in project_mgr_skill
    assert "pixi run houmao-mgr" in project_mgr_skill
    assert "uv run houmao-mgr" in project_mgr_skill
    assert "project init" in project_mgr_skill
    assert "project status" in project_mgr_skill
    assert "project agents launch-profiles ..." in project_mgr_skill
    assert "project easy instance list|get|stop" in project_mgr_skill
    assert "houmao-specialist-mgr" in project_mgr_skill
    assert "houmao-agent-instance" in project_mgr_skill
    assert "actions/init.md" in project_mgr_skill
    assert "actions/status.md" in project_mgr_skill
    assert "actions/launch-profiles.md" in project_mgr_skill
    assert "actions/easy-instances.md" in project_mgr_skill
    assert "references/project-aware-effects.md" in project_mgr_skill
    assert project_init_action_path.is_file()
    assert project_status_action_path.is_file()
    assert project_launch_profiles_action_path.is_file()
    assert project_easy_instances_action_path.is_file()
    assert project_overlay_reference_path.is_file()
    assert project_layout_reference_path.is_file()
    assert project_effects_reference_path.is_file()
    assert project_routing_reference_path.is_file()
    assert (
        "Use the `houmao-mgr` launcher already chosen by the top-level skill."
        in project_init_action
    )
    assert "<chosen houmao-mgr launcher>" in project_init_action
    assert "--with-compatibility-profiles" not in project_init_action
    assert "would_bootstrap_overlay" in project_status_action
    assert (
        "project agents launch-profiles add --name <profile> --recipe <recipe>"
        in project_launch_profiles_action
    )
    assert "project easy instance list" in project_easy_instances_action
    assert "project easy instance get --name <name>" in project_easy_instances_action
    assert "project easy instance stop --name <name>" in project_easy_instances_action
    assert "HOUMAO_PROJECT_OVERLAY_DIR" in project_overlay_reference
    assert "HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE" in project_overlay_reference
    assert "HOUMAO_AGENT_DEF_DIR" in project_overlay_reference
    assert "catalog.sqlite" in project_layout_reference
    assert "content/" in project_layout_reference
    assert "agents/" in project_layout_reference
    assert "runtime/" in project_layout_reference
    assert "jobs/" in project_layout_reference
    assert "mailbox/" in project_layout_reference
    assert "easy/" in project_layout_reference
    assert "brains build" in project_effects_reference
    assert "agents launch" in project_effects_reference
    assert "server start" in project_effects_reference
    assert "admin cleanup runtime" in project_effects_reference
    assert "houmao-specialist-mgr" in project_routing_reference
    assert "houmao-credential-mgr" in project_routing_reference
    assert "houmao-agent-definition" in project_routing_reference
    assert "houmao-agent-instance" in project_routing_reference
    assert "houmao-mailbox-mgr" in project_routing_reference
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
    assert "update specialist" in manage_specialist_skill
    assert "create profile" in manage_specialist_skill
    assert "list profiles" in manage_specialist_skill
    assert "get profile" in manage_specialist_skill
    assert "remove profile" in manage_specialist_skill
    assert "Explicit Auth Mode" in create_action
    assert "project easy profile create" in create_action
    assert "project easy specialist set --name <name>" in create_action
    assert "Do not remove and recreate an easy specialist" in create_action
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
    deprecated_fixture_root = "/".join(("tests", "fixtures", "agents"))
    assert deprecated_fixture_root not in create_action
    assert "project easy profile list" in list_action
    assert "Use the `houmao-mgr` launcher already chosen by the top-level skill." in list_action
    assert "<chosen houmao-mgr launcher>" in list_action
    assert "project easy profile get --name <name>" in get_action
    assert "project easy profile remove --name <name>" in remove_action
    assert "project easy instance launch --profile <profile>" in launch_action
    assert "project easy profile get --name <profile>" in launch_action
    assert "does not accept declarative mailbox fields such as `--mail-address`" in launch_action
    assert "`--name` seeds the managed-agent mailbox address and principal id" in launch_action
    assert (
        "private filesystem mailbox directory that the launch symlinks into the shared root"
        in launch_action
    )
    assert (
        "was preregistered manually already, launch-time safe registration can fail"
        in launch_action
    )
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
    assert "project credentials <tool> ..." in manage_credentials_skill
    assert "credentials <tool> ... --agent-def-dir <path>" in manage_credentials_skill
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
    assert (
        "Use the `houmao-mgr` launcher already chosen by the top-level skill."
        in credentials_get_action
    )
    assert "<chosen houmao-mgr launcher>" in credentials_get_action
    assert "project credentials <tool> get --name <name>" in credentials_get_action
    assert "credentials <tool> get --agent-def-dir <path> --name <name>" in credentials_get_action
    assert "Do not bypass `get`" in credentials_get_action
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
    assert (
        "Use the `houmao-mgr` launcher already chosen by the top-level skill."
        in definition_get_action
    )
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
    assert "authoring/formulate-loop-plan.md" in pairwise_loop_skill
    assert "operating/start.md" in pairwise_loop_skill
    assert "operating/status.md" in pairwise_loop_skill
    assert "operating/stop.md" in pairwise_loop_skill
    assert "prestart/prepare-run.md" not in pairwise_loop_skill
    assert (
        "Use this Houmao skill only when the user explicitly asks for "
        "`houmao-agent-loop-pairwise`." in pairwise_loop_skill
    )
    assert (
        "Do not auto-route generic pairwise loop planning or pairwise run-control "
        "requests here when the user did not explicitly ask for "
        "`houmao-agent-loop-pairwise`." in pairwise_loop_skill
    )
    assert (
        "Do not make the user agent the upstream driver of the execution loop."
        in pairwise_loop_skill
    )
    assert "operating an accepted run through `start`, `status`, and `stop`" in pairwise_loop_skill
    assert "Do not treat `status` polling as a keepalive signal" in pairwise_loop_skill
    assert "houmao-agent-inspect" not in pairwise_loop_skill
    assert "authoring/formulate-loop-plan.md" in pairwise_loop_v2_skill
    assert "prestart/prepare-run.md" in pairwise_loop_v2_skill
    assert "operating/start.md" in pairwise_loop_v2_skill
    assert (
        "Use this Houmao skill only when the user explicitly asks for "
        "`houmao-agent-loop-pairwise-v2`." in pairwise_loop_v2_skill
    )
    assert (
        "Do not auto-route generic pairwise loop planning or pairwise run-control "
        "requests here when the user did not explicitly ask for "
        "`houmao-agent-loop-pairwise-v2`." in pairwise_loop_v2_skill
    )
    assert (
        "The canonical operator-facing lifecycle actions are `plan`, `initialize`, "
        "`start`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill`."
        in pairwise_loop_v2_skill
    )
    assert (
        "The canonical observed states are `authoring`, `initializing`, `awaiting_ack`, "
        "`ready`, `running`, `paused`, `stopping`, `stopped`, and `dead`." in pairwise_loop_v2_skill
    )
    assert "houmao-mgr internals graph high" in pairwise_loop_v2_skill
    assert "houmao-agent-inspect" in pairwise_loop_v2_skill
    assert "default `precomputed_routing_packets` validates routing packets" in pairwise_loop_v2_skill
    assert "durable start-charter page" in pairwise_loop_v2_skill
    assert "houmao-memory-mgr" in pairwise_loop_v2_skill
    assert "ask for the output directory before drafting or revising files" in pairwise_loop_v2_skill
    assert "## Plan Output Directory" in pairwise_loop_v2_skill
    assert "<plan-output-dir>/" in pairwise_loop_v2_skill
    assert "Do not treat live `houmao-memo.md` or memo-linked `pages/` edits as native pairwise-v2 write surfaces" in pairwise_loop_v2_skill
    assert "memo page index" not in pairwise_loop_v2_prepare_run
    assert "pages/<relative-page>" in pairwise_loop_v2_prepare_run
    assert "path-discovery output" in pairwise_loop_v2_prepare_run
    assert "HOUMAO_PAIRWISE_V2_BEGIN" in pairwise_loop_v2_prepare_run
    assert "loop-runs/pairwise-v2/<run_id>/initialize.md" in pairwise_loop_v2_prepare_run
    assert "treat that as a `houmao-memory-mgr` task" in pairwise_loop_v2_prepare_run
    assert "route that work to `houmao-memory-mgr`" in pairwise_loop_v2_start
    assert (
        "Use this Houmao skill when a user-controlled agent needs to formulate or operate one generic loop graph run"
        in relay_loop_skill
    )
    assert "houmao-mgr internals graph high" in relay_loop_skill
    assert (
        "Do not allow free delegation or free forwarding unless the plan says so explicitly."
        in relay_loop_skill
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
    assert deprecated_fixture_root not in claude_reference

    assert "CODEX_HOME" in codex_reference
    assert "auth.json" in codex_reference
    assert "requires_openai_auth = false" in codex_reference
    assert 'wire_api = "responses"' in codex_reference
    assert deprecated_fixture_root not in codex_reference

    assert "GEMINI_CLI_HOME" in gemini_reference
    assert "oauth_creds.json" in gemini_reference
    assert "GOOGLE_APPLICATION_CREDENTIALS" in gemini_reference
    assert deprecated_fixture_root not in gemini_reference


def test_uninstall_system_skills_for_home_removes_current_dirs_symlinks_and_files(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    copied_skill_path = home_path / "skills/houmao-specialist-mgr/SKILL.md"
    symlink_source = tmp_path / "symlink-source"
    symlink_target = home_path / "skills/houmao-agent-email-comms"
    file_target = home_path / "skills/houmao-adv-usage-pattern"
    user_skill_path = home_path / "skills/custom-user-skill/SKILL.md"
    unknown_houmao_path = home_path / "skills/houmao-user-owned/SKILL.md"
    legacy_path = home_path / "skills/mailbox/houmao-agent-email-comms/SKILL.md"
    obsolete_state_path = _obsolete_system_skill_state_path(home_path)
    _write(copied_skill_path, "copied skill\n")
    symlink_source.mkdir(parents=True)
    symlink_target.parent.mkdir(parents=True, exist_ok=True)
    symlink_target.symlink_to(symlink_source)
    _write(file_target, "stale file skill\n")
    _write(user_skill_path, "custom user skill\n")
    _write(unknown_houmao_path, "not catalog owned\n")
    _write(legacy_path, "legacy family path\n")
    _write(obsolete_state_path, "{}\n")

    result = uninstall_system_skills_for_home(tool="codex", home_path=home_path)

    assert result.tool == "codex"
    assert result.home_path == home_path
    assert result.removed_skill_names == (
        "houmao-agent-email-comms",
        "houmao-adv-usage-pattern",
        "houmao-specialist-mgr",
    )
    assert result.removed_projected_relative_dirs == (
        "skills/houmao-agent-email-comms",
        "skills/houmao-adv-usage-pattern",
        "skills/houmao-specialist-mgr",
    )
    assert "houmao-process-emails-via-gateway" in result.absent_skill_names
    assert "skills/houmao-process-emails-via-gateway" in result.absent_projected_relative_dirs
    assert "houmao-agent-gateway" in result.absent_skill_names
    assert not (home_path / "skills/houmao-specialist-mgr").exists()
    assert not symlink_target.exists()
    assert not symlink_target.is_symlink()
    assert symlink_source.is_dir()
    assert not file_target.exists()
    assert (home_path / "skills").is_dir()
    assert user_skill_path.is_file()
    assert unknown_houmao_path.is_file()
    assert legacy_path.is_file()
    assert obsolete_state_path.is_file()


def test_uninstall_system_skills_for_home_does_not_create_missing_home(tmp_path: Path) -> None:
    home_path = (tmp_path / "missing-codex-home").resolve()
    catalog = load_system_skill_catalog()

    result = uninstall_system_skills_for_home(tool="codex", home_path=home_path)

    assert not home_path.exists()
    assert result.removed_skill_names == ()
    assert result.removed_projected_relative_dirs == ()
    assert result.absent_skill_names == catalog.skill_names
    assert result.absent_projected_relative_dirs == tuple(
        f"skills/{skill_name}" for skill_name in catalog.skill_names
    )


def test_uninstall_system_skills_for_home_targets_gemini_dot_gemini_root(
    tmp_path: Path,
) -> None:
    home_path = tmp_path.resolve()
    gemini_skill_path = home_path / ".gemini/skills/houmao-specialist-mgr/SKILL.md"
    upstream_alias_path = home_path / ".agents/skills/houmao-specialist-mgr/SKILL.md"
    _write(gemini_skill_path, "gemini skill\n")
    _write(upstream_alias_path, "upstream alias\n")

    result = uninstall_system_skills_for_home(tool="gemini", home_path=home_path)

    assert result.removed_skill_names == ("houmao-specialist-mgr",)
    assert result.removed_projected_relative_dirs == (".gemini/skills/houmao-specialist-mgr",)
    assert not (home_path / ".gemini/skills/houmao-specialist-mgr").exists()
    assert upstream_alias_path.is_file()


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
    specialist_mgr_path = home_path / "skills/houmao-specialist-mgr/SKILL.md"
    specialist_mgr_actions = home_path / "skills/houmao-specialist-mgr/actions"
    agent_inspect_path = home_path / "skills/houmao-agent-inspect/SKILL.md"
    agent_inspect_actions = home_path / "skills/houmao-agent-inspect/actions"
    mailbox_mgr_path = home_path / "skills/houmao-mailbox-mgr/SKILL.md"
    mailbox_mgr_actions = home_path / "skills/houmao-mailbox-mgr/actions"
    mailbox_mgr_references = home_path / "skills/houmao-mailbox-mgr/references"
    memory_mgr_path = home_path / "skills/houmao-memory-mgr/SKILL.md"
    agent_messaging_path = home_path / "skills/houmao-agent-messaging/SKILL.md"
    agent_messaging_actions = home_path / "skills/houmao-agent-messaging/actions"
    agent_messaging_references = home_path / "skills/houmao-agent-messaging/references"
    agent_gateway_path = home_path / "skills/houmao-agent-gateway/SKILL.md"
    agent_gateway_actions = home_path / "skills/houmao-agent-gateway/actions"
    agent_gateway_references = home_path / "skills/houmao-agent-gateway/references"
    utils_llm_wiki_path = home_path / "skills/houmao-utils-llm-wiki/SKILL.md"
    utils_workspace_mgr_path = home_path / "skills/houmao-utils-workspace-mgr/SKILL.md"
    advanced_usage_path = home_path / "skills/houmao-adv-usage-pattern/SKILL.md"
    advanced_usage_patterns = home_path / "skills/houmao-adv-usage-pattern/patterns"
    touring_path = home_path / "skills/houmao-touring/SKILL.md"
    touring_branches = home_path / "skills/houmao-touring/branches"
    touring_references = home_path / "skills/houmao-touring/references"
    stable_pairwise_loop_path = home_path / "skills/houmao-agent-loop-pairwise/SKILL.md"
    stable_pairwise_loop_authoring = home_path / "skills/houmao-agent-loop-pairwise/authoring"
    stable_pairwise_loop_operating = home_path / "skills/houmao-agent-loop-pairwise/operating"
    pairwise_loop_path = home_path / "skills/houmao-agent-loop-pairwise-v2/SKILL.md"
    pairwise_loop_authoring = home_path / "skills/houmao-agent-loop-pairwise-v2/authoring"
    pairwise_loop_prestart = home_path / "skills/houmao-agent-loop-pairwise-v2/prestart"
    pairwise_loop_operating = home_path / "skills/houmao-agent-loop-pairwise-v2/operating"
    pairwise_loop_references = home_path / "skills/houmao-agent-loop-pairwise-v2/references"
    pairwise_loop_templates = home_path / "skills/houmao-agent-loop-pairwise-v2/templates"
    relay_loop_path = home_path / "skills/houmao-agent-loop-generic/SKILL.md"
    relay_loop_authoring = home_path / "skills/houmao-agent-loop-generic/authoring"
    relay_loop_operating = home_path / "skills/houmao-agent-loop-generic/operating"
    relay_loop_references = home_path / "skills/houmao-agent-loop-generic/references"
    relay_loop_templates = home_path / "skills/houmao-agent-loop-generic/templates"

    assert result.selected_set_names == (SYSTEM_SKILL_SET_ALL,)
    assert result.projection_mode == "copy"
    assert result.resolved_skill_names == ALL_SYSTEM_SKILLS
    assert (home_path / "skills/houmao-credential-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-definition/SKILL.md").is_file()
    assert mailbox_mgr_path.is_file()
    assert memory_mgr_path.is_file()
    assert advanced_usage_path.is_file()
    assert touring_path.is_file()
    assert (home_path / "skills/houmao-project-mgr/SKILL.md").is_file()
    assert specialist_mgr_path.is_file()
    assert manage_agent_instance_path.is_file()
    assert agent_inspect_path.is_file()
    assert agent_messaging_path.is_file()
    assert agent_gateway_path.is_file()
    assert utils_llm_wiki_path.is_file()
    assert utils_workspace_mgr_path.is_file()
    assert stable_pairwise_loop_path.is_file()
    assert pairwise_loop_path.is_file()
    assert relay_loop_path.is_file()
    mailbox_mgr_skill = mailbox_mgr_path.read_text(encoding="utf-8")
    memory_mgr_skill = memory_mgr_path.read_text(encoding="utf-8")
    manage_agent_instance_skill = manage_agent_instance_path.read_text(encoding="utf-8")
    agent_inspect_skill = agent_inspect_path.read_text(encoding="utf-8")
    agent_messaging_skill = agent_messaging_path.read_text(encoding="utf-8")
    agent_gateway_skill = agent_gateway_path.read_text(encoding="utf-8")
    advanced_usage_skill = advanced_usage_path.read_text(encoding="utf-8")
    touring_skill = touring_path.read_text(encoding="utf-8")
    stable_pairwise_loop_skill = stable_pairwise_loop_path.read_text(encoding="utf-8")
    pairwise_loop_skill = pairwise_loop_path.read_text(encoding="utf-8")
    relay_loop_skill = relay_loop_path.read_text(encoding="utf-8")
    launch_action_path = manage_agent_instance_actions / "launch.md"
    specialist_launch_action_path = specialist_mgr_actions / "launch.md"
    join_action_path = manage_agent_instance_actions / "join.md"
    list_action_path = manage_agent_instance_actions / "list.md"
    stop_action_path = manage_agent_instance_actions / "stop.md"
    relaunch_action_path = manage_agent_instance_actions / "relaunch.md"
    cleanup_action_path = manage_agent_instance_actions / "cleanup.md"
    inspect_discover_action_path = agent_inspect_actions / "discover.md"
    inspect_screen_action_path = agent_inspect_actions / "screen.md"
    inspect_mailbox_action_path = agent_inspect_actions / "mailbox.md"
    inspect_logs_action_path = agent_inspect_actions / "logs.md"
    inspect_artifacts_action_path = agent_inspect_actions / "artifacts.md"
    launch_action = launch_action_path.read_text(encoding="utf-8")
    specialist_launch_action = specialist_launch_action_path.read_text(encoding="utf-8")
    relaunch_action = relaunch_action_path.read_text(encoding="utf-8")
    cleanup_action = cleanup_action_path.read_text(encoding="utf-8")
    inspect_discover_action = inspect_discover_action_path.read_text(encoding="utf-8")
    inspect_screen_action = inspect_screen_action_path.read_text(encoding="utf-8")
    inspect_mailbox_action = inspect_mailbox_action_path.read_text(encoding="utf-8")
    inspect_logs_action = inspect_logs_action_path.read_text(encoding="utf-8")
    inspect_artifacts_action = inspect_artifacts_action_path.read_text(encoding="utf-8")
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
    gateway_reminders_action_path = agent_gateway_actions / "reminders.md"
    gateway_mail_notifier_action_path = agent_gateway_actions / "mail-notifier.md"
    gateway_scope_reference_path = agent_gateway_references / "scope-and-routing.md"
    gateway_http_reference_path = agent_gateway_references / "http-surface.md"
    self_notification_pattern_path = advanced_usage_patterns / "self-notification.md"
    self_notification_reminders_path = (
        advanced_usage_patterns / "self-notification-via-reminders.md"
    )
    self_notification_mail_path = advanced_usage_patterns / "self-wakeup-via-self-mail.md"
    pairwise_edge_loop_pattern_path = (
        advanced_usage_patterns / "pairwise-edge-loop-via-gateway-and-mailbox.md"
    )
    relay_loop_pattern_path = advanced_usage_patterns / "relay-loop-via-gateway-and-mailbox.md"
    touring_orient_path = touring_branches / "orient.md"
    touring_setup_path = touring_branches / "setup-project-and-mailbox.md"
    touring_author_launch_path = touring_branches / "author-and-launch.md"
    touring_live_ops_path = touring_branches / "live-operations.md"
    touring_advanced_usage_path = touring_branches / "advanced-usage.md"
    touring_lifecycle_path = touring_branches / "lifecycle-follow-up.md"
    touring_question_style_path = touring_references / "question-style.md"
    stable_pairwise_loop_formulate_path = stable_pairwise_loop_authoring / "formulate-loop-plan.md"
    stable_pairwise_loop_start_path = stable_pairwise_loop_operating / "start.md"
    stable_pairwise_loop_status_path = stable_pairwise_loop_operating / "status.md"
    stable_pairwise_loop_stop_path = stable_pairwise_loop_operating / "stop.md"
    pairwise_loop_formulate_path = pairwise_loop_authoring / "formulate-loop-plan.md"
    pairwise_loop_revise_path = pairwise_loop_authoring / "revise-loop-plan.md"
    pairwise_loop_graph_path = pairwise_loop_authoring / "render-loop-graph.md"
    pairwise_loop_prepare_path = pairwise_loop_prestart / "prepare-run.md"
    pairwise_loop_start_path = pairwise_loop_operating / "start.md"
    pairwise_loop_peek_path = pairwise_loop_operating / "peek.md"
    pairwise_loop_ping_path = pairwise_loop_operating / "ping.md"
    pairwise_loop_pause_path = pairwise_loop_operating / "pause.md"
    pairwise_loop_resume_path = pairwise_loop_operating / "resume.md"
    pairwise_loop_stop_path = pairwise_loop_operating / "stop.md"
    pairwise_loop_hard_kill_path = pairwise_loop_operating / "hard-kill.md"
    pairwise_loop_charter_path = pairwise_loop_references / "run-charter.md"
    pairwise_loop_policy_path = pairwise_loop_references / "delegation-policy.md"
    pairwise_loop_stop_modes_path = pairwise_loop_references / "stop-modes.md"
    pairwise_loop_reporting_path = pairwise_loop_references / "reporting-contract.md"
    pairwise_loop_plan_structure_path = pairwise_loop_references / "plan-structure.md"
    pairwise_loop_single_template_path = pairwise_loop_templates / "single-file-plan.md"
    pairwise_loop_bundle_template_path = pairwise_loop_templates / "bundle-plan.md"
    relay_loop_formulate_path = relay_loop_authoring / "formulate-loop-plan.md"
    relay_loop_revise_path = relay_loop_authoring / "revise-loop-plan.md"
    relay_loop_graph_path = relay_loop_authoring / "render-loop-graph.md"
    relay_loop_start_path = relay_loop_operating / "start.md"
    relay_loop_status_path = relay_loop_operating / "status.md"
    relay_loop_stop_path = relay_loop_operating / "stop.md"
    relay_loop_charter_path = relay_loop_references / "run-charter.md"
    relay_loop_policy_path = relay_loop_references / "graph-policy.md"
    relay_loop_result_contract_path = relay_loop_references / "result-routing.md"
    relay_loop_stop_modes_path = relay_loop_references / "stop-modes.md"
    relay_loop_reporting_path = relay_loop_references / "reporting-contract.md"
    relay_loop_plan_structure_path = relay_loop_references / "plan-structure.md"
    relay_loop_single_template_path = relay_loop_templates / "single-file-plan.md"
    relay_loop_bundle_template_path = relay_loop_templates / "bundle-plan.md"
    mailbox_init_action_path = mailbox_mgr_actions / "init.md"
    mailbox_register_action_path = mailbox_mgr_actions / "register.md"
    mailbox_clear_messages_action_path = mailbox_mgr_actions / "clear-messages.md"
    mailbox_export_action_path = mailbox_mgr_actions / "export.md"
    mailbox_messages_get_action_path = mailbox_mgr_actions / "messages-get.md"
    mailbox_agent_binding_register_action_path = mailbox_mgr_actions / "agent-binding-register.md"
    mailbox_root_reference_path = mailbox_mgr_references / "root-selection.md"
    mailbox_mode_reference_path = mailbox_mgr_references / "mode-vocabulary.md"
    mailbox_structural_reference_path = mailbox_mgr_references / "structural-vs-actor-state.md"
    mailbox_stalwart_reference_path = mailbox_mgr_references / "stalwart-boundary.md"
    mailbox_register_action = mailbox_register_action_path.read_text(encoding="utf-8")
    assert "description: \"Use when the user's intent is to read or write" in memory_mgr_skill
    assert "Necessary trigger: `memo` is mentioned." in memory_mgr_skill
    assert "Sufficient trigger: the prompt or context says `houmao memo`" in memory_mgr_skill
    assert "prompt or recent context mentions `memo`" in memory_mgr_skill
    assert "says `houmao memo`" in memory_mgr_skill
    assert "says `agent memo`" in memory_mgr_skill
    assert "read or write a Houmao-managed agent's `houmao-memo.md` file" in memory_mgr_skill
    assert "explicit reference to `houmao-memo.md` is a very strong hint" in memory_mgr_skill
    assert "HOUMAO_AGENT_MEMO_FILE" in memory_mgr_skill
    assert "agents memory memo show|set|append" in memory_mgr_skill
    assert "agents memory tree|resolve|read|write|append|delete" in memory_mgr_skill
    assert "free-form Markdown" in memory_mgr_skill
    assert "pages/" in memory_mgr_skill
    mailbox_export_action = mailbox_export_action_path.read_text(encoding="utf-8")
    touring_setup = touring_setup_path.read_text(encoding="utf-8")
    discover_action = discover_action_path.read_text(encoding="utf-8")
    interrupt_action = interrupt_action_path.read_text(encoding="utf-8")
    reset_context_action = reset_context_action_path.read_text(encoding="utf-8")
    mail_action = mail_action_path.read_text(encoding="utf-8")
    intent_matrix_reference = intent_matrix_reference_path.read_text(encoding="utf-8")
    managed_agent_http_reference = managed_agent_http_reference_path.read_text(encoding="utf-8")
    gateway_discover_action = gateway_discover_action_path.read_text(encoding="utf-8")
    gateway_lifecycle_action = gateway_lifecycle_action_path.read_text(encoding="utf-8")
    gateway_reminders_action = gateway_reminders_action_path.read_text(encoding="utf-8")
    gateway_mail_notifier_action = gateway_mail_notifier_action_path.read_text(encoding="utf-8")
    gateway_http_reference = gateway_http_reference_path.read_text(encoding="utf-8")
    self_notification_pattern = self_notification_pattern_path.read_text(encoding="utf-8")
    self_notification_reminders = self_notification_reminders_path.read_text(encoding="utf-8")
    self_notification_mail = self_notification_mail_path.read_text(encoding="utf-8")
    pairwise_edge_loop_pattern = pairwise_edge_loop_pattern_path.read_text(encoding="utf-8")
    relay_loop_pattern = relay_loop_pattern_path.read_text(encoding="utf-8")
    touring_author_launch = touring_author_launch_path.read_text(encoding="utf-8")
    touring_advanced_usage = touring_advanced_usage_path.read_text(encoding="utf-8")
    touring_question_style = touring_question_style_path.read_text(encoding="utf-8")
    stable_pairwise_loop_start = stable_pairwise_loop_start_path.read_text(encoding="utf-8")
    stable_pairwise_loop_status = stable_pairwise_loop_status_path.read_text(encoding="utf-8")
    stable_pairwise_loop_stop = stable_pairwise_loop_stop_path.read_text(encoding="utf-8")
    pairwise_loop_formulate = pairwise_loop_formulate_path.read_text(encoding="utf-8")
    pairwise_loop_revise = pairwise_loop_revise_path.read_text(encoding="utf-8")
    pairwise_loop_graph = pairwise_loop_graph_path.read_text(encoding="utf-8")
    pairwise_loop_prepare = pairwise_loop_prepare_path.read_text(encoding="utf-8")
    pairwise_loop_start = pairwise_loop_start_path.read_text(encoding="utf-8")
    pairwise_loop_peek = pairwise_loop_peek_path.read_text(encoding="utf-8")
    pairwise_loop_ping = pairwise_loop_ping_path.read_text(encoding="utf-8")
    pairwise_loop_pause = pairwise_loop_pause_path.read_text(encoding="utf-8")
    pairwise_loop_resume = pairwise_loop_resume_path.read_text(encoding="utf-8")
    pairwise_loop_stop = pairwise_loop_stop_path.read_text(encoding="utf-8")
    pairwise_loop_hard_kill = pairwise_loop_hard_kill_path.read_text(encoding="utf-8")
    pairwise_loop_charter = pairwise_loop_charter_path.read_text(encoding="utf-8")
    pairwise_loop_policy = pairwise_loop_policy_path.read_text(encoding="utf-8")
    pairwise_loop_reporting = pairwise_loop_reporting_path.read_text(encoding="utf-8")
    pairwise_loop_plan_structure = pairwise_loop_plan_structure_path.read_text(encoding="utf-8")
    pairwise_loop_single_template = pairwise_loop_single_template_path.read_text(encoding="utf-8")
    pairwise_loop_bundle_template = pairwise_loop_bundle_template_path.read_text(encoding="utf-8")
    relay_loop_formulate = relay_loop_formulate_path.read_text(encoding="utf-8")
    relay_loop_revise = relay_loop_revise_path.read_text(encoding="utf-8")
    relay_loop_graph = relay_loop_graph_path.read_text(encoding="utf-8")
    relay_loop_start = relay_loop_start_path.read_text(encoding="utf-8")
    relay_loop_status = relay_loop_status_path.read_text(encoding="utf-8")
    relay_loop_stop = relay_loop_stop_path.read_text(encoding="utf-8")
    relay_loop_policy = relay_loop_policy_path.read_text(encoding="utf-8")
    relay_loop_result_contract = relay_loop_result_contract_path.read_text(encoding="utf-8")
    relay_loop_plan_structure = relay_loop_plan_structure_path.read_text(encoding="utf-8")
    relay_loop_single_template = relay_loop_single_template_path.read_text(encoding="utf-8")
    relay_loop_bundle_template = relay_loop_bundle_template_path.read_text(encoding="utf-8")

    assert "actions/init.md" in mailbox_mgr_skill
    assert "actions/register.md" in mailbox_mgr_skill
    assert "actions/clear-messages.md" in mailbox_mgr_skill
    assert "actions/export.md" in mailbox_mgr_skill
    assert "actions/agent-binding-register.md" in mailbox_mgr_skill
    assert "references/root-selection.md" in mailbox_mgr_skill
    assert "command -v houmao-mgr" in mailbox_mgr_skill
    assert "uv tool run --from houmao houmao-mgr" in mailbox_mgr_skill
    assert "houmao-mgr mailbox ..." in mailbox_mgr_skill
    assert "houmao-mgr project mailbox ..." in mailbox_mgr_skill
    assert "houmao-mgr agents mailbox ..." in mailbox_mgr_skill
    assert "manual mailbox-account administration" in mailbox_mgr_skill
    assert (
        "mailbox registration may be owned by the later `project easy instance launch` step"
        in mailbox_mgr_skill
    )
    assert "route to `actions/agent-binding-register.md` instead" in mailbox_mgr_skill
    assert mailbox_init_action_path.is_file()
    assert mailbox_register_action_path.is_file()
    assert mailbox_clear_messages_action_path.is_file()
    assert mailbox_export_action_path.is_file()
    assert mailbox_messages_get_action_path.is_file()
    assert mailbox_agent_binding_register_action_path.is_file()
    assert mailbox_root_reference_path.is_file()
    assert mailbox_mode_reference_path.is_file()
    assert mailbox_structural_reference_path.is_file()
    assert mailbox_stalwart_reference_path.is_file()
    assert (
        "Use the `houmao-mgr` launcher already chosen by the top-level skill."
        in mailbox_init_action_path.read_text(encoding="utf-8")
    )
    assert "<chosen houmao-mgr launcher>" in mailbox_init_action_path.read_text(encoding="utf-8")
    assert "manually administered filesystem mailbox registration" in mailbox_register_action
    assert "for a new specialist-backed easy instance" in mailbox_register_action
    assert (
        "may own mailbox registration instead of preregistering that address here"
        in mailbox_register_action
    )
    assert "mailbox export" in mailbox_export_action
    assert "--symlink-mode materialize|preserve" in mailbox_export_action
    assert "Do not recommend raw recursive mailbox-root copying" in mailbox_export_action
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
    assert specialist_launch_action_path.is_file()
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
    assert "foreground-first" in launch_action
    assert "Do not add one-shot background gateway overrides unless" in launch_action
    assert "Do not add background gateway flags unless" in launch_action
    assert "--mail-transport" in launch_action
    assert "Launch-time gateway auto-attach is enabled by default" in specialist_launch_action
    assert "Default launch-time gateway auto-attach uses foreground" in specialist_launch_action
    assert "A headless managed-agent launch, including a required Gemini headless launch" in (
        specialist_launch_action
    )
    assert "Do not add `--gateway-background` unless the user explicitly requested" in (
        specialist_launch_action
    )
    assert "agents relaunch --agent-name" in relaunch_action
    assert "current-session relaunch" in relaunch_action
    assert "Do not reinterpret a relaunch request as `agents launch`" in relaunch_action
    assert "agents cleanup session" in cleanup_action
    assert "agents cleanup logs" in cleanup_action
    assert "Prefer `--manifest-path` or `--session-root` from recent stop output" in cleanup_action
    assert "bounded runtime-root fallback" in cleanup_action
    assert "stopped-session tombstones" in cleanup_action
    assert "admin cleanup runtime" in cleanup_action
    assert "actions/discover.md" in agent_inspect_skill
    assert "actions/screen.md" in agent_inspect_skill
    assert "actions/mailbox.md" in agent_inspect_skill
    assert "actions/logs.md" in agent_inspect_skill
    assert "actions/artifacts.md" in agent_inspect_skill
    assert "houmao-mgr agents list" in agent_inspect_skill
    assert "houmao-mgr agents turn status|events|stdout|stderr" in agent_inspect_skill
    assert "command -v houmao-mgr" in agent_inspect_skill
    assert "uv tool run --from houmao houmao-mgr" in agent_inspect_skill
    assert inspect_discover_action_path.is_file()
    assert inspect_screen_action_path.is_file()
    assert inspect_mailbox_action_path.is_file()
    assert inspect_logs_action_path.is_file()
    assert inspect_artifacts_action_path.is_file()
    assert "GET /houmao/agents" in inspect_discover_action
    assert "GET /houmao/agents/{agent_ref}/state/detail" in inspect_discover_action
    assert "agents gateway tui state --agent-name <name>" in inspect_screen_action
    assert "tmux capture-pane -p -e -S - <tmux-target>" in inspect_screen_action
    assert "agents mail resolve-live --agent-name <name>" in inspect_mailbox_action
    assert "houmao-mailbox-mgr" in inspect_mailbox_action
    assert "agents turn events --agent-name <name> <turn-id>" in inspect_logs_action
    assert "gateway/events.jsonl" in inspect_logs_action
    assert "<session-root>/manifest.json" in inspect_artifacts_action
    assert "gateway/state.json" in inspect_artifacts_action
    assert "actions/discover.md" in agent_messaging_skill
    assert "actions/prompt.md" in agent_messaging_skill
    assert "actions/interrupt.md" in agent_messaging_skill
    assert "actions/gateway-queue.md" in agent_messaging_skill
    assert "actions/send-keys.md" in agent_messaging_skill
    assert "actions/mail.md" in agent_messaging_skill
    assert "actions/reset-context.md" in agent_messaging_skill
    assert "houmao-mgr agents prompt" in agent_messaging_skill
    assert "houmao-agent-inspect" in agent_messaging_skill
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
    assert "best-effort `Escape` delivery" in interrupt_action
    assert "tracked TUI state can lag the live visible surface" in interrupt_action
    assert "no headless work is active" in interrupt_action
    assert (
        "Do not redirect ordinary TUI interrupt work to `agents gateway send-keys`"
        in interrupt_action
    )
    assert "best-effort `Escape`" in intent_matrix_reference
    assert "may no-op when idle" in intent_matrix_reference
    assert "tracked TUI state currently looks idle" in managed_agent_http_reference
    assert (
        "Do not switch to raw `send-keys` merely to get the normal TUI interrupt behavior."
        in managed_agent_http_reference
    )
    assert "actions/lifecycle.md" in agent_gateway_skill
    assert "actions/discover.md" in agent_gateway_skill
    assert "actions/gateway-services.md" in agent_gateway_skill
    assert "actions/reminders.md" in agent_gateway_skill
    assert "actions/mail-notifier.md" in agent_gateway_skill
    assert "houmao-agent-inspect" in agent_gateway_skill
    assert "patterns/self-notification.md" in advanced_usage_skill
    assert "patterns/pairwise-edge-loop-via-gateway-and-mailbox.md" in advanced_usage_skill
    assert "patterns/relay-loop-via-gateway-and-mailbox.md" in advanced_usage_skill
    assert "manual guided tour skill" in touring_skill
    assert (
        "Use this Houmao skill only when the user explicitly asks for `houmao-touring`"
        in touring_skill
    )
    assert "branches/orient.md" in touring_skill
    assert "branches/advanced-usage.md" in touring_skill
    assert "branches/lifecycle-follow-up.md" in touring_skill
    assert "references/question-style.md" in touring_skill
    assert "houmao-project-mgr" in touring_skill
    assert "houmao-agent-loop-pairwise" in touring_skill
    assert "houmao-agent-loop-pairwise-v2" in touring_skill
    assert "houmao-agent-instance" in touring_skill
    assert "## Welcome Message" in touring_skill
    assert "framework and CLI toolkit for orchestrating teams" in touring_skill
    assert "loosely coupled CLI-based AI agents" in touring_skill
    assert "real CLI process with its own disk state, memory, and native TUI" in touring_skill
    assert "mailbox messaging, per-agent gateways, and loop plans" in touring_skill
    assert "A typical first setup path is:" in touring_skill
    assert "initialize the mailbox root" in touring_skill
    assert "Create a specialist: customize its system prompt" in touring_skill
    assert "Create an optional launch profile" in touring_skill
    assert "Set up and register the agent mail account" in touring_skill
    assert "default tour posture is a visible TUI managed agent" in touring_skill
    assert "gateway mail-notifier polling every 5 seconds" in touring_skill
    assert "foreground-first gateway posture" in touring_author_launch
    assert "not as detached background gateway execution" in touring_author_launch
    assert "gateway_tmux_window_index" in touring_author_launch
    assert "stable pairwise loop" in touring_advanced_usage
    assert "enriched pairwise loop" in touring_advanced_usage
    assert "plan`, `start`, `status`, and `stop" in touring_advanced_usage
    assert "plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `stop`" in (
        touring_advanced_usage
    )
    assert "ask the user to select or explicitly invoke the desired pairwise skill" in (
        touring_advanced_usage
    )
    assert "elemental immediate driver-worker edge protocol guidance belongs to" in (
        touring_advanced_usage
    )
    assert "houmao-adv-usage-pattern" in touring_advanced_usage
    assert "distinguish mailbox-root bootstrap from mailbox-account creation" in touring_setup
    assert "launch-time mailbox bootstrap can own those per-agent addresses later" in touring_setup
    assert "initialize the shared mailbox root now" in touring_question_style
    assert "created by the later launch step" in touring_question_style
    assert "authoring/formulate-loop-plan.md" in stable_pairwise_loop_skill
    assert "operating/start.md" in stable_pairwise_loop_skill
    assert "operating/status.md" in stable_pairwise_loop_skill
    assert "operating/stop.md" in stable_pairwise_loop_skill
    assert "prestart/prepare-run.md" not in stable_pairwise_loop_skill
    assert "operating/hard-kill.md" not in stable_pairwise_loop_skill
    assert (
        "Use this Houmao skill only when the user explicitly asks for "
        "`houmao-agent-loop-pairwise`." in stable_pairwise_loop_skill
    )
    assert "authoring/formulate-loop-plan.md" in pairwise_loop_skill
    assert "authoring/render-loop-graph.md" in pairwise_loop_skill
    assert "prestart/prepare-run.md" in pairwise_loop_skill
    assert "operating/start.md" in pairwise_loop_skill
    assert "operating/peek.md" in pairwise_loop_skill
    assert "operating/ping.md" in pairwise_loop_skill
    assert "operating/pause.md" in pairwise_loop_skill
    assert "operating/resume.md" in pairwise_loop_skill
    assert "operating/stop.md" in pairwise_loop_skill
    assert "operating/hard-kill.md" in pairwise_loop_skill
    assert "references/run-charter.md" in pairwise_loop_skill
    assert "templates/single-file-plan.md" in pairwise_loop_skill
    assert (
        "Use this Houmao skill only when the user explicitly asks for "
        "`houmao-agent-loop-pairwise-v2`." in pairwise_loop_skill
    )
    assert (
        "Do not auto-route generic pairwise loop planning or pairwise run-control "
        "requests here when the user did not explicitly ask for "
        "`houmao-agent-loop-pairwise-v2`." in pairwise_loop_skill
    )
    assert "houmao-mgr internals graph high" in pairwise_loop_skill
    assert "authoring/formulate-loop-plan.md" in relay_loop_skill
    assert "authoring/render-loop-graph.md" in relay_loop_skill
    assert "operating/start.md" in relay_loop_skill
    assert "operating/stop.md" in relay_loop_skill
    assert "references/run-charter.md" in relay_loop_skill
    assert "templates/single-file-plan.md" in relay_loop_skill
    assert "houmao-mgr internals graph high" in relay_loop_skill
    assert "HOUMAO_MANIFEST_PATH" in agent_gateway_skill
    assert "HOUMAO_GATEWAY_ATTACH_PATH" in agent_gateway_skill
    assert "houmao-mgr agents gateway attach|detach|status" in agent_gateway_skill
    assert "houmao-mgr agents gateway reminders list|get|create|set|remove" in agent_gateway_skill
    assert "command -v houmao-mgr" in agent_gateway_skill
    assert "uv tool run --from houmao houmao-mgr" in agent_gateway_skill
    assert gateway_lifecycle_action_path.is_file()
    assert gateway_discover_action_path.is_file()
    assert gateway_services_action_path.is_file()
    assert gateway_reminders_action_path.is_file()
    assert gateway_mail_notifier_action_path.is_file()
    assert "`any_inbox`: default" in gateway_mail_notifier_action
    assert "`unread_only`: notify only while unread inbox mail remains unarchived" in (
        gateway_mail_notifier_action
    )
    assert "Processed mail should be archived" in gateway_mail_notifier_action
    assert gateway_scope_reference_path.is_file()
    assert gateway_http_reference_path.is_file()
    assert self_notification_pattern_path.is_file()
    assert self_notification_reminders_path.is_file()
    assert self_notification_mail_path.is_file()
    assert pairwise_edge_loop_pattern_path.is_file()
    assert relay_loop_pattern_path.is_file()
    assert touring_orient_path.is_file()
    assert touring_setup_path.is_file()
    assert touring_author_launch_path.is_file()
    assert touring_live_ops_path.is_file()
    assert touring_advanced_usage_path.is_file()
    assert touring_lifecycle_path.is_file()
    assert touring_question_style_path.is_file()
    assert stable_pairwise_loop_formulate_path.is_file()
    assert stable_pairwise_loop_start_path.is_file()
    assert stable_pairwise_loop_status_path.is_file()
    assert stable_pairwise_loop_stop_path.is_file()
    assert not (home_path / "skills/houmao-agent-loop-pairwise/prestart").exists()
    assert not (stable_pairwise_loop_operating / "peek.md").exists()
    assert pairwise_loop_formulate_path.is_file()
    assert pairwise_loop_revise_path.is_file()
    assert pairwise_loop_graph_path.is_file()
    assert pairwise_loop_prepare_path.is_file()
    assert pairwise_loop_start_path.is_file()
    assert pairwise_loop_peek_path.is_file()
    assert pairwise_loop_ping_path.is_file()
    assert pairwise_loop_pause_path.is_file()
    assert pairwise_loop_resume_path.is_file()
    assert pairwise_loop_stop_path.is_file()
    assert pairwise_loop_hard_kill_path.is_file()
    assert not (pairwise_loop_operating / "status.md").exists()
    assert pairwise_loop_charter_path.is_file()
    assert pairwise_loop_policy_path.is_file()
    assert pairwise_loop_stop_modes_path.is_file()
    assert pairwise_loop_reporting_path.is_file()
    assert pairwise_loop_plan_structure_path.is_file()
    assert pairwise_loop_single_template_path.is_file()
    assert pairwise_loop_bundle_template_path.is_file()
    assert relay_loop_formulate_path.is_file()
    assert relay_loop_revise_path.is_file()
    assert relay_loop_graph_path.is_file()
    assert relay_loop_start_path.is_file()
    assert relay_loop_status_path.is_file()
    assert relay_loop_stop_path.is_file()
    assert relay_loop_charter_path.is_file()
    assert relay_loop_policy_path.is_file()
    assert relay_loop_result_contract_path.is_file()
    assert relay_loop_stop_modes_path.is_file()
    assert relay_loop_reporting_path.is_file()
    assert relay_loop_plan_structure_path.is_file()
    assert relay_loop_single_template_path.is_file()
    assert relay_loop_bundle_template_path.is_file()
    assert "HOUMAO_AGENT_ID" in gateway_discover_action
    assert "foreground same-session auxiliary-window attach is the default" in (
        gateway_lifecycle_action
    )
    assert "agents gateway attach --background --agent-name <name>" in (gateway_lifecycle_action)
    assert "Do not choose `--background` by default" in gateway_lifecycle_action
    assert "gateway_tmux_window_index" in gateway_lifecycle_action
    assert (
        "Use the `houmao-mgr` launcher already chosen by the top-level skill."
        in gateway_discover_action
    )
    assert "<chosen houmao-mgr launcher>" in gateway_discover_action
    assert "agents mail resolve-live" in gateway_discover_action
    assert "/v1/reminders" in gateway_reminders_action
    assert "send_keys" in gateway_reminders_action
    assert "ensure_enter" in gateway_reminders_action
    assert "agents gateway reminders create" in gateway_reminders_action
    assert "--before-all" in gateway_reminders_action
    assert "--after-all" in gateway_reminders_action
    assert "paused effective reminder still blocks" in gateway_reminders_action
    assert "process-local in-memory state" in gateway_reminders_action
    assert "/houmao/agents/{agent_ref}/gateway/reminders" in gateway_http_reference
    assert "/v1/reminders" in self_notification_pattern
    assert (
        "If you are not sure and durable recovery is not explicitly required, prefer live gateway reminders."
        in self_notification_pattern
    )
    assert "ignore other new mail and work on this first" in self_notification_pattern
    assert "one reminder per major work chunk" in self_notification_pattern
    assert (
        "work is high-priority and should stay focused ahead of unrelated new incoming mail"
        in self_notification_reminders
    )
    assert "does not survive gateway shutdown or restart" in self_notification_reminders
    assert "must survive gateway shutdown or restart" in self_notification_mail
    assert "later rounds may reprioritize against external incoming mail" in self_notification_mail
    assert "foreground-first and treats background gateway execution as explicit user intent" in (
        self_notification_mail
    )
    assert "Do not imply that background gateway execution is the default setup" in (
        self_notification_mail
    )
    assert "exactly one driver sends one worker request" in advanced_usage_skill
    assert "ownership should keep moving forward along that lane" in advanced_usage_skill
    assert "`houmao-agent-loop-generic` for composed topology" in advanced_usage_skill
    assert "edge_loop_id" in pairwise_edge_loop_pattern
    assert "Use a dedicated pairwise loop-planning skill for recursive child edge-loops" in (
        pairwise_edge_loop_pattern
    )
    assert "ask the user for that value" in pairwise_edge_loop_pattern
    assert "one repeating supervisor reminder as the live loop clock" in pairwise_edge_loop_pattern
    assert "Subject: [edge-result] edge_loop=<edge_loop_id>" in pairwise_edge_loop_pattern
    assert "operator-designated work artifact path" in relay_loop_pattern
    assert "Do not use Houmao managed memory pages as the default home" in relay_loop_pattern
    assert "ask the user for that parameter" in relay_loop_pattern
    assert "one repeating supervisor reminder as the live loop clock" in relay_loop_pattern
    assert "Subject: [relay-result] loop=<loop_id> result=<result_id>" in relay_loop_pattern
    assert (
        "After the master accepts the run, the master owns liveness" in stable_pairwise_loop_start
    )
    assert "The user agent may poll `status`, but status polling does not keep the run alive." in (
        stable_pairwise_loop_start
    )
    assert "Status is observational and does not keep the run alive." in stable_pairwise_loop_status
    assert "`interrupt-first` is the default stop posture for this skill." in (
        stable_pairwise_loop_stop
    )
    assert (
        "No free delegation is allowed unless the plan says so explicitly."
        in pairwise_loop_formulate
    )
    assert "Resolve the plan output directory before drafting files" in pairwise_loop_formulate
    assert "canonical entrypoint path: `<plan-output-dir>/plan.md`" in pairwise_loop_formulate
    assert "Write the generated plan into the selected output directory" in pairwise_loop_formulate
    assert "first-class structural preflight before authoring packets" in pairwise_loop_formulate
    assert "houmao-mgr internals graph high analyze --input <graph.json>" in (
        pairwise_loop_formulate
    )
    assert (
        "houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants"
        in pairwise_loop_formulate
    )
    assert "houmao-mgr internals graph high packet-expectations" in pairwise_loop_formulate
    assert "after `analyze` and any needed `slice` calls" in pairwise_loop_formulate
    assert "houmao-mgr internals graph high packet-expectations" in pairwise_loop_revise
    assert "Preserve the current output directory unless the user explicitly asks to move the plan." in (
        pairwise_loop_revise
    )
    assert "Write the revised plan back under the selected output directory" in pairwise_loop_revise
    assert "by running graph analysis after `start`" in pairwise_loop_revise
    assert "```mermaid" in pairwise_loop_graph
    assert "The final plan must include one Mermaid fenced code block." in pairwise_loop_graph
    assert "HOUMAO-operator@houmao.localhost" in pairwise_loop_prepare
    assert "houmao-mgr internals graph high validate-packets" in pairwise_loop_prepare
    assert (
        "explicit deterministic structural check before entering `ready`" in pairwise_loop_prepare
    )
    assert "manually verify visible topology, descendant relationships, packet inventory" in (
        pairwise_loop_prepare
    )
    assert "reply_policy=operator_mailbox" in pairwise_loop_prepare
    assert "canonical `initialize` action" in pairwise_loop_prepare
    assert "loop-runs/pairwise-v2/<run_id>/initialize.md" in pairwise_loop_prepare
    assert "exact begin sentinel and one exact end sentinel keyed by `run_id` and slot" in (
        pairwise_loop_prepare
    )
    assert "Preparation-mail targets are delegating or non-leaf participants by default" in (
        pairwise_loop_prepare
    )
    assert "point the participant at its durable initialize page" in pairwise_loop_prepare
    assert "Do not treat standalone participant preparation mail as the default initialize path." in (
        pairwise_loop_prepare
    )
    assert (
        "Do not guess packet coverage, initialize page paths, or explicit preparation-wave targets when the topology is unclear"
        in (pairwise_loop_prepare)
    )
    assert "`awaiting_ack`" in pairwise_loop_prepare
    assert "`ready`" in pairwise_loop_prepare
    assert "After the master accepts the run, the master owns liveness" in pairwise_loop_start
    assert "houmao-agent-inspect" in pairwise_loop_start
    assert "`<plan-output-dir>/plan.md` for the single-file form" in pairwise_loop_start
    assert "`initialize` remains separate from `start`." in pairwise_loop_start
    assert "durable initialize pages and exact-sentinel memo reference blocks have been written or refreshed" in (
        pairwise_loop_start
    )
    assert "required replies from targeted preparation recipients have arrived" in (
        pairwise_loop_start
    )
    assert "compact start trigger" in pairwise_loop_start
    assert "loop-runs/pairwise-v2/<run_id>/start-charter.md" in pairwise_loop_start
    assert "Do not treat acknowledgement replies as readiness blockers" in pairwise_loop_start
    assert (
        "Later `peek` remains unintrusive, read-only, and does not keep the run alive."
        in pairwise_loop_start
    )
    assert "Do not ask the master or intermediate drivers to run graph analysis" in (
        pairwise_loop_start
    )
    assert "Use this page when the user wants canonical read-only inspection" in pairwise_loop_peek
    assert "`peek master`, `peek all`, or `peek <agent-name>`" in pairwise_loop_peek
    assert "`peek` is observational." in pairwise_loop_peek
    assert (
        "Use this page when the user wants to actively ask one selected pairwise-loop participant"
        in pairwise_loop_ping
    )
    assert "`ping <agent-name>` is active messaging." in pairwise_loop_ping
    assert "suspend the run's wakeup mechanisms" in pairwise_loop_pause
    assert "Disabling mail notifier alone is not sufficient" in pairwise_loop_pause
    assert "`resume` is not a synonym for `start`." in pairwise_loop_resume
    assert "`interrupt-first` is the default stop posture for this skill." in pairwise_loop_stop
    assert "`broadcast-stop`" in pairwise_loop_stop
    assert "participant-wide direct intervention" in pairwise_loop_hard_kill
    assert "disable gateway mail-notifier polling" in pairwise_loop_hard_kill
    assert "archive every open `message_ref`" in pairwise_loop_hard_kill
    assert "Do not collapse `hard-kill` into canonical `stop`." in pairwise_loop_hard_kill
    assert "`peek master <run_id>`" in pairwise_loop_charter
    assert "`pause <run_id>`" in pairwise_loop_charter
    assert "path: <canonical plan path such as <plan-output-dir>/plan.md>" in pairwise_loop_charter
    assert "prestart strategy: <precomputed_routing_packets | operator_preparation_wave>" in (
        pairwise_loop_charter
    )
    assert "root routing packet: <inline packet text or exact packet reference>" in (
        pairwise_loop_charter
    )
    assert "Read the durable start-charter page at `pages/<relative-page>`." in (
        pairwise_loop_charter
    )
    assert "delegate_freely_within_named_set" in pairwise_loop_policy
    assert "## Canonical Observed States" in pairwise_loop_reporting
    assert "## Hard-Kill Summary Fields" in pairwise_loop_reporting
    assert (
        "Treat these state names as observations, not operator actions." in pairwise_loop_reporting
    )
    assert "## Lifecycle Vocabulary" in pairwise_loop_plan_structure
    assert "## Output Directory Contract" in pairwise_loop_plan_structure
    assert "Every authored pairwise-v2 plan should live under one user-chosen output directory." in (
        pairwise_loop_plan_structure
    )
    assert "`<plan-output-dir>/plan.md`" in pairwise_loop_plan_structure
    assert "## Durable Initialize Material" in pairwise_loop_plan_structure
    assert "Every plan using pairwise-v2 durable initialize pages should record" in (
        pairwise_loop_plan_structure
    )
    assert "Do not describe explicit `operator_preparation_wave` as the default prestart strategy." in (
        pairwise_loop_plan_structure
    )
    assert "NetworkX node-link graph artifact location" in pairwise_loop_plan_structure
    assert "packet JSON document location" in pairwise_loop_plan_structure
    assert "optional `houmao-mgr internals graph high slice" in pairwise_loop_plan_structure
    assert "preparation-mail target policy and delivery procedure" in (
        pairwise_loop_plan_structure
    )
    assert "`hard-kill`" in pairwise_loop_plan_structure
    assert (
        "Treat `hard-kill` as a separate operator action"
        in pairwise_loop_stop_modes_path.read_text(encoding="utf-8")
    )
    assert "# Prestart Procedure" in pairwise_loop_single_template
    assert "Write this template as `<plan-output-dir>/plan.md`." in pairwise_loop_single_template
    assert "## Expected Output Directory" in pairwise_loop_single_template
    assert "prestart_strategy: <precomputed_routing_packets | operator_preparation_wave>" in (
        pairwise_loop_single_template
    )
    assert "graph-tool preflight: <analyze, optional slice, and packet-expectations results" in (
        pairwise_loop_single_template
    )
    assert "routing packet validation: <validate-packets result when graph and packet JSON" in (
        pairwise_loop_single_template
    )
    assert "Initialize<br/>validate packets<br/>write durable pages" in pairwise_loop_single_template
    assert "# Routing Packets" in pairwise_loop_single_template
    assert "`stop`, `hard-kill`" in pairwise_loop_single_template
    assert "The generated single-file output directory should contain only `plan.md`." in (
        pairwise_loop_single_template
    )
    assert "`stop`, `hard-kill`" in pairwise_loop_bundle_template
    assert "Ask for the output directory if it is not already known" in pairwise_loop_bundle_template
    assert "<plan-output-dir>/" in pairwise_loop_bundle_template
    assert "selected `prestart_strategy`: default `precomputed_routing_packets`" in (
        pairwise_loop_bundle_template
    )
    assert "graph artifact and packet JSON artifact locations when available" in (
        pairwise_loop_bundle_template
    )
    assert "validation fallback when graph or packet JSON artifacts are unavailable" in (
        pairwise_loop_bundle_template
    )
    assert "# Lifecycle Vocabulary" in pairwise_loop_single_template
    assert "# Mermaid Control Graph" in pairwise_loop_single_template
    assert "prestart.md" in pairwise_loop_bundle_template
    assert "# Lifecycle Vocabulary" in pairwise_loop_bundle_template
    assert "agents/<participant>.md" in pairwise_loop_bundle_template
    assert "scripts/README.md" in pairwise_loop_bundle_template
    assert (
        "No free delegation, free forwarding, or hidden dependency is allowed unless the plan says so explicitly."
        in relay_loop_formulate
    )
    assert "first-class structural preflight" in relay_loop_formulate
    assert "houmao-mgr internals graph high analyze" in relay_loop_formulate
    assert "houmao-mgr internals graph high slice" in relay_loop_formulate
    assert (
        "do not use `graph low` primitives for normal typed loop planning" in relay_loop_formulate
    )
    assert "houmao-mgr internals graph high analyze" in relay_loop_revise
    assert "houmao-mgr internals graph high slice" in relay_loop_revise
    assert "Do not use `graph low` primitives for normal typed loop planning" in relay_loop_revise
    assert "```mermaid" in relay_loop_graph
    assert "The final plan must include one Mermaid fenced code block." in relay_loop_graph
    assert "houmao-mgr internals graph high render-mermaid" in relay_loop_graph
    assert "Do not treat graph-tool Mermaid output as final" in relay_loop_graph
    assert "After the root owner accepts the run, the root owner owns liveness" in relay_loop_start
    assert "Status is observational and does not keep the run alive." in relay_loop_status
    assert "`interrupt-first` is the default stop posture for this skill." in relay_loop_stop
    assert "forward_freely_within_named_set" in relay_loop_policy
    assert (
        "The designated loop egress returns the component final result to the relay origin."
        in relay_loop_result_contract
    )
    assert "## Graph Artifact Fields" in relay_loop_plan_structure
    assert "semantic review notes confirming graph policy" in relay_loop_plan_structure
    assert "# Mermaid Generic Loop Graph" in relay_loop_single_template
    assert "# Graph Artifact" in relay_loop_single_template
    assert "semantic review: <graph policy, result routing" in relay_loop_single_template
    assert "## `graph.md`" in relay_loop_bundle_template
    assert "semantic review notes for graph policy" in relay_loop_bundle_template
    assert "scripts/README.md" in relay_loop_bundle_template
    assert "A specialist is a reusable agent template" in touring_question_style
    assert "You can skip this now and come back later." in touring_question_style
    assert "stop `research`" in touring_question_style
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
    installed_records = discover_installed_system_skills(tool="codex", home_path=home_path)

    assert result.projection_mode == "symlink"
    assert installed_skill_dir.is_symlink()
    assert installed_skill_dir.readlink().is_absolute()
    assert installed_skill_dir.readlink() == _packaged_skill_asset_root("houmao-specialist-mgr")
    assert (installed_skill_dir / "SKILL.md").is_file()
    assert tuple(record.name for record in installed_records) == ("houmao-specialist-mgr",)
    assert tuple(record.projection_mode for record in installed_records) == ("symlink",)
    _assert_no_install_state_written(home_path)


def test_install_system_skills_for_home_projects_copilot_selected_skills_and_status(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "copilot-home").resolve()

    result = install_system_skills_for_home(
        tool="copilot",
        home_path=home_path,
        skill_names=("houmao-specialist-mgr",),
    )

    installed_records = discover_installed_system_skills(tool="copilot", home_path=home_path)

    assert result.projected_relative_dirs == ("skills/houmao-specialist-mgr",)
    assert result.projection_mode == "copy"
    assert (home_path / "skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert tuple(record.name for record in installed_records) == ("houmao-specialist-mgr",)
    assert tuple(record.projected_relative_dir for record in installed_records) == (
        "skills/houmao-specialist-mgr",
    )
    assert tuple(record.projection_mode for record in installed_records) == ("copy",)
    _assert_no_install_state_written(home_path)


def test_install_system_skills_for_home_supports_copilot_symlink_projection(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "copilot-home").resolve()

    result = install_system_skills_for_home(
        tool="copilot",
        home_path=home_path,
        skill_names=("houmao-specialist-mgr",),
        projection_mode="symlink",
    )

    installed_skill_dir = home_path / "skills/houmao-specialist-mgr"
    installed_records = discover_installed_system_skills(tool="copilot", home_path=home_path)

    assert result.projected_relative_dirs == ("skills/houmao-specialist-mgr",)
    assert result.projection_mode == "symlink"
    assert installed_skill_dir.is_symlink()
    assert installed_skill_dir.readlink().is_absolute()
    assert installed_skill_dir.readlink() == _packaged_skill_asset_root("houmao-specialist-mgr")
    assert (installed_skill_dir / "SKILL.md").is_file()
    assert tuple(record.name for record in installed_records) == ("houmao-specialist-mgr",)
    assert tuple(record.projected_relative_dir for record in installed_records) == (
        "skills/houmao-specialist-mgr",
    )
    assert tuple(record.projection_mode for record in installed_records) == ("symlink",)
    _assert_no_install_state_written(home_path)


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

    installed_records = discover_installed_system_skills(tool="codex", home_path=home_path)
    assert tuple(record.name for record in installed_records) == ("houmao-specialist-mgr",)
    assert tuple(record.projection_mode for record in installed_records) == ("copy",)
    _assert_no_install_state_written(home_path)


def test_install_system_skills_for_home_overwrites_existing_current_skill_path_without_state(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    selected_skill_dir = home_path / "skills/houmao-agent-email-comms"
    selected_skill_path = selected_skill_dir / "SKILL.md"
    stale_child = selected_skill_dir / "stale.txt"
    _write(selected_skill_path, "user-authored collision\n")
    _write(stale_child, "stale child\n")

    install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        skill_names=("houmao-agent-email-comms",),
    )

    assert selected_skill_path.is_file()
    assert selected_skill_path.read_text(encoding="utf-8") != "user-authored collision\n"
    assert not stale_child.exists()
    _assert_no_install_state_written(home_path)


def test_install_system_skills_for_home_ignores_obsolete_state_version(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    state_path = _obsolete_system_skill_state_path(home_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    stale_payload = {
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
        ],
    }
    state_path.write_text(json.dumps(stale_payload, indent=2) + "\n", encoding="utf-8")

    install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        skill_names=("houmao-process-emails-via-gateway",),
    )

    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert json.loads(state_path.read_text(encoding="utf-8")) == stale_payload


def test_install_system_skills_for_home_preserves_unselected_legacy_unrelated_and_state(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "gemini-home").resolve()
    _write(
        home_path / ".agents/skills/houmao-specialist-mgr/SKILL.md",
        "old specialist path\n",
    )
    _write(
        home_path / ".gemini/skills/houmao-project-mgr/SKILL.md",
        "unselected current skill\n",
    )
    _write(home_path / "notes/unrelated.txt", "unrelated\n")
    state_path = _obsolete_system_skill_state_path(home_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    stale_state = "obsolete state\n"
    state_path.write_text(stale_state, encoding="utf-8")

    install_system_skills_for_home(
        tool="gemini",
        home_path=home_path,
        skill_names=("houmao-specialist-mgr",),
    )

    assert (home_path / ".gemini/skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert (home_path / ".agents/skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert (home_path / ".gemini/skills/houmao-project-mgr/SKILL.md").read_text(
        encoding="utf-8"
    ) == "unselected current skill\n"
    assert (home_path / "notes/unrelated.txt").read_text(encoding="utf-8") == "unrelated\n"
    assert state_path.read_text(encoding="utf-8") == stale_state


def test_install_system_skills_for_home_ignores_superseded_skill_record(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    _write(
        home_path / "skills/houmao-create-specialist/SKILL.md",
        "old flat project-easy path\n",
    )
    state_path = _obsolete_system_skill_state_path(home_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "tool": "codex",
                "installed_at": "2026-04-08T00:00:00Z",
                "installed_skills": [
                    {
                        "name": "houmao-create-specialist",
                        "asset_subpath": "houmao-create-specialist",
                        "projected_relative_dir": "skills/houmao-create-specialist",
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

    install_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        skill_names=("houmao-specialist-mgr",),
    )

    assert (home_path / "skills/houmao-specialist-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-create-specialist/SKILL.md").is_file()
    assert state_path.is_file()
