"""Coverage for the static Houmao system-skill collection."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

import houmao.agents.system_skill_lifecycle as lifecycle_module
from houmao.agents.system_skills import (
    EXPECTED_STANDALONE_SKILL_NAMES,
    SYSTEM_SKILL_AGENT_ENTRYPOINT,
    SYSTEM_SKILL_PACK_AGENT,
    SYSTEM_SKILL_SHARED_ROUTINES,
    StandaloneSystemSkillRecord,
    SystemSkillInstallError,
    SystemSkillManifest,
    SystemSkillManifestError,
    SystemSkillSelectionPolicy,
    inspect_system_skill_packs,
    inspect_system_skill_config,
    install_system_skill_packs_for_home,
    load_system_skill_manifest,
    load_system_skill_manifest_from_paths,
    project_system_skills_to_destination,
    resolve_managed_system_skill_selection,
    resolve_system_skill_pack_members,
    resolve_system_skill_pack_selection,
    stage_system_skill_collection,
    system_skill_reference_for_name,
    sync_system_skill_packs_for_home,
    tree_content_digest,
    uninstall_system_skill_packs_for_home,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ASSET_ROOT = REPO_ROOT / "src/houmao/agents/assets/system_skills"
PUBLIC_ROOT = ASSET_ROOT / "public"
MANIFEST_PATH = ASSET_ROOT / "manifest.toml"
SCHEMA_PATH = ASSET_ROOT / "manifest.schema.json"

ADMIN_MEMBERS = (
    "houmao-admin-welcome",
    "houmao-admin-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
)
AGENT_MEMBERS = (
    "houmao-agent-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
)


def _load_modified_manifest(tmp_path: Path, transform: object) -> object:
    """Load one textually transformed manifest against the packaged source tree."""

    if not callable(transform):
        raise TypeError("transform must be callable")
    manifest_path = tmp_path / "manifest.toml"
    manifest_path.write_text(transform(MANIFEST_PATH.read_text(encoding="utf-8")), encoding="utf-8")
    return load_system_skill_manifest_from_paths(
        manifest_path=manifest_path,
        schema_path=SCHEMA_PATH,
        assets_root=ASSET_ROOT,
    )


def test_manifest_v5_declares_exact_static_collection() -> None:
    """The manifest exposes the fixed public roots and resolves actor packs."""

    manifest = load_system_skill_manifest()

    assert manifest.schema_version == "houmao-system-skills.v5"
    assert manifest.standalone_skill_names == EXPECTED_STANDALONE_SKILL_NAMES
    assert manifest.packs["admin"].standalone_skill_names == ADMIN_MEMBERS
    assert manifest.packs["agent"].standalone_skill_names == AGENT_MEMBERS
    assert manifest.defaults.cli == ("admin",)
    assert manifest.defaults.managed_launch == ("agent",)
    assert manifest.packs["admin"].default_lanes == ("cli",)
    assert manifest.packs["agent"].default_lanes == ("managed_launch",)
    assert "join" not in manifest.shared_routines["houmao-agent-instance"].commands
    assert not (
        PUBLIC_ROOT / "houmao-shared-routines/subskills/houmao-agent-instance/commands/join.md"
    ).exists()
    assert not hasattr(manifest, "auto_skill_name")
    assert tuple(
        record.name
        for record in manifest.standalone_skills.values()
        if record.activation == "narrow-implicit"
    ) == ("houmao-admin-entrypoint", "houmao-agent-entrypoint")
    assert tuple(
        record.name
        for record in manifest.standalone_skills.values()
        if record.activation == "explicit"
    ) == (
        "houmao-admin-welcome",
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    )


def test_manifest_rejects_any_other_implicit_activation_set(tmp_path: Path) -> None:
    """Cross-reference validation fixes the two implicit and four explicit roots exactly."""

    with pytest.raises(SystemSkillManifestError, match="only actor entrypoints"):
        _load_modified_manifest(
            tmp_path,
            lambda text: text.replace(
                'name = "houmao-admin-welcome"\nrole = "welcome"\nsource_path = "public/houmao-admin-welcome"\nactivation = "explicit"',
                'name = "houmao-admin-welcome"\nrole = "welcome"\nsource_path = "public/houmao-admin-welcome"\nactivation = "narrow-implicit"',
                1,
            ),
        )


def test_manifest_rejects_obsolete_composition_fields(tmp_path: Path) -> None:
    """V5 schema does not accept any protected-mount declaration."""

    with pytest.raises(SystemSkillManifestError, match="Additional properties"):
        _load_modified_manifest(
            tmp_path,
            lambda text: text.replace(
                'schema_version = "houmao-system-skills.v5"',
                'schema_version = "houmao-system-skills.v5"\nprotected_mounts = []',
                1,
            ),
        )


def test_manifest_rejects_retired_managed_join_lane(tmp_path: Path) -> None:
    """Restoring the removed lane cannot silently select an actor pack."""

    with pytest.raises(SystemSkillManifestError, match="managed_join"):
        _load_modified_manifest(
            tmp_path,
            lambda text: text.replace(
                'managed_launch = ["agent"]',
                'managed_launch = ["agent"]\nmanaged_join = ["agent"]',
                1,
            ),
        )


def test_pack_resolver_deduplicates_both_packs_in_first_occurrence_order() -> None:
    """Overlapping static members occur once when both packs are selected."""

    manifest = load_system_skill_manifest()
    records = resolve_system_skill_pack_members(manifest, pack_ids=("admin", "agent", "admin"))

    assert tuple(record.name for record in records) == (
        *ADMIN_MEMBERS,
        "houmao-agent-entrypoint",
    )
    assert resolve_system_skill_pack_selection(
        manifest,
        pack_ids=("agent", "agent"),
    ) == ("agent",)
    with pytest.raises(SystemSkillManifestError, match="not a pack selector"):
        resolve_system_skill_pack_selection(
            manifest,
            pack_ids=("houmao-shared-routines",),
        )


def test_exact_skill_discovery_returns_standalone_roots_and_declared_children() -> None:
    """Packaged entrypoints mirror the public and shared manifest layout."""

    manifest = load_system_skill_manifest()
    standalone_roots = [
        ASSET_ROOT / record.source_path for record in manifest.standalone_skills.values()
    ]
    child_roots = {
        routine_id: ASSET_ROOT / record.source_path
        for routine_id, record in manifest.shared_routines.items()
    }

    assert set(PUBLIC_ROOT.rglob("SKILL.md")) == {root / "SKILL.md" for root in standalone_roots}
    assert set(PUBLIC_ROOT.rglob("SKILL-MAIN.md")) == {
        root / "SKILL-MAIN.md" for root in child_roots.values()
    }
    for root in (*standalone_roots, *child_roots.values()):
        assert (root / "agents/openai.yaml").is_file()
    for routine_id, references in (
        ("houmao-agent-access", ("access-scope.md",)),
        ("houmao-agent-files", ("mount-scope.md", "receipts.md")),
    ):
        root = child_roots[routine_id]
        for command in manifest.shared_routines[routine_id].commands:
            if command != "help":
                assert (root / "commands" / f"{command}.md").is_file()
        for reference in references:
            assert (root / "references" / reference).is_file()
    assert not (ASSET_ROOT / "protected").exists()


def test_system_skill_references_use_static_siblings() -> None:
    """Reference helpers keep loops top-level and ordinary routines parent-qualified."""

    assert system_skill_reference_for_name("houmao-agent-loop-pro") == "houmao-agent-loop-pro"
    assert system_skill_reference_for_name("houmao-agent-inspect") == (
        "houmao-shared-routines->houmao-agent-inspect"
    )
    assert system_skill_reference_for_name("houmao-specialist-mgr") == (
        "houmao-shared-routines->houmao-agent-definition"
    )


def test_copy_staging_is_byte_identical_and_symlink_staging_is_direct(tmp_path: Path) -> None:
    """Admin, agent, and combined staging copy bytes or directly link source roots."""

    manifest = load_system_skill_manifest()
    selections = (
        (("admin",), ADMIN_MEMBERS),
        (("agent",), AGENT_MEMBERS),
        (("admin", "agent"), EXPECTED_STANDALONE_SKILL_NAMES),
    )
    for pack_ids, expected_names in selections:
        label = "-".join(pack_ids)
        copied = stage_system_skill_collection(
            manifest,
            pack_ids=pack_ids,
            destination_root=tmp_path / f"copied-{label}",
            projection_mode="copy",
        )
        assert len(copied.skills) == len(expected_names)
        assert {staged.name for staged in copied.skills} == set(expected_names)
        for staged in copied.skills:
            source = PUBLIC_ROOT / staged.name
            assert not staged.path.is_symlink()
            assert tree_content_digest(staged.path) == tree_content_digest(source)

        linked = stage_system_skill_collection(
            manifest,
            pack_ids=pack_ids,
            destination_root=tmp_path / f"linked-{label}",
            projection_mode="symlink",
        )
        assert len(linked.skills) == len(expected_names)
        assert {staged.name for staged in linked.skills} == set(expected_names)
        for staged in linked.skills:
            assert staged.path.is_symlink()
            assert staged.path.resolve() == (PUBLIC_ROOT / staged.name).resolve()


def test_project_pack_to_destination_copies_all_static_agent_members(tmp_path: Path) -> None:
    """Explicit projection is a normal complete-directory copy."""

    names = project_system_skills_to_destination(tmp_path / "skills", pack_id="agent")

    assert names == AGENT_MEMBERS
    assert all((tmp_path / "skills" / name / "SKILL.md").is_file() for name in names)


def test_install_both_packs_records_shared_owner_sets_once(tmp_path: Path) -> None:
    """One config record owns each deduplicated top-level destination."""

    result = install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("admin", "agent"),
    )
    inspection = inspect_system_skill_config(tool="codex", home_path=tmp_path)

    assert result.selected_pack_ids == ("admin", "agent")
    assert len(result.standalone_skill_names) == 6
    assert result.owning_pack_ids_by_skill["houmao-shared-routines"] == (
        "admin",
        "agent",
    )
    assert inspection.status == "current"
    assert inspection.config is not None
    assert inspection.config.selected_pack_ids == ("admin", "agent")
    assert len(inspection.config.skills) == 6
    assert set(inspection.config.to_payload()) == {
        "schema_version",
        "houmao_version",
        "projection_mode",
        "skills",
    }
    assert all(
        set(record.to_payload()) == {"name", "relative_path", "content_digest", "owning_pack_ids"}
        for record in inspection.config.skills
    )
    assert "selected_packs" not in inspection.config.to_payload()
    assert all((tmp_path / "skills" / name).is_dir() for name in EXPECTED_STANDALONE_SKILL_NAMES)


def test_symlink_install_targets_source_without_materialization(tmp_path: Path) -> None:
    """Symlink mode has no config-owned hidden copy tree."""

    install_system_skill_packs_for_home(
        tool="kimi",
        home_path=tmp_path,
        pack_ids=("agent",),
        projection_mode="symlink",
    )

    for name in AGENT_MEMBERS:
        target = tmp_path / "skills" / name
        assert target.is_symlink()
        assert target.resolve() == (PUBLIC_ROOT / name).resolve()
    assert not (tmp_path / ".houmao/system-skills/kimi/materialized").exists()


def test_install_collision_fails_before_projection_or_config(tmp_path: Path) -> None:
    """An untracked same-name destination blocks the complete transaction."""

    collision = tmp_path / "skills/houmao-shared-routines"
    collision.mkdir(parents=True)
    (collision / "user.txt").write_text("mine", encoding="utf-8")

    with pytest.raises(SystemSkillInstallError, match="Untracked.*collision"):
        install_system_skill_packs_for_home(
            tool="codex",
            home_path=tmp_path,
            pack_ids=("agent",),
        )

    assert (collision / "user.txt").read_text(encoding="utf-8") == "mine"
    assert not (tmp_path / "skills/houmao-agent-entrypoint").exists()
    assert inspect_system_skill_config(tool="codex", home_path=tmp_path).status == "absent"


def test_install_blocks_drift_but_explicit_sync_repairs_it(tmp_path: Path) -> None:
    """Additive install preserves drift while managed sync explicitly replaces it."""

    install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("agent",),
    )
    drifted = tmp_path / "skills/houmao-shared-routines/SKILL.md"
    drifted.write_text(drifted.read_text(encoding="utf-8") + "\nmodified\n", encoding="utf-8")

    with pytest.raises(SystemSkillInstallError, match="drifted"):
        install_system_skill_packs_for_home(
            tool="codex",
            home_path=tmp_path,
            pack_ids=("admin",),
        )
    repaired = sync_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        selected_pack_ids=("agent",),
    )

    assert repaired.selected_pack_ids == ("agent",)
    assert "modified" not in drifted.read_text(encoding="utf-8")
    assert inspect_system_skill_packs(tool="codex", home_path=tmp_path).packs[1].status == (
        "complete"
    )


def test_status_detects_missing_shared_child_as_incomplete(tmp_path: Path) -> None:
    """Shared-routines integrity includes the declared parent-scoped children."""

    install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("agent",),
    )
    shutil.rmtree(
        tmp_path / "skills/houmao-shared-routines/subskills/houmao-process-emails-via-gateway"
    )
    status = inspect_system_skill_packs(tool="codex", home_path=tmp_path)

    shared = next(
        record for record in status.members if record.name == SYSTEM_SKILL_SHARED_ROUTINES
    )
    agent = next(record for record in status.packs if record.pack_id == SYSTEM_SKILL_PACK_AGENT)
    assert shared.status == "incomplete"
    assert agent.status == "incomplete"


def test_status_detects_packaged_source_digest_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A config from older static source reports drift even when its copy is untouched."""

    install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("agent",),
    )
    packaged_digest = lifecycle_module.standalone_system_skill_content_digest

    def changed_digest(
        manifest: SystemSkillManifest,
        record: StandaloneSystemSkillRecord,
    ) -> str:
        if record.name == "houmao-agent-entrypoint":
            return "0" * 64
        return packaged_digest(manifest, record)

    monkeypatch.setattr(
        lifecycle_module,
        "standalone_system_skill_content_digest",
        changed_digest,
    )
    status = inspect_system_skill_packs(tool="codex", home_path=tmp_path)

    entrypoint = next(
        record for record in status.members if record.name == "houmao-agent-entrypoint"
    )
    agent = next(record for record in status.packs if record.pack_id == SYSTEM_SKILL_PACK_AGENT)
    assert entrypoint.status == "drifted"
    assert agent.status == "drifted"


