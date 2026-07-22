"""Structural contracts for Houmao development testing skills."""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_ROOT = REPO_ROOT / "skillset" / "dev"
BEHAVIOR_ROOT = DEV_ROOT / "houmao-dev-behavior-testing"
TUI_ROOT = DEV_ROOT / "houmao-dev-tui-testing"
MANIFEST_PATH = (
    REPO_ROOT / "src" / "houmao" / "agents" / "assets" / "system_skills" / "manifest.toml"
)
ADMIN_ENTRYPOINT_PATH = (
    REPO_ROOT
    / "src"
    / "houmao"
    / "agents"
    / "assets"
    / "system_skills"
    / "public"
    / "houmao-admin-entrypoint"
    / "SKILL.md"
)

EXPECTED_BEHAVIOR_COMMANDS = {
    "plan-run",
    "execute-case",
    "adjudicate-case",
    "report-run",
    "snapshot-context",
    "collect-evidence",
    "run-case",
    "run-suite",
}
EXPECTED_TUI_COMMANDS = {
    "record",
    "label",
    "replay",
    "compare",
    "render-video",
    "run-all",
    "help",
}
EXPECTED_CASE_IDS = {
    *(f"ACT-{index:03d}" for index in range(1, 7)),
    *(f"AUTO-{index:03d}" for index in range(1, 3)),
    *(f"ADM-{index:03d}" for index in range(1, 9)),
    *(f"AGT-{index:03d}" for index in range(1, 9)),
    *(f"SHR-{index:03d}" for index in range(1, 10)),
    *(f"LOOP-{index:03d}" for index in range(1, 9)),
    *(f"PRM-{index:03d}" for index in range(1, 6)),
}
EXPECTED_AREA_CASE_PROFILES = {
    "activation.md": {
        "area": "activation",
        "cases": {
            "ACT-001": "minimal",
            "ACT-002": "minimal",
            "ACT-003": "minimal",
            "ACT-004": "normal",
            "ACT-005": "minimal",
            "ACT-006": "extended",
        },
    },
    "managed-bootstrap.md": {
        "area": "managed-bootstrap",
        "cases": {"AUTO-001": "minimal", "AUTO-002": "extended"},
    },
    "admin-routing.md": {
        "area": "admin-entrypoint",
        "cases": {
            "ADM-001": "extended",
            "ADM-002": "extended",
            "ADM-003": "minimal",
            "ADM-004": "normal",
            "ADM-005": "extended",
            "ADM-006": "normal",
            "ADM-007": "extended",
            "ADM-008": "complete",
            "PRM-005": "extended",
        },
    },
    "managed-agent-routing.md": {
        "area": "agent-entrypoint",
        "cases": {
            "AGT-001": "extended",
            "AGT-002": "minimal",
            "AGT-003": "extended",
            "AGT-004": "normal",
            "AGT-005": "normal",
            "AGT-006": "extended",
            "AGT-007": "extended",
            "AGT-008": "extended",
            "PRM-004": "extended",
        },
    },
    "shared-routines.md": {
        "area": "shared-routines",
        "cases": {
            "SHR-001": "minimal",
            "SHR-002": "minimal",
            "SHR-003": "normal",
            "SHR-004": "normal",
            "SHR-005": "extended",
            "SHR-006": "extended",
            "SHR-007": "extended",
            "SHR-008": "extended",
            "SHR-009": "normal",
        },
    },
    "loops.md": {
        "area": "agent-loops",
        "cases": {
            "LOOP-001": "minimal",
            "LOOP-002": "minimal",
            "LOOP-003": "minimal",
            "LOOP-004": "normal",
            "LOOP-005": "normal",
            "LOOP-006": "extended",
            "LOOP-007": "extended",
            "LOOP-008": "normal",
        },
    },
    "generated-prompts.md": {
        "area": "generated-prompts",
        "cases": {
            "PRM-001": "minimal",
            "PRM-002": "normal",
            "PRM-003": "extended",
        },
    },
}
EXPECTED_PROFILE_TOTALS = {"minimal": 13, "normal": 25, "extended": 45, "complete": 46}
EXPECTED_TAG_CASES = {
    "critical": {
        "ACT-001",
        "ACT-002",
        "ACT-003",
        "ACT-004",
        "ACT-005",
        "AUTO-001",
        "ADM-003",
        "ADM-004",
        "ADM-006",
        "AGT-002",
        "AGT-004",
        "AGT-005",
        "SHR-001",
        "SHR-002",
        "SHR-004",
        "SHR-009",
        "LOOP-001",
        "LOOP-002",
        "LOOP-003",
        "LOOP-008",
        "PRM-001",
        "PRM-002",
    },
    "actor-boundaries": {
        "ACT-006",
        "ADM-005",
        "ADM-007",
        "ADM-008",
        "AGT-004",
        "AGT-005",
        "AGT-006",
        "AGT-007",
        "SHR-002",
        "SHR-003",
        "SHR-006",
        "SHR-007",
        "SHR-009",
        "LOOP-005",
        "LOOP-006",
        "LOOP-008",
    },
    "route-coverage": {
        "ACT-003",
        "ADM-003",
        "AGT-002",
        "SHR-003",
        "SHR-004",
        "SHR-005",
        "SHR-006",
        "SHR-007",
        "SHR-009",
        "LOOP-002",
        "LOOP-003",
        "LOOP-008",
        "PRM-001",
    },
}
EXPECTED_CASE_VARIANTS = {
    "ACT-004": {
        "admin-welcome",
        "admin-entrypoint",
        "agent-entrypoint",
        "shared-routines",
        "agent-loop-pro",
        "agent-loop-lite",
    },
    "ACT-005": {"informational", "operational"},
    "ACT-006": {"raw-operator", "genuine-managed"},
    "AUTO-002": {"resume", "relaunch", "compaction"},
    "SHR-003": {"admin-entrypoint", "agent-entrypoint"},
    "SHR-009": {"admin", "managed-agent"},
    "LOOP-004": {"pro-admin", "pro-agent", "lite-admin", "lite-agent"},
    "LOOP-005": {"admin-pro", "agent-lite"},
    "LOOP-006": {"pro", "lite"},
    "LOOP-007": {"pro", "lite"},
    "LOOP-008": {"admin-pro", "agent-lite"},
    "PRM-003": {"entrypoint-missing", "shared-routines-missing"},
}
VERSION_3_NEW_CASE_IDS = {"ACT-005", "ACT-006", "SHR-009", "LOOP-008"}
VERSION_3_REVISION_2_CASE_IDS = {"ACT-001", "ACT-003", "ADM-002", "LOOP-001"}
VERSION_2_CASE_SEMANTIC_DIGESTS = {
    "ACT-001": "acb0de95c879d01cd190c6e25c095f26dabf1f3c012efbb518dc6e7c2ed8341b",
    "ACT-002": "f7c631eb47b731d90529e67effddb3667f54c903d3137d2bb11cdb7089d3d977",
    "ACT-003": "1581a9f16af04a70bc1e2c5005403471721347476f058873511f1a047fb3f723",
    "ACT-004": "e18fa844a839c053fbe0b7dc19c6ab0acc12d69a27d7bb117c8b08e7bcfeb291",
    "ADM-001": "8fa4bfad8d985242524648cf1ceb102ec1b6695e2ad8799a959f963e11a27de3",
    "ADM-002": "28cd31c1aa7d7f4cfc558939f4f80b88f846986127080c0e082491f35fa1d75e",
    "ADM-003": "bc38749dcae17795d02df1ae6b0067ed669816298372fcca15511cadd35279c2",
    "ADM-004": "ab92f79f1d6f667395fe2d44926ffc461518e1e41c43d0a1ea174398aff1864f",
    "ADM-005": "dbb595c9c7dba46699229a3f8d7dd614646678fa04b059485160b4d5159c7e92",
    "ADM-006": "5414aed727e63f5a92d9822691e33e7dec72f492a9a95241a1a1f0cc1f8951b7",
    "ADM-007": "05e6ee9385ec4226ffb8dc1911d9cfb08a0ddc040dcd0e14cc5e6ef30f66c4a1",
    "ADM-008": "627d40f5d24825d835104212842ccdd6cd5edb659db919dde61bb33282f506c7",
    "AGT-001": "ed414f66440f13bd68f332a4b2c356a98252e0eb0a5fef17e616ccba2b5ead7e",
    "AGT-002": "c8e7e58219eaf08fb7a02de279da32b297463bffa59e1421c73029ef36f4e652",
    "AGT-003": "151f26314562abea70eac51a260ff489251993312c75ddce911a62975cf762fd",
    "AGT-004": "2a131928eeed16bd0470a94085f27cf20ec0814e7efd59cea94b470b4fe6cc32",
    "AGT-005": "a4f24f620e992a84d4a939779acc14f25b271c11294977b1c8e166455b80104f",
    "AGT-006": "b641cc4b610254ebfd15f31f2898dcb774a543b9d998ae2dbbfadc40657ed396",
    "AGT-007": "ae617d639e45d5181d74f96d00d263ae073305c89b41ff287a2ea0e7cd5ed05e",
    "AGT-008": "d1a340a33aa76ba3ff830377b5165c12cc15de780120282c4c247b272723ab29",
    "AUTO-001": "20e1c110753cf91cbd966b1471dab94b2c255e10bd2289c50d3322bc2ad2a600",
    "AUTO-002": "e50f67c298b52bf23c0f10ac929c4b1e28a1e758f7b00888255ca8693694b7e6",
    "LOOP-001": "aa67b777ae88263d8d6de9f7200939399994ee4db32791e67577a030f55eaa1c",
    "LOOP-002": "277b207b7575160634e7fb24e48d21f278896990e6ab03d0c5d9c582fd1e45ba",
    "LOOP-003": "b87982e8bd4f0599a2037922372a31f3fb3cc6c2f7fb999b84d9353011bd89d3",
    "LOOP-004": "e7322af2aca0634f4314e615979445a8bd6b963de4eab05e58fd4ce1784a1de7",
    "LOOP-005": "e84a0c3a4c11b479d92cc2f294adc566fb666e3cb37fad34b1300f24d8581c4a",
    "LOOP-006": "b901876cc842e9ff8b1a616333ba3c9413acb9641ba7478ba0975f78c8b17df1",
    "LOOP-007": "53f5cb4dd1c896bf1dcc32d2776aa3625137038b9195ea08e6060f5dea5586fd",
    "PRM-001": "381cbe709c50ed5440dda1b45c6ba86eefe6800e4fd0254b0ecc70efc1513797",
    "PRM-002": "693608e517ee64004007e5a1d9dd00be5f59fd1a9aa714d219c3d5093fff07eb",
    "PRM-003": "d91e7c49d477752a6b3dcb013f9de19eb7626912c1c7ff1a61d3dcfda64a7ae9",
    "PRM-004": "b16027a247713808e683a28877b4d8c460acb3acbfb5c7a2a30b1b74f5357264",
    "PRM-005": "f045df1bab58d09461937209c74685d803a56b048810f360729d9e0acd772ad5",
    "SHR-001": "10a3790a15929b4b20eed490d05ac56b5bff3807219b98e7f8377cdcd7f4b456",
    "SHR-002": "ce0b8adc4b55ebe59c747cd756081837a0308a2a2fe70aa6d5628475c454c40e",
    "SHR-003": "b8fb15f9e0ce5f32573c92ad1219f7802c2b15ab1395a2da57b8803d847379ab",
    "SHR-004": "8e60b3e8313528ee13e7d460d626c042b831b421a2af176cfb358749ef0cf44e",
    "SHR-005": "bcb9ccced381355b5542888a460387b0ff3d3cee108bcd87f37620f9475fb30e",
    "SHR-006": "7c985c655b01de9e71197c82febf863d06dbc154b97f3aeaf46c90f810f154af",
    "SHR-007": "7a6c230231c39210d6b185515eda5ef995d144d1ade51f2b4319a9cce0dbeea3",
    "SHR-008": "fcd59322c92f583456976c1fbb7ee4ec72c0777503cbb32b014d50a8f2805d10",
}
EXPECTED_PUBLIC_SYSTEM_SKILLS = {
    "houmao-admin-welcome",
    "houmao-admin-entrypoint",
    "houmao-agent-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
}


