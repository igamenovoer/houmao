from __future__ import annotations

import sqlite3
from pathlib import Path
import shutil

from click.testing import CliRunner
import pytest
import yaml

from houmao.project.catalog import ProjectCatalog
from houmao.project.overlay import (
    bootstrap_project_overlay,
    ensure_project_agent_compatibility_tree,
    require_project_overlay,
)
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


def test_project_catalog_exposes_sql_views_and_integrity_checks(
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

    overlay = require_project_overlay(repo_root)
    catalog = ProjectCatalog.from_overlay(overlay)
    report = catalog.validate_integrity()
    assert report.missing_content == ()
    auth_profile = catalog.load_auth_profile(tool="codex", name="researcher-creds")

    connection = sqlite3.connect(overlay.catalog_path)
    try:
        specialist_row = connection.execute(
            "SELECT specialist_name, prompt_relative_path, auth_relative_path FROM v_specialists"
        ).fetchone()
        assert specialist_row == (
            "researcher",
            "prompts/researcher.md",
            auth_profile.content_ref.relative_path,
        )
        preset_row = connection.execute(
            "SELECT preset_name, role_name, tool, setup_name, auth_name FROM v_presets"
        ).fetchone()
        assert preset_row == (
            "researcher-codex-default",
            "researcher",
            "codex",
            "default",
            "researcher-creds",
        )
    finally:
        connection.close()

    (overlay.content_root / "prompts" / "researcher.md").unlink()
    degraded = catalog.validate_integrity()
    assert degraded.missing_content == ("prompts/researcher.md",)


def test_project_catalog_does_not_import_legacy_specialist_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    bootstrap_project_overlay(repo_root)
    overlay = require_project_overlay(repo_root)
    ensure_project_agent_compatibility_tree(overlay)

    role_root = overlay.agents_root / "roles" / "researcher"
    role_root.mkdir(parents=True, exist_ok=True)
    (role_root / "system-prompt.md").write_text("Legacy prompt\n", encoding="utf-8")
    preset_root = overlay.agents_root / "presets"
    preset_root.mkdir(parents=True, exist_ok=True)
    (preset_root / "researcher-codex-default.yaml").write_text(
        "\n".join(
            [
                "role: researcher",
                "tool: codex",
                "setup: default",
                "skills: [notes]",
                "auth: legacy-creds",
                "",
            ]
        ),
        encoding="utf-8",
    )

    auth_root = overlay.agents_root / "tools" / "codex" / "auth" / "legacy-creds"
    (auth_root / "env").mkdir(parents=True, exist_ok=True)
    (auth_root / "files").mkdir(parents=True, exist_ok=True)
    (auth_root / "env" / "vars.env").write_text("OPENAI_API_KEY=sk-openai\n", encoding="utf-8")
    (auth_root / "files" / "auth.json").write_text('{"logged_in": true}\n', encoding="utf-8")

    skill_root = overlay.agents_root / "skills" / "notes"
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# notes\n\nLegacy notes.\n", encoding="utf-8")

    overlay.specialists_root.mkdir(parents=True, exist_ok=True)
    (overlay.specialists_root / "researcher.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                'name = "researcher"',
                'tool = "codex"',
                'provider = "codex"',
                'credential_name = "legacy-creds"',
                'role_name = "researcher"',
                'system_prompt_path = "agents/roles/researcher/system-prompt.md"',
                'preset_path = "agents/presets/researcher-codex-default.yaml"',
                'auth_path = "agents/tools/codex/auth/legacy-creds"',
                'skills = ["notes"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    catalog = ProjectCatalog.from_overlay(overlay)
    assert catalog.list_specialists() == []
    with pytest.raises(FileNotFoundError, match="Specialist `researcher` was not found"):
        catalog.load_specialist("researcher")


def test_project_catalog_persists_and_projects_launch_profiles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    bootstrap_project_overlay(repo_root)
    overlay = require_project_overlay(repo_root)
    catalog = ProjectCatalog.from_overlay(overlay)
    auth_source = (tmp_path / "alice-creds").resolve()
    (auth_source / "env").mkdir(parents=True, exist_ok=True)
    (auth_source / "files").mkdir(parents=True, exist_ok=True)
    (auth_source / "env" / "vars.env").write_text("OPENAI_API_KEY=sk-openai\n", encoding="utf-8")
    (auth_source / "files" / "auth.json").write_text('{"logged_in": true}\n', encoding="utf-8")
    catalog.create_auth_profile_from_source(
        tool="codex",
        display_name="alice-creds",
        source_path=auth_source,
    )
    memo_seed_dir = (tmp_path / "memo-seed").resolve()
    memo_seed_dir.mkdir(parents=True, exist_ok=True)
    (memo_seed_dir / "houmao-memo.md").write_text(
        "Read pages/review.md before you begin.\n",
        encoding="utf-8",
    )
    (memo_seed_dir / "pages" / "review.md").parent.mkdir(parents=True, exist_ok=True)
    (memo_seed_dir / "pages" / "review.md").write_text(
        "Review checklist.\n",
        encoding="utf-8",
    )

    profile = catalog.store_launch_profile(
        name="alice",
        profile_lane="launch_profile",
        source_kind="recipe",
        source_name="researcher-codex-default",
        managed_agent_name="alice",
        managed_agent_id="agent-alice",
        workdir="/repos/alice",
        auth_tool="codex",
        auth_name="alice-creds",
        model_name="gpt-5.4-mini",
        reasoning_level=4,
        operator_prompt_mode="unattended",
        env_mapping={"OPENAI_BASE_URL": "https://api.example.test/v1"},
        mailbox_mapping={
            "transport": "filesystem",
            "principal_id": "alice",
            "address": "alice@agents.localhost",
            "filesystem_root": "/mail-root",
        },
        posture_mapping={"headless": True, "gateway_port": 9011},
        relaunch_chat_session_mapping={"mode": "tool_last_or_new"},
        managed_header_policy="inherit",
        managed_header_section_policy={
            "automation-notice": "disabled",
            "task-reminder": "enabled",
        },
        prompt_overlay_mode="append",
        prompt_overlay_text="Prefer Alice repository conventions.",
        gateway_mail_notifier_appendix_text="Prefer urgent legal mail before routine updates.",
        memo_seed_source_kind="tree",
        memo_seed_source_path=memo_seed_dir,
    )

    assert profile.name == "alice"
    assert profile.source_name == "researcher-codex-default"
    assert profile.prompt_overlay_ref is not None
    assert profile.gateway_mail_notifier_appendix_ref is not None
    assert profile.memo_seed is not None

    projection_root = catalog.materialize_projection()
    projection_path = projection_root / "launch-profiles" / "alice.yaml"
    assert projection_path.is_file()
    projection_payload = yaml.safe_load(projection_path.read_text(encoding="utf-8"))
    assert projection_payload == {
        "profile_lane": "launch_profile",
        "source": {"kind": "recipe", "name": "researcher-codex-default"},
        "defaults": {
            "agent_name": "alice",
            "agent_id": "agent-alice",
            "workdir": "/repos/alice",
            "auth": "alice-creds",
            "model": {
                "name": "gpt-5.4-mini",
                "reasoning": {"level": 4},
            },
            "prompt_mode": "unattended",
            "env": {"OPENAI_BASE_URL": "https://api.example.test/v1"},
            "mailbox": {
                "transport": "filesystem",
                "principal_id": "alice",
                "address": "alice@agents.localhost",
                "filesystem_root": "/mail-root",
            },
            "posture": {"headless": True, "gateway_port": 9011},
            "managed_header": "inherit",
            "managed_header_sections": {
                "automation-notice": "disabled",
                "task-reminder": "enabled",
            },
            "prompt_overlay": {
                "mode": "append",
                "text": "Prefer Alice repository conventions.",
            },
            "gateway_mail_notifier_appendix": {
                "text": "Prefer urgent legal mail before routine updates.",
            },
            "memo_seed": {
                "source_kind": "tree",
                "content_ref": {
                    "content_kind": "memo_seed",
                    "storage_kind": "tree",
                    "relative_path": "memo-seeds/launch-profiles/alice/seed",
                    "path": str(
                        (
                            repo_root
                            / ".houmao"
                            / "content"
                            / "memo-seeds"
                            / "launch-profiles"
                            / "alice"
                            / "seed"
                        ).resolve()
                    ),
                },
            },
        },
        "relaunch": {"chat_session": {"mode": "tool_last_or_new"}},
    }

    connection = sqlite3.connect(overlay.catalog_path)
    try:
        launch_profile_row = connection.execute(
            """
            SELECT
                launch_profile_name,
                profile_lane,
                source_kind,
                source_name,
                managed_agent_name,
                auth_name,
                model_name,
                reasoning_level,
                managed_header_policy,
                managed_header_section_policy,
                prompt_overlay_mode,
                gateway_mail_notifier_appendix_relative_path,
                relaunch_chat_session_payload,
                memo_seed_source_kind,
                memo_seed_relative_path
            FROM v_launch_profiles
            """
        ).fetchone()
        assert launch_profile_row == (
            "alice",
            "launch_profile",
            "recipe",
            "researcher-codex-default",
            "alice",
            "alice-creds",
            "gpt-5.4-mini",
            4,
            "inherit",
            '{"automation-notice": "disabled", "task-reminder": "enabled"}',
            "append",
            "prompts/launch-profiles/alice-mail-notifier-appendix.md",
            '{"mode": "tool_last_or_new"}',
            "tree",
            "memo-seeds/launch-profiles/alice/seed",
        )
    finally:
        connection.close()

    report = catalog.validate_integrity()
    assert report.missing_content == ()

    assert profile.prompt_overlay_ref is not None
    profile.prompt_overlay_ref.resolve(overlay).unlink()
    assert profile.gateway_mail_notifier_appendix_ref is not None
    profile.gateway_mail_notifier_appendix_ref.resolve(overlay).unlink()
    assert profile.memo_seed is not None
    shutil.rmtree(profile.memo_seed.content_ref.resolve(overlay))
    degraded = catalog.validate_integrity()
    assert degraded.missing_content == (
        "memo-seeds/launch-profiles/alice/seed",
        "prompts/launch-profiles/alice-mail-notifier-appendix.md",
        "prompts/launch-profiles/alice.md",
    )


@pytest.mark.parametrize(
    ("seed_setup", "expected_message"),
    [
        (
            lambda root: (root / "README.md").write_text("unsupported\n", encoding="utf-8"),
            "may contain only",
        ),
        (
            lambda root: (
                (root / "pages").mkdir(parents=True, exist_ok=True)
                or (root / "pages" / "bad.md").write_bytes(b"bad\x00content")
            ),
            "must not contain NUL bytes",
        ),
        (
            lambda root: (
                (root / "pages").mkdir(parents=True, exist_ok=True)
                or (root / "pages" / "bad.md").write_bytes(b"\xff\xfe")
            ),
            "must be valid UTF-8 text",
        ),
    ],
)
def test_project_catalog_rejects_invalid_memo_seed_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    seed_setup,
    expected_message: str,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    bootstrap_project_overlay(repo_root)
    overlay = require_project_overlay(repo_root)
    catalog = ProjectCatalog.from_overlay(overlay)
    seed_dir = (tmp_path / "invalid-seed").resolve()
    seed_dir.mkdir(parents=True, exist_ok=True)
    seed_setup(seed_dir)

    with pytest.raises(ValueError, match=expected_message):
        catalog.store_launch_profile(
            name="bad-seed",
            profile_lane="launch_profile",
            source_kind="recipe",
            source_name="researcher-codex-default",
            managed_agent_name=None,
            managed_agent_id=None,
            workdir=None,
            auth_tool=None,
            auth_name=None,
            model_name=None,
            reasoning_level=None,
            operator_prompt_mode=None,
            env_mapping={},
            mailbox_mapping=None,
            posture_mapping={},
            managed_header_policy="inherit",
            managed_header_section_policy={},
            prompt_overlay_mode=None,
            prompt_overlay_text=None,
            memo_seed_source_kind="tree",
            memo_seed_source_path=seed_dir,
        )


def test_project_catalog_rejects_unsupported_schema_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    bootstrap_project_overlay(repo_root)
    overlay = require_project_overlay(repo_root)
    catalog = ProjectCatalog.from_overlay(overlay)
    catalog.initialize()

    connection = sqlite3.connect(overlay.catalog_path)
    try:
        connection.execute("UPDATE catalog_meta SET value = '10' WHERE key = 'schema_version'")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="Recreate or reinitialize the project overlay"):
        catalog.initialize()


def test_project_catalog_rejects_obsolete_current_table_shape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    bootstrap_project_overlay(repo_root)
    overlay = require_project_overlay(repo_root)
    catalog = ProjectCatalog.from_overlay(overlay)
    catalog.initialize()

    connection = sqlite3.connect(overlay.catalog_path)
    try:
        connection.execute("ALTER TABLE launch_profiles ADD COLUMN memo_seed_policy TEXT")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="obsolete column"):
        catalog.initialize()


