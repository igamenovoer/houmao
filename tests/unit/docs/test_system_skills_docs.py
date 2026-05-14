from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_system_skill_help_docs_cover_standard_convention() -> None:
    """Guard docs that introduce explicit system-skill help."""

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    overview = (REPO_ROOT / "docs/getting-started/system-skills-overview.md").read_text(
        encoding="utf-8"
    )

    assert "Each installed Houmao system skill also supports explicit read-only help" in readme
    assert "$houmao-touring help" in readme
    assert "$houmao-agent-email-comms help" in readme
    assert "separate from the `houmao-mgr system-skills install` CLI surface" in readme

    assert "Every current packaged Houmao system skill supports explicit skill-level help" in (
        overview
    )
    assert "read-only summary" in overview
    assert "do not run commands, mutate files, send mail" in overview
    assert "Explicit help or usage requests are handled before normal workflow routing" in overview
    assert '"help me send mail to this agent"' in overview
