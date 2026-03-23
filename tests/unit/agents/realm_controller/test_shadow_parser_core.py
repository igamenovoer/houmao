from __future__ import annotations

import re

import pytest

from houmao.agents.realm_controller.backends.shadow_parser_core import find_prompt_boundary


@pytest.mark.parametrize(
    ("tail_lines", "expected_index"),
    [
        (["no", "anchors", "here"], None),
        (["anchor", "middle", "anchor"], 2),
        (["anchor", "other", "lines"], 0),
        (["other", "lines", "anchor"], 2),
    ],
)
def test_find_prompt_boundary_handles_edge_cases(
    tail_lines: list[str],
    expected_index: int | None,
) -> None:
    anchor_patterns = (re.compile(r"^anchor$"),)

    assert find_prompt_boundary(tail_lines, anchor_patterns) == expected_index