def _read_frontmatter(path: Path) -> dict[str, Any]:
    """Parse one Markdown file's YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    marker = text.find("\n---\n", 4)
    assert marker > 0
    payload = yaml.safe_load(text[4:marker])
    assert isinstance(payload, dict)
    return payload


def _local_markdown_links(path: Path) -> tuple[str, ...]:
    """Return relative file links from one Markdown document."""
    text = path.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    return tuple(
        link.split("#", 1)[0]
        for link in links
        if link and not link.startswith(("http://", "https://", "#"))
    )


def _manifest_payload() -> dict[str, Any]:
    """Load the packaged system-skill manifest."""
    with MANIFEST_PATH.open("rb") as stream:
        return tomllib.load(stream)


def _behavior_case_rows() -> dict[str, tuple[Path, list[str]]]:
    """Return one introduced-profile row for every committed behavior case."""
    tiers = set(EXPECTED_PROFILE_TOTALS)
    result: dict[str, tuple[Path, list[str]]] = {}
    for path in sorted((BEHAVIOR_ROOT / "references" / "cases").glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| `"):
                continue
            cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
            if len(cells) < 2 or cells[1] not in tiers or cells[0] not in EXPECTED_CASE_IDS:
                continue
            assert cells[0] not in result, f"duplicate behavior case row: {cells[0]}"
            result[cells[0]] = (path, cells)
    return result


def _behavior_semantic_digests(
    rows: dict[str, tuple[Path, list[str]]],
) -> dict[str, str]:
    """Hash each case's version 2 semantic columns independently."""
    result: dict[str, str] = {}
    for case_id, (_, cells) in rows.items():
        if case_id.startswith(("ACT-", "AUTO-")):
            semantic = (cells[3], cells[4], cells[5], cells[6])
        elif case_id.startswith("ADM-") or case_id == "PRM-005":
            semantic = (cells[2], cells[3], cells[4], cells[5])
        else:
            semantic = (cells[2], cells[4], cells[5], cells[6])
        result[case_id] = hashlib.sha256("\x1f".join(semantic).encode()).hexdigest()
    return result


