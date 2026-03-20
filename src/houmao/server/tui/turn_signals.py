"""Compatibility exports for the shared tracked-TUI detector boundary."""

from houmao.shared_tui_tracking.detectors import (
    BaseTrackedTurnSignalDetector,
    ClaudeCodeSignalDetectorV2_1_X,
    CodexTrackedTurnSignalDetector,
    FallbackClaudeDetector,
    FallbackTrackedTurnSignalDetector,
    select_claude_detector,
    select_tracked_turn_signal_detector,
)
from houmao.shared_tui_tracking.models import DetectedTurnSignals

__all__ = [
    "BaseTrackedTurnSignalDetector",
    "ClaudeCodeSignalDetectorV2_1_X",
    "CodexTrackedTurnSignalDetector",
    "DetectedTurnSignals",
    "FallbackClaudeDetector",
    "FallbackTrackedTurnSignalDetector",
    "select_claude_detector",
    "select_tracked_turn_signal_detector",
]
