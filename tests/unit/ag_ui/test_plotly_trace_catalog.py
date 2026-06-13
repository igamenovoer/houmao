from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from houmao.ag_ui.plotly_trace_catalog import (
    PLOTLY_2D_TRACE_CATALOG,
    PLOTLY_2D_TRACE_TYPES,
    PLOTLY_EXCLUDED_TRACE_TYPES,
)


def test_plotly_trace_catalog_includes_2d_and_excludes_true_3d_traces() -> None:
    """Catalog coverage follows the Houmao Plotly 2D policy."""

    assert "heatmap" in PLOTLY_2D_TRACE_TYPES
    assert "box" in PLOTLY_2D_TRACE_TYPES
    assert "sankey" in PLOTLY_2D_TRACE_TYPES
    assert "scatterpolar" in PLOTLY_2D_TRACE_TYPES
    assert "candlestick" in PLOTLY_2D_TRACE_TYPES
    assert "scatter3d" not in PLOTLY_2D_TRACE_TYPES
    assert PLOTLY_EXCLUDED_TRACE_TYPES["scatter3d"] == "true_3d_scene_trace"
    assert PLOTLY_EXCLUDED_TRACE_TYPES["surface"] == "true_3d_scene_trace"
    assert PLOTLY_2D_TRACE_CATALOG["sankey"]["binding_paths"]
    assert "link.value" in PLOTLY_2D_TRACE_CATALOG["sankey"]["binding_paths"]


def test_plotly_trace_catalog_generated_artifacts_are_current() -> None:
    """The checked-in Python and TypeScript catalog artifacts must not drift."""

    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, "scripts/generate_plotly_trace_catalog.py", "--check"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
