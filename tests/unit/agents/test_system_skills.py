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
    PROFILE_SYSTEM_SKILL_POLICY_MODES,
    SOURCE_SYSTEM_SKILL_POLICY_MODES,
    SystemSkillPolicyError,
    SystemSkillSelectionPolicy,
    SystemSkillCatalogError,
    SystemSkillInstallError,
    discover_installed_system_skills,
    install_system_skills_for_home,
    load_system_skill_catalog,
    load_system_skill_catalog_from_paths,
    parse_system_skill_selection_policy,
    resolve_auto_install_skill_selection,
    resolve_managed_system_skill_selection,
    resolve_system_skill_selection,
    sync_system_skills_for_home,
    system_skill_selection_policy_to_payload,
    uninstall_system_skills_for_home,
)

CORE_SYSTEM_SKILLS = (
    "houmao-process-emails-via-gateway",
    "houmao-agent-email-comms",
    SYSTEM_SKILL_UTILS_WORKSPACE_MGR,
    "houmao-mailbox-mgr",
    "houmao-memory-mgr",
    "houmao-adv-usage-pattern",
    "houmao-touring",
    "houmao-project-mgr",
    "houmao-specialist-mgr",
    "houmao-credential-mgr",
    "houmao-agent-definition",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
    "houmao-agent-instance",
    "houmao-agent-inspect",
    "houmao-agent-messaging",
    "houmao-agent-gateway",
)
ALL_SYSTEM_SKILLS = (
    *CORE_SYSTEM_SKILLS,
    SYSTEM_SKILL_UTILS_LLM_WIKI,
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
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
        "houmao-agent-instance",
        "houmao-agent-inspect",
        "houmao-agent-messaging",
        "houmao-agent-gateway",
    )
    assert "Canonical pre-launch agent-definition skill" in (
        catalog.skills["houmao-agent-definition"].description or ""
    )
    assert "Markdown/direct-SQL loop authoring" in (
        catalog.skills["houmao-agent-loop-lite"].description or ""
    )
    assert "Compatibility wrapper" in (catalog.skills["houmao-specialist-mgr"].description or "")
    assert catalog.retired_skill_names == (
        "houmao-agent-loop-pairwise",
        "houmao-agent-loop-pairwise-v2",
        "houmao-agent-loop-pairwise-v3",
        "houmao-agent-loop-pairwise-v4",
        "houmao-agent-loop-pairwise-v5",
        "houmao-agent-loop-generic",
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


def test_agent_loop_pro_prepare_agents_routes_agent_definition() -> None:
    skill_root = _packaged_skill_asset_root("houmao-agent-loop-pro")
    prepare_agents = (skill_root / "subskills/execution/prepare-agents.md").read_text(
        encoding="utf-8"
    )
    platform_boundaries = (skill_root / "subskills/reference/platform-boundaries.md").read_text(
        encoding="utf-8"
    )

    assert "Route persisted agent/profile preparation through `houmao-agent-definition`" in (
        prepare_agents
    )
    assert "`create-agent-fast-forward`: default" in prepare_agents
    assert "`profiles`: when the specialist already exists" in prepare_agents
    assert "`specialists`: when only specialist material changes" in prepare_agents
    assert "`raw-profiles`: only when the execplan or operator explicitly requires" in (
        prepare_agents
    )
    assert "Do not reimplement specialist creation" in prepare_agents
    assert "credential-defaulting" in platform_boundaries
    assert "Treat `houmao-mgr project easy ...` as its underlying CLI surface" in (
        platform_boundaries
    )


def test_agent_loop_lite_packaged_asset_contract() -> None:
    skill_root = _packaged_skill_asset_root("houmao-agent-loop-lite")
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    template_example = skill_text.split("```markdown", maxsplit=1)[1].split("```", maxsplit=1)[0]

    assert "name: houmao-agent-loop-lite" in skill_text
    assert "Use this Houmao skill only after the user explicitly selects" in skill_text
    assert "Do not auto-route generic loop requests here" in skill_text
    assert "<loop-dir>/intention/" in skill_text
    assert "<loop-dir>/execplan/" in skill_text
    assert "<loop-dir>/runs/" in skill_text
    assert "Do not generate `execplan/harness/` or `execplan/docs/`" in skill_text
    assert "Do not create JSON schemas, Jinja2 renderers" in skill_text
    assert "Loop-Template-Type" in skill_text
    assert "Loop-Template-Version" in skill_text
    assert "<placeholder work_item_id>" in skill_text
    assert "sender, receiver, subject, message id, thread id, timestamps" in skill_text.lower()
    assert "Always generate one shared guidance skill" in skill_text
    assert "Loop-Template-Type: task-request" in skill_text
    assert "unresolved `<placeholder` tokens before sending" in skill_text
    assert "execplan/specs/state/schema.sql" in skill_text
    assert "runs/<run-id>/state.sqlite3" in skill_text
    assert "BEGIN IMMEDIATE" in skill_text
    assert "Do not tell agents to sleep, poll, tail logs, or wait in-chat" in skill_text
    assert "houmao-agent-email-comms" in skill_text
    assert "houmao-agent-gateway" in skill_text
    assert "houmao-agent-definition" in skill_text
    assert "houmao-agent-instance" in skill_text
    for envelope_field in (
        "sender",
        "receiver",
        "subject",
        "message_id",
        "thread_id",
        "timestamp",
    ):
        assert f"<placeholder {envelope_field}" not in template_example


def test_retired_loop_skill_sources_are_legacy_only() -> None:
    catalog = load_system_skill_catalog()
    asset_root = Path(__file__).resolve().parents[3] / "src/houmao/agents/assets/system_skills"

    assert "houmao-agent-loop-pro" in catalog.skills
    assert "houmao-agent-loop-lite" in catalog.skills
    for retired_name in catalog.retired_skill_names:
        assert retired_name not in catalog.skills
        assert not (asset_root / retired_name).exists()
        assert (asset_root / "legacy" / retired_name / "SKILL.md").is_file()


def test_houmao_system_input_questions_distinguish_required_and_optional_inputs() -> None:
    definition_missing_inputs = (
        _packaged_skill_asset_root("houmao-agent-definition") / "subskills/common/missing-inputs.md"
    ).read_text(encoding="utf-8")
    credential_skill = (_packaged_skill_asset_root("houmao-credential-mgr") / "SKILL.md").read_text(
        encoding="utf-8"
    )
    workspace_skill = (
        _packaged_skill_asset_root(SYSTEM_SKILL_UTILS_WORKSPACE_MGR) / "SKILL.md"
    ).read_text(encoding="utf-8")
    touring_question_style = (
        _packaged_skill_asset_root("houmao-touring") / "references/question-style.md"
    ).read_text(encoding="utf-8")

    for text in (
        definition_missing_inputs,
        credential_skill,
        workspace_skill,
        touring_question_style,
    ):
        assert "`Required`" in text or "Required:" in text
        assert "`Optional`" in text or "Optional:" in text

    assert "Do not force this shape onto user-task or domain-intent questions" in (
        definition_missing_inputs
    )
    assert "Optional: none for this step." in credential_skill
    assert "Required when not safely inferred:" in workspace_skill
    assert "Do not force `Required`/`Optional` labels onto user-task" in (touring_question_style)


def test_loop_skills_route_system_input_question_guidance() -> None:
    skill_root = _packaged_skill_asset_root("houmao-agent-loop-pro")
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    question_ref = (skill_root / "subskills/reference/system-input-questions.md").read_text(
        encoding="utf-8"
    )
    init_page = (skill_root / "subskills/authoring/init.md").read_text(encoding="utf-8")
    clarify_protocol = (skill_root / "subskills/reference/clarification-protocol.md").read_text(
        encoding="utf-8"
    )
    launch_agents = (skill_root / "subskills/execution/launch-agents.md").read_text(
        encoding="utf-8"
    )

    assert "subskills/reference/system-input-questions.md" in skill_text
    assert "When asking for Houmao runtime or artifact-location inputs" in skill_text
    assert "Do not force this shape onto user-task or domain-intent questions" in question_ref
    assert "Required:" in question_ref
    assert "Optional:" in question_ref
    assert "`../reference/system-input-questions.md`" in init_page
    assert "ask with `Required: <loop-dir>`" in init_page
    assert "user-task or domain-intent questions" in clarify_protocol
    assert "`../reference/system-input-questions.md`" in launch_agents


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


def test_parse_system_skill_selection_policy_normalizes_and_serializes_selectors() -> None:
    policy = parse_system_skill_selection_policy(
        {
            "mode": "extend",
            "sets": [SYSTEM_SKILL_SET_CORE, SYSTEM_SKILL_SET_CORE],
            "skills": [SYSTEM_SKILL_UTILS_LLM_WIKI, SYSTEM_SKILL_UTILS_LLM_WIKI],
        },
        allowed_modes=SOURCE_SYSTEM_SKILL_POLICY_MODES,
        default_mode="default",
        source="recipe.launch",
    )

    assert policy == SystemSkillSelectionPolicy(
        mode="extend",
        set_names=(SYSTEM_SKILL_SET_CORE,),
        skill_names=(SYSTEM_SKILL_UTILS_LLM_WIKI,),
    )
    assert system_skill_selection_policy_to_payload(policy) == {
        "mode": "extend",
        "sets": [SYSTEM_SKILL_SET_CORE],
        "skills": [SYSTEM_SKILL_UTILS_LLM_WIKI],
    }
    assert (
        parse_system_skill_selection_policy(
            {},
            allowed_modes=PROFILE_SYSTEM_SKILL_POLICY_MODES,
            default_mode="inherit",
            source="profile.defaults",
        )
        is None
    )
    assert system_skill_selection_policy_to_payload(None) == {}


def test_parse_system_skill_selection_policy_rejects_invalid_modes_and_selectors() -> None:
    with pytest.raises(SystemSkillPolicyError, match="mode `inherit` is not allowed"):
        parse_system_skill_selection_policy(
            {"mode": "inherit"},
            allowed_modes=SOURCE_SYSTEM_SKILL_POLICY_MODES,
            default_mode="default",
            source="recipe.launch",
        )

    with pytest.raises(SystemSkillPolicyError, match="cannot be combined"):
        parse_system_skill_selection_policy(
            {"mode": "none", "skills": [SYSTEM_SKILL_UTILS_LLM_WIKI]},
            allowed_modes=PROFILE_SYSTEM_SKILL_POLICY_MODES,
            default_mode="inherit",
            source="profile.defaults",
        )

    with pytest.raises(SystemSkillPolicyError, match="requires at least one"):
        parse_system_skill_selection_policy(
            {"mode": "replace"},
            allowed_modes=PROFILE_SYSTEM_SKILL_POLICY_MODES,
            default_mode="inherit",
            source="profile.defaults",
        )

    with pytest.raises(SystemSkillCatalogError, match="Unknown system-skill set `utilities`"):
        parse_system_skill_selection_policy(
            {"mode": "extend", "sets": ["utilities"]},
            allowed_modes=SOURCE_SYSTEM_SKILL_POLICY_MODES,
            default_mode="default",
            source="recipe.launch",
        )

    with pytest.raises(SystemSkillCatalogError, match="Unknown system skill `not-a-skill`"):
        parse_system_skill_selection_policy(
            {"mode": "extend", "skills": ["not-a-skill"]},
            allowed_modes=SOURCE_SYSTEM_SKILL_POLICY_MODES,
            default_mode="default",
            source="recipe.launch",
        )


def test_resolve_managed_system_skill_selection_applies_source_and_profile_modes() -> None:
    catalog = load_system_skill_catalog()

    default_selection = resolve_managed_system_skill_selection(catalog=catalog)
    source_additive = resolve_managed_system_skill_selection(
        catalog=catalog,
        source_policy=SystemSkillSelectionPolicy(
            mode="extend",
            skill_names=(SYSTEM_SKILL_UTILS_LLM_WIKI,),
        ),
    )
    profile_additive = resolve_managed_system_skill_selection(
        catalog=catalog,
        source_policy=SystemSkillSelectionPolicy(
            mode="extend",
            skill_names=(SYSTEM_SKILL_UTILS_LLM_WIKI,),
        ),
        profile_policy=SystemSkillSelectionPolicy(
            mode="extend",
            set_names=(SYSTEM_SKILL_SET_CORE,),
            skill_names=(SYSTEM_SKILL_UTILS_LLM_WIKI,),
        ),
    )
    profile_replace = resolve_managed_system_skill_selection(
        catalog=catalog,
        source_policy=SystemSkillSelectionPolicy(
            mode="extend",
            skill_names=(SYSTEM_SKILL_UTILS_LLM_WIKI,),
        ),
        profile_policy=SystemSkillSelectionPolicy(
            mode="replace",
            set_names=(SYSTEM_SKILL_SET_ALL,),
        ),
    )
    profile_disabled = resolve_managed_system_skill_selection(
        catalog=catalog,
        profile_policy=SystemSkillSelectionPolicy(mode="none"),
    )

    assert default_selection.selected_set_names == (SYSTEM_SKILL_SET_CORE,)
    assert default_selection.explicit_skill_names == ()
    assert default_selection.resolved_skill_names == CORE_SYSTEM_SKILLS
    assert source_additive.selected_set_names == (SYSTEM_SKILL_SET_CORE,)
    assert source_additive.explicit_skill_names == (SYSTEM_SKILL_UTILS_LLM_WIKI,)
    assert source_additive.resolved_skill_names == ALL_SYSTEM_SKILLS
    assert profile_additive.selected_set_names == (SYSTEM_SKILL_SET_CORE,)
    assert profile_additive.explicit_skill_names == (SYSTEM_SKILL_UTILS_LLM_WIKI,)
    assert profile_additive.resolved_skill_names == ALL_SYSTEM_SKILLS
    assert profile_replace.selected_set_names == (SYSTEM_SKILL_SET_ALL,)
    assert profile_replace.explicit_skill_names == ()
    assert profile_replace.resolved_skill_names == ALL_SYSTEM_SKILLS
    assert profile_disabled.selected_set_names == ()
    assert profile_disabled.explicit_skill_names == ()
    assert profile_disabled.resolved_skill_names == ()


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


def test_current_packaged_system_skills_expose_help_contract() -> None:
    """Guard the standard skill-level help contract for current catalog entries."""

    catalog = load_system_skill_catalog()
    asset_root = Path(__file__).resolve().parents[3] / "src/houmao/agents/assets/system_skills"
    help_section_pattern = re.compile(r"(?ms)^## Help\n(?P<body>.*?)(?=^## |\Z)")

    for skill_name, skill_record in catalog.skills.items():
        skill_text = (asset_root / skill_record.asset_subpath / "SKILL.md").read_text(
            encoding="utf-8"
        )
        help_match = help_section_pattern.search(skill_text)

        assert help_match is not None, f"{skill_name} is missing a top-level help section"
        help_body = help_match.group("body")
        assert f"${skill_name} help" in help_body
        assert (
            "read-only help: do not run commands, mutate files, send mail, change gateway state, "
            "or alter managed-agent lifecycle state"
        ) in help_body
        assert "Available functionality:" in help_body
        assert "Common starting prompts:" in help_body
        assert "Related skills and boundaries:" in help_body
        assert "help me" in help_body


def test_current_packaged_system_skills_route_explicit_help_before_workflows() -> None:
    """Guard that help is treated as a narrow read-only meta operation."""

    catalog = load_system_skill_catalog()
    asset_root = Path(__file__).resolve().parents[3] / "src/houmao/agents/assets/system_skills"

    for skill_name, skill_record in catalog.skills.items():
        skill_text = (asset_root / skill_record.asset_subpath / "SKILL.md").read_text(
            encoding="utf-8"
        )
        if "\n## Workflow\n" in skill_text:
            assert "answer explicit skill-help intent from `## Help` and stop" in skill_text, (
                f"{skill_name} workflow does not handle explicit help before routing"
            )

    operation_markers = {
        "houmao-agent-definition": "| `help` |",
        "houmao-agent-gateway": "- `help` (read-only meta operation)",
        "houmao-agent-instance": "- `help` (read-only meta operation)",
        "houmao-agent-inspect": "- `help` (read-only meta operation)",
        "houmao-agent-messaging": "- `help` (read-only meta operation)",
        "houmao-mailbox-mgr": "- `help` (read-only meta operation)",
        "houmao-memory-mgr": "- `help` (read-only meta operation)",
        "houmao-project-mgr": "- `help` (read-only meta operation)",
        "houmao-credential-mgr": "- `help` (read-only meta operation)",
        "houmao-agent-loop-pro": "- `help`: explain this skill's purpose",
        "houmao-agent-loop-lite": "- `help`: explain this skill's purpose",
        SYSTEM_SKILL_UTILS_WORKSPACE_MGR: "- `help`: explain this skill's purpose",
        SYSTEM_SKILL_UTILS_LLM_WIKI: "read-only meta operation `help`",
    }
    for skill_name, marker in operation_markers.items():
        skill_text = (_packaged_skill_asset_root(skill_name) / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert marker in skill_text


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
    assert "Loop execplans may request additional task-scoped bookkeeping directories" in (
        in_repo_text
    )
    assert "<repo-root>/houmao-ws/<task-name>/<agent-name>/artifacts/**" in in_repo_text
    assert "The per-agent `repo/` worktree is the safe mutation surface" in in_repo_text
    assert "recursive local-state symlink decisions" in in_repo_text
    assert "hidden-path skips, symlink traversal skips, and tracked-content conflict skips" in (
        in_repo_text
    )
    assert "Resolve one `task-name` for the workspace team." in in_repo_text
    assert "<repo-root>/houmao-ws/<task-name>" in in_repo_text
    assert "houmao/<task-name>/<agent-name>/main" in in_repo_text
    assert "| `<repo-root>/houmao-ws/<task-name>/<agent-name>/kb/**` | yes | yes | yes | no |" in (
        in_repo_text
    )
    assert (
        "| `<repo-root>/houmao-ws/workspaces.md` | yes | no by default | yes | no by default |"
        in (in_repo_text)
    )
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
    retired_skill_path = home_path / "skills/houmao-agent-loop-pairwise-v3/SKILL.md"
    _write(user_skill_path, "custom user skill\n")
    _write(retired_skill_path, "retired loop skill\n")

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
    manage_credentials_path = home_path / "skills/houmao-credential-mgr/SKILL.md"
    manage_credentials_actions = home_path / "skills/houmao-credential-mgr/actions"
    manage_agent_definition_path = home_path / "skills/houmao-agent-definition/SKILL.md"
    manage_agent_definition_agents = home_path / "skills/houmao-agent-definition/agents"
    manage_agent_definition_actions = home_path / "skills/houmao-agent-definition/actions"
    manage_agent_definition_subskills = home_path / "skills/houmao-agent-definition/subskills"
    manage_agent_definition_references = (
        home_path / "skills/houmao-agent-definition/references/credentials"
    )
    loop_pro_skill_path = home_path / "skills/houmao-agent-loop-pro/SKILL.md"
    loop_pro_authoring = home_path / "skills/houmao-agent-loop-pro/subskills/authoring"
    loop_pro_execution = home_path / "skills/houmao-agent-loop-pro/subskills/execution"
    loop_pro_reference = home_path / "skills/houmao-agent-loop-pro/subskills/reference"
    loop_lite_skill_path = home_path / "skills/houmao-agent-loop-lite/SKILL.md"

    assert result.selected_set_names == (SYSTEM_SKILL_SET_CORE,)
    assert result.resolved_skill_names == CORE_SYSTEM_SKILLS
    assert result.removed_retired_skill_names == ("houmao-agent-loop-pairwise-v3",)
    assert result.removed_retired_projected_relative_dirs == (
        "skills/houmao-agent-loop-pairwise-v3",
    )
    assert set(record.name for record in installed_records) == set(result.resolved_skill_names)
    assert tuple(record.projection_mode for record in installed_records) == ("copy",) * len(
        CORE_SYSTEM_SKILLS
    )
    _assert_no_install_state_written(home_path)
    assert user_skill_path.is_file()
    assert not retired_skill_path.exists()
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-email-comms/SKILL.md").is_file()
    assert project_mgr_path.is_file()
    assert manage_specialist_path.is_file()
    assert manage_credentials_path.is_file()
    assert manage_agent_definition_path.is_file()
    assert loop_pro_skill_path.is_file()
    assert loop_lite_skill_path.is_file()
    assert (loop_pro_authoring / "init.md").is_file()
    assert (loop_pro_authoring / "clarify-intent.md").is_file()
    assert (loop_pro_authoring / "execplan-fast-forward.md").is_file()
    assert (loop_pro_authoring / "execplan-specs-contract.md").is_file()
    assert (loop_pro_authoring / "validate-execplan.md").is_file()
    assert (loop_pro_execution / "prepare-agents.md").is_file()
    assert (loop_pro_execution / "prepare-workspace.md").is_file()
    assert (loop_pro_execution / "validate-loop.md").is_file()
    assert (loop_pro_execution / "launch-agents.md").is_file()
    assert (loop_pro_execution / "start.md").is_file()
    assert (loop_pro_execution / "status.md").is_file()
    assert (loop_pro_execution / "recover.md").is_file()
    assert (loop_pro_reference / "runtime-mail-model.md").is_file()
    project_mgr_skill = project_mgr_path.read_text(encoding="utf-8")
    manage_specialist_skill = manage_specialist_path.read_text(encoding="utf-8")
    manage_credentials_skill = manage_credentials_path.read_text(encoding="utf-8")
    manage_agent_definition_skill = manage_agent_definition_path.read_text(encoding="utf-8")
    loop_pro_skill = loop_pro_skill_path.read_text(encoding="utf-8")
    loop_lite_skill = loop_lite_skill_path.read_text(encoding="utf-8")
    loop_pro_init = (loop_pro_authoring / "init.md").read_text(encoding="utf-8")
    loop_pro_clarify_intent = (loop_pro_authoring / "clarify-intent.md").read_text(encoding="utf-8")
    loop_pro_generate_execplan = (
        (loop_pro_authoring / "execplan-fast-forward.md").read_text(encoding="utf-8")
        + "\n"
        + (loop_pro_authoring / "execplan-specs-contract.md").read_text(encoding="utf-8")
    )
    loop_pro_validate_execplan = (loop_pro_authoring / "validate-execplan.md").read_text(
        encoding="utf-8"
    )
    loop_pro_prepare_agents = (loop_pro_execution / "prepare-agents.md").read_text(encoding="utf-8")
    project_init_action_path = project_mgr_actions / "init.md"
    project_status_action_path = project_mgr_actions / "status.md"
    project_launch_profiles_action_path = project_mgr_actions / "launch-profiles.md"
    project_easy_instances_action_path = project_mgr_actions / "easy-instances.md"
    project_overlay_reference_path = project_mgr_references / "overlay-resolution.md"
    project_layout_reference_path = project_mgr_references / "project-layout.md"
    project_effects_reference_path = project_mgr_references / "project-aware-effects.md"
    project_routing_reference_path = project_mgr_references / "routing-boundaries.md"
    definition_launcher_path = manage_agent_definition_subskills / "common/launcher.md"
    definition_missing_inputs_path = manage_agent_definition_subskills / "common/missing-inputs.md"
    definition_profile_lanes_path = manage_agent_definition_subskills / "common/profile-lanes.md"
    definition_credential_routing_path = (
        manage_agent_definition_subskills / "common/credential-routing.md"
    )
    definition_roles_path = manage_agent_definition_subskills / "low-level/roles.md"
    definition_recipes_path = manage_agent_definition_subskills / "low-level/recipes.md"
    definition_launch_profiles_path = (
        manage_agent_definition_subskills / "low-level/raw-profiles.md"
    )
    easy_specialists_path = manage_agent_definition_subskills / "easy/specialists.md"
    easy_profiles_path = manage_agent_definition_subskills / "easy/profiles.md"
    ready_profile_path = manage_agent_definition_subskills / "easy/create-agent-fast-forward.md"
    easy_launch_path = manage_agent_definition_subskills / "easy/launch-instance.md"
    easy_stop_path = manage_agent_definition_subskills / "easy/stop-instance.md"
    project_init_action = project_init_action_path.read_text(encoding="utf-8")
    project_status_action = project_status_action_path.read_text(encoding="utf-8")
    project_launch_profiles_action = project_launch_profiles_action_path.read_text(encoding="utf-8")
    project_easy_instances_action = project_easy_instances_action_path.read_text(encoding="utf-8")
    project_overlay_reference = project_overlay_reference_path.read_text(encoding="utf-8")
    project_layout_reference = project_layout_reference_path.read_text(encoding="utf-8")
    project_effects_reference = project_effects_reference_path.read_text(encoding="utf-8")
    project_routing_reference = project_routing_reference_path.read_text(encoding="utf-8")
    definition_launcher = definition_launcher_path.read_text(encoding="utf-8")
    definition_missing_inputs = definition_missing_inputs_path.read_text(encoding="utf-8")
    definition_profile_lanes = definition_profile_lanes_path.read_text(encoding="utf-8")
    definition_credential_routing = definition_credential_routing_path.read_text(encoding="utf-8")
    definition_roles = definition_roles_path.read_text(encoding="utf-8")
    definition_recipes = definition_recipes_path.read_text(encoding="utf-8")
    definition_launch_profiles = definition_launch_profiles_path.read_text(encoding="utf-8")
    easy_specialists = easy_specialists_path.read_text(encoding="utf-8")
    easy_profiles = easy_profiles_path.read_text(encoding="utf-8")
    ready_profile = ready_profile_path.read_text(encoding="utf-8")
    easy_launch = easy_launch_path.read_text(encoding="utf-8")
    easy_stop = easy_stop_path.read_text(encoding="utf-8")
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
    assert "houmao-agent-definition" in project_mgr_skill
    assert "houmao-agent-instance" in project_mgr_skill
    assert "actions/init.md" in project_mgr_skill
    assert "actions/status.md" in project_mgr_skill
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
    assert "Raw Profiles Have Moved" in project_launch_profiles_action
    assert "houmao-agent-definition/subskills/low-level/raw-profiles.md" in (
        project_launch_profiles_action
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
    assert "server start" not in project_effects_reference
    assert "admin cleanup runtime" in project_effects_reference
    assert "houmao-specialist-mgr" not in project_routing_reference
    assert "houmao-credential-mgr" in project_routing_reference
    assert "houmao-agent-definition" in project_routing_reference
    assert "houmao-agent-instance" in project_routing_reference
    assert "houmao-mailbox-mgr" in project_routing_reference
    assert "Compatibility Wrapper" in manage_specialist_skill
    assert "houmao-agent-definition/subskills/easy/specialists.md" in manage_specialist_skill
    assert "create-agent-fast-forward" in manage_specialist_skill
    assert "Do not run commands from this wrapper." in manage_specialist_skill
    assert "command -v houmao-mgr" in definition_launcher
    assert "uv tool run --from houmao houmao-mgr" in definition_launcher
    assert ".venv/bin/houmao-mgr" in definition_launcher
    assert "pixi run houmao-mgr" in definition_launcher
    assert "uv run houmao-mgr" in definition_launcher
    assert "user explicitly requests one launcher" in definition_launcher
    assert "Ask the user for exactly the missing fields" in definition_missing_inputs
    assert "Easy Profile" in definition_profile_lanes
    assert "Raw Profile" in definition_profile_lanes
    assert "loose `profile`, `agent profile`, `launch profile`, or `ready profile`" in (
        definition_profile_lanes
    )
    assert "project easy specialist create" in definition_credential_routing
    assert "Explicit Auth Mode" in easy_specialists
    assert "project easy profile create" in easy_profiles
    assert "project easy specialist set --name <name>" in easy_specialists
    assert "Do not remove and recreate an easy specialist" in easy_specialists
    assert "--prompt-overlay-mode append|replace" in easy_profiles
    assert "Env Lookup Mode" in easy_specialists
    assert "Directory Scan Mode" in easy_specialists
    assert "Auto Credentials Mode" in easy_specialists
    assert "No Discovery Mode" in easy_specialists
    assert "Specialist Create Defaulting" in easy_specialists
    assert "registered credentials exist: pick a matching registered credential" in (
        easy_specialists
    )
    assert "Resolve the specialist tool and credential from the prompt" in (
        definition_credential_routing
    )
    assert "Inventory registered credentials across supported tool lanes" in (
        definition_credential_routing
    )
    assert "project credentials <tool> list" in definition_credential_routing
    assert "credentials <tool> list --agent-def-dir <path>" in definition_credential_routing
    assert "credential_records[].updated_at_utc" in definition_credential_routing
    assert "choose the credential with the latest listed update time" in (
        definition_credential_routing
    )
    assert "no target: initialize/select a Houmao project" in definition_credential_routing
    assert "references/credentials/claude-lookup.md" in easy_specialists
    assert "references/credentials/codex-lookup.md" in easy_specialists
    assert "references/credentials/gemini-lookup.md" in easy_specialists
    assert "--claude-oauth-token" in easy_specialists
    assert "--claude-config-dir" in easy_specialists
    assert "optional bootstrap state" in easy_specialists
    assert "not a credential-providing method" in easy_specialists
    assert (
        "Do not scan env vars, directories, repo-local tool homes" in definition_credential_routing
    )
    deprecated_fixture_root = "/".join(("tests", "fixtures", "agents"))
    assert deprecated_fixture_root not in easy_specialists
    assert "project easy profile list" in easy_profiles
    assert "project easy profile get --name <name>" in easy_profiles
    assert "project easy profile remove --name <profile>" in easy_profiles
    assert "project easy instance launch --profile <profile>" in easy_launch
    assert "project easy profile get --name <profile>" in easy_launch
    assert "does not accept declarative mailbox fields such as `--mail-address`" in easy_launch
    assert "`--name` seeds the managed-agent mailbox address and principal id" in easy_launch
    assert "private filesystem mailbox directory outside the shared root" in easy_launch
    assert (
        "was preregistered manually already, launch-time safe registration can fail" in easy_launch
    )
    assert "project easy instance stop --name <name>" in easy_stop
    assert "create-agent-fast-forward" in ready_profile
    assert "Do not launch the managed agent." in ready_profile
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
    assert "stored easy-profile or raw-profile `--auth` override" in credentials_get_action
    assert "Do not invent unsupported clear flags" in credentials_set_action
    assert "stored easy-profile or raw-profile `--auth` override change" in credentials_set_action
    assert (
        "Do not continue with set when the user has not provided any explicit supported change"
        in credentials_set_action
    )
    assert "command -v houmao-mgr" in manage_agent_definition_skill
    assert "uv tool run --from houmao houmao-mgr" in manage_agent_definition_skill
    assert ".venv/bin/houmao-mgr" in manage_agent_definition_skill
    assert "pixi run houmao-mgr" in manage_agent_definition_skill
    assert "uv run houmao-mgr" in manage_agent_definition_skill
    assert "subskills/low-level/roles.md" in manage_agent_definition_skill
    assert "subskills/low-level/recipes.md" in manage_agent_definition_skill
    assert "subskills/low-level/raw-profiles.md" in manage_agent_definition_skill
    assert "subskills/easy/specialists.md" in manage_agent_definition_skill
    assert "subskills/easy/profiles.md" in manage_agent_definition_skill
    assert "subskills/easy/create-agent-fast-forward.md" in manage_agent_definition_skill
    assert "`raw-profiles`" in manage_agent_definition_skill
    assert "`profiles` as the default meaning" in manage_agent_definition_skill
    assert "project agents roles list" in definition_roles
    assert "project agents recipes list" in definition_recipes
    assert "project agents launch-profiles add --name <profile> --recipe <recipe>" in (
        definition_launch_profiles
    )
    assert "project agents presets ..." in definition_recipes
    assert "houmao-credential-mgr" in manage_agent_definition_skill
    assert "direct hand-editing under `.houmao/`" in manage_agent_definition_skill
    assert (manage_agent_definition_agents / "openai.yaml").is_file()
    assert definition_launcher_path.is_file()
    assert definition_missing_inputs_path.is_file()
    assert definition_profile_lanes_path.is_file()
    assert definition_credential_routing_path.is_file()
    assert definition_roles_path.is_file()
    assert definition_recipes_path.is_file()
    assert definition_launch_profiles_path.is_file()
    assert easy_specialists_path.is_file()
    assert easy_profiles_path.is_file()
    assert ready_profile_path.is_file()
    assert easy_launch_path.is_file()
    assert easy_stop_path.is_file()
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
    assert "Use this Houmao skill only after the user explicitly selects it" in loop_pro_skill
    assert "`houmao-agent-loop-pro`" in loop_pro_skill
    assert "treat it as `init`" in loop_pro_skill
    assert "<loop-dir>/intention/" in loop_pro_skill
    assert "<loop-dir>/execplan/" in loop_pro_skill
    assert "subskills/authoring/clarify-intent.md" in loop_pro_skill
    assert "subskills/execution/prepare-agents.md" in loop_pro_skill
    assert "Do not require `adrs/`" in loop_pro_skill
    assert "Do not import policy from examples or reference plans as global behavior" in (
        loop_pro_skill
    )
    assert "use `houmao-utils-workspace-mgr` through `prepare-workspace`" in loop_pro_skill
    assert "MUST READ for mail-driven loops" in loop_pro_skill
    assert "subskills/reference/runtime-mail-model.md" in loop_pro_skill
    assert "subskills/reference/topology-modes.md" in loop_pro_skill
    assert "subskills/reference/platform-boundaries.md" in loop_pro_skill
    assert "Do not duplicate maintained Houmao platform-operation contracts" in loop_pro_skill
    assert "tree-loop" in loop_pro_skill
    assert "generic-loop" in loop_pro_skill
    assert "name: houmao-agent-loop-lite" in loop_lite_skill
    assert "Do not auto-route generic loop requests here" in loop_lite_skill
    assert "Loop-Template-Type" in loop_lite_skill
    assert "runs/<run-id>/state.sqlite3" in loop_lite_skill
    assert "Do not generate `execplan/harness/` or `execplan/docs/`" in loop_lite_skill
    assert "If `<loop-dir>` is missing, ask with `Required: <loop-dir>`" in loop_pro_init
    assert "<loop-dir>/intention/README.md" in loop_pro_init
    assert "<loop-dir>/intention/project-context.md" in loop_pro_init
    assert "Show the provisional high-level Mermaid agent architecture" in (loop_pro_clarify_intent)
    assert "Ask at most five accepted questions per session, exactly one at a time" in (
        loop_pro_clarify_intent
    )
    assert "objective, agent communication, or loop process logic" in loop_pro_clarify_intent
    assert "<loop-dir>/adrs/" in loop_pro_clarify_intent
    assert "Do not generate, repair, or directly edit `execplan/`" in loop_pro_clarify_intent
    assert "<loop-dir>/execplan/" in loop_pro_generate_execplan
    assert "manifest.toml" in loop_pro_generate_execplan
    assert "Do not create `execplan/adrs/` just to explain routine defaults" in (
        loop_pro_generate_execplan
    )
    assert "defaulting to `in-repo`" in loop_pro_generate_execplan
    assert "schema-validated payload plus human-readable rendering" in (loop_pro_generate_execplan)
    assert "communication schemas, renderers, registry, and reply links" in (
        loop_pro_generate_execplan
    )
    assert "notification prompt and trigger contracts" in loop_pro_generate_execplan
    assert "templates.toml" in loop_pro_generate_execplan
    assert "<message-family>.schema.json" in loop_pro_generate_execplan
    assert "which on-event skill handles each received message family" in (
        loop_pro_generate_execplan
    )
    assert "generated skills under `execplan/skills/*/SKILL.md`" in (loop_pro_validate_execplan)
    assert "workspace setup contracts route workspace planning or creation" in (
        loop_pro_validate_execplan
    )
    assert "execplan/specs/comms/templates.toml" in loop_pro_validate_execplan
    assert "houmao-email-metadata" in loop_pro_validate_execplan
    assert "payload lifecycle contracts" in loop_pro_validate_execplan
    assert "archive-after-success behavior" in loop_pro_validate_execplan
    assert "houmao-utils-workspace-mgr" in loop_pro_prepare_agents
    assert "houmao-agent-definition" in loop_pro_prepare_agents
    assert "Do not launch live agents as normal preparation behavior; use `launch-agents`" in (
        loop_pro_prepare_agents
    )
    assert "maintained mail support skills" in loop_pro_prepare_agents
    assert "houmao-process-emails-via-gateway" in loop_pro_prepare_agents
    assert easy_specialists_path.is_file()
    assert easy_profiles_path.is_file()
    assert easy_launch_path.is_file()

    claude_reference_path = manage_agent_definition_references / "claude-lookup.md"
    codex_reference_path = manage_agent_definition_references / "codex-lookup.md"
    gemini_reference_path = manage_agent_definition_references / "gemini-lookup.md"
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
    retired_loop_path = home_path / "skills/houmao-agent-loop-pairwise-v5/SKILL.md"
    obsolete_state_path = _obsolete_system_skill_state_path(home_path)
    _write(copied_skill_path, "copied skill\n")
    symlink_source.mkdir(parents=True)
    symlink_target.parent.mkdir(parents=True, exist_ok=True)
    symlink_target.symlink_to(symlink_source)
    _write(file_target, "stale file skill\n")
    _write(user_skill_path, "custom user skill\n")
    _write(unknown_houmao_path, "not catalog owned\n")
    _write(legacy_path, "legacy family path\n")
    _write(retired_loop_path, "retired loop skill\n")
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
    assert result.removed_retired_skill_names == ("houmao-agent-loop-pairwise-v5",)
    assert result.removed_retired_projected_relative_dirs == (
        "skills/houmao-agent-loop-pairwise-v5",
    )
    assert "houmao-process-emails-via-gateway" in result.absent_skill_names
    assert "skills/houmao-process-emails-via-gateway" in result.absent_projected_relative_dirs
    assert "houmao-agent-gateway" in result.absent_skill_names
    assert not (home_path / "skills/houmao-specialist-mgr").exists()
    assert not symlink_target.exists()
    assert not symlink_target.is_symlink()
    assert symlink_source.is_dir()
    assert not file_target.exists()
    assert not retired_loop_path.exists()
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
    assert result.absent_retired_skill_names == catalog.retired_skill_names
    assert result.absent_retired_projected_relative_dirs == tuple(
        f"skills/{skill_name}" for skill_name in catalog.retired_skill_names
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

    assert result.selected_set_names == (SYSTEM_SKILL_SET_ALL,)
    assert result.projection_mode == "copy"
    assert result.resolved_skill_names == ALL_SYSTEM_SKILLS
    assert result.removed_retired_skill_names == ()
    assert (home_path / "skills/houmao-agent-instance/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-inspect/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-messaging/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-mailbox-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-memory-mgr/SKILL.md").is_file()
    assert (home_path / "skills/houmao-adv-usage-pattern/SKILL.md").is_file()
    assert (home_path / "skills/houmao-touring/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-loop-pro/SKILL.md").is_file()
    assert (home_path / "skills/houmao-agent-loop-lite/SKILL.md").is_file()
    assert (
        home_path / "skills/houmao-agent-loop-pro/subskills/reference/runtime-mail-model.md"
    ).is_file()
    assert (
        home_path / "skills/houmao-agent-loop-pro/subskills/reference/topology-modes.md"
    ).is_file()
    assert (home_path / "skills/houmao-agent-loop-pro/subskills/authoring/init.md").is_file()
    assert (
        home_path / "skills/houmao-agent-loop-pro/subskills/authoring/execplan-fast-forward.md"
    ).is_file()
    assert (
        home_path / "skills/houmao-agent-loop-pro/subskills/execution/prepare-agents.md"
    ).is_file()
    assert (
        home_path / "skills/houmao-agent-loop-pro/subskills/execution/prepare-workspace.md"
    ).is_file()
    assert (home_path / "skills/houmao-utils-llm-wiki/SKILL.md").is_file()
    assert (home_path / "skills/houmao-utils-workspace-mgr/SKILL.md").is_file()

    loop_pro_skill = (home_path / "skills/houmao-agent-loop-pro/SKILL.md").read_text(
        encoding="utf-8"
    )
    loop_lite_skill = (home_path / "skills/houmao-agent-loop-lite/SKILL.md").read_text(
        encoding="utf-8"
    )
    advanced_usage_skill = (home_path / "skills/houmao-adv-usage-pattern/SKILL.md").read_text(
        encoding="utf-8"
    )
    touring_skill = (home_path / "skills/houmao-touring/SKILL.md").read_text(encoding="utf-8")
    touring_advanced_usage = (
        home_path / "skills/houmao-touring/branches/advanced-usage.md"
    ).read_text(encoding="utf-8")
    pairwise_edge_loop_pattern = (
        home_path
        / "skills/houmao-adv-usage-pattern/patterns/pairwise-edge-loop-via-gateway-and-mailbox.md"
    ).read_text(encoding="utf-8")
    relay_loop_pattern = (
        home_path / "skills/houmao-adv-usage-pattern/patterns/relay-loop-via-gateway-and-mailbox.md"
    ).read_text(encoding="utf-8")

    assert "tree-loop" in loop_pro_skill
    assert "generic-loop" in loop_pro_skill
    assert "MUST READ for mail-driven loops" in loop_pro_skill
    assert "subskills/reference/runtime-mail-model.md" in loop_pro_skill
    assert "Markdown/direct-SQL" in loop_lite_skill
    assert "Loop-Template-Type" in loop_lite_skill
    assert "direct SQLite" in loop_lite_skill
    assert "houmao-agent-loop-pro" in advanced_usage_skill
    assert "houmao-agent-loop-lite" in advanced_usage_skill
    assert "Choose `tree-loop` or `generic-loop` inside pro" in advanced_usage_skill
    assert "beginner, intermediate, and advanced stages" in touring_skill
    assert "Guide the beginner stage" in touring_skill
    assert "Guide the intermediate stage" in touring_skill
    assert "Guide the advanced stage" in touring_skill
    assert "houmao-process-emails-via-gateway" in touring_skill
    assert "houmao-memory-mgr" in touring_skill
    assert "houmao-utils-workspace-mgr" in touring_skill
    assert "Lite loop authoring" in touring_advanced_usage
    assert "Pro loop authoring" in touring_advanced_usage
    assert "Tree-loop mode in pro" in touring_advanced_usage
    assert "Generic-loop mode in pro" in touring_advanced_usage
    assert "Isolated multi-agent workspace management" in touring_advanced_usage
    assert "Managed-agent memory" not in touring_advanced_usage
    assert "Credential management" not in touring_advanced_usage
    assert "houmao-utils-llm-wiki" not in touring_skill
    assert "houmao-utils-llm-wiki" not in touring_advanced_usage
    assert "Use `houmao-agent-loop-lite` instead" in pairwise_edge_loop_pattern
    assert "Use `houmao-agent-loop-pro` in `tree-loop` mode" in pairwise_edge_loop_pattern
    assert "Use `houmao-agent-loop-lite` instead" in relay_loop_pattern
    assert "Use `houmao-agent-loop-pro` instead" in relay_loop_pattern

    retired_names = load_system_skill_catalog().retired_skill_names
    for retired_name in retired_names:
        assert not (home_path / f"skills/{retired_name}").exists()
        assert retired_name not in advanced_usage_skill
        assert retired_name not in touring_skill
        assert retired_name not in touring_advanced_usage


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


def test_sync_system_skills_for_home_removes_unselected_current_and_retired_paths(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    stale_wiki_path = home_path / "skills/houmao-utils-llm-wiki/SKILL.md"
    stale_project_mgr_path = home_path / "skills/houmao-project-mgr/SKILL.md"
    user_skill_path = home_path / "skills/custom-user-skill/SKILL.md"
    unknown_houmao_path = home_path / "skills/houmao-user-owned/SKILL.md"
    retired_loop_path = home_path / "skills/houmao-agent-loop-pairwise-v5/SKILL.md"
    _write(stale_wiki_path, "stale wiki\n")
    _write(stale_project_mgr_path, "stale project manager\n")
    _write(user_skill_path, "custom user skill\n")
    _write(unknown_houmao_path, "not catalog owned\n")
    _write(retired_loop_path, "retired loop skill\n")
    selection = resolve_managed_system_skill_selection(
        profile_policy=SystemSkillSelectionPolicy(mode="none")
    )

    result = sync_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        selection=selection,
    )

    assert result.selected_set_names == ()
    assert result.explicit_skill_names == ()
    assert result.resolved_skill_names == ()
    assert result.projected_relative_dirs == ()
    assert result.removed_skill_names == (
        SYSTEM_SKILL_UTILS_LLM_WIKI,
        "houmao-project-mgr",
    )
    assert result.removed_projected_relative_dirs == (
        "skills/houmao-utils-llm-wiki",
        "skills/houmao-project-mgr",
    )
    assert result.removed_retired_skill_names == ("houmao-agent-loop-pairwise-v5",)
    assert result.removed_retired_projected_relative_dirs == (
        "skills/houmao-agent-loop-pairwise-v5",
    )
    assert not stale_wiki_path.exists()
    assert not stale_project_mgr_path.exists()
    assert not retired_loop_path.exists()
    assert user_skill_path.is_file()
    assert unknown_houmao_path.is_file()
    assert discover_installed_system_skills(tool="codex", home_path=home_path) == ()


def test_sync_system_skills_for_home_projects_exact_replacement_selection(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    stale_project_mgr_path = home_path / "skills/houmao-project-mgr/SKILL.md"
    _write(stale_project_mgr_path, "stale project manager\n")
    selection = resolve_managed_system_skill_selection(
        source_policy=SystemSkillSelectionPolicy(
            mode="replace",
            skill_names=(SYSTEM_SKILL_UTILS_LLM_WIKI,),
        )
    )

    result = sync_system_skills_for_home(
        tool="codex",
        home_path=home_path,
        selection=selection,
    )
    installed_records = discover_installed_system_skills(tool="codex", home_path=home_path)

    assert result.selected_set_names == ()
    assert result.explicit_skill_names == (SYSTEM_SKILL_UTILS_LLM_WIKI,)
    assert result.resolved_skill_names == (SYSTEM_SKILL_UTILS_LLM_WIKI,)
    assert result.projected_relative_dirs == ("skills/houmao-utils-llm-wiki",)
    assert result.removed_skill_names == ("houmao-project-mgr",)
    assert not stale_project_mgr_path.exists()
    assert (home_path / "skills/houmao-utils-llm-wiki/SKILL.md").is_file()
    assert tuple(record.name for record in installed_records) == (SYSTEM_SKILL_UTILS_LLM_WIKI,)


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
