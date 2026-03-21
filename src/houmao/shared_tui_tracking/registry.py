"""Tracker-local app and detector profile registry."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from houmao.shared_tui_tracking.detectors import (
    BaseTrackedTurnSignalDetector,
    ClaudeCodeSignalDetectorV2_1_X,
    CodexTrackedTurnSignalDetector,
    FallbackClaudeDetector,
    FallbackTrackedTurnSignalDetector,
)


_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


@dataclass(frozen=True)
class DetectorProfileRegistration:
    """One registered detector profile for a supported TUI app."""

    app_id: str
    detector_name: str
    detector_version: str
    minimum_supported_version: tuple[int, ...] | None
    detector_factory: Callable[[], BaseTrackedTurnSignalDetector]


@dataclass(frozen=True)
class ResolvedDetectorProfile:
    """Resolved detector profile for one tracker session."""

    app_id: str
    detector_name: str
    detector_version: str
    minimum_supported_version: tuple[int, ...] | None
    detector: BaseTrackedTurnSignalDetector


class DetectorProfileRegistry:
    """Resolve supported TUI apps to closest-compatible detector profiles."""

    def __init__(self, *, registrations: tuple[DetectorProfileRegistration, ...]) -> None:
        """Initialize one registry instance."""

        self.m_registrations: tuple[DetectorProfileRegistration, ...] = registrations

    @classmethod
    def default(cls) -> "DetectorProfileRegistry":
        """Return the repository-default detector registry."""

        return cls(
            registrations=(
                DetectorProfileRegistration(
                    app_id="claude_code",
                    detector_name="claude_code",
                    detector_version="2.1.x",
                    minimum_supported_version=(2, 1, 0),
                    detector_factory=ClaudeCodeSignalDetectorV2_1_X,
                ),
                DetectorProfileRegistration(
                    app_id="claude_code",
                    detector_name="claude_code",
                    detector_version="fallback",
                    minimum_supported_version=None,
                    detector_factory=FallbackClaudeDetector,
                ),
                DetectorProfileRegistration(
                    app_id="codex_app_server",
                    detector_name="codex_app_server",
                    detector_version="builtin",
                    minimum_supported_version=None,
                    detector_factory=CodexTrackedTurnSignalDetector,
                ),
                DetectorProfileRegistration(
                    app_id="unsupported_tool",
                    detector_name="unsupported_tool",
                    detector_version="builtin",
                    minimum_supported_version=None,
                    detector_factory=FallbackTrackedTurnSignalDetector,
                ),
            )
        )

    def resolve(
        self,
        *,
        app_id: str,
        observed_version: str | None,
    ) -> ResolvedDetectorProfile:
        """Resolve one app id and observed version to the best detector profile."""

        candidates = [
            item for item in self.m_registrations if item.app_id == app_id
        ] or [
            item for item in self.m_registrations if item.app_id == "unsupported_tool"
        ]
        observed_version_tuple = _parse_version(observed_version)
        selected = _select_best_registration(
            registrations=tuple(candidates),
            observed_version=observed_version_tuple,
        )
        return ResolvedDetectorProfile(
            app_id=selected.app_id,
            detector_name=selected.detector_name,
            detector_version=selected.detector_version,
            minimum_supported_version=selected.minimum_supported_version,
            detector=selected.detector_factory(),
        )


def app_id_from_tool(*, tool: str) -> str:
    """Map one legacy tool identifier to the tracker-local app identifier."""

    if tool == "claude":
        return "claude_code"
    if tool == "codex":
        return "codex_app_server"
    return "unsupported_tool"


def _parse_version(version_text: str | None) -> tuple[int, ...] | None:
    """Parse one optional semantic version prefix."""

    if version_text is None:
        return None
    match = _VERSION_RE.search(version_text)
    if match is None:
        return None
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3) or 0)
    return (major, minor, patch)


def _select_best_registration(
    *,
    registrations: tuple[DetectorProfileRegistration, ...],
    observed_version: tuple[int, ...] | None,
) -> DetectorProfileRegistration:
    """Select the closest-compatible profile from one registration set."""

    fallback = next((item for item in registrations if item.minimum_supported_version is None), None)
    if observed_version is None:
        return fallback or registrations[0]

    compatible = [
        item
        for item in registrations
        if item.minimum_supported_version is not None
        and item.minimum_supported_version <= observed_version
    ]
    if compatible:
        return max(compatible, key=lambda item: item.minimum_supported_version or (0, 0, 0))
    return fallback or registrations[0]
