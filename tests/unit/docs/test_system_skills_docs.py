from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_NAMES = (
    "houmao-admin-welcome",
    "houmao-admin-entrypoint",
    "houmao-agent-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
)
SHARED_CHILDREN = (
    "houmao-project-mgr",
    "houmao-credential-mgr",
    "houmao-agent-definition",
    "houmao-operator-messaging",
    "houmao-process-emails-via-gateway",
    "houmao-agent-email-comms",
    "houmao-adv-usage-pattern",
    "houmao-utils-workspace-mgr",
    "houmao-ext-graphing",
    "houmao-mailbox-mgr",
    "houmao-memory-mgr",
    "houmao-agent-instance",
    "houmao-agent-inspect",
    "houmao-agent-messaging",
    "houmao-agent-gateway",
    "houmao-interop-ag-ui",
)
ADMIN_MEMBERS = (
    "houmao-admin-welcome",
    "houmao-admin-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
)
AGENT_MEMBERS = (
    "houmao-agent-entrypoint",
    "houmao-shared-routines",
    "houmao-agent-loop-pro",
    "houmao-agent-loop-lite",
)


def _read(relative_path: str) -> str:
    """Read one repository document."""

    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_system_skill_docs_match_static_collection_and_pack_membership() -> None:
    """Guard the six-root inventory, pack closure, and shared-child distinction."""

    readme = _read("README.md")
    docs_index = _read("docs/index.md")
    overview = _read("docs/getting-started/system-skills-overview.md")
    cli_reference = _read("docs/reference/cli/system-skills.md")

    for name in PUBLIC_NAMES:
        assert f"| `{name}` |" in readme
        assert f"| `{name}` |" in overview
        assert f"`{name}`" in cli_reference

    assert "six static roots" in docs_index
    assert "six complete, host-discoverable system skills" in readme
    assert "## Static Public Collection" in overview
    assert "six standalone source directories" in cli_reference
    assert "sixteen parent-scoped" in overview
    assert "sixteen parent-scoped" in cli_reference
    for logical_id in SHARED_CHILDREN:
        assert f"`{logical_id}`" in overview
        assert f"| `{logical_id}` |" in cli_reference

    pack_table = overview.split("The two packs contain static top-level siblings:", maxsplit=1)[
        1
    ].split("### Standard Skills CLI", maxsplit=1)[0]
    admin_row = next(line for line in pack_table.splitlines() if line.startswith("| `admin` |"))
    agent_row = next(line for line in pack_table.splitlines() if line.startswith("| `agent` |"))
    for member in ADMIN_MEMBERS:
        assert member in admin_row
    for member in AGENT_MEMBERS:
        assert member in agent_row

    for text in (readme, overview, cli_reference):
        assert "entrypoint-local `subskills/houmao-shared-routines`" not in text
        assert "protected mount" not in text.lower()
        assert "runtime composition" not in text.lower()


def test_system_skill_docs_cover_installation_choices_and_invocation() -> None:
    """Guard manager, Skills CLI, copy-paste, welcome, shared, and loop examples."""

    readme = _read("README.md")
    overview = _read("docs/getting-started/system-skills-overview.md")
    cli_reference = _read("docs/reference/cli/system-skills.md")
    combined = "\n".join((readme, overview, cli_reference))

    assert "houmao-mgr system-skills install --tool codex --pack admin" in readme
    assert "houmao-mgr system-skills install --tool codex --pack agent" in readme
    assert "npx skills add ./src/houmao/agents/assets/system_skills/public --list" in combined
    assert "--skill '*'" in combined
    assert "for houmao_skill_name in" in overview
    assert "Skills CLI installs each selected directory independently" in overview
    assert "do not resolve Houmao dependencies" in cli_reference

    for member in ADMIN_MEMBERS:
        assert f"--skill {member}" in combined
    for member in AGENT_MEMBERS:
        assert f"--skill {member}" in combined

    assert "$houmao-admin-welcome start-guided-tour" in combined
    assert "$houmao-admin-entrypoint agent-inspect" in combined
    assert "$houmao-agent-entrypoint agent-email-comms" in combined
    assert "$houmao-shared-routines agent-inspect" in combined
    assert "$houmao-shared-routines as-agent agent-email-comms" in combined
    assert "$houmao-agent-loop-pro init <loop-dir>" in combined
    assert "$houmao-agent-loop-lite init <loop-dir>" in combined
    assert "Direct calls do not bypass actor eligibility" in cli_reference


def test_system_skill_docs_cover_actor_welcome_and_static_lifecycle() -> None:
    """Guard actor frames, guided paths, v4 receipts, owner sets, and v3 migration."""

    overview = _read("docs/getting-started/system-skills-overview.md")
    cli_reference = _read("docs/reference/cli/system-skills.md")

    assert "houmao-mgr --print-json agents self identity" in overview
    assert "Joined-session adoption is the only admin-to-agent transition" in overview
    assert "Direct loop calls default to admin posture" in overview
    assert "leading `as-agent`" in overview
    for guided_path in (
        "Single Agent Full Run",
        "Operator-Controlled Agent Team",
        "Pro Agent Loop",
        "Subsystem Exploration",
        "Existing Project Reorientation",
    ):
        assert guided_path in overview

    for heading in ("## `list`", "## `install`", "## `status`", "## `upgrade`", "## `uninstall`"):
        assert heading in cli_reference
    assert "<home>/.houmao/system-skills/<tool>/receipt.json" in cli_reference
    assert "houmao-system-skills-receipt.v2" in cli_reference
    assert "non-empty `owning_pack_ids` set" in cli_reference
    for pack_status in ("`absent`", "`complete`", "`incomplete`", "`drifted`", "`conflicting`"):
        assert pack_status in cli_reference
    for classification in ("package-linked", "digest-matched", "modified", "unknown"):
        assert classification in cli_reference
    assert "A v3 composed receipt is `legacy-v3`" in cli_reference
    assert "writes the v4 receipt last" in cli_reference
    assert "removed only after its final owning pack is removed" in cli_reference
    assert "The receipt disappears when no owned packs remain" in cli_reference
    assert "`specialist-mgr` remains" in cli_reference
    assert "`houmao-auto-system-prompt`" in overview


def test_readme_keeps_agent_first_onboarding_and_static_collection_order() -> None:
    """Guard README information architecture while allowing the static refactor."""

    readme = _read("README.md")

    expected_heading_order = [
        "## Quick Start",
        "## Agent-Driven Examples",
        "## Core Concepts",
        "## Agent Loops",
        "## Typical Use Cases",
        "## System Skills: Static Actor-Aware Collection",
        "## Subsystems at a Glance",
        "## Demos and Examples",
        "## CLI Entry Points",
    ]
    positions = [readme.index(heading) for heading in expected_heading_order]

    assert positions == sorted(positions)
    assert "You: Create a Codex backend reviewer specialist" in readme
    assert "AI: Done." in readme
    assert "attached or discovered its gateway" in readme
    assert "The complete admin pack installs five roots" in readme
    assert "The complete agent pack installs four roots" in readme
    assert "Houmao does not assemble skill Markdown at runtime" in readme
    assert "Stored specialist and profile policy uses `packs: [admin|agent]`" in readme
    assert "`houmao-auto-system-prompt` remains a separate managed auto skill" in readme
