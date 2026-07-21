"""Tests for actor-pack system-skill composition and lifecycle."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

import houmao.agents.system_skill_lifecycle as lifecycle_module
from houmao.agents.system_skills import (
    PROFILE_SYSTEM_SKILL_POLICY_MODES,
    SOURCE_SYSTEM_SKILL_POLICY_MODES,
    SYSTEM_SKILL_ADMIN_ENTRYPOINT,
    SYSTEM_SKILL_ADMIN_WELCOME,
    SYSTEM_SKILL_AGENT_ENTRYPOINT,
    SYSTEM_SKILL_PACK_ADMIN,
    SYSTEM_SKILL_PACK_AGENT,
    SystemSkillInstallError,
    SystemSkillManifestError,
    SystemSkillPolicyError,
    SystemSkillSelectionPolicy,
    compose_system_skill_pack,
    inspect_legacy_system_skill_paths,
    inspect_system_skill_packs,
    inspect_system_skill_receipt,
    install_system_skill_packs_for_home,
    load_legacy_system_skill_catalog,
    load_system_skill_manifest,
    load_system_skill_manifest_from_paths,
    parse_system_skill_selection_policy,
    protected_invocation_designator,
    protected_routine_closure,
    resolve_managed_system_skill_selection,
    resolve_system_skill_pack_selection,
    sync_system_skill_packs_for_home,
    system_skill_selection_policy_to_payload,
    uninstall_system_skill_packs_for_home,
    upgrade_system_skill_packs_for_home,
)


ASSET_ROOT = (
    Path(__file__).resolve().parents[3] / "src/houmao/agents/assets/system_skills"
).resolve()
MANIFEST_PATH = ASSET_ROOT / "manifest.toml"
SCHEMA_PATH = ASSET_ROOT / "manifest.schema.json"
PROTECTED_ROOT = ASSET_ROOT / "protected/houmao-shared-routines"

ADMIN_ONLY = {
    "houmao-project-mgr",
    "houmao-credential-mgr",
    "houmao-agent-definition",
    "houmao-operator-messaging",
}
AGENT_ONLY = {"houmao-process-emails-via-gateway"}
SHARED = {
    "houmao-agent-email-comms",
    "houmao-adv-usage-pattern",
    "houmao-utils-workspace-mgr",
    "houmao-ext-graphing",
    "houmao-mailbox-mgr",
    "houmao-memory-mgr",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
    "houmao-agent-instance",
    "houmao-agent-inspect",
    "houmao-agent-messaging",
    "houmao-agent-gateway",
    "houmao-interop-ag-ui",
}


def _load_fixture_manifest(tmp_path: Path, transform: object) -> object:
    """Write transformed manifest text and load it against packaged assets."""

    text = MANIFEST_PATH.read_text(encoding="utf-8")
    assert callable(transform)
    transformed = transform(text)
    fixture = tmp_path / "manifest.toml"
    fixture.write_text(transformed, encoding="utf-8")
    return load_system_skill_manifest_from_paths(
        manifest_path=fixture,
        schema_path=SCHEMA_PATH,
        assets_root=ASSET_ROOT,
    )


def test_manifest_exposes_two_actor_packs_and_three_public_skills() -> None:
    manifest = load_system_skill_manifest()

    assert manifest.schema_version == "houmao-system-skills.v2"
    assert manifest.pack_ids == (SYSTEM_SKILL_PACK_ADMIN, SYSTEM_SKILL_PACK_AGENT)
    assert manifest.public_skill_names == (
        SYSTEM_SKILL_ADMIN_WELCOME,
        SYSTEM_SKILL_ADMIN_ENTRYPOINT,
        SYSTEM_SKILL_AGENT_ENTRYPOINT,
    )
    assert manifest.defaults.cli == (SYSTEM_SKILL_PACK_ADMIN,)
    assert manifest.defaults.managed_launch == (SYSTEM_SKILL_PACK_AGENT,)
    assert manifest.defaults.managed_join == (SYSTEM_SKILL_PACK_AGENT,)
    assert manifest.auto_skill_name == "houmao-auto-system-prompt"
    assert manifest.auto_skill_name not in manifest.public_skills
    assert manifest.auto_skill_name not in manifest.protected_routines


def test_manifest_role_cardinality_and_audience_matrix() -> None:
    manifest = load_system_skill_manifest()
    admin = manifest.packs[SYSTEM_SKILL_PACK_ADMIN]
    agent = manifest.packs[SYSTEM_SKILL_PACK_AGENT]

    assert [manifest.public_skills[name].role for name in admin.public_skill_names] == [
        "welcome",
        "entrypoint",
    ]
    assert [manifest.public_skills[name].role for name in agent.public_skill_names] == [
        "entrypoint"
    ]
    assert {
        record.logical_id for record in protected_routine_closure(manifest, audience="admin")
    } == ADMIN_ONLY | SHARED
    assert {
        record.logical_id for record in protected_routine_closure(manifest, audience="agent")
    } == AGENT_ONLY | SHARED


def test_protected_logical_ids_are_not_install_selectors() -> None:
    manifest = load_system_skill_manifest()

    with pytest.raises(SystemSkillManifestError, match="not an install selector"):
        resolve_system_skill_pack_selection(
            manifest,
            pack_ids=("houmao-agent-inspect",),
        )


def test_actor_qualified_invocation_designators_are_stable() -> None:
    admin = protected_invocation_designator("houmao-agent-inspect", audience="admin")
    agent = protected_invocation_designator("houmao-agent-inspect", audience="agent")

    assert admin.value == ("houmao-admin-entrypoint->houmao-shared-routines->agent-inspect")
    assert agent.value == ("houmao-agent-entrypoint->houmao-shared-routines->agent-inspect")
    assert agent.command("status") == (
        "houmao-agent-entrypoint->houmao-shared-routines->agent-inspect->status()"
    )
    with pytest.raises(SystemSkillManifestError, match="not eligible"):
        protected_invocation_designator("houmao-credential-mgr", audience="agent")


@pytest.mark.parametrize(
    ("transform", "message"),
    [
        (
            lambda text: text.replace(
                'pack_id = "agent"\naudience = "agent"',
                'pack_id = "admin"\naudience = "agent"',
            ),
            "Duplicate pack",
        ),
        (
            lambda text: text.replace(
                'source_path = "public/houmao-admin-welcome"',
                'source_path = "../houmao-admin-welcome"',
            ),
            "escapes the asset root",
        ),
        (
            lambda text: text.replace(
                'public_skills = ["houmao-admin-welcome", "houmao-admin-entrypoint"]',
                'public_skills = ["houmao-admin-entrypoint"]',
            ),
            "must contain roles",
        ),
        (
            lambda text: text.replace(
                'dependencies = ["houmao-agent-email-comms"]\ncommands = ["help", "process-round"]',
                'dependencies = ["houmao-credential-mgr"]\ncommands = ["help", "process-round"]',
            ),
            "ineligible `agent` dependency",
        ),
        (
            lambda text: text.replace(
                'logical_id = "houmao-project-mgr"',
                'logical_id = "houmao-auto-system-prompt"',
                1,
            ),
            "must stay outside",
        ),
    ],
)
def test_manifest_rejects_invalid_pack_and_dependency_fixtures(
    tmp_path: Path,
    transform: object,
    message: str,
) -> None:
    with pytest.raises(SystemSkillManifestError, match=message):
        _load_fixture_manifest(tmp_path, transform)


def test_read_only_v1_catalog_and_digest_inventory_are_available() -> None:
    legacy = load_legacy_system_skill_catalog()
    manifest = load_system_skill_manifest()

    assert legacy.schema_version == 1
    assert len(legacy.skills) == 20
    assert "houmao-touring" in {record.name for record in legacy.skills}
    assert "houmao-specialist-mgr" in manifest.legacy_skills
    assert all(len(record.content_digest) == 64 for record in manifest.legacy_skills.values())


@pytest.mark.parametrize(
    ("pack_id", "expected_public", "expected_count"),
    [
        (
            SYSTEM_SKILL_PACK_ADMIN,
            {SYSTEM_SKILL_ADMIN_WELCOME, SYSTEM_SKILL_ADMIN_ENTRYPOINT},
            17,
        ),
        (SYSTEM_SKILL_PACK_AGENT, {SYSTEM_SKILL_AGENT_ENTRYPOINT}, 14),
    ],
)
def test_composer_materializes_only_audience_eligible_nested_routines(
    tmp_path: Path,
    pack_id: str,
    expected_public: set[str],
    expected_count: int,
) -> None:
    result = compose_system_skill_pack(
        load_system_skill_manifest(),
        pack_id=pack_id,
        destination_root=tmp_path / pack_id,
    )

    assert {record.name for record in result.public_skills} == expected_public
    entrypoint = next(record for record in result.public_skills if record.role == "entrypoint")
    shared = entrypoint.path / "subskills/houmao-shared-routines"
    nested_names = {path.name for path in (shared / "subskills").iterdir()}
    composed_markdown = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(entrypoint.path.rglob("*.md"))
    )
    assert len(nested_names) == expected_count
    assert "<public-entrypoint>" not in composed_markdown
    assert f"${entrypoint.name}" in composed_markdown
    if pack_id == SYSTEM_SKILL_PACK_ADMIN:
        welcome = next(record for record in result.public_skills if record.role == "welcome")
        assert not (welcome.path / "subskills").exists()
        assert ADMIN_ONLY <= nested_names
        assert nested_names.isdisjoint(AGENT_ONLY)
    else:
        assert AGENT_ONLY <= nested_names
        assert nested_names.isdisjoint(ADMIN_ONLY)


def test_protected_layout_has_true_subskills_actor_guards_and_no_flat_wrappers() -> None:
    manifest = load_system_skill_manifest()
    source_subskills = PROTECTED_ROOT / "subskills"

    assert {path.name for path in source_subskills.iterdir()} == set(manifest.protected_logical_ids)
    assert not (ASSET_ROOT / "houmao-touring").exists()
    assert not (ASSET_ROOT / "houmao-specialist-mgr").exists()
    for routine in manifest.protected_routines.values():
        root = ASSET_ROOT / routine.source_path
        text = (root / "SKILL.md").read_text(encoding="utf-8")
        assert "## Actor Frame Gate" in text
        assert "MUST NOT execute standalone" in text
        assert not list(root.rglob("actions"))
        for nested in (path for path in root.rglob("subskills") if path.is_dir()):
            assert all((child / "SKILL.md").is_file() for child in nested.iterdir())


def test_public_content_declares_actor_and_welcome_boundaries() -> None:
    welcome = (ASSET_ROOT / "public/houmao-admin-welcome/SKILL.md").read_text(encoding="utf-8")
    admin = (ASSET_ROOT / "public/houmao-admin-entrypoint/SKILL.md").read_text(encoding="utf-8")
    agent = (ASSET_ROOT / "public/houmao-agent-entrypoint/SKILL.md").read_text(encoding="utf-8")

    for command in (
        "help",
        "show-options",
        "choose-path",
        "show-command-map",
        "next-step",
        "start-guided-tour",
    ):
        assert f"`{command}`" in welcome
        assert (ASSET_ROOT / f"public/houmao-admin-welcome/commands/{command}.md").is_file()
    for path_name in (
        "Single Agent Full Run",
        "Operator-Controlled Agent Team",
        "Pro Agent Loop",
        "Subsystem Exploration",
        "Existing Project Reorientation",
    ):
        assert path_name in (
            ASSET_ROOT / "public/houmao-admin-welcome/references/guided-paths.md"
        ).read_text(encoding="utf-8")
    orientation = (ASSET_ROOT / "public/houmao-admin-welcome/references/orientation.md").read_text(
        encoding="utf-8"
    )
    assert "## Intent Guess Matrix" in orientation
    assert "The guess orders choices. It never authorizes a concrete operation." in orientation
    assert "MUST NOT create or edit files" in welcome
    assert "$houmao-admin-entrypoint" in welcome
    assert "You are NOT the managed Houmao agent" in admin
    assert "agents self" in admin and "never" in admin.lower()
    assert "`agent-instance join` is the only actor transition" in admin
    assert "join-self" not in admin
    assert "houmao-mgr --print-json agents self identity" in agent
    assert "Before EVERY substantive route" in agent
    assert "Never use the admin-only project, credential, agent-definition" in agent
    assert "There is no agent welcome" in agent


def test_external_default_installs_atomic_admin_pack_with_receipt(tmp_path: Path) -> None:
    home = tmp_path / "home"
    result = install_system_skill_packs_for_home(
        tool="codex",
        home_path=home,
        use_cli_default=True,
    )

    assert result.selected_pack_ids == (SYSTEM_SKILL_PACK_ADMIN,)
    assert result.public_skill_names == (
        SYSTEM_SKILL_ADMIN_WELCOME,
        SYSTEM_SKILL_ADMIN_ENTRYPOINT,
    )
    assert result.receipt_path.is_file()
    status = inspect_system_skill_packs(tool="codex", home_path=home)
    assert status.receipt.status == "current"
    assert [(record.pack_id, record.status) for record in status.packs] == [
        (SYSTEM_SKILL_PACK_ADMIN, "complete"),
        (SYSTEM_SKILL_PACK_AGENT, "absent"),
    ]


def test_untracked_public_collision_rejects_entire_admin_pack(tmp_path: Path) -> None:
    home = tmp_path / "home"
    collision = home / "skills/houmao-admin-entrypoint"
    collision.mkdir(parents=True)
    (collision / "user.txt").write_text("mine", encoding="utf-8")

    with pytest.raises(SystemSkillInstallError, match="Untracked.*collision"):
        install_system_skill_packs_for_home(
            tool="codex",
            home_path=home,
            use_cli_default=True,
        )

    assert (collision / "user.txt").read_text(encoding="utf-8") == "mine"
    assert not (home / "skills/houmao-admin-welcome").exists()
    assert inspect_system_skill_receipt(tool="codex", home_path=home).status == "absent"


def test_multi_public_commit_failure_rolls_back_admin_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    original_commit = lifecycle_module._commit_public_projection
    calls = 0

    def fail_second(staged_path: Path, target_path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected commit failure")
        original_commit(staged_path, target_path)

    monkeypatch.setattr(lifecycle_module, "_commit_public_projection", fail_second)
    with pytest.raises(OSError, match="injected"):
        install_system_skill_packs_for_home(
            tool="codex",
            home_path=home,
            use_cli_default=True,
        )

    assert not (home / "skills/houmao-admin-welcome").exists()
    assert not (home / "skills/houmao-admin-entrypoint").exists()
    assert inspect_system_skill_receipt(tool="codex", home_path=home).status == "absent"


def test_symlink_mode_targets_receipt_owned_complete_materialization(tmp_path: Path) -> None:
    home = tmp_path / "home"
    result = install_system_skill_packs_for_home(
        tool="kimi",
        home_path=home,
        pack_ids=(SYSTEM_SKILL_PACK_ADMIN,),
        projection_mode="symlink",
    )

    for relative_path in result.projected_relative_dirs:
        public_path = home / relative_path
        assert public_path.is_symlink()
        assert public_path.resolve().is_relative_to(
            home / ".houmao/system-skills/kimi/materialized"
        )
        assert (public_path.resolve() / "SKILL.md").is_file()
    assert inspect_system_skill_packs(tool="kimi", home_path=home).packs[0].status == ("complete")


def test_status_classifies_incomplete_drifted_and_conflicting_packs(tmp_path: Path) -> None:
    home = tmp_path / "home"
    install_system_skill_packs_for_home(
        tool="codex",
        home_path=home,
        use_cli_default=True,
    )
    welcome = home / "skills/houmao-admin-welcome"
    shutil.rmtree(welcome)
    status = inspect_system_skill_packs(tool="codex", home_path=home)
    assert status.packs[0].status == "incomplete"

    install_system_skill_packs_for_home(
        tool="codex",
        home_path=home,
        use_cli_default=True,
    )
    (welcome / "SKILL.md").write_text("changed", encoding="utf-8")
    status = inspect_system_skill_packs(tool="codex", home_path=home)
    assert status.packs[0].status == "drifted"

    other_home = tmp_path / "other"
    (other_home / "skills/houmao-agent-entrypoint").mkdir(parents=True)
    status = inspect_system_skill_packs(tool="codex", home_path=other_home)
    assert status.packs[1].status == "conflicting"


def test_corrupt_and_forward_receipts_are_read_only_and_block_mutation(tmp_path: Path) -> None:
    home = tmp_path / "home"
    receipt_path = home / ".houmao/system-skills/codex/receipt.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text("{bad", encoding="utf-8")

    assert inspect_system_skill_receipt(tool="codex", home_path=home).status == "corrupt"
    with pytest.raises(SystemSkillInstallError, match="Cannot read"):
        install_system_skill_packs_for_home(
            tool="codex",
            home_path=home,
            use_cli_default=True,
        )

    receipt_path.write_text(
        json.dumps({"schema_version": "houmao-system-skills-receipt.v99"}),
        encoding="utf-8",
    )
    assert inspect_system_skill_receipt(tool="codex", home_path=home).status == "unsupported"


def test_sync_removes_only_receipt_owned_pack_and_preserves_unrelated_skill(tmp_path: Path) -> None:
    home = tmp_path / "home"
    unrelated = home / "skills/user-skill/SKILL.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("mine", encoding="utf-8")
    install_system_skill_packs_for_home(
        tool="codex",
        home_path=home,
        pack_ids=(SYSTEM_SKILL_PACK_ADMIN, SYSTEM_SKILL_PACK_AGENT),
    )

    result = sync_system_skill_packs_for_home(
        tool="codex",
        home_path=home,
        selected_pack_ids=(SYSTEM_SKILL_PACK_AGENT,),
    )

    assert result.removed_pack_ids == (SYSTEM_SKILL_PACK_ADMIN,)
    assert not (home / "skills/houmao-admin-welcome").exists()
    assert not (home / "skills/houmao-admin-entrypoint").exists()
    assert (home / "skills/houmao-agent-entrypoint").is_dir()
    assert unrelated.read_text(encoding="utf-8") == "mine"


def test_uninstall_is_pack_selected_and_receipt_owned(tmp_path: Path) -> None:
    home = tmp_path / "home"
    install_system_skill_packs_for_home(
        tool="claude",
        home_path=home,
        pack_ids=(SYSTEM_SKILL_PACK_ADMIN, SYSTEM_SKILL_PACK_AGENT),
    )

    result = uninstall_system_skill_packs_for_home(
        tool="claude",
        home_path=home,
        pack_ids=(SYSTEM_SKILL_PACK_ADMIN,),
    )

    assert result.removed_pack_ids == (SYSTEM_SKILL_PACK_ADMIN,)
    assert (home / "skills/houmao-agent-entrypoint").is_dir()
    receipt = inspect_system_skill_receipt(tool="claude", home_path=home).receipt
    assert receipt is not None
    assert receipt.selected_pack_ids == (SYSTEM_SKILL_PACK_AGENT,)


def test_legacy_upgrade_removes_package_link_and_preserves_modified_path(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    manifest = load_system_skill_manifest()
    legacy_link = home / "skills/houmao-agent-inspect"
    legacy_link.parent.mkdir(parents=True)
    expected_old_source = ASSET_ROOT / manifest.legacy_skills["houmao-agent-inspect"].asset_subpath
    legacy_link.symlink_to(expected_old_source)
    modified = home / "skills/houmao-mailbox-mgr"
    modified.mkdir()
    (modified / "SKILL.md").write_text("user-modified", encoding="utf-8")

    inspection = inspect_legacy_system_skill_paths(tool="codex", home_path=home)
    classifications = {record.name: record.classification for record in inspection.paths}
    assert classifications["houmao-agent-inspect"] == "package-linked"
    assert classifications["houmao-mailbox-mgr"] == "modified"

    result = upgrade_system_skill_packs_for_home(
        tool="codex",
        home_path=home,
        use_cli_default=True,
    )
    assert not legacy_link.exists() and not legacy_link.is_symlink()
    assert modified.is_dir()
    assert result.preserved_legacy_paths == ("skills/houmao-mailbox-mgr",)


def test_pack_policy_defaults_extensions_replacement_and_disable() -> None:
    default = resolve_managed_system_skill_selection()
    assert default.selected_pack_ids == (SYSTEM_SKILL_PACK_AGENT,)
    assert default.resolved_public_skill_names == (SYSTEM_SKILL_AGENT_ENTRYPOINT,)

    extended = resolve_managed_system_skill_selection(
        profile_policy=SystemSkillSelectionPolicy(
            mode="extend",
            pack_ids=(SYSTEM_SKILL_PACK_ADMIN,),
        )
    )
    assert extended.selected_pack_ids == (
        SYSTEM_SKILL_PACK_AGENT,
        SYSTEM_SKILL_PACK_ADMIN,
    )

    replaced = resolve_managed_system_skill_selection(
        source_policy=SystemSkillSelectionPolicy(
            mode="replace",
            pack_ids=(SYSTEM_SKILL_PACK_ADMIN,),
        )
    )
    assert replaced.selected_pack_ids == (SYSTEM_SKILL_PACK_ADMIN,)
    disabled = resolve_managed_system_skill_selection(
        source_policy=SystemSkillSelectionPolicy(mode="none")
    )
    assert disabled.selected_pack_ids == ()


def test_policy_payload_uses_packs_and_rejects_obsolete_or_protected_selectors() -> None:
    policy = parse_system_skill_selection_policy(
        {"mode": "replace", "packs": ["agent"]},
        allowed_modes=SOURCE_SYSTEM_SKILL_POLICY_MODES,
        default_mode="default",
        source="recipe",
    )
    assert policy is not None
    assert system_skill_selection_policy_to_payload(policy) == {
        "mode": "replace",
        "packs": ["agent"],
    }
    with pytest.raises(SystemSkillPolicyError, match="obsolete"):
        parse_system_skill_selection_policy(
            {"mode": "replace", "skills": ["houmao-agent-inspect"]},
            allowed_modes=SOURCE_SYSTEM_SKILL_POLICY_MODES,
            default_mode="default",
            source="recipe",
        )
    with pytest.raises(SystemSkillPolicyError, match="not an install selector"):
        parse_system_skill_selection_policy(
            {"mode": "replace", "packs": ["houmao-agent-inspect"]},
            allowed_modes=PROFILE_SYSTEM_SKILL_POLICY_MODES,
            default_mode="inherit",
            source="profile",
        )
