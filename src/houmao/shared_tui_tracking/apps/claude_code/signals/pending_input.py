"""Claude pending-input detection from the composer placeholder payload."""

from __future__ import annotations

from houmao.shared_tui_tracking.apps.claude_code.signals.prompt_behavior import (
    PromptAreaSnapshot,
)
from houmao.shared_tui_tracking.models import Tristate
from houmao.shared_tui_tracking.surface import SurfaceView


_QUEUE_PLACEHOLDER = "press up to edit queued messages"


def pending_input_state(
    *,
    surface: SurfaceView,
    composer: PromptAreaSnapshot,
) -> Tristate:
    """Return whether Claude renders queued input behind the active turn.

    Claude 2.1.296 renders the queued state as the composer's own placeholder
    payload (``Press up to edit queued messages``); a positive match reads
    that bounded label on the current composer. A complete visible composer
    without the hint reports ``no``; a missing composer degrades to
    ``unknown``.
    """

    del surface
    if not composer.prompt_visible:
        return "unknown"
    payload = (composer.payload_text or "").strip().lower()
    if _QUEUE_PLACEHOLDER in payload:
        return "yes"
    return "no"
