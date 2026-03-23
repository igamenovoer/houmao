"""Small calculation helpers for interactive demo prompts."""

from __future__ import annotations


def summarize_numbers(values: list[int]) -> dict[str, int]:
    """Return count and sum for a list of integers."""

    return {
        "count": len(values),
        "total": sum(values),
    }