def test_mode_change_replaces_the_whole_owned_union_transactionally(tmp_path: Path) -> None:
    """One config-owned collection never mixes copy and symlink projections."""

    install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("admin",),
        projection_mode="copy",
    )
    result = install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("agent",),
        projection_mode="symlink",
    )
    config = inspect_system_skill_config(tool="codex", home_path=tmp_path).config

    assert result.selected_pack_ids == ("admin", "agent")
    assert config is not None
    assert config.projection_mode == "symlink"
    assert all("projection_mode" not in record.to_payload() for record in config.skills)
    assert all((tmp_path / record.relative_path).is_symlink() for record in config.skills)


def test_uninstall_subtracts_owners_and_removes_only_last_owner(tmp_path: Path) -> None:
    """Removing admin preserves the three members still owned by agent."""

    install_system_skill_packs_for_home(
        tool="claude",
        home_path=tmp_path,
        pack_ids=("admin", "agent"),
    )
    result = uninstall_system_skill_packs_for_home(
        tool="claude",
        home_path=tmp_path,
        pack_ids=("admin",),
    )
    config = inspect_system_skill_config(tool="claude", home_path=tmp_path).config

    assert result.removed_pack_ids == ("admin",)
    assert result.retained_shared_skill_names == (
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    )
    assert not (tmp_path / "skills/houmao-admin-welcome").exists()
    assert not (tmp_path / "skills/houmao-admin-entrypoint").exists()
    assert all((tmp_path / "skills" / name).exists() for name in AGENT_MEMBERS)
    assert config is not None
    assert config.selected_pack_ids == ("agent",)


