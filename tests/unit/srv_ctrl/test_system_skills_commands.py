"""CLI coverage for actor-oriented system-skill packs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from click.testing import CliRunner
import pytest

from houmao.agents.system_skill_doctor import SystemSkillDoctorTarget
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
    for command in ("list", "install", "status", "doctor", "upgrade", "uninstall"):
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


def test_system_skills_list_reports_static_collection_and_shared_routines() -> None:
    payload, _ = _invoke_json("system-skills", "list")

    packs = payload["packs"]
    assert isinstance(packs, list)
    assert [pack["pack_id"] for pack in packs] == ["admin", "agent"]
    assert [len(pack["standalone_skills"]) for pack in packs] == [5, 4]
    assert [record["name"] for record in payload["standalone_skills"]] == [
        "houmao-admin-welcome",
        "houmao-admin-entrypoint",
        "houmao-agent-entrypoint",
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    ]
    assert payload["overlapping_standalone_skills"] == [
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    ]
    assert payload["defaults"] == {
        "cli": ["admin"],
        "managed_launch": ["agent"],
        "managed_join": ["agent"],
    }
    activation_by_name = {
        record["name"]: record["activation"] for record in payload["standalone_skills"]
    }
    assert activation_by_name == {
        "houmao-admin-welcome": "explicit",
        "houmao-admin-entrypoint": "narrow-implicit",
        "houmao-agent-entrypoint": "narrow-implicit",
        "houmao-shared-routines": "explicit",
        "houmao-agent-loop-pro": "explicit",
        "houmao-agent-loop-lite": "explicit",
    }
    shared = payload["shared_routines"]
    assert isinstance(shared, list)
    assert len(shared) == 16
    assert all(record["invocation"].startswith("houmao-shared-routines->") for record in shared)
    assert "protected_routines" not in payload
    assert payload["auto_skill_separate"] == "houmao-auto-system-prompt"


def test_system_skills_install_defaults_to_admin_pack(tmp_path: Path) -> None:
    home = tmp_path / "codex-home"

    payload, _ = _invoke_json("system-skills", "install", "--tool", "codex", "--home", str(home))

    assert payload["selected_packs"] == ["admin"]
    assert payload["standalone_skills"] == [
        "houmao-admin-welcome",
        "houmao-admin-entrypoint",
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    ]
    assert (home / "skills/houmao-admin-welcome/SKILL.md").is_file()
    assert (home / "skills/houmao-admin-entrypoint/SKILL.md").is_file()
    shared = home / "skills/houmao-shared-routines"
    assert (shared / "SKILL.md").is_file()
    assert (shared / "subskills/houmao-project-mgr/SKILL-MAIN.md").is_file()
    assert (shared / "subskills/houmao-process-emails-via-gateway/SKILL-MAIN.md").is_file()
    assert (home / "skills/houmao-agent-loop-pro/SKILL.md").is_file()
    assert (home / "skills/houmao-agent-loop-lite/SKILL.md").is_file()
    assert not (home / "skills/houmao-project-mgr").exists()
    assert not (home / "skills/houmao-admin-entrypoint/subskills").exists()
    assert Path(str(payload["config_path"])).is_file()
    assert "receipt_path" not in payload


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
    assert payload["standalone_skills"] == [
        "houmao-agent-entrypoint",
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    ]
    for skill_name in payload["standalone_skills"]:
        assert (home / "skills" / skill_name / "SKILL.md").is_file()


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

    assert payload["selected_packs"] == ["admin", "agent"]
    assert payload["standalone_skills"] == [
        "houmao-admin-welcome",
        "houmao-admin-entrypoint",
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
        "houmao-agent-entrypoint",
    ]
    assert payload["owning_pack_ids_by_skill"] == {
        "houmao-admin-welcome": ["admin"],
        "houmao-admin-entrypoint": ["admin"],
        "houmao-shared-routines": ["admin", "agent"],
        "houmao-agent-loop-pro": ["admin", "agent"],
        "houmao-agent-loop-lite": ["admin", "agent"],
        "houmao-agent-entrypoint": ["agent"],
    }


def test_system_skills_symlink_mode_links_directly_to_packaged_sources(tmp_path: Path) -> None:
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
    expected = Path(load_system_skill_manifest().source_root) / "public/houmao-agent-entrypoint"
    assert public.resolve() == expected.resolve()
    assert not (home / ".houmao/system-skills/codex/materialized").exists()


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
        ("houmao-shared-routines", "not a pack selector"),
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
    assert complete["config"]["status"] == "current"
    assert "receipt" not in complete
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


def test_system_skills_doctor_defaults_to_configless_agent_pack(tmp_path: Path) -> None:
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
    (home / ".houmao/system-skills/codex/houmao-skill-config.json").unlink()

    payload, _ = _invoke_json(
        "system-skills",
        "doctor",
        "--tool",
        "codex",
        "--home",
        str(home),
    )

    assert payload["healthy"] is True
    assert payload["running_houmao_version"] == get_version()
    assert payload["selected_packs"] == ["agent"]
    assert payload["config"]["status"] == "absent"
    assert "receipt" not in payload
    assert [member["name"] for member in payload["members"]] == [
        "houmao-agent-entrypoint",
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    ]
    assert all(member["integrity_status"] == "complete" for member in payload["members"])
    assert all(member["version_status"] == "match" for member in payload["members"])


def test_system_skills_doctor_emits_json_before_health_exit_one(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "system-skills",
            "doctor",
            "--tool",
            "codex",
            "--home",
            str(tmp_path / "missing-home"),
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["healthy"] is False
    assert payload["selected_packs"] == ["agent"]
    assert {member["integrity_status"] for member in payload["members"]} == {"absent"}


def test_houmao_mgr_module_preserves_doctor_health_exit_one(tmp_path: Path) -> None:
    result = _run_houmao_mgr_module(
        "--print-json",
        "system-skills",
        "doctor",
        "--tool",
        "codex",
        "--home",
        str(tmp_path / "missing-home"),
    )

    assert result.returncode == 1
    assert json.loads(result.stdout)["healthy"] is False


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("--tool", "bogus"),
        ("--tool", "codex", "--agent-id", "agent-id"),
        ("--agent-id", "agent-id", "--agent-name", "agent-name"),
        ("--tool", "codex", "--pack", "unknown"),
    ],
)
def test_system_skills_doctor_rejects_invalid_target_or_pack_usage(args: tuple[str, ...]) -> None:
    result = CliRunner().invoke(cli, ["system-skills", "doctor", *args])

    assert result.exit_code == 2


def test_system_skills_doctor_supports_repeatable_combined_packs(tmp_path: Path) -> None:
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
        "doctor",
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

    assert payload["healthy"] is True
    assert payload["selected_packs"] == ["agent", "admin"]
    assert len(payload["members"]) == 6


def test_system_skills_doctor_supports_managed_agent_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "managed-home"
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
    target = SystemSkillDoctorTarget(
        kind="managed-agent",
        tool="codex",
        home_path=home,
        agent_id="agent-authoritative-id",
        agent_name="HOUMAO-worker",
        lifecycle_state="stopped",
        session_manifest_path=tmp_path / "manifest.json",
        brain_manifest_path=tmp_path / "brain-manifest.yaml",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.system_skills.resolve_managed_system_skill_doctor_target",
        lambda **_: target,
    )

    payload, _ = _invoke_json(
        "system-skills",
        "doctor",
        "--agent-id",
        "agent-authoritative-id",
    )

    assert payload["healthy"] is True
    assert payload["target"]["kind"] == "managed-agent"
    assert payload["target"]["agent_id"] == "agent-authoritative-id"
    assert payload["target"]["lifecycle_state"] == "stopped"


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
    assert status["config"]["selected_packs"] == ["agent"]


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
    assert not Path(str(payload["config_path"])).exists()
    assert "receipt_path" not in payload


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
