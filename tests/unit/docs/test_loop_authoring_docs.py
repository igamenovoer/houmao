from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_loop_authoring_docs_describe_page_backed_pairwise_v2_initialize() -> None:
    """Guard pairwise-v2 loop-authoring docs against email-first regressions."""

    guide = (REPO_ROOT / "docs/getting-started/loop-authoring.md").read_text(encoding="utf-8")

    assert "The default strategy is `precomputed_routing_packets`" in guide
    assert "loop-runs/pairwise-v2/<run_id>/initialize.md" in guide
    assert "`start` then writes the master-facing `start-charter` page" in guide
    assert "loop-runs/pairwise-v2/<run_id>/record.json" in guide
    assert "pause-only `resume`" in guide
    assert "`recover_and_continue`" in guide
    assert "loop-runs/pairwise-v2/<run_id>/recover-and-continue.md" in guide
    assert "compact control-plane trigger" in guide
    assert "it is no longer the default carrier for initialize guidance" in guide
    assert "email_initialization" not in guide