def test_project_catalog_rejects_obsolete_content_refs_check(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    bootstrap_project_overlay(repo_root)
    overlay = require_project_overlay(repo_root)
    catalog = ProjectCatalog.from_overlay(overlay)
    catalog.initialize()

    connection = sqlite3.connect(overlay.catalog_path)
    try:
        connection.executescript(
            """
            DROP VIEW IF EXISTS v_content_refs;
            DROP VIEW IF EXISTS v_roles;
            DROP VIEW IF EXISTS v_presets;
            DROP VIEW IF EXISTS v_specialists;
            DROP VIEW IF EXISTS v_launch_profiles;
            PRAGMA foreign_keys = OFF;
            CREATE TABLE content_refs_legacy_check (
                id INTEGER PRIMARY KEY,
                content_kind TEXT NOT NULL CHECK(
                    content_kind IN ('prompt_blob', 'auth_tree', 'skill_tree', 'setup_tree')
                ),
                storage_kind TEXT NOT NULL CHECK(storage_kind IN ('file', 'tree')),
                relative_path TEXT NOT NULL UNIQUE,
                sha256 TEXT,
                created_at TEXT NOT NULL
            );
            INSERT INTO content_refs_legacy_check (
                id,
                content_kind,
                storage_kind,
                relative_path,
                sha256,
                created_at
            )
            SELECT
                id,
                content_kind,
                storage_kind,
                relative_path,
                sha256,
                created_at
            FROM content_refs;
            DROP TABLE content_refs;
            ALTER TABLE content_refs_legacy_check RENAME TO content_refs;
            PRAGMA foreign_keys = ON;
            """
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="memo_seed content references"):
        catalog.initialize()
