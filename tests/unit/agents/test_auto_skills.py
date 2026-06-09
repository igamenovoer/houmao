from __future__ import annotations

from pathlib import Path

from houmao.agents.auto_skills import (
    AUTO_SKILL_SYSTEM_PROMPT,
    AUTO_SKILL_SYSTEM_PROMPT_REASON,
    load_auto_skill_catalog,
    project_auto_skills_for_home,
    prompt_sha256,
)
from houmao.agents.system_skills import load_system_skill_catalog


def test_auto_skill_catalog_is_separate_from_system_skill_catalog() -> None:
    auto_catalog = load_auto_skill_catalog()
    system_catalog = load_system_skill_catalog()

    assert auto_catalog.skill_names == (AUTO_SKILL_SYSTEM_PROMPT,)
    assert AUTO_SKILL_SYSTEM_PROMPT not in system_catalog.skill_names
    assert AUTO_SKILL_SYSTEM_PROMPT not in system_catalog.retired_skill_names


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
