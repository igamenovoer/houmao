"""Shared detector/profile contracts plus compatibility exports."""

from __future__ import annotations

import abc
from collections.abc import Sequence

from houmao.shared_tui_tracking.models import (
    DetectedTurnSignals,
    ParsedSurfaceContext,
    RecentProfileFrame,
    TemporalHintSignals,
)


class BaseTrackedTurnSignalDetector(abc.ABC):
    """Abstract detector/profile for one tracked-TUI app family."""

    @property
    def temporal_window_seconds(self) -> float:
        """Return the recent-window duration used by this profile."""

        return 0.0

    @abc.abstractmethod
    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return normalized tracked turn signals for one visible surface."""

    def build_temporal_frame(
        self,
        *,
        output_text: str | None,
        signals: DetectedTurnSignals,
        observed_at_seconds: float,
    ) -> object | None:
        """Return one profile-private frame for recent-window inference."""

        del output_text
        del signals
        del observed_at_seconds
        return None

    def derive_temporal_hints(
        self,
        *,
        recent_frames: Sequence[RecentProfileFrame],
    ) -> TemporalHintSignals:
        """Return recent-window lifecycle hints for the selected profile."""

        del recent_frames
        return TemporalHintSignals()


class BaseVersionedClaudeDetector(BaseTrackedTurnSignalDetector, abc.ABC):
    """Abstract Claude detector with version scoring."""

    @property
    @abc.abstractmethod
    def detector_name(self) -> str:
        """Return the detector family name."""

    @property
    @abc.abstractmethod
    def detector_version(self) -> str:
        """Return the detector version selector."""

    @abc.abstractmethod
    def compatibility_score(self, *, observed_version: str | None) -> int:
        """Return a higher score for a closer-compatible version match."""


from houmao.shared_tui_tracking.apps.claude_code.profile import (  # noqa: E402
    ClaudeCodeSignalDetectorV2_1_X,
    FallbackClaudeDetector,
)
from houmao.shared_tui_tracking.apps.codex_tui.profile import (  # noqa: E402
    CodexTrackedTurnSignalDetector,
    CodexTuiSignalDetector,
)
from houmao.shared_tui_tracking.apps.unsupported_tool.profile import (  # noqa: E402
    FallbackTrackedTurnSignalDetector,
)

__all__ = [
    "BaseTrackedTurnSignalDetector",
    "BaseVersionedClaudeDetector",
    "ClaudeCodeSignalDetectorV2_1_X",
    "CodexTrackedTurnSignalDetector",
    "CodexTuiSignalDetector",
    "FallbackClaudeDetector",
    "FallbackTrackedTurnSignalDetector",
    "select_claude_detector",
    "select_tracked_turn_signal_detector",
]


def select_claude_detector(*, observed_version: str | None) -> BaseTrackedTurnSignalDetector:
    """Return the closest-compatible Claude detector for one observed version."""

    from houmao.shared_tui_tracking.registry import DetectorProfileRegistry

    resolved = DetectorProfileRegistry.default().resolve(
        app_id="claude_code",
        observed_version=observed_version,
    )
    return resolved.profile


def select_tracked_turn_signal_detector(
    *,
    tool: str,
    observed_version: str | None = None,
) -> BaseTrackedTurnSignalDetector:
    """Return the best available detector/profile for one official/runtime tool."""

    from houmao.shared_tui_tracking.registry import DetectorProfileRegistry, app_id_from_tool

    resolved = DetectorProfileRegistry.default().resolve(
        app_id=app_id_from_tool(tool=tool),
        observed_version=observed_version,
    )
    return resolved.profile
