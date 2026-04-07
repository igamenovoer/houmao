from __future__ import annotations

import sqlite3
from pathlib import Path

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

    connection = sqlite3.connect(overlay.catalog_path)
    try:
        specialist_row = connection.execute(
            "SELECT specialist_name, prompt_relative_path, auth_relative_path FROM v_specialists"
        ).fetchone()
        assert specialist_row == (
            "researcher",
            "prompts/researcher.md",
            "auth/codex/researcher-creds",
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


def test_project_catalog_imports_legacy_specialist_metadata(
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
    specialist = catalog.load_specialist("researcher")

    assert specialist.name == "researcher"
    assert specialist.tool == "codex"
    assert specialist.preset_name == "researcher-codex-default"
    assert specialist.credential_name == "legacy-creds"
    assert specialist.skills == ("notes",)
    assert specialist.prompt_ref.resolve(overlay).is_file()
    assert specialist.auth_ref.resolve(overlay).is_dir()


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

    profile = catalog.store_launch_profile(
        name="alice",
        profile_lane="launch_profile",
        source_kind="recipe",
        source_name="researcher-codex-default",
        managed_agent_name="alice",
        managed_agent_id="agent-alice",
        workdir="/repos/alice",
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
        managed_header_policy="inherit",
        prompt_overlay_mode="append",
        prompt_overlay_text="Prefer Alice repository conventions.",
    )

    assert profile.name == "alice"
    assert profile.source_name == "researcher-codex-default"
    assert profile.prompt_overlay_ref is not None

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
            "prompt_overlay": {
                "mode": "append",
                "text": "Prefer Alice repository conventions.",
            },
        },
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
                prompt_overlay_mode
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
            "append",
        )
    finally:
        connection.close()

    report = catalog.validate_integrity()
    assert report.missing_content == ()

    assert profile.prompt_overlay_ref is not None
    profile.prompt_overlay_ref.resolve(overlay).unlink()
    degraded = catalog.validate_integrity()
    assert degraded.missing_content == ("prompts/launch-profiles/alice.md",)
