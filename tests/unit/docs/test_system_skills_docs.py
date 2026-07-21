from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_system_skill_docs_cover_actor_packs_and_receipt_lifecycle() -> None:
    """Guard the public actor surface and pack lifecycle documentation."""

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_index = (REPO_ROOT / "docs/index.md").read_text(encoding="utf-8")
    overview = (REPO_ROOT / "docs/getting-started/system-skills-overview.md").read_text(
        encoding="utf-8"
    )
    cli_reference = (REPO_ROOT / "docs/reference/cli/system-skills.md").read_text(encoding="utf-8")

    for public_name in (
        "houmao-admin-welcome",
        "houmao-admin-entrypoint",
        "houmao-agent-entrypoint",
    ):
        assert public_name in readme
        assert public_name in docs_index
        assert public_name in overview
        assert public_name in cli_reference

    assert "houmao-mgr system-skills install --tool codex --pack admin" in readme
    assert "$houmao-admin-welcome start-guided-tour" in readme
    assert "$houmao-admin-entrypoint help" in readme
    assert "$houmao-agent-entrypoint help" in readme
    assert "Managed launch, relaunch, rebuild, and join select `agent`" in readme
    assert "$houmao-agent-email-comms" not in readme

    assert "Install the admin pack" in docs_index
    assert "$houmao-admin-welcome start-guided-tour" in docs_index
    assert "protected `memory-mgr` route" in docs_index

    assert "## Public Surface" in overview
    assert "## Actor Rules" in overview
    assert "## Admin Welcome" in overview
    assert "## Protected Route Matrix" in overview
    assert "houmao-mgr --print-json agents self identity" in overview
    assert "The only actor transition is explicit joined-session adoption" in overview
    for guided_path in (
        "Single Agent Full Run",
        "Operator-Controlled Agent Team",
        "Pro Agent Loop",
        "Subsystem Exploration",
        "Existing Project Reorientation",
    ):
        assert guided_path in overview

    protected_logical_ids = (
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
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
        "houmao-agent-instance",
        "houmao-agent-inspect",
        "houmao-agent-messaging",
        "houmao-agent-gateway",
        "houmao-interop-ag-ui",
    )
    protected_route_names = (
        "project-mgr",
        "credential-mgr",
        "agent-definition",
        "operator-messaging",
        "process-emails-via-gateway",
        "agent-email-comms",
        "adv-usage-pattern",
        "utils-workspace-mgr",
        "ext-graphing",
        "mailbox-mgr",
        "memory-mgr",
        "agent-loop-pro",
        "agent-loop-lite",
        "agent-instance",
        "agent-inspect",
        "agent-messaging",
        "agent-gateway",
        "interop-ag-ui",
    )
    for route_name in protected_route_names:
        assert f"| `{route_name}` |" in overview
    for logical_id in protected_logical_ids:
        assert f"`{logical_id}`" in cli_reference

    for heading in ("## `list`", "## `install`", "## `status`", "## `upgrade`", "## `uninstall`"):
        assert heading in cli_reference
    assert "<home>/.houmao/system-skills/<tool>/receipt.json" in cli_reference
    for pack_status in ("`absent`", "`complete`", "`incomplete`", "`drifted`", "`conflicting`"):
        assert pack_status in cli_reference
    assert "package-linked" in cli_reference
    assert "digest-matched" in cli_reference
    assert "modified" in cli_reference
    assert "unknown" in cli_reference
    assert "Individual `--skill` and set-based `--set` or `--skill-set` selectors are obsolete" in (
        cli_reference
    )
    assert "Passing `houmao-shared-routines` or a protected logical id to `--pack` fails" in (
        cli_reference
    )
    assert "The receipt disappears when no owned packs remain" in cli_reference


def test_readme_uses_actor_aware_agent_first_onboarding() -> None:
    """Guard the README's agent-first onboarding and actor distinction."""

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    expected_heading_order = [
        "## Quick Start",
        "## Agent-Driven Examples",
        "## Core Concepts",
        "## Agent Loops",
        "## Typical Use Cases",
        "## System Skills: Actor-Aware Entrypoints",
        "## Subsystems at a Glance",
        "## Demos and Examples",
        "## CLI Entry Points",
    ]
    positions = [readme.index(heading) for heading in expected_heading_order]

    assert positions == sorted(positions)
    assert "You: Create a Codex backend reviewer specialist" in readme
    assert "AI: Done." in readme
    assert "attached or discovered its gateway" in readme
    assert "The complete admin pack installs `houmao-admin-welcome`" in readme
    assert "The eighteen maintained routines live inside the protected" in readme
    assert "houmao-admin-entrypoint->houmao-shared-routines->agent-loop-pro" in readme
    assert "Stored specialist and profile policy uses `packs: [admin|agent]`" in readme
    assert "`houmao-auto-system-prompt` remains a separate managed auto skill" in readme
    assert "`houmao-specialist-mgr` may still appear in older installed homes" not in readme
