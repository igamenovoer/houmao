"""Coverage for the v4 static Houmao system-skill collection."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import tomllib

import pytest

import houmao.agents.system_skill_lifecycle as lifecycle_module
from houmao.agents.system_skills import (
    EXPECTED_SHARED_ROUTINE_IDS,
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
SEMANTIC_FIXTURE_PATH = REPO_ROOT / "tests/fixtures/system-skills/semantic-preservation.v1.toml"
INVENTORY_FIXTURE_PATH = REPO_ROOT / "tests/fixtures/system-skills/pre-compaction-files.txt"

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


def _entrypoint_paths() -> tuple[Path, ...]:
    """Return all standalone and parent-scoped entrypoint paths."""

    return tuple(sorted(PUBLIC_ROOT.rglob("SKILL.md"))) + tuple(
        sorted(PUBLIC_ROOT.rglob("SKILL-MAIN.md"))
    )


def _workflow_body(text: str) -> str:
    """Return the Workflow section body from one executable page."""

    match = re.search(r"(?ms)^## Workflow\s*$\n(?P<body>.*?)(?=^## |\Z)", text)
    assert match is not None
    return match.group("body")


def test_manifest_v4_declares_exact_static_collection() -> None:
    """The manifest exposes the fixed six roots and sixteen owned children."""

    manifest = load_system_skill_manifest()

    assert manifest.schema_version == "houmao-system-skills.v4"
    assert manifest.standalone_skill_names == EXPECTED_STANDALONE_SKILL_NAMES
    assert set(manifest.shared_logical_ids) == set(EXPECTED_SHARED_ROUTINE_IDS)
    assert manifest.packs["admin"].standalone_skill_names == ADMIN_MEMBERS
    assert manifest.packs["agent"].standalone_skill_names == AGENT_MEMBERS
    assert manifest.defaults.cli == ("admin",)
    assert manifest.defaults.managed_launch == ("agent",)
    assert manifest.defaults.managed_join == ("agent",)
    assert manifest.auto_skill_name == "houmao-auto-system-prompt"
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


def test_actor_entrypoint_metadata_and_phase_contracts_match_activation_policy() -> None:
    """Only actor entrypoints are implicit and they classify before operational gates."""

    manifest = load_system_skill_manifest()
    for name, record in manifest.standalone_skills.items():
        metadata = (PUBLIC_ROOT / name / "agents/openai.yaml").read_text(encoding="utf-8")
        expected_value = "true" if record.activation == "narrow-implicit" else "false"
        assert f"allow_implicit_invocation: {expected_value}" in metadata

    admin = (PUBLIC_ROOT / "houmao-admin-entrypoint/SKILL.md").read_text(encoding="utf-8")
    agent = (PUBLIC_ROOT / "houmao-agent-entrypoint/SKILL.md").read_text(encoding="utf-8")
    welcome = (PUBLIC_ROOT / "houmao-admin-welcome/SKILL.md").read_text(encoding="utf-8")
    assert admin.index("**Classify intent before gates**") < admin.index(
        "**Establish the operational actor frame**"
    )
    assert agent.index("**Classify intent before gates**") < agent.index(
        "**Verify managed self for operational work**"
    )
    assert "DO NOT invoke or delegate to `$houmao-admin-welcome`" in admin
    assert (
        "DO NOT run managed-self identity verification for an informational-only response" in agent
    )
    assert "explicitly invokes $houmao-admin-welcome" in welcome


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
    """V4 schema does not accept any protected-mount declaration."""

    with pytest.raises(SystemSkillManifestError, match="Additional properties"):
        _load_modified_manifest(
            tmp_path,
            lambda text: text.replace(
                'auto_skill_name = "houmao-auto-system-prompt"',
                'auto_skill_name = "houmao-auto-system-prompt"\nprotected_mounts = []',
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


def test_exact_skill_discovery_returns_six_roots_and_no_children() -> None:
    """Exact SKILL.md discovery exposes only standalone roots."""

    discovered = tuple(sorted(path.parent.name for path in PUBLIC_ROOT.rglob("SKILL.md")))
    child_entrypoints = tuple(
        sorted(PUBLIC_ROOT.joinpath("houmao-shared-routines/subskills").rglob("SKILL-MAIN.md"))
    )

    assert discovered == tuple(sorted(EXPECTED_STANDALONE_SKILL_NAMES))
    assert len(child_entrypoints) == 16
    assert not any(path.with_name("SKILL.md").exists() for path in child_entrypoints)
    assert not (ASSET_ROOT / "protected").exists()


def test_static_source_has_complete_local_links_and_no_placeholders() -> None:
    """Loading the manifest validates links, roles, metadata, and placeholders in place."""

    manifest = load_system_skill_manifest()

    assert all((PUBLIC_ROOT / name / "SKILL.md").is_file() for name in manifest.skill_names)
    assert not any(
        "<public-entrypoint>" in path.read_text(encoding="utf-8")
        for path in PUBLIC_ROOT.rglob("*.md")
    )


def test_imsight_format_applies_to_entrypoints_and_command_pages() -> None:
    """Every executable page has workflow fallback and each entrypoint has DO NOT rules."""

    entrypoints = _entrypoint_paths()
    assert len(entrypoints) == 22
    for path in entrypoints:
        text = path.read_text(encoding="utf-8")
        assert re.search(r'(?m)^description:\s*["\']?Use when', text)
        assert "## Subcommands" in text
        workflow = _workflow_body(text)
        assert re.search(r"(?m)^1\. ", workflow)
        assert "native planning tool" in workflow
        guardrail_match = re.search(
            r"(?ms)^## Guardrails\s*$\n(?P<body>.*?)(?=^## |\Z)",
            text,
        )
        assert guardrail_match is not None
        bullets = re.findall(r"(?m)^- (.+)$", guardrail_match.group("body"))
        assert bullets
        assert all(item.startswith("DO NOT") for item in bullets)

    command_pages = tuple(sorted(PUBLIC_ROOT.glob("*/commands/**/*.md"))) + tuple(
        sorted(PUBLIC_ROOT.glob("*/subskills/*/commands/**/*.md"))
    )
    assert command_pages
    for path in command_pages:
        workflow = _workflow_body(path.read_text(encoding="utf-8"))
        assert re.search(r"(?m)^1\. ", workflow)
        assert "native planning tool" in workflow


def test_route_tables_cover_actor_eligibility_and_top_level_loops() -> None:
    """Admin, agent, and direct shared routers expose the fixed sibling matrix."""

    manifest = load_system_skill_manifest()
    admin = (PUBLIC_ROOT / "houmao-admin-entrypoint/SKILL.md").read_text(encoding="utf-8")
    agent = (PUBLIC_ROOT / "houmao-agent-entrypoint/SKILL.md").read_text(encoding="utf-8")
    shared = (PUBLIC_ROOT / "houmao-shared-routines/SKILL.md").read_text(encoding="utf-8")

    for routine in manifest.shared_routines.values():
        assert f"| `{routine.route_name}` |" in shared
        if "admin" in routine.audiences:
            assert f"| `{routine.route_name}` |" in admin
        if "agent" in routine.audiences:
            assert f"| `{routine.route_name}` |" in agent
    for text in (admin, agent, shared):
        assert "houmao-agent-loop-pro" in text
        assert "houmao-agent-loop-lite" in text
        assert "When to Route Here" in text
    assert "subskills/houmao-agent-loop-pro" not in shared
    assert "subskills/houmao-agent-loop-lite" not in shared
    assert "specialist-mgr" in admin
    assert "specialist-mgr" in shared
    assert "process-emails-via-gateway" in agent
    admin_subcommands = re.search(
        r"(?ms)^## Subcommands\s*$\n(?P<body>.*?)(?=^## |\Z)",
        admin,
    )
    assert admin_subcommands is not None
    assert "| `process-emails-via-gateway` |" not in admin_subcommands.group("body")


def test_semantic_preservation_fixture_matches_operations_aliases_and_help() -> None:
    """The checked-in semantic ledger remains represented by the v4 owners."""

    manifest = load_system_skill_manifest()
    fixture = tomllib.loads(SEMANTIC_FIXTURE_PATH.read_text(encoding="utf-8"))

    assert fixture["baseline_commit"] == "8f377c468bc7f87ff40dbf40c0a68327616112bd"
    assert len(INVENTORY_FIXTURE_PATH.read_text(encoding="utf-8").splitlines()) == 291
    assert len(fixture["skills"]) == 20
    for item in fixture["skills"]:
        source = item["source"]
        if source in {"houmao-agent-loop-pro", "houmao-agent-loop-lite"}:
            record = manifest.standalone_skills[source]
            target_root = PUBLIC_ROOT / source
        elif source == "houmao-touring":
            record = manifest.standalone_skills["houmao-admin-welcome"]
            target_root = PUBLIC_ROOT / "houmao-admin-welcome"
        elif source == "houmao-specialist-mgr":
            record = manifest.shared_routines["houmao-agent-definition"]
            target_root = PUBLIC_ROOT / "houmao-shared-routines/subskills/houmao-agent-definition"
        else:
            record = manifest.shared_routines[source]
            target_root = PUBLIC_ROOT / "houmao-shared-routines/subskills" / source
        assert set(item["operations"]).issubset(record.commands)
        assert set(item["aliases"]).issubset(record.aliases)
        if default_operation := item.get("default_operation"):
            assert default_operation in record.commands
        target_text = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(target_root.rglob("*.md"))
        ).lower()
        if default_operation:
            _assert_semantic_phrase_evidence(
                phrase=f"default {default_operation}",
                target_text=target_text,
                source=source,
                field="default_operation",
            )
        for phrase in item.get("default_behavior", []):
            _assert_semantic_phrase_evidence(
                phrase=phrase,
                target_text=target_text,
                source=source,
                field="default_behavior",
            )
        for field in (
            "activation",
            "inputs",
            "outputs",
            "gates",
            "blockers",
            "evidence_handoffs",
            "target_rules",
            "side_effects",
            "stop_conditions",
        ):
            raw_values = item[field]
            values = [raw_values] if isinstance(raw_values, str) else raw_values
            for phrase in values:
                _assert_semantic_phrase_evidence(
                    phrase=phrase,
                    target_text=target_text,
                    source=source,
                    field=field,
                )
        assert item["help_read_only"] is True
        assert "help" in record.commands


def _assert_semantic_phrase_evidence(
    *,
    phrase: str,
    target_text: str,
    source: str,
    field: str,
) -> None:
    """Require source-ledger concepts to remain visible in the reformatted owner."""

    stopwords = {
        "admin",
        "agent",
        "current",
        "explicit",
        "houmao",
        "only",
        "operation",
        "required",
        "result",
        "routine",
        "selected",
        "supported",
        "target",
        "through",
        "when",
        "with",
        "work",
        "workflow",
    }
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", phrase.lower())
        if len(token) >= 4 and token not in stopwords
    }
    if not tokens:
        tokens = {token for token in re.findall(r"[a-z0-9]+", phrase.lower()) if len(token) >= 4}
    equivalent_terms = {
        "recipient": {"recipient", "target"},
        "recipients": {"recipient", "target"},
    }
    evidence_terms = {
        equivalent
        for token in tokens
        for equivalent in equivalent_terms.get(token, {token, token.rstrip("s")})
    }
    assert any(term in target_text for term in evidence_terms), (
        f"{source} lacks {field} evidence for {phrase!r}; expected one of {sorted(tokens)}"
    )


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
    """Shared-routines integrity includes all sixteen parent-scoped children."""

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
