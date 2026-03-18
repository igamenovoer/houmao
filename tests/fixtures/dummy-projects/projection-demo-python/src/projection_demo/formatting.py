"""Formatting helpers for the projection demo fixture."""

from __future__ import annotations


def render_projection_summary(name: str, values: list[int]) -> str:
    """Render a compact summary line for a named list of values."""

    count = len(values)
    total = sum(values)
    return f"{name}: count={count}, total={total}"
