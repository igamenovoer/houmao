"""Tests for the reviewed long-horizon operation catalog."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.catalog import (
    default_catalog_path,
    expand_matrix,
    expand_prompt_tokens,
    load_suite_catalog,
)


_REPO_ROOT = Path(__file__).resolve().parents[5]


def test_full_catalog_expands_exact_matrix() -> None:
    """The reviewed provider matrix contains exactly 12 cells and 242 operations."""

    suite = load_suite_catalog(repo_root=_REPO_ROOT)
    plan = expand_matrix(suite=suite)

    assert len(plan.cells) == 12
    assert plan.total_operations == 242
    assert plan.complete_matrix is True
    assert {item.provider for item in plan.cells} == {"claude", "codex", "kimi"}
    assert all("gemini" not in item.cell_id for item in plan.cells)
    assert len({op.event_id for cell in plan.cells for op in cell.operations}) == 242


def test_partial_selection_cannot_be_complete() -> None:
    """A diagnostic cell selection never becomes a full-matrix plan."""

    suite = load_suite_catalog(repo_root=_REPO_ROOT)
    plan = expand_matrix(suite=suite, selected_cells=("codex:st-05",))

    assert [item.cell_id for item in plan.cells] == ["codex:st-05"]
    assert plan.total_operations == 21
    assert plan.complete_matrix is False


def test_stable_operation_ids_include_attempt_number() -> None:
    """Planned event ids correlate provider, procedure, attempt, and operation."""

    suite = load_suite_catalog(repo_root=_REPO_ROOT)
    plan = expand_matrix(
        suite=suite,
        selected_cells=("kimi:st-03",),
        attempt_number=7,
    )

    assert plan.cells[0].operations[0].event_id == "kimi:st-03:attempt-007:op-001"
    assert plan.cells[0].operations[-1].event_id == "kimi:st-03:attempt-007:op-020"


def test_unknown_cell_is_rejected() -> None:
    """The planner rejects providers and procedures outside the reviewed matrix."""

    suite = load_suite_catalog(repo_root=_REPO_ROOT)

    with pytest.raises(ValueError, match="Unknown long-horizon cells"):
        expand_matrix(suite=suite, selected_cells=("gemini:st-01",))


def test_prompt_expansion_accepts_only_reviewed_tokens() -> None:
    """Prompt expansion is complete and rejects undeclared template names."""

    assert (
        expand_prompt_tokens(
            text="{{SAFE}} pane={{PANE}}",
            values={"SAFE": "safe", "PANE": "%1"},
        )
        == "safe pane=%1"
    )
    with pytest.raises(ValueError, match="Unknown long-horizon prompt tokens"):
        expand_prompt_tokens(text="{{OTHER}}", values={"OTHER": "value"})
    with pytest.raises(ValueError, match="Missing long-horizon prompt token values"):
        expand_prompt_tokens(text="{{SAFE}}", values={})


def test_source_document_drift_is_rejected(tmp_path: Path) -> None:
    """Catalog loading stops when the reviewed UC-02 source changes."""

    payload = json.loads(default_catalog_path(repo_root=_REPO_ROOT).read_text(encoding="utf-8"))
    source_path = tmp_path / payload["source_path"]
    source_path.parent.mkdir(parents=True)
    source_path.write_text("changed", encoding="utf-8")
    catalog_path = tmp_path / "suite.json"
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="source digest differs"):
        load_suite_catalog(repo_root=tmp_path, catalog_path=catalog_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload["procedures"][0]["operations"].pop(), "must contain 20"),
        (
            lambda payload: payload["procedures"][0]["operations"][0].update(
                {"instruction": "{{OTHER}}"}
            ),
            "unknown tokens",
        ),
        (
            lambda payload: payload["procedures"][0]["operations"][1].update({"number": 1}),
            "not contiguous",
        ),
    ],
)
def test_malformed_catalog_is_rejected(tmp_path: Path, mutation, message: str) -> None:
    """Malformed counts, tokens, and operation numbering fail validation."""

    payload = json.loads(default_catalog_path(repo_root=_REPO_ROOT).read_text(encoding="utf-8"))
    mutation(payload)
    catalog_path = tmp_path / "suite.json"
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_suite_catalog(
            repo_root=_REPO_ROOT,
            catalog_path=catalog_path,
            validate_source_digest=False,
        )
