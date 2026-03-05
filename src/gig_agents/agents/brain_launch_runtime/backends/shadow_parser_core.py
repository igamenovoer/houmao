"""Shared runtime shadow-parser contracts, helpers, and preset resolution."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Callable, Final, Literal

ShadowStatus = Literal["processing", "waiting_user_answer", "completed", "idle", "unknown"]
ShadowRuntimeStatus = Literal[
    "processing",
    "waiting_user_answer",
    "completed",
    "idle",
    "unknown",
    "stalled",
]

ANOMALY_UNKNOWN_VERSION_FLOOR_USED: Final[str] = "unknown_version_floor_used"
ANOMALY_BASELINE_INVALIDATED: Final[str] = "baseline_invalidated"
ANOMALY_PRESET_OVERRIDE_USED: Final[str] = "preset_override_used"
ANOMALY_STALLED_ENTERED: Final[str] = "stalled_entered"
ANOMALY_STALLED_RECOVERED: Final[str] = "stalled_recovered"

_ANSI_ESCAPE_PATTERN: Final[str] = r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
_ANSI_ESCAPE_RE: Final[re.Pattern[str]] = re.compile(_ANSI_ESCAPE_PATTERN)
_SEMVER_RE: Final[re.Pattern[str]] = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)\s*$")


@dataclass(frozen=True)
class ShadowParserAnomaly:
    """Structured anomaly attached to parser metadata."""

    code: str
    message: str
    details: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ShadowParserMetadata:
    """Provider-agnostic parser metadata for status/extraction results."""

    provider_id: str
    parser_preset_id: str
    parser_preset_version: str
    output_format: str
    output_variant: str
    output_format_match: bool
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
    detected_version: str | None = None
    requested_version: str | None = None
    selection_source: str = "fallback_latest"
    baseline_invalidated: bool = False


@dataclass(frozen=True)
class ShadowParserStatusResult:
    """Classification result for one shadow parser snapshot."""

    status: ShadowStatus
    metadata: ShadowParserMetadata
    waiting_user_answer_excerpt: str | None = None


@dataclass(frozen=True)
class ShadowParserExtractionResult:
    """Extraction result for one shadow parser snapshot."""

    answer_text: str
    metadata: ShadowParserMetadata


class ShadowParserError(RuntimeError):
    """Structured parse error raised by runtime shadow parsers."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "parse_error",
        metadata: ShadowParserMetadata | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.metadata = metadata

    @property
    def output_format(self) -> str:
        """Return output format id from metadata when available."""

        if self.metadata is None:
            return "unknown"
        return self.metadata.output_format

    @property
    def output_format_match(self) -> bool:
        """Return output-format probe match flag from metadata."""

        if self.metadata is None:
            return False
        return self.metadata.output_format_match

    @property
    def output_variant(self) -> str:
        """Return matched output variant id from metadata."""

        if self.metadata is None:
            return "unknown"
        return self.metadata.output_variant

    @property
    def parser_preset_id(self) -> str:
        """Return parser preset id from metadata."""

        if self.metadata is None:
            return "unknown"
        return self.metadata.parser_preset_id


@dataclass(frozen=True)
class VersionedParserPreset:
    """Versioned parser preset identity."""

    preset_id: str
    version: str


@dataclass(frozen=True)
class PresetResolution:
    """Result of version-aware preset selection."""

    preset: VersionedParserPreset
    requested_version: str | None
    detected_version: str | None
    selection_source: str
    anomalies: tuple[ShadowParserAnomaly, ...]


