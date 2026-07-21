"""CLI coverage for actor-oriented system-skill packs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from click.testing import CliRunner
import pytest

from houmao.agents.system_skill_manifest import load_system_skill_manifest
from houmao.srv_ctrl.commands.main import cli
from houmao.version import get_version


def _invoke_json(*args: str) -> tuple[dict[str, object], str]:
    """Invoke the manager with JSON output and return its payload and output."""

    result = CliRunner().invoke(cli, ["--print-json", *args])
    assert result.exit_code == 0, result.output
    return json.loads(result.output), result.output


def _run_houmao_mgr_module(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the package module entrypoint in a fresh Python subprocess."""

    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    entries = [str(repo_root / "src")]
    if existing := env.get("PYTHONPATH"):
        entries.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    return subprocess.run(
        [sys.executable, "-m", "houmao.srv_ctrl", *args],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def test_system_skills_help_lists_pack_lifecycle_commands() -> None:
    result = CliRunner().invoke(cli, ["system-skills", "--help"])

    assert result.exit_code == 0
    for command in ("list", "install", "status", "upgrade", "uninstall"):
        assert command in result.output


def test_houmao_mgr_module_starts_with_version_and_system_skills_help() -> None:
    version = _run_houmao_mgr_module("--version")
    help_result = _run_houmao_mgr_module("system-skills", "--help")

    assert version.returncode == 0, version.stderr
    assert get_version() in version.stdout
    assert help_result.returncode == 0, help_result.stderr
    assert "upgrade" in help_result.stdout


def test_system_skills_install_help_exposes_only_pack_selection() -> None:
    result = CliRunner().invoke(cli, ["system-skills", "install", "--help"])

    assert result.exit_code == 0
    assert "--pack" in result.output
    assert "--skill" not in result.output
    assert "--set" not in result.output
    assert "claude" in result.output
    assert "codex" in result.output
    assert "copilot" in result.output
    assert "kimi" in result.output
    assert "universal" in result.output


def test_system_skills_list_reports_actor_packs_and_nested_protected_records() -> None:
    payload, _ = _invoke_json("system-skills", "list")

    packs = payload["packs"]
    assert isinstance(packs, list)
    assert [pack["pack_id"] for pack in packs] == ["admin", "agent"]
    assert [skill["name"] for pack in packs for skill in pack["public_skills"]] == [
        "houmao-admin-welcome",
        "houmao-admin-entrypoint",
        "houmao-agent-entrypoint",
    ]
    assert payload["defaults"] == {
        "cli": ["admin"],
        "managed_launch": ["agent"],
        "managed_join": ["agent"],
    }
    protected = payload["protected_routines"]
    assert isinstance(protected, list)
    assert len(protected) == 18
    assert all("invocation_designators" in record for record in protected)
    assert payload["auto_skill_separate"] == "houmao-auto-system-prompt"


def test_system_skills_install_defaults_to_admin_pack(tmp_path: Path) -> None:
    home = tmp_path / "codex-home"

    payload, _ = _invoke_json("system-skills", "install", "--tool", "codex", "--home", str(home))

    assert payload["selected_packs"] == ["admin"]
    assert payload["public_skills"] == [
        "houmao-admin-welcome",
        "houmao-admin-entrypoint",
    ]
    assert (home / "skills/houmao-admin-welcome/SKILL.md").is_file()
    entrypoint = home / "skills/houmao-admin-entrypoint"
    assert (entrypoint / "SKILL.md").is_file()
    shared = entrypoint / "subskills/houmao-shared-routines"
    assert (shared / "SKILL-MAIN.md").is_file()
    assert (shared / "subskills/houmao-project-mgr/SKILL-MAIN.md").is_file()
    assert not (shared / "subskills/houmao-process-emails-via-gateway").exists()
    assert not (home / "skills/houmao-project-mgr").exists()
    assert Path(str(payload["receipt_path"])).is_file()


@pytest.mark.parametrize("tool", ["claude", "codex", "copilot", "kimi", "universal"])
def test_system_skills_install_supports_each_target(tmp_path: Path, tool: str) -> None:
    home = tmp_path / tool

    payload, _ = _invoke_json(
        "system-skills",
        "install",
        "--tool",
        tool,
        "--home",
        str(home),
        "--pack",
        "agent",
    )

    assert payload["tool"] == tool
    assert payload["selected_packs"] == ["agent"]
    assert payload["public_skills"] == ["houmao-agent-entrypoint"]
    assert (home / "skills/houmao-agent-entrypoint/SKILL.md").is_file()


def test_system_skills_install_supports_both_packs_and_deduplicates(tmp_path: Path) -> None:
    home = tmp_path / "home"

    payload, _ = _invoke_json(
        "system-skills",
        "install",
        "--tool",
        "codex",
        "--home",
        str(home),
        "--pack",
        "agent",
        "--pack",
        "admin",
        "--pack",
        "agent",
    )

    assert payload["selected_packs"] == ["agent", "admin"]
    assert set(payload["public_skills"]) == {
        "houmao-agent-entrypoint",
        "houmao-admin-welcome",
        "houmao-admin-entrypoint",
    }


def test_system_skills_symlink_mode_uses_receipt_owned_materialization(tmp_path: Path) -> None:
    home = tmp_path / "home"

    payload, _ = _invoke_json(
        "system-skills",
        "install",
        "--tool",
        "codex",
        "--home",
        str(home),
        "--pack",
        "agent",
        "--symlink",
    )

    public = home / "skills/houmao-agent-entrypoint"
    assert payload["projection_mode"] == "symlink"
    assert public.is_symlink()
    assert public.resolve().is_dir()
    assert ".houmao/system-skills/codex/materialized" in public.resolve().as_posix()


@pytest.mark.parametrize("selector", ["--skill", "--set", "--skill-set"])
def test_system_skills_rejects_obsolete_selectors(selector: str, tmp_path: Path) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "codex",
            "--home",
            str(tmp_path / "home"),
            selector,
            "legacy-value",
        ],
    )

    assert result.exit_code != 0
    assert "selectors were removed" in result.output
    assert "--pack admin|agent" in result.output


