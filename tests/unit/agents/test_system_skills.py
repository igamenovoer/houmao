from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.agents.system_skills import (
    SYSTEM_SKILL_STATE_SCHEMA_VERSION,
    SYSTEM_SKILL_SET_MAILBOX_FULL,
    SYSTEM_SKILL_SET_PROJECT_EASY,
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
        "houmao-create-specialist",
    )
    assert tuple(catalog.sets.keys()) == ("mailbox-core", "mailbox-full", "project-easy")
    assert catalog.auto_install.managed_launch_sets == (
        SYSTEM_SKILL_SET_MAILBOX_FULL,
        SYSTEM_SKILL_SET_PROJECT_EASY,
    )
    assert catalog.auto_install.managed_join_sets == (
        SYSTEM_SKILL_SET_MAILBOX_FULL,
        SYSTEM_SKILL_SET_PROJECT_EASY,
    )
    assert catalog.auto_install.cli_default_sets == (
        SYSTEM_SKILL_SET_MAILBOX_FULL,
        SYSTEM_SKILL_SET_PROJECT_EASY,
    )


def test_resolve_system_skill_selection_dedupes_sets_and_explicit_skills() -> None:
    catalog = load_system_skill_catalog()

    resolved = resolve_system_skill_selection(
        catalog,
        set_names=("mailbox-core", "mailbox-full", "project-easy"),
        skill_names=("houmao-email-via-filesystem", "houmao-create-specialist"),
    )

    assert resolved == (
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-email-via-filesystem",
        "houmao-email-via-stalwart",
        "houmao-create-specialist",
    )
    assert resolve_auto_install_skill_selection(catalog, kind="managed_launch") == resolved


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
        set_names=("mailbox-core", "project-easy"),
        skill_names=("houmao-email-via-filesystem",),
    )

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    create_specialist_path = home_path / "skills/houmao-create-specialist/SKILL.md"
    create_specialist_references = home_path / "skills/houmao-create-specialist/references"

    assert result.resolved_skill_names == (
        "houmao-process-emails-via-gateway",
        "houmao-email-via-agent-gateway",
        "houmao-create-specialist",
        "houmao-email-via-filesystem",
    )
    assert state is not None
    assert tuple(record.name for record in state.installed_skills) == result.resolved_skill_names
    assert user_skill_path.is_file()
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-email-via-agent-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-email-via-filesystem/SKILL.md").is_file()
    assert create_specialist_path.is_file()
    create_specialist_skill = create_specialist_path.read_text(encoding="utf-8")
    assert ".venv/bin/houmao-mgr" in create_specialist_skill
    assert "pixi run houmao-mgr" in create_specialist_skill
    assert "uv run houmao-mgr" in create_specialist_skill
    assert "globally installed `houmao-mgr` from uv tools" in create_specialist_skill
    assert "Explicit Auth Mode" in create_specialist_skill
    assert "Env Lookup Mode" in create_specialist_skill
    assert "Directory Scan Mode" in create_specialist_skill
    assert "auto credentials" in create_specialist_skill
    assert "No Discovery Mode" in create_specialist_skill
    assert "references/claude-credential-lookup.md" in create_specialist_skill
    assert "references/codex-credential-lookup.md" in create_specialist_skill
    assert "references/gemini-credential-lookup.md" in create_specialist_skill
    assert "--claude-oauth-token" in create_specialist_skill
    assert "--claude-config-dir" in create_specialist_skill
    assert "optional bootstrap state" in create_specialist_skill
    assert "not a credential-providing method" in create_specialist_skill
    assert "do not scan env vars, directories, repo-local tool homes" in create_specialist_skill
    assert "tests/fixtures/agents" not in create_specialist_skill

    claude_reference_path = create_specialist_references / "claude-credential-lookup.md"
    codex_reference_path = create_specialist_references / "codex-credential-lookup.md"
    gemini_reference_path = create_specialist_references / "gemini-credential-lookup.md"
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
    assert "do not treat `.credentials.json` or `~/.claude.json` as directly importable specialist inputs" not in claude_reference
    assert "tests/fixtures/agents" not in claude_reference

    assert "CODEX_HOME" in codex_reference
    assert "auth.json" in codex_reference
    assert 'requires_openai_auth = false' in codex_reference
    assert 'wire_api = "responses"' in codex_reference
    assert "tests/fixtures/agents" not in codex_reference

    assert "GEMINI_CLI_HOME" in gemini_reference
    assert "oauth_creds.json" in gemini_reference
    assert "GOOGLE_APPLICATION_CREDENTIALS" in gemini_reference
    assert "tests/fixtures/agents" not in gemini_reference


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


def test_install_system_skills_for_home_migrates_previous_owned_family_paths(tmp_path: Path) -> None:
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
        skill_names=("houmao-process-emails-via-gateway", "houmao-create-specialist"),
    )

    assert result.projected_relative_dirs == (
        "skills/houmao-process-emails-via-gateway",
        "skills/houmao-create-specialist",
    )
    assert (home_path / "skills/houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (home_path / "skills/houmao-create-specialist/SKILL.md").is_file()
    assert not (home_path / "skills/mailbox/houmao-process-emails-via-gateway").exists()
    assert not (home_path / "skills/project/houmao-create-specialist").exists()
    assert not (home_path / "skills/mailbox").exists()
    assert not (home_path / "skills/project").exists()

    state = load_system_skill_install_state(tool="codex", home_path=home_path)
    assert state is not None
    assert tuple(record.projected_relative_dir for record in state.installed_skills) == (
        "skills/houmao-process-emails-via-gateway",
        "skills/houmao-create-specialist",
    )
