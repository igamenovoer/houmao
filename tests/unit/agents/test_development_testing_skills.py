"""Structural contracts for Houmao development testing skills."""

from __future__ import annotations

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


def test_behavior_catalog_declares_every_required_case_and_family() -> None:
    """The committed catalog and its family pages expose the complete v1 case set."""
    catalog = (BEHAVIOR_ROOT / "references" / "case-catalog.md").read_text(encoding="utf-8")
    assert "houmao-dev-behavior-cases.v1" in catalog
    catalog_ids = set(re.findall(r"`((?:ACT|AUTO|ADM|AGT|SHR|LOOP|PRM)-\d{3})`", catalog))
    assert catalog_ids == EXPECTED_CASE_IDS

    family_paths = {
        "activation.md",
        "admin-routing.md",
        "managed-agent-routing.md",
        "shared-routines.md",
        "loops.md",
        "generated-prompts.md",
    }
    actual_family_paths = {
        path.name for path in (BEHAVIOR_ROOT / "references" / "cases").glob("*.md")
    }
    assert actual_family_paths == family_paths
    family_text = "\n".join(
        (BEHAVIOR_ROOT / "references" / "cases" / name).read_text(encoding="utf-8")
        for name in sorted(family_paths)
    )
    assert EXPECTED_CASE_IDS <= set(
        re.findall(r"`((?:ACT|AUTO|ADM|AGT|SHR|LOOP|PRM)-\d{3})`", family_text)
    )


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
