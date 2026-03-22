"""Codex TUI interruption detection helpers."""

from __future__ import annotations

import re
from collections.abc import Sequence

from houmao.shared_tui_tracking.surface import SurfaceView


CODEX_INTERRUPTED_TEXT = (
    "Conversation interrupted - tell the model what to do differently. "
    "Something went wrong? Hit `/feedback` to report the issue."
)
CODEX_STEER_INTERRUPTION_TEXT = "Model interrupted to submit steer instructions."
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_wrapped_text(value: str) -> str:
    """Return one whitespace-normalized surface string."""

    return _WHITESPACE_RE.sub(" ", value).strip()


def interrupted_text_visible(*, surface: SurfaceView) -> bool:
    """Return whether the interrupted banner is visible despite line wrapping."""

    return _normalize_wrapped_text(CODEX_INTERRUPTED_TEXT) in _normalize_wrapped_text(
        "\n".join(surface.stripped_lines)
    )


def steer_interruption_text_visible(*, lines: Sequence[str]) -> bool:
    """Return whether the steer-handoff interruption text is visible despite wrapping."""

    return _normalize_wrapped_text(CODEX_STEER_INTERRUPTION_TEXT) in _normalize_wrapped_text(
        "\n".join(lines)
    )


def is_interrupted_surface(
    *,
    surface: SurfaceView,
    prompt_visible: bool,
    active_status_row_visible: bool,
) -> bool:
    """Return whether the current Codex surface matches the exact interruption rule."""

    return interrupted_text_visible(
        surface=surface
    ) and prompt_visible and not active_status_row_visible
