"""Tests for the UC-03 replay comparator and readiness-label oracle."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_ROOT = _REPO_ROOT / "scripts" / "qualification" / "tui-prompt-admission"


def _load_script_module(name: str) -> ModuleType:
    """Load one non-package qualification script by its filename."""

    path = _SCRIPT_ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


UC03_LABEL = _load_script_module("uc03_label")
UC03_COMPARATOR = _load_script_module("uc03_classification_test")


def test_diagnostics_precede_retained_surface_rows() -> None:
    """A dead pane stays indeterminate even when its old surface looked active."""

    label = UC03_LABEL.map_public_state_to_uc03_label(
        turn_phase="active",
        surface_ready_posture="no",
        surface_editing_input="no",
        surface_accepting_input="no",
        diagnostics_availability="tui_down",
        active_reasons=["working_status"],
    )

    assert label == UC03_LABEL.Uc03ReadinessLabel.INDETERMINATE


def test_overlay_requires_affirmative_evidence() -> None:
    """Unknown input posture alone does not invent a selector or menu."""

    unknown = UC03_LABEL.map_public_state_to_uc03_label(
        turn_phase="unknown",
        surface_ready_posture="unknown",
        surface_editing_input="unknown",
        surface_accepting_input="unknown",
        diagnostics_availability="available",
        active_reasons=[],
    )
    overlay = UC03_LABEL.map_public_state_to_uc03_label(
        turn_phase="unknown",
        surface_ready_posture="unknown",
        surface_editing_input="unknown",
        surface_accepting_input="no",
        diagnostics_availability="available",
        active_reasons=[],
        ambiguous_interactive_surface=True,
    )

    assert unknown == UC03_LABEL.Uc03ReadinessLabel.INDETERMINATE
    assert overlay == UC03_LABEL.Uc03ReadinessLabel.BUSY_OVERLAY


@pytest.mark.parametrize(
    ("turn_phase", "ready", "editing", "accepting", "active_reasons", "expected"),
    (
        ("active", "no", "no", "no", ["status_row"], "busy_active"),
        ("ready", "yes", "yes", "yes", [], "busy_draft"),
        ("ready", "yes", "no", "yes", [], "ready_immediate"),
    ),
)
def test_core_tracker_samples_map_to_uc03_labels(
    turn_phase: str,
    ready: str,
    editing: str,
    accepting: str,
    active_reasons: list[str],
    expected: str,
) -> None:
    """Active, draft, and immediate-ready samples retain their direct meanings."""

    actual = UC03_LABEL.map_public_state_to_uc03_label(
        turn_phase=turn_phase,
        surface_ready_posture=ready,
        surface_editing_input=editing,
        surface_accepting_input=accepting,
        diagnostics_availability="available",
        active_reasons=active_reasons,
    )

    assert actual.value == expected


def test_mismatch_summary_separates_boundary_and_sustained_runs() -> None:
    """The summary groups only consecutive mismatches and uses elapsed duration."""

    label = UC03_COMPARATOR.Uc03ReadinessLabel

    def _sample(index: int, elapsed_seconds: float) -> object:
        """Build one compact mismatch row."""

        return UC03_COMPARATOR.SampleComparison(
            sample_id=f"s{index:06d}",
            elapsed_seconds=elapsed_seconds,
            tracker_label=label.BUSY_ACTIVE,
            groundtruth_label=label.READY_IMMEDIATE,
            tracker_state={},
            groundtruth_state={},
            sequence_index=index,
        )

    intervals = UC03_COMPARATOR._mismatch_intervals(
        [_sample(1, 0.0), _sample(2, 0.2), _sample(4, 2.0), _sample(5, 3.2)]
    )

    assert [item.classification for item in intervals] == [
        "transition_boundary",
        "sustained",
    ]
    assert [item.sample_count for item in intervals] == [2, 2]


def test_direct_labels_require_approved_independent_provenance(tmp_path: Path) -> None:
    """Direct labels cannot silently reuse unreviewed generated state labels."""

    path = tmp_path / "labels.json"
    path.write_text(
        json.dumps(
            {
                "provenance": {
                    "labeler": "operator-a",
                    "reviewer": "operator-b",
                    "rubric_digest": "sha256:rubric",
                    "review_status": "draft",
                },
                "labels": [
                    {
                        "start_sample_id": "s000001",
                        "end_sample_id": "s000002",
                        "label": "ready_immediate",
                        "visible_evidence": "empty prompt processed a probe immediately",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="approved labeler/reviewer/rubric provenance"):
        UC03_COMPARATOR._load_direct_labels(
            path,
            sample_ids=["s000001", "s000002"],
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["provenance"]["review_status"] = "approved"
    path.write_text(json.dumps(payload), encoding="utf-8")

    labels = UC03_COMPARATOR._load_direct_labels(
        path,
        sample_ids=["s000001", "s000002"],
    )

    assert set(labels.values()) == {UC03_COMPARATOR.Uc03ReadinessLabel.READY_IMMEDIATE}
