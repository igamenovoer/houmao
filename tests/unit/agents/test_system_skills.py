from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.system_skills import (
    SYSTEM_SKILL_SET_MAILBOX_FULL,
    SystemSkillCatalogError,
    SystemSkillInstallError,
    install_system_skills_for_home,
    load_system_skill_catalog,
    load_system_skill_catalog_from_paths,
    load_system_skill_install_state,
    resolve_auto_install_skill_selection,
    resolve_system_skill_selection,
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
    )
    assert tuple(catalog.sets.keys()) == ("mailbox-core", "mailbox-full")
    assert catalog.auto_install.managed_launch_sets == (SYSTEM_SKILL_SET_MAILBOX_FULL,)
    assert catalog.auto_install.managed_join_sets == (SYSTEM_SKILL_SET_MAILBOX_FULL,)
    assert catalog.auto_install.cli_default_sets == (SYSTEM_SKILL_SET_MAILBOX_FULL,)


def test_resolve_system_skill_selection_dedupes_sets_and_explicit_skills() -> None:
    catalog = load_system_skill_catalog()

    resolved = resolve_system_skill_selection(
        catalog,
        set_names=("mailbox-core", "mailbox-full"),
        skill_names=("houmao-email-via-filesystem",),
    )

    assert resolved == (
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-email-via-filesystem",
        "houmao-email-via-stalwart",
    )
    assert resolve_auto_install_skill_selection(catalog, kind="managed_launch") == resolved


def test_load_system_skill_catalog_rejects_unknown_set_member(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.toml"
    _write(
        catalog_path,
        """
schema_version = 1

[skills.houmao-email-via-agent-gateway]
asset_subpath = "mailbox/houmao-email-via-agent-gateway"

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
        set_names=("mailbox-core",),
        skill_names=("houmao-email-via-filesystem",),
    )

    state = load_system_skill_install_state(tool="codex", home_path=home_path)

    assert result.resolved_skill_names == (
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-email-via-filesystem",
    )
    assert state is not None
    assert tuple(record.name for record in state.installed_skills) == result.resolved_skill_names
    assert user_skill_path.is_file()
    assert (home_path / "skills/mailbox/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/mailbox/houmao-email-via-agent-gateway/SKILL.md").is_file()
    assert (home_path / "skills/mailbox/houmao-email-via-filesystem/SKILL.md").is_file()


def test_install_system_skills_for_home_rejects_non_owned_collision(tmp_path: Path) -> None:
    home_path = (tmp_path / "codex-home").resolve()
    conflicting_skill_path = home_path / "skills/mailbox/houmao-email-via-agent-gateway/SKILL.md"
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