@pytest.mark.parametrize(
    ("pack_id", "message"),
    [
        ("unknown", "Unknown system-skill pack"),
        ("houmao-agent-email-comms", "not an install selector"),
        ("houmao-shared-routines", "not an install selector"),
    ],
)
def test_system_skills_rejects_unknown_or_protected_pack_selectors(
    pack_id: str,
    message: str,
    tmp_path: Path,
) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "codex",
            "--home",
            str(tmp_path / "home"),
            "--pack",
            pack_id,
        ],
    )

    assert result.exit_code != 0
    assert message in result.output


def test_system_skills_explicit_home_precedes_environment_redirect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirected = tmp_path / "redirected"
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("CODEX_HOME", str(redirected))

    _invoke_json(
        "system-skills",
        "install",
        "--tool",
        "codex",
        "--home",
        str(explicit),
        "--pack",
        "agent",
    )

    assert (explicit / "skills/houmao-agent-entrypoint").is_dir()
    assert not redirected.exists()


def test_system_skills_status_reports_complete_then_drifted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _invoke_json(
        "system-skills",
        "install",
        "--tool",
        "codex",
        "--home",
        str(home),
        "--pack",
        "agent",
    )

    complete, _ = _invoke_json("system-skills", "status", "--tool", "codex", "--home", str(home))
    assert complete["receipt"]["status"] == "current"
    assert {record["pack_id"]: record["status"] for record in complete["packs"]} == {
        "admin": "absent",
        "agent": "complete",
    }

    skill_path = home / "skills/houmao-agent-entrypoint/SKILL.md"
    skill_path.write_text(
        skill_path.read_text(encoding="utf-8") + "\nlocal edit\n", encoding="utf-8"
    )
    drifted, _ = _invoke_json("system-skills", "status", "--tool", "codex", "--home", str(home))
    assert {record["pack_id"]: record["status"] for record in drifted["packs"]}[
        "agent"
    ] == "drifted"


def test_system_skills_upgrade_preserves_modified_legacy_paths(tmp_path: Path) -> None:
    home = tmp_path / "home"
    legacy = home / "skills/houmao-specialist-mgr"
    legacy.mkdir(parents=True)
    (legacy / "SKILL.md").write_text("operator customization\n", encoding="utf-8")

    payload, _ = _invoke_json(
        "system-skills",
        "upgrade",
        "--tool",
        "codex",
        "--home",
        str(home),
        "--pack",
        "admin",
    )

    assert payload["selected_packs"] == ["admin"]
    assert payload["legacy_before"]["status"] == "conflicting"
    assert "skills/houmao-specialist-mgr" in payload["preserved_legacy_paths"]
    assert (legacy / "SKILL.md").read_text(encoding="utf-8") == "operator customization\n"


def test_system_skills_upgrade_removes_package_linked_legacy_path(tmp_path: Path) -> None:
    home = tmp_path / "home"
    legacy = home / "skills/houmao-touring"
    legacy.parent.mkdir(parents=True)
    asset_root = Path(load_system_skill_manifest().source_root)
    legacy.symlink_to(asset_root / "houmao-touring", target_is_directory=True)

    payload, _ = _invoke_json(
        "system-skills",
        "upgrade",
        "--tool",
        "codex",
        "--home",
        str(home),
        "--pack",
        "admin",
    )

    assert "skills/houmao-touring" in payload["safely_removed_legacy_paths"]
    assert not legacy.is_symlink()


def test_system_skills_uninstall_removes_only_selected_owned_pack(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _invoke_json(
        "system-skills",
        "install",
        "--tool",
        "codex",
        "--home",
        str(home),
        "--pack",
        "admin",
        "--pack",
        "agent",
    )

    payload, _ = _invoke_json(
        "system-skills",
        "uninstall",
        "--tool",
        "codex",
        "--home",
        str(home),
        "--pack",
        "admin",
    )

    assert payload["removed_packs"] == ["admin"]
    assert not (home / "skills/houmao-admin-welcome").exists()
    assert not (home / "skills/houmao-admin-entrypoint").exists()
    assert (home / "skills/houmao-agent-entrypoint").is_dir()
    status, _ = _invoke_json("system-skills", "status", "--tool", "codex", "--home", str(home))
    assert status["receipt"]["selected_packs"] == ["agent"]


def test_system_skills_uninstall_without_pack_removes_all_owned_packs(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _invoke_json(
        "system-skills",
        "install",
        "--tool",
        "codex",
        "--home",
        str(home),
        "--pack",
        "admin",
        "--pack",
        "agent",
    )

    payload, _ = _invoke_json("system-skills", "uninstall", "--tool", "codex", "--home", str(home))

    assert payload["removed_packs"] == ["admin", "agent"]
    assert not Path(str(payload["receipt_path"])).exists()


def test_system_skills_rejects_one_home_for_multiple_tools(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "system-skills",
            "install",
            "--tool",
            "codex,claude",
            "--home",
            str(tmp_path / "home"),
            "--pack",
            "agent",
        ],
    )

    assert result.exit_code != 0
    assert "--home can only be used" in result.output
