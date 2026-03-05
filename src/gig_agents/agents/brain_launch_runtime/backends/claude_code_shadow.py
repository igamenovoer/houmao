"""Runtime-owned Claude Code shadow parser for CAO ``mode=full`` output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from .shadow_parser_core import (
    ANOMALY_BASELINE_INVALIDATED,
    PresetResolution,
    ShadowParserAnomaly,
    ShadowParserError,
    ShadowParserMetadata,
    ShadowStatus,
    VersionedParserPreset,
    VersionedPresetRegistry,
    ansi_stripped_tail_excerpt,
    normalize_shadow_output,
    strip_ansi,
)

_BANNER_VERSION_RE: Final[re.Pattern[str]] = re.compile(
    r"(?im)Claude Code v(\d+\.\d+\.\d+)"
)
_WAITING_OPTION_RE: Final[re.Pattern[str]] = re.compile(r"^\s*(?:❯\s*)?\d+\.\s+\S+")
_WAITING_SELECTED_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*❯\s*\d+\.\s+\S+"
)
_WAITING_HINT_RE: Final[re.Pattern[str]] = re.compile(
    r"(select (?:an )?option|choose (?:an )?option|arrow keys|press enter)",
    flags=re.IGNORECASE,
)

_DEFAULT_STATUS_TAIL_LINES: Final[int] = 100
_ENV_PRESET_OVERRIDE: Final[str] = "AGENTSYS_CAO_CLAUDE_CODE_VERSION"

_OUTPUT_VARIANT_PROMPT_IDLE_V1: Final[str] = "claude_prompt_idle_v1"
_OUTPUT_VARIANT_RESPONSE_MARKER_V1: Final[str] = "claude_response_marker_v1"
_OUTPUT_VARIANT_WAITING_MENU_V1: Final[str] = "claude_waiting_menu_v1"
_OUTPUT_VARIANT_SPINNER_V1: Final[str] = "claude_spinner_v1"


@dataclass(frozen=True)
class ClaudeCodeParsingPreset:
    """Regex/prompt preset for one Claude Code version baseline."""

    identity: VersionedParserPreset
    response_markers: tuple[str, ...]
    idle_prompts: tuple[str, ...]
    supported_variants: tuple[str, ...]
    spinner_chars: str = "✶✢✽✻·✳"
    spinner_requires_parenthesized_suffix: bool = False
    separator_token: str = "────────"


@dataclass(frozen=True)
class ClaudeCodeShadowStatus:
    """Classification result for one Claude Code scrollback snapshot."""

    status: ShadowStatus
    metadata: ShadowParserMetadata
    waiting_user_answer_excerpt: str | None = None

    @property
    def preset_version(self) -> str:
        """Compatibility accessor for older runtime wiring."""

        return self.metadata.parser_preset_version

    @property
    def parser_preset_id(self) -> str:
        """Return selected parser preset id."""

        return self.metadata.parser_preset_id

    @property
    def output_format(self) -> str:
        """Return selected output-format id."""

        return self.metadata.output_format

    @property
    def output_format_match(self) -> bool:
        """Return whether the output probe matched."""

        return self.metadata.output_format_match

    @property
    def output_variant(self) -> str:
        """Return matched Claude output variant id."""

        return self.metadata.output_variant

    @property
    def baseline_invalidated(self) -> bool:
        """Return whether baseline invalidation was detected."""

        return self.metadata.baseline_invalidated

    @property
    def anomalies(self) -> tuple[ShadowParserAnomaly, ...]:
        """Return parser anomalies attached to this status result."""

        return self.metadata.anomalies


@dataclass(frozen=True)
class ClaudeCodeExtractionResult:
    """Extracted answer details from one Claude Code scrollback snapshot."""

    answer_text: str
    metadata: ShadowParserMetadata

    @property
    def preset_version(self) -> str:
        """Compatibility accessor for older runtime wiring."""

        return self.metadata.parser_preset_version

    @property
    def parser_preset_id(self) -> str:
        """Return selected parser preset id."""

        return self.metadata.parser_preset_id

    @property
    def output_format(self) -> str:
        """Return selected output-format id."""

        return self.metadata.output_format

    @property
    def output_format_match(self) -> bool:
        """Return whether the output probe matched."""

        return self.metadata.output_format_match

    @property
    def output_variant(self) -> str:
        """Return matched Claude output variant id."""

        return self.metadata.output_variant

    @property
    def baseline_invalidated(self) -> bool:
        """Return whether baseline invalidation was detected."""

        return self.metadata.baseline_invalidated

    @property
    def anomalies(self) -> tuple[ShadowParserAnomaly, ...]:
        """Return parser anomalies attached to this extraction result."""

        return self.metadata.anomalies


@dataclass(frozen=True)
class _CompiledPreset:
    preset: ClaudeCodeParsingPreset
    response_patterns: tuple[re.Pattern[str], ...]
    spinner_pattern: re.Pattern[str]


@dataclass(frozen=True)
class _ResponseMatch:
    start: int
    end: int
    first_line: str


class ClaudeCodeShadowParseError(ShadowParserError):
    """Raised when Claude Code answer extraction/classification fails."""


class ClaudeCodeShadowParser:
    """Parse Claude Code output from CAO ``mode=full`` scrollback."""

    _PRESETS: Final[dict[str, ClaudeCodeParsingPreset]] = {
        "0.0.0": ClaudeCodeParsingPreset(
            identity=VersionedParserPreset(
                preset_id="claude_shadow_v0",
                version="0.0.0",
            ),
            response_markers=("⏺",),
            idle_prompts=(">",),
            supported_variants=(
                _OUTPUT_VARIANT_PROMPT_IDLE_V1,
                _OUTPUT_VARIANT_RESPONSE_MARKER_V1,
                _OUTPUT_VARIANT_WAITING_MENU_V1,
                _OUTPUT_VARIANT_SPINNER_V1,
            ),
            spinner_requires_parenthesized_suffix=True,
        ),
        "2.1.0": ClaudeCodeParsingPreset(
            identity=VersionedParserPreset(
                preset_id="claude_shadow_v1",
                version="2.1.0",
            ),
            response_markers=("⏺",),
            idle_prompts=(">", "❯"),
            supported_variants=(
                _OUTPUT_VARIANT_PROMPT_IDLE_V1,
                _OUTPUT_VARIANT_RESPONSE_MARKER_V1,
                _OUTPUT_VARIANT_WAITING_MENU_V1,
                _OUTPUT_VARIANT_SPINNER_V1,
            ),
            spinner_requires_parenthesized_suffix=True,
        ),
        "2.1.62": ClaudeCodeParsingPreset(
            identity=VersionedParserPreset(
                preset_id="claude_shadow_v2",
                version="2.1.62",
            ),
            response_markers=("●",),
            idle_prompts=("❯",),
            supported_variants=(
                _OUTPUT_VARIANT_PROMPT_IDLE_V1,
                _OUTPUT_VARIANT_RESPONSE_MARKER_V1,
                _OUTPUT_VARIANT_WAITING_MENU_V1,
                _OUTPUT_VARIANT_SPINNER_V1,
            ),
            spinner_requires_parenthesized_suffix=False,
        ),
    }

    def __init__(self, *, status_tail_lines: int = _DEFAULT_STATUS_TAIL_LINES) -> None:
        if status_tail_lines <= 0:
            raise ValueError("status_tail_lines must be positive")

        self._status_tail_lines = status_tail_lines
        self._registry = VersionedPresetRegistry(
            provider_id="claude",
            override_env_var=_ENV_PRESET_OVERRIDE,
            presets=tuple(preset.identity for preset in self._PRESETS.values()),
        )
        self._compiled_preset_cache: dict[str, _CompiledPreset] = {}

    def resolve_preset_version(self, scrollback: str) -> str:
        """Resolve the preset version for a scrollback snapshot."""

        preset, _ = self._resolve_preset(scrollback)
        return preset.identity.version

    def detect_output_format(self, scrollback: str) -> tuple[str, bool]:
        """Detect whether scrollback matches a supported Claude format."""

        preset, _ = self._resolve_preset(scrollback)
        compiled = self._compiled_for_preset(preset)
        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        variant = self._detect_output_variant(clean_output, compiled)
        if variant is None or variant not in set(preset.supported_variants):
            return ("unknown", False)
        return (preset.identity.preset_id, True)

    def capture_baseline_pos(self, scrollback: str) -> int:
        """Capture the baseline marker end offset for current turn gating."""

        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        preset, resolution = self._resolve_preset(scrollback)
        compiled = self._compiled_for_preset(preset)
        metadata, _ = self._require_supported_variant(
            clean_output=clean_output,
            compiled=compiled,
            resolution=resolution,
            baseline_invalidated=False,
        )
        _ = metadata
        matches = self._response_marker_matches(
            clean_output=clean_output,
            compiled=compiled,
            baseline_pos=0,
        )
        if not matches:
            return 0
        return max(match.end for match in matches)

    def classify_shadow_status(
        self,
        scrollback: str,
        *,
        baseline_pos: int = 0,
    ) -> ClaudeCodeShadowStatus:
        """Classify Claude Code shadow status from ``mode=full`` output."""

        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        preset, resolution = self._resolve_preset(scrollback)
        compiled = self._compiled_for_preset(preset)
        baseline_invalidated = baseline_pos > 0 and len(clean_output) < baseline_pos
        metadata, _ = self._require_supported_variant(
            clean_output=clean_output,
            compiled=compiled,
            resolution=resolution,
            baseline_invalidated=baseline_invalidated,
        )

        effective_baseline = 0 if baseline_invalidated else max(baseline_pos, 0)
        tail_lines = self._tail_lines(clean_output, max_lines=self._status_tail_lines)
        waiting_excerpt = self._waiting_user_answer_excerpt(tail_lines)
        if waiting_excerpt:
            return ClaudeCodeShadowStatus(
                status="waiting_user_answer",
                metadata=metadata,
                waiting_user_answer_excerpt=waiting_excerpt,
            )

        if self._contains_processing_spinner(tail_lines, compiled):
            return ClaudeCodeShadowStatus(
                status="processing",
                metadata=metadata,
            )

        has_idle_prompt = any(
            self._is_idle_prompt_line(line, compiled.preset) for line in tail_lines
        )
        if not has_idle_prompt:
            return ClaudeCodeShadowStatus(
                status="unknown",
                metadata=metadata,
            )

        marker_matches = self._response_marker_matches(
            clean_output=clean_output,
            compiled=compiled,
            baseline_pos=effective_baseline,
        )
        if marker_matches:
            if baseline_invalidated:
                if any(
                    self._has_stop_boundary_after(
                        clean_output=clean_output,
                        marker_end=match.end,
                        preset=compiled.preset,
                    )
                    for match in marker_matches
                ):
                    return ClaudeCodeShadowStatus(
                        status="completed",
                        metadata=metadata,
                    )
            else:
                return ClaudeCodeShadowStatus(
                    status="completed",
                    metadata=metadata,
                )

        return ClaudeCodeShadowStatus(
            status="idle",
            metadata=metadata,
        )

    def extract_last_answer(
        self,
        scrollback: str,
        *,
        baseline_pos: int = 0,
    ) -> ClaudeCodeExtractionResult:
        """Extract the last assistant answer from Claude Code scrollback."""

        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        preset, resolution = self._resolve_preset(scrollback)
        compiled = self._compiled_for_preset(preset)
        baseline_invalidated = baseline_pos > 0 and len(clean_output) < baseline_pos
        metadata, _ = self._require_supported_variant(
            clean_output=clean_output,
            compiled=compiled,
            resolution=resolution,
            baseline_invalidated=baseline_invalidated,
        )
        effective_baseline = 0 if baseline_invalidated else max(baseline_pos, 0)

        marker_matches = self._response_marker_matches(
            clean_output=clean_output,
            compiled=compiled,
            baseline_pos=effective_baseline,
        )
        if not marker_matches:
            raise ClaudeCodeShadowParseError(
                "No Claude Code response marker found after baseline",
                metadata=metadata,
            )

        last_marker = marker_matches[-1]
        remaining_output = clean_output[last_marker.end :]

        collected_lines: list[str] = []
        if last_marker.first_line.strip():
            collected_lines.append(last_marker.first_line.rstrip())
        stop_boundary_found = False
        for line in remaining_output.splitlines():
            clean_line = line.rstrip("\r")
            if (
                self._is_idle_prompt_line(clean_line, compiled.preset)
                or compiled.preset.separator_token in clean_line
            ):
                stop_boundary_found = True
                break
            if not clean_line.strip():
                if collected_lines and collected_lines[-1]:
                    collected_lines.append("")
                continue
            collected_lines.append(clean_line)

        if baseline_invalidated and not stop_boundary_found:
            raise ClaudeCodeShadowParseError(
                "Baseline was invalidated and no extraction stop boundary was found",
                metadata=metadata,
            )

        answer_text = "\n".join(collected_lines).strip()
        if not answer_text:
            raise ClaudeCodeShadowParseError(
                "Extracted Claude Code answer is empty",
                metadata=metadata,
            )

        return ClaudeCodeExtractionResult(
            answer_text=answer_text,
            metadata=metadata,
        )

    def ansi_stripped_tail_excerpt(self, scrollback: str, *, max_lines: int = 12) -> str:
        """Return an ANSI-stripped tail excerpt for diagnostics."""

        return ansi_stripped_tail_excerpt(scrollback, max_lines=max_lines)

    @staticmethod
    def strip_ansi(value: str) -> str:
        """Strip ANSI escape sequences from text."""

        return strip_ansi(value)

    def _resolve_preset(
        self,
        scrollback: str,
    ) -> tuple[ClaudeCodeParsingPreset, PresetResolution]:
        resolution = self._registry.resolve(
            scrollback,
            detect_version=self._detected_banner_version,
        )
        preset = self._PRESETS.get(resolution.preset.version)
        if preset is None:
            raise RuntimeError(
                "Claude parser preset registry selected an unknown version "
                f"{resolution.preset.version!r}."
            )
        return preset, resolution

    def _compiled_for_preset(self, preset: ClaudeCodeParsingPreset) -> _CompiledPreset:
        cached = self._compiled_preset_cache.get(preset.identity.version)
        if cached is not None:
            return cached

        response_patterns = tuple(
            re.compile(rf"(?m)^[ \t]*{re.escape(marker)}[ \t]+(.*)$")
            for marker in preset.response_markers
        )
        parenthesized_suffix = (
            r".*\(.+\)" if preset.spinner_requires_parenthesized_suffix else r".*"
        )
        spinner_pattern = re.compile(
            rf"^\s*[{re.escape(preset.spinner_chars)}].*…{parenthesized_suffix}$"
        )
        compiled = _CompiledPreset(
            preset=preset,
            response_patterns=response_patterns,
            spinner_pattern=spinner_pattern,
        )
        self._compiled_preset_cache[preset.identity.version] = compiled
        return compiled

    def _require_supported_variant(
        self,
        *,
        clean_output: str,
        compiled: _CompiledPreset,
        resolution: PresetResolution,
        baseline_invalidated: bool,
    ) -> tuple[ShadowParserMetadata, str]:
        variant = self._detect_output_variant(clean_output, compiled)
        if variant is None or variant not in set(compiled.preset.supported_variants):
            metadata = self._metadata_for(
                preset=compiled.preset,
                resolution=resolution,
                output_variant="unknown",
                output_format_match=False,
                baseline_invalidated=baseline_invalidated,
            )
            raise ClaudeCodeShadowParseError(
                "unsupported_output_format: mode=full output does not match "
                f"{compiled.preset.identity.preset_id}",
                error_code="unsupported_output_format",
                metadata=metadata,
            )

        metadata = self._metadata_for(
            preset=compiled.preset,
            resolution=resolution,
            output_variant=variant,
            output_format_match=True,
            baseline_invalidated=baseline_invalidated,
        )
        return metadata, variant

    def _metadata_for(
        self,
        *,
        preset: ClaudeCodeParsingPreset,
        resolution: PresetResolution,
        output_variant: str,
        output_format_match: bool,
        baseline_invalidated: bool,
    ) -> ShadowParserMetadata:
        anomalies = list(resolution.anomalies)
        if baseline_invalidated:
            anomalies.append(
                ShadowParserAnomaly(
                    code=ANOMALY_BASELINE_INVALIDATED,
                    message="Scrollback length fell below recorded baseline offset",
                    details={
                        "provider": "claude",
                        "preset": preset.identity.preset_id,
                    },
                )
            )
        return ShadowParserMetadata(
            provider_id="claude",
            parser_preset_id=preset.identity.preset_id,
            parser_preset_version=preset.identity.version,
            output_format=preset.identity.preset_id,
            output_variant=output_variant,
            output_format_match=output_format_match,
            anomalies=tuple(anomalies),
            detected_version=resolution.detected_version,
            requested_version=resolution.requested_version,
            selection_source=resolution.selection_source,
            baseline_invalidated=baseline_invalidated,
        )

    def _detect_output_variant(
        self,
        clean_output: str,
        compiled: _CompiledPreset,
    ) -> str | None:
        tail_lines = self._tail_lines(clean_output, max_lines=self._status_tail_lines)
        if self._waiting_user_answer_excerpt(tail_lines):
            return _OUTPUT_VARIANT_WAITING_MENU_V1

        if self._contains_processing_spinner(tail_lines, compiled):
            return _OUTPUT_VARIANT_SPINNER_V1

        has_marker = bool(
            self._response_marker_matches(
                clean_output=clean_output,
                compiled=compiled,
                baseline_pos=0,
            )
        )
        has_idle_prompt = any(
            self._is_idle_prompt_line(line, compiled.preset) for line in tail_lines
        )
        if has_marker:
            return _OUTPUT_VARIANT_RESPONSE_MARKER_V1
        if has_idle_prompt:
            return _OUTPUT_VARIANT_PROMPT_IDLE_V1
        return None

    @staticmethod
    def _detected_banner_version(clean_output: str) -> str | None:
        match = _BANNER_VERSION_RE.search(clean_output)
        if match is None:
            return None
        return match.group(1)

    @staticmethod
    def _tail_lines(scrollback: str, *, max_lines: int) -> list[str]:
        lines = scrollback.splitlines()
        if not lines:
            return []
        return [line.rstrip("\r") for line in lines[-max_lines:]]

    @staticmethod
    def _is_idle_prompt_line(clean_line: str, preset: ClaudeCodeParsingPreset) -> bool:
        line = clean_line
        trimmed = line.lstrip()
        if not trimmed:
            return False

        if trimmed[0] not in set(preset.idle_prompts):
            return False

        if len(trimmed) == 1:
            return True
        return trimmed[1].isspace()

    @staticmethod
    def _contains_processing_spinner(
        clean_tail_lines: list[str],
        compiled: _CompiledPreset,
    ) -> bool:
        return any(compiled.spinner_pattern.search(line) for line in clean_tail_lines)

    def _response_marker_matches(
        self,
        *,
        clean_output: str,
        compiled: _CompiledPreset,
        baseline_pos: int,
    ) -> list[_ResponseMatch]:
        matches: list[_ResponseMatch] = []
        for response_pattern in compiled.response_patterns:
            for match in response_pattern.finditer(clean_output):
                if match.start() < baseline_pos:
                    continue
                matches.append(
                    _ResponseMatch(
                        start=match.start(),
                        end=match.end(),
                        first_line=match.group(1).rstrip(),
                    )
                )
        matches.sort(key=lambda item: item.start)
        return matches

    def _has_stop_boundary_after(
        self,
        *,
        clean_output: str,
        marker_end: int,
        preset: ClaudeCodeParsingPreset,
    ) -> bool:
        segment = clean_output[marker_end:]
        for line in segment.splitlines():
            clean_line = line.rstrip("\r")
            if self._is_idle_prompt_line(clean_line, preset):
                return True
            if preset.separator_token in clean_line:
                return True
        return False

    @staticmethod
    def _waiting_user_answer_excerpt(clean_tail_lines: list[str]) -> str | None:
        if not clean_tail_lines:
            return None

        option_indices = [
            index
            for index, line in enumerate(clean_tail_lines)
            if _WAITING_OPTION_RE.match(line)
        ]
        if len(option_indices) < 2:
            return None

        has_selected_option = any(
            _WAITING_SELECTED_OPTION_RE.match(clean_tail_lines[index])
            for index in option_indices
        )
        has_hint = any(_WAITING_HINT_RE.search(line) for line in clean_tail_lines)
        if not has_selected_option and not has_hint:
            return None

        start = max(option_indices[0] - 1, 0)
        end = min(option_indices[-1] + 2, len(clean_tail_lines))
        excerpt = "\n".join(
            line.rstrip() for line in clean_tail_lines[start:end] if line.strip()
        )
        return excerpt.strip() or None
