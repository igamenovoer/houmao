"""Kimi Code shared TUI tracking profile."""

from houmao.shared_tui_tracking.apps.kimi_code.profile import (
    KimiCodeSignalDetector,
    KimiCodeSignalDetectorV2_1_X,
    KimiSurfaceAnalysis,
    analyze_kimi_surface,
    kimi_goal_start_prompt_present,
    kimi_question_dialog_present,
    kimi_startup_modal_present,
    kimi_trust_modal_present,
)

__all__ = [
    "KimiCodeSignalDetector",
    "KimiCodeSignalDetectorV2_1_X",
    "KimiSurfaceAnalysis",
    "analyze_kimi_surface",
    "kimi_goal_start_prompt_present",
    "kimi_question_dialog_present",
    "kimi_startup_modal_present",
    "kimi_trust_modal_present",
]