def test_uninstall_preserves_modified_final_owner_as_untracked_conflict(tmp_path: Path) -> None:
    """A modified final-owner destination is never deleted."""

    install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("agent",),
    )
    skill = tmp_path / "skills/houmao-agent-entrypoint/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nuser edit\n", encoding="utf-8")
    result = uninstall_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("agent",),
    )

    assert "skills/houmao-agent-entrypoint" in result.preserved_conflicting_paths
    assert skill.is_file()
    assert inspect_system_skill_config(tool="codex", home_path=tmp_path).status == "absent"


def test_transaction_rolls_back_paths_and_config_when_config_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Config-last failure restores the prior complete static collection."""

    install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("admin",),
    )
    config_path = tmp_path / ".houmao/system-skills/codex/houmao-skill-config.json"
    config_before = config_path.read_bytes()

    def fail_config(_config: object) -> None:
        raise OSError("injected config failure")

    monkeypatch.setattr(lifecycle_module, "_persist_config_atomic", fail_config)
    with pytest.raises(OSError, match="injected"):
        sync_system_skill_packs_for_home(
            tool="codex",
            home_path=tmp_path,
            selected_pack_ids=("agent",),
        )

    assert config_path.read_bytes() == config_before
    assert all((tmp_path / "skills" / name).is_dir() for name in ADMIN_MEMBERS)
    assert not (tmp_path / "skills/houmao-agent-entrypoint").exists()


def test_old_receipt_without_roots_is_ignored(tmp_path: Path) -> None:
    """The breaking lifecycle neither reads nor removes a generic old receipt."""

    receipt_path = tmp_path / ".houmao/system-skills/codex/receipt.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text("{not even valid json\n", encoding="utf-8")

    inspection = inspect_system_skill_config(tool="codex", home_path=tmp_path)
    status = inspect_system_skill_packs(tool="codex", home_path=tmp_path)

    assert inspection.status == "absent"
    assert status.config.status == "absent"
    assert receipt_path.read_text(encoding="utf-8") == "{not even valid json\n"


def test_old_receipt_does_not_authorize_overwriting_old_roots(tmp_path: Path) -> None:
    """Old projected roots remain unowned collisions even beside an old receipt."""

    receipt_path = tmp_path / ".houmao/system-skills/codex/receipt.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text("{}\n", encoding="utf-8")
    old_root = tmp_path / "skills/houmao-agent-entrypoint"
    old_root.parent.mkdir(parents=True)
    shutil.copytree(PUBLIC_ROOT / "houmao-agent-entrypoint", old_root)

    with pytest.raises(SystemSkillInstallError, match="Untracked.*collision"):
        install_system_skill_packs_for_home(
            tool="codex",
            home_path=tmp_path,
            pack_ids=("agent",),
        )

    assert old_root.is_dir()
    assert receipt_path.is_file()
    assert inspect_system_skill_config(tool="codex", home_path=tmp_path).status == "absent"


def test_config_inspection_is_strict_and_classifies_unsupported_schema(tmp_path: Path) -> None:
    """Malformed minimal fields are corrupt while future schemas are unsupported."""

    install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=("agent",),
    )
    config_path = tmp_path / ".houmao/system-skills/codex/houmao-skill-config.json"
    original = json.loads(config_path.read_text(encoding="utf-8"))

    invalid_payloads: list[dict[str, object]] = []
    with_extra = json.loads(json.dumps(original))
    with_extra["selected_packs"] = ["agent"]
    invalid_payloads.append(with_extra)
    missing_version = json.loads(json.dumps(original))
    del missing_version["houmao_version"]
    invalid_payloads.append(missing_version)
    missing_schema = json.loads(json.dumps(original))
    del missing_schema["schema_version"]
    invalid_payloads.append(missing_schema)
    record_extra = json.loads(json.dumps(original))
    record_extra["skills"][0]["role"] = "entrypoint"
    invalid_payloads.append(record_extra)
    unsafe_path = json.loads(json.dumps(original))
    unsafe_path["skills"][0]["relative_path"] = "../escape"
    invalid_payloads.append(unsafe_path)
    empty_owners = json.loads(json.dumps(original))
    empty_owners["skills"][0]["owning_pack_ids"] = []
    invalid_payloads.append(empty_owners)

    for payload in invalid_payloads:
        config_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        assert inspect_system_skill_config(tool="codex", home_path=tmp_path).status == "corrupt"

    config_path.write_text(
        json.dumps({"schema_version": "houmao-skill-config.v99"}) + "\n",
        encoding="utf-8",
    )
    assert inspect_system_skill_config(tool="codex", home_path=tmp_path).status == "unsupported"


def test_managed_policy_defaults_to_complete_four_member_agent_pack() -> None:
    """Omitted managed policy resolves the full static agent pack."""

    default = resolve_managed_system_skill_selection()
    disabled = resolve_managed_system_skill_selection(
        profile_policy=SystemSkillSelectionPolicy(mode="none")
    )

    assert default.selected_pack_ids == (SYSTEM_SKILL_PACK_AGENT,)
    assert default.resolved_standalone_skill_names == AGENT_MEMBERS
    assert disabled.selected_pack_ids == ()
    assert disabled.resolved_standalone_skill_names == ()


def test_install_result_agent_entrypoint_and_shared_are_top_level_siblings(tmp_path: Path) -> None:
    """The complete managed pack never creates entrypoint-local shared content."""

    result = install_system_skill_packs_for_home(
        tool="codex",
        home_path=tmp_path,
        pack_ids=(SYSTEM_SKILL_PACK_AGENT,),
    )

    assert result.standalone_skill_names == AGENT_MEMBERS
    assert (tmp_path / "skills" / SYSTEM_SKILL_AGENT_ENTRYPOINT / "SKILL.md").is_file()
    assert (tmp_path / "skills" / SYSTEM_SKILL_SHARED_ROUTINES / "SKILL.md").is_file()
    assert not (
        tmp_path / "skills" / SYSTEM_SKILL_AGENT_ENTRYPOINT / "subskills/houmao-shared-routines"
    ).exists()


def test_installed_hermes_mail_routes_preserve_actor_frame_and_parent_lookup(
    tmp_path: Path,
) -> None:
    """Hermes finds public roots and loads only the routed protected child."""

    install_system_skill_packs_for_home(
        tool="hermes", home_path=tmp_path, pack_ids=(SYSTEM_SKILL_PACK_AGENT,)
    )
    skills = tmp_path / "skills"
    entrypoint = (skills / SYSTEM_SKILL_AGENT_ENTRYPOINT / "SKILL.md").read_text()
    shared = skills / SYSTEM_SKILL_SHARED_ROUTINES
    shared_prompt = (shared / "SKILL.md").read_text()
    assert entrypoint.index("Verify fresh managed self") < entrypoint.index(
        'skill_view(name="houmao-shared-routines")'
    )
    assert "Pass the intact actor frame" in entrypoint
    assert "supplied gateway URL, channel, and expected binding ID" in entrypoint
    assert "After the actor and target checks" in shared_prompt
    assert 'with `name="houmao-shared-routines"`' in shared_prompt
    assert "selected route's linked child path as `file_path`" in shared_prompt
    for child in ("houmao-process-emails-via-gateway", "houmao-agent-email-comms"):
        relative_child = f"subskills/{child}/SKILL-MAIN.md"
        assert relative_child in shared_prompt
        assert (shared / relative_child).is_file()
        assert not (skills / child).exists()
