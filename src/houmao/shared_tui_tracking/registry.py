"""Tracker-local app and detector profile registry."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from houmao.shared_tui_tracking.detectors import (
    BaseTrackedTurnSignalDetector,
    ClaudeCodeSignalDetectorV2_1_X,
    CodexTuiSignalDetectorV0_162_X,
    FallbackClaudeDetector,
    FallbackTrackedTurnSignalDetector,
    KimiCodeSignalDetectorV2_1_X,
)


_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")
# User-facing tool names for floor-gate error messages where the app id would
# misname the tool (the codex tool tracks under the `codex_tui` app id).
_APP_TOOL_NAMES = {"codex_tui": "codex"}


class UnsupportedToolVersionError(ValueError):
    """Raised when a tool's observed version falls below its support floor.

    Apps with a maintained floor-gated profile and no fallback registration
    (currently ``kimi_code`` and ``codex_tui``) resolve to this error instead
    of silently scraping with an unqualified detector.
    """

    def __init__(
        self,
        *,
        app_id: str,
        observed_version: str | None,
        minimum_supported_version: tuple[int, ...],
        version_parseable: bool = True,
        tool_name: str | None = None,
    ) -> None:
        """Build the error naming the version, the floor, and the migration action."""

        self.app_id: str = app_id
        self.observed_version: str | None = observed_version
        self.minimum_supported_version: tuple[int, ...] = minimum_supported_version
        self.version_parseable: bool = version_parseable
        floor_text = ".".join(str(part) for part in minimum_supported_version)
        tool_name = tool_name or app_id.replace("_", "-")
        if observed_version is None:
            detail = f"the {tool_name} version could not be determined"
        elif version_parseable:
            detail = f"{tool_name} {observed_version} is below the supported floor"
        else:
            detail = f"the {tool_name} version {observed_version!r} could not be parsed"
        super().__init__(
            f"Unsupported {tool_name} version for TUI tracking: {detail}; "
            f"this houmao release supports {tool_name} {floor_text} and later; "
            f"upgrade {tool_name} to {floor_text} or later."
        )


@dataclass(frozen=True)
class DetectorProfileRegistration:
    """One registered detector profile for a supported TUI app."""

    app_id: str
    detector_name: str
    detector_version: str
    minimum_supported_version: tuple[int, ...] | None
    profile_factory: Callable[[], BaseTrackedTurnSignalDetector]
    maximum_supported_version: tuple[int, ...] | None = None
    qualified_through_version: str | None = None

    def __post_init__(self) -> None:
        """Validate one evidence-backed compatibility interval."""

        if self.minimum_supported_version is None:
            if self.maximum_supported_version is not None:
                raise ValueError("Fallback detector registrations cannot define a maximum version.")
            return
        if (
            self.maximum_supported_version is not None
            and self.maximum_supported_version <= self.minimum_supported_version
        ):
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
    qualified_through_version: str | None = None

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
                    detector_version="0.162.x",
                    minimum_supported_version=(0, 162, 1),
                    maximum_supported_version=None,
                    profile_factory=CodexTuiSignalDetectorV0_162_X,
                    qualified_through_version="0.162.1",
                ),
                DetectorProfileRegistration(
                    app_id="kimi_code",
                    detector_name="kimi_code",
                    detector_version="2.1.x",
                    minimum_supported_version=(2, 1, 1),
                    maximum_supported_version=None,
                    profile_factory=KimiCodeSignalDetectorV2_1_X,
                    qualified_through_version="2.1.1",
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

    def maintained_registration(self, *, app_id: str) -> DetectorProfileRegistration | None:
        """Return the app's maintained (non-fallback) registration, when one exists."""

        return next(
            (
                item
                for item in self.m_registrations
                if item.app_id == app_id and item.minimum_supported_version is not None
            ),
            None,
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
                observed_version_text=observed_version,
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
            qualified_through_version=selected.qualified_through_version,
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
    observed_version_text: str | None = None,
) -> DetectorProfileRegistration:
    """Select the closest-compatible profile from one registration set.

    Raises
    ------
    UnsupportedToolVersionError
        When the app has floor-gated registrations but no fallback and the
        observed version is missing/unparseable or below every floor.
    """

    fallback = next(
        (item for item in registrations if item.minimum_supported_version is None), None
    )
    if observed_version is None:
        if fallback is not None:
            return fallback
        raise _unsupported_version_error(
            registrations=registrations,
            observed_version_tuple=None,
            observed_version_text=observed_version_text,
        )

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
    if fallback is not None:
        return fallback
    raise _unsupported_version_error(
        registrations=registrations,
        observed_version_tuple=observed_version,
        observed_version_text=observed_version_text,
    )


def _unsupported_version_error(
    *,
    registrations: tuple[DetectorProfileRegistration, ...],
    observed_version_tuple: tuple[int, ...] | None,
    observed_version_text: str | None,
) -> UnsupportedToolVersionError:
    """Build the floor-gate error for one registration set with no fallback."""

    floor = min(
        item.minimum_supported_version
        for item in registrations
        if item.minimum_supported_version is not None
    )
    if observed_version_tuple is not None:
        observed_text: str | None = ".".join(str(part) for part in observed_version_tuple)
        parseable = True
    else:
        observed_text = observed_version_text
        parseable = False
    return UnsupportedToolVersionError(
        app_id=registrations[0].app_id,
        observed_version=observed_text,
        minimum_supported_version=floor,
        version_parseable=parseable,
        tool_name=_APP_TOOL_NAMES.get(registrations[0].app_id),
    )
