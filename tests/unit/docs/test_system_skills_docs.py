from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_system_skill_help_docs_cover_standard_convention() -> None:
    """Guard docs that introduce explicit system-skill help."""

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_index = (REPO_ROOT / "docs/index.md").read_text(encoding="utf-8")
    overview = (REPO_ROOT / "docs/getting-started/system-skills-overview.md").read_text(
        encoding="utf-8"
    )
    cli_reference = (REPO_ROOT / "docs/reference/cli/system-skills.md").read_text(encoding="utf-8")

    system_skills_collection = "igamenovoer/tool-skills/houmao"

    assert "Recommended when `npx` is available and the target machine has internet access" in (
        readme
    )
    assert f"npx skills add {system_skills_collection}" in readme
    assert "choose which packaged skill(s) to install from the prompt" in readme
    assert "working offline from" in readme
    assert "an installed Houmao package" in readme
    assert "subset skills, explicit homes, symlink/copy projection, or retired-skill cleanup" in (
        readme
    )
    assert "Each installed Houmao system skill also supports explicit read-only help" in readme
    assert "$houmao-touring help" in readme
    assert "$houmao-agent-email-comms help" in readme
    assert "separate from the `houmao-mgr system-skills install` CLI surface" in readme
    assert "beginner setup, intermediate live operation, and advanced coordination" in readme

    assert f"npx skills add {system_skills_collection}" in docs_index
    assert "offline/package-local or customized installs" in docs_index
    assert "invoke `houmao-touring` or ask `$houmao-touring help`" in docs_index
    assert "Run `houmao-mgr system-skills install --tool claude`" not in docs_index

    assert "## Installation Choices" in overview
    assert f"npx skills add {system_skills_collection}" in overview
    assert "small release-synced `igamenovoer/tool-skills` repository" in overview
    assert "not at the full Houmao source repository" in overview
    assert "Use Houmao's own installer when `npx` is unavailable" in overview
    assert "named sets, subset skills, explicit homes, symlink/copy projection" in overview
    assert "Managed launch and join are separate from these explicit user-driven" in overview
    assert "Managed launch defaults to the same `core` selection" in overview
    assert "managed system-skill policy that extends, replaces, or disables" in overview
    assert "uses the catalog's `all` set" in overview
    assert "Every current packaged Houmao system skill supports explicit skill-level help" in (
        overview
    )
    assert "read-only summary" in overview
    assert "do not run commands, mutate files, send mail" in overview
    assert "Explicit help or usage requests are handled before normal workflow routing" in overview
    assert '"help me send mail to this agent"' in overview
    assert "teaches Houmao in stages" in overview
    assert "offers stage-aware next actions" in overview

    assert "This page documents `houmao-mgr system-skills` command behavior" in cli_reference
    assert f"npx skills add {system_skills_collection}" in cli_reference
    assert "adjacent install guidance" in cli_reference
    assert "$houmao-touring help" in cli_reference
    assert "$houmao-agent-email-comms help" in cli_reference
    assert "not a `houmao-mgr system-skills help` subcommand" in cli_reference
    assert "├── list" in cli_reference
    assert "├── status --tool <tool> [--home <path>]" in cli_reference
    assert "├── install --tool <tool>[,<tool>...]" in cli_reference
    assert "└── uninstall --tool <tool>[,<tool>...]" in cli_reference
