"""Tracker-local app and detector profile registry."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from houmao.shared_tui_tracking.detectors import (
    BaseTrackedTurnSignalDetector,
    ClaudeCodeSignalDetectorV2_1_X,
    CodexTuiSignalDetectorV0_116_X,
    FallbackClaudeDetector,
    FallbackCodexTuiSignalDetector,
    FallbackTrackedTurnSignalDetector,
    FallbackKimiCodeSignalDetector,
    KimiCodeSignalDetectorV0_11_X,
    KimiCodeSignalDetectorV0_23_X,
)


_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


@dataclass(frozen=True)
class DetectorProfileRegistration:
    """One registered detector profile for a supported TUI app."""

    app_id: str
    detector_name: str
    detector_version: str
    minimum_supported_version: tuple[int, ...] | None
    profile_factory: Callable[[], BaseTrackedTurnSignalDetector]
    maximum_supported_version: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        """Validate one evidence-backed compatibility interval."""

        if self.minimum_supported_version is None:
            if self.maximum_supported_version is not None:
                raise ValueError("Fallback detector registrations cannot define a maximum version.")
            return
        if self.maximum_supported_version is None:
            raise ValueError(
                "Maintained detector registrations require an exclusive maximum version."
            )
        if self.maximum_supported_version <= self.minimum_supported_version:
            raise ValueError("Detector maximum version must be greater than its minimum version.")


@dataclass(frozen=True)
class ResolvedDetectorProfile:
    """Resolved detector profile for one tracker session."""

    app_id: str
    detector_name: str
    detector_version: str
    minimum_supported_version: tuple[int, ...] | None
    maximum_supported_version: tuple[int, ...] | None
    profile: BaseTrackedTurnSignalDetector

    @property
    def detector(self) -> BaseTrackedTurnSignalDetector:
        """Return the resolved profile through the legacy detector name."""

        return self.profile


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
                    maximum_supported_version=(2, 2, 0),
                    profile_factory=ClaudeCodeSignalDetectorV2_1_X,
                ),
                DetectorProfileRegistration(
                    app_id="claude_code",
                    detector_name="claude_code",
                    detector_version="fallback",
                    minimum_supported_version=None,
                    profile_factory=FallbackClaudeDetector,
                ),
                DetectorProfileRegistration(
                    app_id="codex_tui",
                    detector_name="codex_tui",
                    detector_version="0.116.x",
                    minimum_supported_version=(0, 116, 0),
                    maximum_supported_version=(0, 117, 0),
                    profile_factory=CodexTuiSignalDetectorV0_116_X,
                ),
                DetectorProfileRegistration(
                    app_id="codex_tui",
                    detector_name="codex_tui",
                    detector_version="fallback",
                    minimum_supported_version=None,
                    profile_factory=FallbackCodexTuiSignalDetector,
                ),
                DetectorProfileRegistration(
                    app_id="kimi_code",
                    detector_name="kimi_code",
                    detector_version="0.11.x",
                    minimum_supported_version=(0, 11, 0),
                    maximum_supported_version=(0, 12, 0),
                    profile_factory=KimiCodeSignalDetectorV0_11_X,
                ),
                DetectorProfileRegistration(
                    app_id="kimi_code",
                    detector_name="kimi_code",
                    detector_version="0.23.x",
                    minimum_supported_version=(0, 23, 0),
                    maximum_supported_version=(0, 24, 0),
                    profile_factory=KimiCodeSignalDetectorV0_23_X,
                ),
                DetectorProfileRegistration(
                    app_id="kimi_code",
                    detector_name="kimi_code",
                    detector_version="fallback",
                    minimum_supported_version=None,
                    profile_factory=FallbackKimiCodeSignalDetector,
                ),
                DetectorProfileRegistration(
                    app_id="unsupported_tool",
                    detector_name="unsupported_tool",
                    detector_version="builtin",
                    minimum_supported_version=None,
                    profile_factory=FallbackTrackedTurnSignalDetector,
                ),
            )
        )

    def resolve(
        self,
        *,
        app_id: str,
        observed_version: str | None,
        detector_version_override: str | None = None,
    ) -> ResolvedDetectorProfile:
        """Resolve one app id and observed version to the best detector profile."""

        candidates = [item for item in self.m_registrations if item.app_id == app_id] or [
            item for item in self.m_registrations if item.app_id == "unsupported_tool"
        ]
        observed_version_tuple = _parse_version(observed_version)
        if detector_version_override is None:
            selected = _select_best_registration(
                registrations=tuple(candidates),
                observed_version=observed_version_tuple,
            )
        else:
            override_selected = next(
                (item for item in candidates if item.detector_version == detector_version_override),
                None,
            )
            if override_selected is None:
                raise ValueError(
                    f"Detector profile override {detector_version_override!r} is not registered "
                    f"for app {app_id!r}."
                )
            selected = override_selected
        return ResolvedDetectorProfile(
            app_id=selected.app_id,
            detector_name=selected.detector_name,
            detector_version=selected.detector_version,
            minimum_supported_version=selected.minimum_supported_version,
            maximum_supported_version=selected.maximum_supported_version,
            profile=selected.profile_factory(),
        )


def app_id_from_tool(*, tool: str) -> str:
    """Map one legacy tool identifier to the tracker-local app identifier."""

    if tool == "claude":
        return "claude_code"
    if tool == "codex":
        return "codex_tui"
    if tool == "kimi":
        return "kimi_code"
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

    fallback = next(
        (item for item in registrations if item.minimum_supported_version is None), None
    )
    if observed_version is None:
        return fallback or registrations[0]

    compatible = [
        item
        for item in registrations
        if item.minimum_supported_version is not None
        and item.minimum_supported_version <= observed_version
        and (
            item.maximum_supported_version is None
            or observed_version < item.maximum_supported_version
        )
    ]
    if compatible:
        return max(compatible, key=lambda item: item.minimum_supported_version or (0, 0, 0))
    return fallback or registrations[0]
