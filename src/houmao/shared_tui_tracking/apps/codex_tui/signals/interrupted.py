"""Codex TUI interruption detection helpers."""

from __future__ import annotations

from houmao.shared_tui_tracking.surface import SurfaceView


CODEX_INTERRUPTED_TEXT = (
    "Conversation interrupted - tell the model what to do differently. "
    "Something went wrong? Hit `/feedback` to report the issue."
)
CODEX_STEER_INTERRUPTION_TEXT = "Model interrupted to submit steer instructions."


def is_interrupted_surface(
    *,
    surface: SurfaceView,
    prompt_visible: bool,
    active_status_row_visible: bool,
) -> bool:
    """Return whether the current Codex surface matches the exact interruption rule."""

    stripped_text = "\n".join(surface.stripped_lines)
    return (
        CODEX_INTERRUPTED_TEXT in stripped_text and prompt_visible and not active_status_row_visible
    )
