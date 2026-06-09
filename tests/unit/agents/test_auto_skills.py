from __future__ import annotations

from pathlib import Path

import yaml

from houmao.agents.auto_skills import (
    AUTO_SKILL_SYSTEM_PROMPT,
    AUTO_SKILL_SYSTEM_PROMPT_REASON,
    load_auto_skill_catalog,
    project_auto_skills_for_home,
    prompt_sha256,
)
from houmao.agents.system_skills import load_system_skill_catalog


def _auto_system_prompt_skill_text() -> str:
    """Return the packaged auto system prompt skill text."""

    return (
        Path("src/houmao/agents/assets/auto_skills") / AUTO_SKILL_SYSTEM_PROMPT / "SKILL.md"
    ).read_text(encoding="utf-8")


def _frontmatter(text: str) -> dict[str, object]:
    """Parse the YAML frontmatter from a skill file."""

    lines = text.splitlines()
    assert lines[0] == "---"
    closing_index = lines.index("---", 1)
    payload = yaml.safe_load("\n".join(lines[1:closing_index]))
    assert isinstance(payload, dict)
    return payload


def test_auto_skill_catalog_is_separate_from_system_skill_catalog() -> None:
    auto_catalog = load_auto_skill_catalog()
    system_catalog = load_system_skill_catalog()

    assert auto_catalog.skill_names == (AUTO_SKILL_SYSTEM_PROMPT,)
    assert AUTO_SKILL_SYSTEM_PROMPT not in system_catalog.skill_names
    assert AUTO_SKILL_SYSTEM_PROMPT not in system_catalog.retired_skill_names


def test_auto_system_prompt_skill_metadata_triggers_startup_invocation() -> None:
    skill_text = _auto_system_prompt_skill_text()
    metadata = _frontmatter(skill_text)

    description = metadata["description"]
    when_to_use = metadata["whenToUse"]

    assert isinstance(description, str)
    assert isinstance(when_to_use, str)
    assert len(description) <= 250
    assert "MUST invoke/read this skill before doing anything else" in description
    assert "MUST invoke it at chat start" in description
    assert "after context compaction, resume, relaunch" in description
    assert "before any task work" in description
    assert "Do not plan, answer, inspect files, or process tasks" in when_to_use
    assert "houmao-mgr agents self system-prompt show" not in description
    assert "houmao-mgr agents self system-prompt show" not in when_to_use


def test_auto_system_prompt_skill_metadata_survives_kimi_listing_truncation() -> None:
    skill_text = _auto_system_prompt_skill_text()
    metadata = _frontmatter(skill_text)
    description = metadata["description"]

    assert isinstance(description, str)
    kimi_listing_line = f"- {AUTO_SKILL_SYSTEM_PROMPT}: {description[:250]}"

    assert "MUST invoke/read this skill before doing anything else" in kimi_listing_line
    assert "MUST invoke it at chat start" in kimi_listing_line
    assert "after context compaction, resume, relaunch" in kimi_listing_line
    assert "before any task work" in kimi_listing_line


def test_project_auto_skills_for_home_copies_packaged_skill_and_records_provenance(
    tmp_path: Path,
) -> None:
    prompt_text = "Use the effective Houmao system prompt."

    result = project_auto_skills_for_home(
        tool="kimi",
        home_path=tmp_path,
        skill_names=(AUTO_SKILL_SYSTEM_PROMPT, AUTO_SKILL_SYSTEM_PROMPT),
        reason=AUTO_SKILL_SYSTEM_PROMPT_REASON,
        prompt_reference="launch_plan.role_injection.prompt",
        prompt_sha256=prompt_sha256(prompt_text),
    )

    skill_path = tmp_path / "skills" / AUTO_SKILL_SYSTEM_PROMPT / "SKILL.md"
    payload = result.to_payload()

    assert skill_path.is_file()
    assert "houmao-mgr agents self system-prompt show --format text" in skill_path.read_text(
        encoding="utf-8"
    )
    assert result.selected_skill_names == (AUTO_SKILL_SYSTEM_PROMPT,)
    assert result.projected_relative_dirs == (f"skills/{AUTO_SKILL_SYSTEM_PROMPT}",)
    assert payload["state"] == "projected"
    assert payload["applied"] is False
    assert payload["destination_root"] == "skills"
    assert payload["reason"] == AUTO_SKILL_SYSTEM_PROMPT_REASON
    assert payload["prompt_reference"] == "launch_plan.role_injection.prompt"
    assert payload["prompt_sha256"] == prompt_sha256(prompt_text)
