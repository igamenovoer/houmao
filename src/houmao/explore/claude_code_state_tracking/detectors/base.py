"""Compatibility exports for the shared tracked-TUI detector boundary."""

from houmao.shared_tui_tracking.detectors import (
    BaseTrackedTurnSignalDetector as BaseTurnSignalDetector,
    select_claude_detector,
)
from houmao.shared_tui_tracking.surface import SurfaceView, strip_ansi

__all__ = [
    "BaseTurnSignalDetector",
    "SurfaceView",
    "select_claude_detector",
    "strip_ansi",
]
