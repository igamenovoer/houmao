"""Coverage for versioned static roots and read-only doctor diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

import houmao.agents.system_skill_version as version_module
from houmao.agents.system_skill_doctor import (
    SystemSkillDoctorTarget,
    inspect_system_skill_doctor,
)
from houmao.agents.system_skill_manifest import EXPECTED_STANDALONE_SKILL_NAMES
from houmao.agents.system_skill_version import (
    SystemSkillFrontmatterError,
    check_system_skill_source_versions,
    parse_top_level_system_skill_frontmatter,
)
from houmao.agents.system_skills import (
    install_system_skill_packs_for_home,
    load_system_skill_manifest,
    load_system_skill_manifest_from_paths,
    stage_system_skill_collection,
    sync_system_skill_packs_for_home,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_ROOT = REPO_ROOT / "src/houmao/agents/assets/system_skills/public"


def _target(home: Path) -> SystemSkillDoctorTarget:
    """Return one explicit Codex-home target."""

    return SystemSkillDoctorTarget(kind="explicit-home", tool="codex", home_path=home)


def _install(home: Path, *, pack_ids: tuple[str, ...] = ("agent",), symlink: bool = False) -> None:
    """Install one test collection through the existing static lifecycle."""

    install_system_skill_packs_for_home(
        tool="codex",
        home_path=home,
        pack_ids=pack_ids,
        projection_mode="symlink" if symlink else "copy",
    )


def _write_skill(path: Path, frontmatter: str) -> Path:
    """Write one minimal top-level skill fixture."""

    path.write_text(f"---\n{frontmatter}\n---\n\n# Fixture\n", encoding="utf-8")
    return path


def test_six_source_roots_have_versions_and_children_remain_unversioned() -> None:
    """Only the six independently installed roots carry release metadata."""

    result = check_system_skill_source_versions(project_root=REPO_ROOT)

    assert result.healthy
    assert result.checked_skill_names == EXPECTED_STANDALONE_SKILL_NAMES
    assert result.project_version == "1.2.1"
    children = tuple((PUBLIC_ROOT / "houmao-shared-routines/subskills").glob("*/SKILL-MAIN.md"))
    assert len(children) == 16
    assert all("houmao_version:" not in path.read_text(encoding="utf-8") for path in children)
    auto_skill = (
        REPO_ROOT / "src/houmao/agents/assets/auto_skills/houmao-auto-system-prompt/SKILL.md"
    )
    assert "houmao_version:" not in auto_skill.read_text(encoding="utf-8")


def test_frontmatter_parser_preserves_exact_version_string(tmp_path: Path) -> None:
    path = _write_skill(
        tmp_path / "SKILL.md",
        'name: houmao-test\nhoumao_version: "1.2.1+local.7"',
    )

    metadata = parse_top_level_system_skill_frontmatter(path, expected_name="houmao-test")

    assert metadata.name == "houmao-test"
    assert metadata.houmao_version == "1.2.1+local.7"


@pytest.mark.parametrize(
    ("text", "expected_name", "code"),
    [
        (
            "name: houmao-test\nname: duplicate\nhoumao_version: '1.2.1'",
            "houmao-test",
            "duplicate-key",
        ),
        (
            "name: houmao-test\nhoumao_version: '1.2.1'\nhoumao_version: '1.2.0'",
            "houmao-test",
            "duplicate-key",
        ),
        ("name: [broken\nhoumao_version: '1.2.1'", "houmao-test", "malformed-yaml"),
        ("name: other\nhoumao_version: '1.2.1'", "houmao-test", "name-mismatch"),
        ("houmao_version: '1.2.1'", "houmao-test", "missing-name"),
        ("name: houmao-test", "houmao-test", "missing-version"),
        ("name: houmao-test\nhoumao_version: 1.2", "houmao-test", "non-string-version"),
        ("name: houmao-test\nhoumao_version: 'not a release'", "houmao-test", "invalid-version"),
    ],
)
def test_frontmatter_parser_reports_specific_failures(
    tmp_path: Path,
    text: str,
    expected_name: str,
    code: str,
) -> None:
    path = _write_skill(tmp_path / "SKILL.md", text)

    with pytest.raises(SystemSkillFrontmatterError) as exc_info:
        parse_top_level_system_skill_frontmatter(path, expected_name=expected_name)

    assert exc_info.value.code == code


@pytest.mark.parametrize("content", ["", "name: houmao-test\n"])
def test_frontmatter_parser_rejects_missing_delimiters(tmp_path: Path, content: str) -> None:
    path = tmp_path / "SKILL.md"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(SystemSkillFrontmatterError) as exc_info:
        parse_top_level_system_skill_frontmatter(path, expected_name="houmao-test")

    assert exc_info.value.code == "malformed-delimiters"


def test_frontmatter_parser_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SystemSkillFrontmatterError) as exc_info:
        parse_top_level_system_skill_frontmatter(
            tmp_path / "missing.md",
            expected_name="houmao-test",
        )

    assert exc_info.value.code == "missing-file"


def test_source_check_fails_project_version_drift_without_rewriting_sources(
    tmp_path: Path,
) -> None:
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text('[project]\nversion = "9.9.9"\n', encoding="utf-8")
    copied_assets = tmp_path / "src/houmao/agents/assets/system_skills"
    shutil.copytree(
        REPO_ROOT / "src/houmao/agents/assets/system_skills",
        copied_assets,
    )
    before = {
        name: (PUBLIC_ROOT / name / "SKILL.md").read_bytes()
        for name in EXPECTED_STANDALONE_SKILL_NAMES
    }

    result = check_system_skill_source_versions(project_root=tmp_path)

    assert not result.healthy
    assert len(result.issues) == 6
    assert {issue.observed_version for issue in result.issues} == {"1.2.1"}
    assert {issue.expected_version for issue in result.issues} == {"9.9.9"}
    assert before == {
        name: (PUBLIC_ROOT / name / "SKILL.md").read_bytes()
        for name in EXPECTED_STANDALONE_SKILL_NAMES
    }


@pytest.mark.parametrize("symlink", [False, True])
def test_doctor_accepts_current_copy_or_symlink_with_or_without_config(
    tmp_path: Path,
    symlink: bool,
) -> None:
    home = tmp_path / "home"
    _install(home, symlink=symlink)
    config = home / ".houmao/system-skills/codex/houmao-skill-config.json"
    if not symlink:
        config.unlink()

    result = inspect_system_skill_doctor(target=_target(home))

    assert result.healthy
    assert result.selected_pack_ids == ("agent",)
    assert result.config.status == ("current" if symlink else "absent")
    assert len(result.members) == 4
    assert all(member.integrity_status == "complete" for member in result.members)
    assert all(member.version_status == "match" for member in result.members)


def test_doctor_deduplicates_combined_packs(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _install(home, pack_ids=("admin", "agent"))

    result = inspect_system_skill_doctor(
        target=_target(home),
        pack_ids=("agent", "admin", "agent"),
    )

    assert result.healthy
    assert result.selected_pack_ids == ("agent", "admin")
    assert len(result.members) == 6
    assert len({member.name for member in result.members}) == 6


def test_doctor_separates_missing_incomplete_drift_and_version_mismatch(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    _install(home)
    shutil.rmtree(home / "skills/houmao-agent-entrypoint")
    shared_child = home / "skills/houmao-shared-routines/subskills/houmao-project-mgr"
    shutil.rmtree(shared_child)
    pro = home / "skills/houmao-agent-loop-pro/SKILL.md"
    pro.write_text(pro.read_text(encoding="utf-8") + "\nlocal edit\n", encoding="utf-8")
    lite = home / "skills/houmao-agent-loop-lite/SKILL.md"
    lite.write_text(
        lite.read_text(encoding="utf-8").replace(
            'houmao_version: "1.2.1"',
            'houmao_version: "1.2.0"',
        ),
        encoding="utf-8",
    )

    result = inspect_system_skill_doctor(target=_target(home))
    by_name = {member.name: member for member in result.members}

    assert not result.healthy
    assert by_name["houmao-agent-entrypoint"].integrity_status == "absent"
    assert by_name["houmao-shared-routines"].integrity_status == "incomplete"
    assert by_name["houmao-agent-loop-pro"].integrity_status == "drifted"
    assert by_name["houmao-agent-loop-pro"].version_status == "match"
    assert by_name["houmao-agent-loop-lite"].integrity_status == "drifted"
    assert by_name["houmao-agent-loop-lite"].observed_version == "1.2.0"
    assert by_name["houmao-agent-loop-lite"].version_status == "mismatch"


def test_doctor_reports_unknown_running_version_without_losing_observed_value(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    _install(home)

    result = inspect_system_skill_doctor(
        target=_target(home),
        running_houmao_version="0+unknown",
    )

    assert not result.healthy
    assert {member.observed_version for member in result.members} == {"1.2.1"}
    assert {member.version_status for member in result.members} == {"unavailable"}


def test_corrupt_config_stays_separate_from_direct_health(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _install(home)
    config = home / ".houmao/system-skills/codex/houmao-skill-config.json"
    config.write_text("{broken\n", encoding="utf-8")

    result = inspect_system_skill_doctor(target=_target(home))

    assert result.healthy
    assert result.config.status == "corrupt"
    assert result.config.message is not None
    assert all(not member.config.present for member in result.members)


@pytest.mark.parametrize(
    ("config_payload", "expected_status"),
    [
        ({"schema_version": "future.v99"}, "unsupported"),
        (
            {
                "schema_version": "houmao-skill-config.v1",
                "houmao_version": "1.2.1",
                "projection_mode": "copy",
                "skills": [],
            },
            "corrupt",
        ),
    ],
)
def test_noncurrent_config_posture_does_not_replace_direct_health(
    tmp_path: Path,
    config_payload: dict[str, object],
    expected_status: str,
) -> None:
    home = tmp_path / "home"
    _install(home)
    config = home / ".houmao/system-skills/codex/houmao-skill-config.json"
    config.write_text(json.dumps(config_payload) + "\n", encoding="utf-8")

    result = inspect_system_skill_doctor(target=_target(home))

    assert result.healthy
    assert result.config.status == expected_status
    assert all(not member.config.present for member in result.members)


def test_config_version_and_digest_do_not_replace_installed_evidence(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    _install(home)
    config = home / ".houmao/system-skills/codex/houmao-skill-config.json"
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["houmao_version"] = "0.1.0"
    payload["skills"][0]["content_digest"] = "0" * 64
    config.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = inspect_system_skill_doctor(target=_target(home))

    assert result.healthy
    assert result.config.status == "current"
    assert result.config.houmao_version == "0.1.0"
    first = result.members[0]
    assert first.observed_version == "1.2.1"
    assert first.version_status == "match"
    assert first.config.content_digest == "0" * 64


def test_doctor_does_not_modify_configless_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _install(home)
    shutil.rmtree(home / ".houmao")
    before = {
        path.relative_to(home): path.read_bytes() for path in home.rglob("*") if path.is_file()
    }

    inspect_system_skill_doctor(target=_target(home))

    after = {
        path.relative_to(home): path.read_bytes() for path in home.rglob("*") if path.is_file()
    }
    assert after == before
    assert not (home / ".houmao").exists()


def test_manifest_loading_does_not_require_version_metadata(tmp_path: Path) -> None:
    """The version parser remains outside static manifest lifecycle preflight."""

    manifest = load_system_skill_manifest()
    source_root = REPO_ROOT / "src/houmao/agents/assets/system_skills"
    copied_root = tmp_path / "system_skills"
    shutil.copytree(source_root, copied_root)
    entrypoint = copied_root / "public/houmao-agent-entrypoint/SKILL.md"
    entrypoint.write_text(
        entrypoint.read_text(encoding="utf-8").replace('houmao_version: "1.2.1"\n', ""),
        encoding="utf-8",
    )

    loaded = load_system_skill_manifest_from_paths(
        manifest_path=copied_root / "manifest.toml",
        schema_path=copied_root / "manifest.schema.json",
        assets_root=copied_root,
    )
    staged = stage_system_skill_collection(
        loaded,
        pack_ids=("agent",),
        destination_root=tmp_path / "staged",
    )

    assert manifest.schema_version == "houmao-system-skills.v4"
    assert loaded.schema_version == manifest.schema_version
    staged_entrypoint = staged.skills[0].path / "SKILL.md"
    assert "houmao_version:" not in staged_entrypoint.read_text(encoding="utf-8")


def test_lifecycle_install_and_sync_do_not_call_diagnostic_version_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Version parsing remains outside all static lifecycle mutations."""

    def _reject(*args: object, **kwargs: object) -> object:
        raise AssertionError("lifecycle called diagnostic version parser")

    monkeypatch.setattr(version_module, "parse_top_level_system_skill_frontmatter", _reject)
    home = tmp_path / "home"

    _install(home)
    sync_system_skill_packs_for_home(
        tool="codex",
        home_path=home,
        selected_pack_ids=("agent",),
    )

    assert (home / "skills/houmao-agent-entrypoint/SKILL.md").is_file()