def _case_stimulus(case_id: str, cells: list[str]) -> str:
    """Return the exact-stimulus or stimulus-authority column for one case row."""

    if case_id.startswith(("ACT-", "AUTO-")):
        return cells[3]
    return cells[2]


def _invocation_fields(cells: list[str]) -> tuple[str, str, str, str, str, str]:
    """Return the six appended invocation-provenance fields."""

    assert len(cells) >= 13
    driver_mode, origin, activation, initial_root, delegated_roots, route = cells[-6:]
    return driver_mode, origin, activation, initial_root, delegated_roots, route


def test_development_testing_skill_identities_are_unambiguous() -> None:
    """The broad legacy identity is replaced by behavior and TUI-specific roots."""
    assert not (DEV_ROOT / "houmao-dev-testing").exists()
    assert _read_frontmatter(BEHAVIOR_ROOT / "SKILL.md")["name"] == ("houmao-dev-behavior-testing")
    assert _read_frontmatter(TUI_ROOT / "SKILL.md")["name"] == "houmao-dev-tui-testing"

    behavior_metadata = yaml.safe_load(
        (BEHAVIOR_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    )
    tui_metadata = yaml.safe_load((TUI_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    assert behavior_metadata["policy"]["allow_implicit_invocation"] is False
    assert "$houmao-dev-behavior-testing" in behavior_metadata["interface"]["default_prompt"]
    assert "$houmao-dev-tui-testing" in tui_metadata["interface"]["default_prompt"]


def test_behavior_skill_uses_complete_imsight_command_layout() -> None:
    """The behavior router and every command page satisfy the selected skill shape."""
    skill_text = (BEHAVIOR_ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = _read_frontmatter(BEHAVIOR_ROOT / "SKILL.md")
    standard_notation = _read_frontmatter(ADMIN_ENTRYPOINT_PATH)["skill_invocation_notation"]
    assert frontmatter["description"].startswith("Use when ")
    assert frontmatter["skill_invocation_notation"] == standard_notation
    assert "## Workflow" in skill_text
    assert "### Procedural Subcommands" in skill_text
    assert "### Helper Subcommands" in skill_text
    assert "### Misc Subcommands" in skill_text
    assert not (BEHAVIOR_ROOT / "subskills").exists()

    command_names = {path.stem for path in (BEHAVIOR_ROOT / "commands").glob("*.md")}
    assert command_names == EXPECTED_BEHAVIOR_COMMANDS
    for command_path in (BEHAVIOR_ROOT / "commands").glob("*.md"):
        assert "## Workflow" in command_path.read_text(encoding="utf-8")


def test_development_testing_skill_links_resolve() -> None:
    """Every local Markdown link in both development testing skills resolves."""
    for skill_root in (BEHAVIOR_ROOT, TUI_ROOT):
        for markdown_path in skill_root.rglob("*.md"):
            for link in _local_markdown_links(markdown_path):
                assert (markdown_path.parent / link).resolve().exists(), (
                    f"broken link in {markdown_path.relative_to(REPO_ROOT)}: {link}"
                )


def test_behavior_catalog_declares_every_required_case_and_functional_area() -> None:
    """The versioned catalog owns all stable cases through seven functional areas."""
    catalog = (BEHAVIOR_ROOT / "references" / "case-catalog.md").read_text(encoding="utf-8")
    assert "houmao-dev-behavior-cases.v3" in catalog

    expected_area_paths = set(EXPECTED_AREA_CASE_PROFILES)
    actual_area_paths = {
        path.name for path in (BEHAVIOR_ROOT / "references" / "cases").glob("*.md")
    }
    assert actual_area_paths == expected_area_paths

    rows = _behavior_case_rows()
    assert set(rows) == EXPECTED_CASE_IDS
    for filename, expected in EXPECTED_AREA_CASE_PROFILES.items():
        path = BEHAVIOR_ROOT / "references" / "cases" / filename
        text = path.read_text(encoding="utf-8")
        assert f"Functional area: `{expected['area']}`" in text
        actual_cases = {
            case_id: cells[1] for case_id, (case_path, cells) in rows.items() if case_path == path
        }
        assert actual_cases == expected["cases"]
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((BEHAVIOR_ROOT / "references" / "cases").glob("*.md"))
    )
    assert "Case revision: `2` for `ACT-001` and `ACT-003`" in combined
    assert "Case revision: `2` for `ADM-002`" in combined
    assert "Case revision: `2` for `LOOP-001`" in combined


def test_behavior_case_semantics_change_only_for_declared_version_3_cases() -> None:
    """Version 3 preserves every old semantic oracle outside four revision bumps."""

    actual = _behavior_semantic_digests(_behavior_case_rows())
    assert set(VERSION_2_CASE_SEMANTIC_DIGESTS) == EXPECTED_CASE_IDS - VERSION_3_NEW_CASE_IDS
    unchanged = set(VERSION_2_CASE_SEMANTIC_DIGESTS) - VERSION_3_REVISION_2_CASE_IDS
    assert {case_id: actual[case_id] for case_id in unchanged} == {
        case_id: VERSION_2_CASE_SEMANTIC_DIGESTS[case_id] for case_id in unchanged
    }
    for case_id in VERSION_3_REVISION_2_CASE_IDS:
        assert actual[case_id] != VERSION_2_CASE_SEMANTIC_DIGESTS[case_id]


def test_behavior_profiles_are_cumulative_and_match_committed_counts() -> None:
    """Every profile is a cumulative slice and complete equals the full catalog."""
    profile_rank = {name: rank for rank, name in enumerate(EXPECTED_PROFILE_TOTALS)}
    rows = _behavior_case_rows()
    resolved_profiles = {
        profile: {case_id for case_id, (_, cells) in rows.items() if profile_rank[cells[1]] <= rank}
        for profile, rank in profile_rank.items()
    }
    for profile, expected_count in EXPECTED_PROFILE_TOTALS.items():
        assert len(resolved_profiles[profile]) == expected_count
    assert resolved_profiles["minimal"] < resolved_profiles["normal"]
    assert resolved_profiles["normal"] < resolved_profiles["extended"]
    assert resolved_profiles["extended"] < resolved_profiles["complete"]
    assert resolved_profiles["complete"] == EXPECTED_CASE_IDS

    catalog = (BEHAVIOR_ROOT / "references" / "case-catalog.md").read_text(encoding="utf-8")
    assert "| `all` | 13 | 25 | 45 | 46 |" in catalog
    for selector in (
        "<area>/<profile>",
        "<area>/<manual|automatic>/<profile>",
        "all/<profile>",
        "all/<manual|automatic>/<profile>",
        "tag:<name>",
        "<case-id>/<variant-id>",
    ):
        assert f"`{selector}`" in catalog
    assert "An absent selector never implies `all/normal`" in catalog


def test_behavior_invocation_modes_and_mode_aware_profiles_are_deterministic() -> None:
    """Every case has one valid invocation mode and mode filters preserve profiles."""

    rows = _behavior_case_rows()
    modes: dict[str, str] = {}
    for case_id, (_, cells) in rows.items():
        driver_mode, stimulus_origin, activation_mode, initial_root, delegated, route = (
            _invocation_fields(cells)
        )
        assert driver_mode in {"manual", "automatic", "not-applicable"}
        assert activation_mode in {"implicit", "explicit", "generated-prompt", "lifecycle"}
        assert initial_root
        assert delegated
        assert route
        if driver_mode == "not-applicable":
            assert stimulus_origin in {"generated-prompt", "lifecycle"}
        else:
            assert stimulus_origin == "driving-agent"
        modes[case_id] = driver_mode

    profile_rank = {name: rank for rank, name in enumerate(EXPECTED_PROFILE_TOTALS)}
    automatic_normal = {
        case_id
        for case_id, (_, cells) in rows.items()
        if modes[case_id] == "automatic" and profile_rank[cells[1]] <= profile_rank["normal"]
    }
    assert automatic_normal == {
        "ACT-001",
        "ACT-002",
        "ACT-003",
        "ACT-005",
        "LOOP-001",
        "LOOP-008",
        "SHR-009",
    }


def test_behavior_driver_stimuli_and_root_oracles_enforce_invocation_boundaries() -> None:
    """Automatic discovery and manual direct invocation cannot be mislabeled."""

    rows = _behavior_case_rows()
    explicit_only_initial_roots = {
        "houmao-admin-welcome",
        "houmao-shared-routines",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
    }
    matrix_manual_cases = {"ACT-004"}
    for case_id, (_, cells) in rows.items():
        driver_mode, _, _, initial_root, delegated, _ = _invocation_fields(cells)
        stimulus = _case_stimulus(case_id, cells)
        if driver_mode == "automatic":
            assert "$houmao-" not in stimulus
            assert initial_root not in explicit_only_initial_roots
            assert "houmao-admin-welcome" not in delegated
        elif driver_mode == "manual" and case_id not in matrix_manual_cases:
            assert "$houmao-" in stimulus

    activation = (BEHAVIOR_ROOT / "references/cases/activation.md").read_text(encoding="utf-8")
    assert "$houmao-admin-welcome help` | `houmao-admin-welcome`" in activation
    assert "ACT-005/informational" in activation
    assert "without identity verification" in activation
    assert "exact fresh identity before substantive route selection" in activation
    assert "Prompt claims must not select the opposite actor root" in activation


def test_behavior_generated_and_combined_context_cases_keep_distinct_provenance() -> None:
    """Generated/lifecycle origins and combined-pack actors remain explicit contracts."""

    rows = _behavior_case_rows()
    for case_id in {"AUTO-001", "AUTO-002", "PRM-001", "PRM-002", "PRM-003"}:
        driver_mode, origin, _, _, _, _ = _invocation_fields(rows[case_id][1])
        assert driver_mode == "not-applicable"
        assert origin in {"generated-prompt", "lifecycle"}

    fixture_contexts = (BEHAVIOR_ROOT / "references/fixture-contexts.md").read_text(
        encoding="utf-8"
    )
    assert "`raw-admin-combined`" in fixture_contexts
    assert "https://github.com/igamenovoer/houmao-skills#<houmao-release-tag>" in fixture_contexts
    assert "latest-stable discovery" in fixture_contexts
    assert "`managed-agent-combined`" in fixture_contexts
    assert "live attempts as explicit maintainer-run, credential-gated qualification" in (
        fixture_contexts
    )

    generated = (BEHAVIOR_ROOT / "references/cases/generated-prompts.md").read_text(
        encoding="utf-8"
    )
    bootstrap = (BEHAVIOR_ROOT / "references/cases/managed-bootstrap.md").read_text(
        encoding="utf-8"
    )
    assert "DO NOT report generated prompt delivery as automatic driver-origin" in generated
    assert "DO NOT report lifecycle prompt loading as automatic driver-origin" in bootstrap


def test_behavior_tags_and_matrix_variants_are_stable() -> None:
    """Legacy diagnostic views and existing matrix cells remain selectable."""
    catalog = (BEHAVIOR_ROOT / "references" / "case-catalog.md").read_text(encoding="utf-8")
    for tag, expected_cases in EXPECTED_TAG_CASES.items():
        line = next(line for line in catalog.splitlines() if line.startswith(f"- `{tag}`:"))
        actual_cases = set(re.findall(r"`((?:ACT|AUTO|ADM|AGT|SHR|LOOP|PRM)-\d{3})`", line))
        assert actual_cases == expected_cases

    area_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((BEHAVIOR_ROOT / "references" / "cases").glob("*.md"))
    )
    for case_id, variants in EXPECTED_CASE_VARIANTS.items():
        for variant in variants:
            assert f"`{case_id}/{variant}`" in area_text

    admin_text = (BEHAVIOR_ROOT / "references" / "cases" / "admin-routing.md").read_text(
        encoding="utf-8"
    )
    agent_text = (BEHAVIOR_ROOT / "references" / "cases" / "managed-agent-routing.md").read_text(
        encoding="utf-8"
    )
    generated_text = (BEHAVIOR_ROOT / "references" / "cases" / "generated-prompts.md").read_text(
        encoding="utf-8"
    )
    assert "`PRM-005`" in admin_text and "`PRM-005`" not in generated_text
    assert "`PRM-004`" in agent_text and "`PRM-004`" not in generated_text


def test_behavior_verdict_vocabulary_is_complete() -> None:
    """Attempt dimensions and aggregate outcomes remain explicit and non-majoritarian."""
    rubric = (BEHAVIOR_ROOT / "references" / "verdict-rubric.md").read_text(encoding="utf-8")
    for dimension in ("activation", "routing", "actor", "gates", "effects", "outcome"):
        assert f"`{dimension}`" in rubric
    for attempt_status in ("pass", "fail", "incomplete", "unobservable"):
        assert f"`{attempt_status}`" in rubric
    for aggregate in (
        "stable-pass",
        "flaky",
        "stable-fail",
        "inconclusive",
        "behavior-pass-activation-unobserved",
    ):
        assert f"`{aggregate}`" in rubric
    assert "Do not use majority vote" in rubric


def test_manifest_routes_have_committed_behavior_coverage() -> None:
    """Every current actor-entrypoint route occurs in the static coverage matrix."""
    manifest = _manifest_payload()
    standalone = {record["name"]: record for record in manifest["standalone_skills"]}
    route_coverage = (BEHAVIOR_ROOT / "references" / "cases" / "shared-routines.md").read_text(
        encoding="utf-8"
    )
    for entrypoint_name in ("houmao-admin-entrypoint", "houmao-agent-entrypoint"):
        for route in standalone[entrypoint_name]["commands"]:
            assert f"| `{route}` |" in route_coverage, (
                f"missing behavior coverage for {entrypoint_name} route {route}"
            )


def test_tui_skill_preserves_workflow_and_launcher_boundary() -> None:
    """The renamed TUI skill retains its command and delegated-launch contracts."""
    skill_text = (TUI_ROOT / "SKILL.md").read_text(encoding="utf-8")
    listed_commands = set(re.findall(r"^\| `([^`]+)` \|", skill_text, flags=re.MULTILINE))
    assert listed_commands == EXPECTED_TUI_COMMANDS
    assert "houmao-dev-launch-agents" in skill_text
    assert "tmp/houmao-dev-tui-testing/<run-id>/" in skill_text
    assert "houmao-dev-testing" not in skill_text


def test_development_skills_are_excluded_from_runtime_manifest() -> None:
    """Development qualification skills never become runtime pack members."""
    manifest = _manifest_payload()
    standalone_names = {record["name"] for record in manifest["standalone_skills"]}
    assert standalone_names == EXPECTED_PUBLIC_SYSTEM_SKILLS
    assert "houmao-dev-behavior-testing" not in MANIFEST_PATH.read_text(encoding="utf-8")
    assert "houmao-dev-tui-testing" not in MANIFEST_PATH.read_text(encoding="utf-8")


def test_current_qualification_material_has_no_stale_broad_name() -> None:
    """Current development and qualification docs use the unambiguous TUI identity."""
    scanned_roots = (DEV_ROOT, REPO_ROOT / "scripts" / "qualification")
    stale_paths = [
        path.relative_to(REPO_ROOT)
        for root in scanned_roots
        for path in root.rglob("*")
        if path.is_file()
        and "houmao-dev-testing" in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert stale_paths == []
