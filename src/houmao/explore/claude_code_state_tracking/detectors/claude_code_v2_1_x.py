"""Compatibility exports for shared Claude tracked-TUI detectors."""

from houmao.shared_tui_tracking.detectors import (
    ClaudeCodeSignalDetectorV2_1_X,
    FallbackClaudeDetector,
)

__all__ = [
    "ClaudeCodeSignalDetectorV2_1_X",
    "FallbackClaudeDetector",
]
