from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_loop_authoring_docs_cover_pairwise_v2_v3_and_v4_modes() -> None:
    """Guard loop-authoring docs for the pairwise-v2 baseline and v3/v4 extensions."""

    guide = (REPO_ROOT / "docs/getting-started/loop-authoring.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    system_skills = (REPO_ROOT / "docs/getting-started/system-skills-overview.md").read_text(
        encoding="utf-8"
    )

    assert "The default strategy is `precomputed_routing_packets`" in guide
    assert "Houmao ships five packaged loop skills." in guide
    assert "`houmao-agent-loop-pairwise-v3`" in guide
    assert "`houmao-agent-loop-pairwise-v4`" in guide
    assert "workspace-aware extension of pairwise-v2" in guide
    assert "template-driven source-contract layer" in guide
    assert "strict generated document templates" in guide
    assert "constraint coverage audit" in guide
    assert "workspace_contract:" in guide
    assert "mode: standard | custom" in guide
    assert "houmao-ws/<task-name>" in guide
    assert "`houmao-utils-workspace-mgr` remains the standard workspace-preparation skill" in guide
    assert "loop-runs/pairwise-v2/<run_id>/initialize.md" in guide
    assert "`start` then writes the master-facing `start-charter` page" in guide
    assert "loop-runs/pairwise-v2/<run_id>/record.json" in guide
    assert "pause-only `resume`" in guide
    assert "`recover_and_continue`" in guide
    assert "loop-runs/pairwise-v2/<run_id>/recover-and-continue.md" in guide
    assert "compact control-plane trigger" in guide
    assert "verifies or enables gateway mail-notifier behavior" in guide
    assert "default initialize-time gateway mail-notifier readiness" in readme
    assert "pairwise-v4 template-driven source contract" in readme
    assert "verify or enable gateway mail-notifier behavior" in system_skills
    assert "source-contract authoring" in system_skills
    assert "email_initialization" not in guide
