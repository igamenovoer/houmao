from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_loop_authoring_docs_cover_pairwise_v2_baseline_and_pairwise_v3_workspace_mode() -> None:
    """Guard loop-authoring docs for the pairwise-v2 baseline and pairwise-v3 extension."""

    guide = (REPO_ROOT / "docs/getting-started/loop-authoring.md").read_text(encoding="utf-8")

    assert "The default strategy is `precomputed_routing_packets`" in guide
    assert "Houmao ships four packaged loop skills." in guide
    assert "`houmao-agent-loop-pairwise-v3`" in guide
    assert "workspace-aware extension of pairwise-v2" in guide
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
    assert "it is no longer the default carrier for initialize guidance" in guide
    assert "email_initialization" not in guide
