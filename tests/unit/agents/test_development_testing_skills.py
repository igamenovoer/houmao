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
    *(f"ACT-{index:03d}" for index in range(1, 5)),
    *(f"AUTO-{index:03d}" for index in range(1, 3)),
    *(f"ADM-{index:03d}" for index in range(1, 9)),
    *(f"AGT-{index:03d}" for index in range(1, 9)),
    *(f"SHR-{index:03d}" for index in range(1, 9)),
    *(f"LOOP-{index:03d}" for index in range(1, 8)),
    *(f"PRM-{index:03d}" for index in range(1, 6)),
}
EXPECTED_AREA_CASE_PROFILES = {
    "activation.md": {
        "area": "activation",
        "cases": {
            "ACT-001": "minimal",
            "ACT-002": "minimal",
            "ACT-003": "normal",
            "ACT-004": "normal",
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
EXPECTED_PROFILE_TOTALS = {"minimal": 11, "normal": 22, "extended": 41, "complete": 42}
EXPECTED_TAG_CASES = {
    "critical": {
        "ACT-001",
        "ACT-002",
        "ACT-003",
        "ACT-004",
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
        "LOOP-001",
        "LOOP-002",
        "LOOP-003",
        "PRM-001",
        "PRM-002",
    },
    "actor-boundaries": {
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
        "LOOP-005",
        "LOOP-006",
    },
    "route-coverage": {
        "ADM-003",
        "AGT-002",
        "SHR-003",
        "SHR-004",
        "SHR-005",
        "SHR-006",
        "SHR-007",
        "LOOP-002",
        "LOOP-003",
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
    "AUTO-002": {"resume", "relaunch", "compaction"},
    "SHR-003": {"admin-entrypoint", "agent-entrypoint"},
    "LOOP-004": {"pro-admin", "pro-agent", "lite-admin", "lite-agent"},
    "LOOP-005": {"admin-pro", "agent-lite"},
    "LOOP-006": {"pro", "lite"},
    "LOOP-007": {"pro", "lite"},
    "PRM-003": {"entrypoint-missing", "shared-routines-missing"},
}
EXPECTED_CASE_SEMANTIC_DIGEST = "5067f8a0dc3e085002f25982d4a6b287e9621400fd2058d1aec8a594c7f0fdfb"
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


def _behavior_semantic_digest(rows: dict[str, tuple[Path, list[str]]]) -> str:
    """Hash the stimuli and semantic oracles while excluding profile metadata."""
    semantics: dict[str, tuple[str, str, str, str]] = {}
    for case_id, (_, cells) in rows.items():
        if case_id.startswith(("ACT-", "AUTO-")):
            semantic = (cells[3], cells[4], cells[5], cells[6])
        elif case_id.startswith("ADM-") or case_id == "PRM-005":
            semantic = (cells[2], cells[3], cells[4], cells[5])
        else:
            semantic = (cells[2], cells[4], cells[5], cells[6])
        semantics[case_id] = semantic
    payload = "\n".join(
        "\x1f".join((case_id, *semantics[case_id])) for case_id in sorted(semantics)
    )
    return hashlib.sha256(payload.encode()).hexdigest()


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
    assert "houmao-dev-behavior-cases.v2" in catalog

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
        assert "Case revision: `1` for every listed case." in text
        actual_cases = {
            case_id: cells[1] for case_id, (case_path, cells) in rows.items() if case_path == path
        }
        assert actual_cases == expected["cases"]


def test_behavior_case_semantics_survive_profile_reorganization() -> None:
    """Profile metadata does not change any v1 stimulus or semantic oracle."""
    assert _behavior_semantic_digest(_behavior_case_rows()) == EXPECTED_CASE_SEMANTIC_DIGEST


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
    assert "| `all` | 11 | 22 | 41 | 42 |" in catalog
    for selector in (
        "<area>/<profile>",
        "all/<profile>",
        "tag:<name>",
        "<case-id>/<variant-id>",
    ):
        assert f"`{selector}`" in catalog
    assert "An absent selector never implies `all/normal`" in catalog


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