class VersionedPresetRegistry:
    """Resolve parser presets via env override, detection, and floor fallback."""

    def __init__(
        self,
        *,
        provider_id: str,
        override_env_var: str,
        presets: tuple[VersionedParserPreset, ...],
    ) -> None:
        if not presets:
            raise ValueError("presets must not be empty")
        self._provider_id = provider_id
        self._override_env_var = override_env_var
        self._presets_by_version = {preset.version: preset for preset in presets}
        self._sorted_presets = tuple(
            sorted(
                presets,
                key=lambda preset: parse_semver_tuple(preset.version) or (0, 0, 0),
            )
        )
        self._latest = self._sorted_presets[-1]

    @property
    def provider_id(self) -> str:
        """Return provider identifier associated with this registry."""

        return self._provider_id

    @property
    def latest_preset(self) -> VersionedParserPreset:
        """Return the latest known preset."""

        return self._latest

    def resolve(
        self,
        scrollback: str,
        *,
        detect_version: Callable[[str], str | None],
    ) -> PresetResolution:
        """Resolve the preset selection for one output snapshot.

        Parameters
        ----------
        scrollback:
            Raw tool output text.
        detect_version:
            Callable that extracts a version signature from normalized output.

        Returns
        -------
        PresetResolution
            Selected preset and selection diagnostics.
        """

        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        env_override = os.environ.get(self._override_env_var, "").strip()
        detected_version = detect_version(clean_output)
        requested_version = env_override or detected_version

        anomalies: list[ShadowParserAnomaly] = []
        selection_source = "fallback_latest"

        if env_override:
            selection_source = "env_override"
            anomalies.append(
                ShadowParserAnomaly(
                    code=ANOMALY_PRESET_OVERRIDE_USED,
                    message="Preset selection pinned by environment override",
                    details={"env_var": self._override_env_var, "requested": env_override},
                )
            )
        elif detected_version is not None:
            selection_source = "detected_version"

        if requested_version is None:
            return PresetResolution(
                preset=self._latest,
                requested_version=None,
                detected_version=detected_version,
                selection_source=selection_source,
                anomalies=tuple(anomalies),
            )

        exact = self._presets_by_version.get(requested_version)
        if exact is not None:
            return PresetResolution(
                preset=exact,
                requested_version=requested_version,
                detected_version=detected_version,
                selection_source=selection_source,
                anomalies=tuple(anomalies),
            )

        requested_tuple = parse_semver_tuple(requested_version)
        if requested_tuple is None:
            return PresetResolution(
                preset=self._latest,
                requested_version=requested_version,
                detected_version=detected_version,
                selection_source="fallback_latest",
                anomalies=tuple(anomalies),
            )

        floor = self._sorted_presets[0]
        for candidate in self._sorted_presets:
            candidate_tuple = parse_semver_tuple(candidate.version)
            if candidate_tuple is None:
                continue
            if candidate_tuple <= requested_tuple:
                floor = candidate
                continue
            break

        anomalies.append(
            ShadowParserAnomaly(
                code=ANOMALY_UNKNOWN_VERSION_FLOOR_USED,
                message="Detected/overridden version is unknown; using floor preset",
                details={
                    "requested": requested_version,
                    "selected": floor.version,
                    "provider": self._provider_id,
                },
            )
        )

        return PresetResolution(
            preset=floor,
            requested_version=requested_version,
            detected_version=detected_version,
            selection_source="fallback_floor",
            anomalies=tuple(anomalies),
        )


def parse_semver_tuple(value: str) -> tuple[int, int, int] | None:
    """Parse ``X.Y.Z`` semver text into a tuple."""

    match = _SEMVER_RE.match(value)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def strip_ansi(value: str) -> str:
    """Remove ANSI escape sequences from text."""

    return _ANSI_ESCAPE_RE.sub("", value)


def normalize_shadow_output(value: str) -> str:
    """Normalize output for parser matching across providers."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\xa0", " ")


def ansi_stripped_tail_excerpt(scrollback: str, *, max_lines: int = 12) -> str:
    """Return ANSI-stripped tail excerpt for diagnostics."""

    clean_output = normalize_shadow_output(strip_ansi(scrollback))
    lines = clean_output.splitlines()
    if not lines:
        return ""
    excerpt = "\n".join(line.rstrip() for line in lines[-max_lines:] if line.strip())
    return excerpt.strip()
