from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SYSTEM_SKILLS_ROOT = REPO_ROOT / "src/houmao/agents/assets/system_skills"


def test_system_skills_do_not_reference_retired_command_templates() -> None:
    """Packaged skills use direct commands or config drafts, not command templates."""

    retired_terms = (
        "internals command-templates",
        "command-templates",
        "command-template",
        "command templates",
        "template blockers",
        "template id",
        "template ids",
    )

    offenders: list[str] = []
    for path in sorted(SYSTEM_SKILLS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for term in retired_terms:
            if term in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {term}")

    assert offenders == []
