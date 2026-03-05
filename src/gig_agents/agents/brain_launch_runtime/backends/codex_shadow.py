"""Runtime-owned Codex shadow parser for CAO ``mode=full`` output."""

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

_DEFAULT_STATUS_TAIL_LINES: Final[int] = 100
_ENV_PRESET_OVERRIDE: Final[str] = "AGENTSYS_CAO_CODEX_VERSION"

_BANNER_VERSION_RE: Final[re.Pattern[str]] = re.compile(
    r"(?im)(?:codex(?:\s+cli)?\s+v|openai\s+codex\s*\(v)(\d+\.\d+\.\d+)"
)
_ASSISTANT_LABEL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?im)^\s*(?:assistant|codex|agent)\s*[:>]\s?(.*)$"
)
_ASSISTANT_BULLET_RE: Final[re.Pattern[str]] = re.compile(r"(?m)^\s*•\s?(.*)$")
_USER_LABEL_RE: Final[re.Pattern[str]] = re.compile(r"(?m)^\s*You\b")
_USER_TUI_RE: Final[re.Pattern[str]] = re.compile(r"(?m)^\s*[❯›][^\S\n]*\S+")
_IDLE_PROMPT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?im)^\s*(?:❯|›|>|codex>)\s*(?:$|\S.*)$"
)
_IDLE_PROMPT_STRICT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?im)^\s*(?:❯|›|>|codex>)\s*$"
)
_WAITING_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:[❯›>]\s*)?\d+\.\s+\S+"
)
_WAITING_SELECTED_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*[❯›>]\s*\d+\.\s+\S+"
)
_WAITING_HINT_RE: Final[re.Pattern[str]] = re.compile(
    r"(select (?:an )?option|choose (?:an )?option|arrow keys|press enter|approve)",
    flags=re.IGNORECASE,
)
_WAITING_APPROVAL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?im)^\s*(?:approve|allow)\b.*(?:\[(?:y/n|yes/no)\]|\b(?:y/n|yes/no)\b)"
)
_TRUST_PROMPT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:allow codex to work in this folder|yes,\s*i trust this folder|do you trust the contents of this (?:directory|folder))"
)
_FOOTER_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:\?\s+for shortcuts|context left)"
)
_PROCESSING_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(thinking|processing|generating|working|running|executing|analyzing|starting|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏)"
)
_TUI_PROGRESS_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)^\s*•.*\(\d+s\s*•\s*esc to interrupt\)"
)

_OUTPUT_VARIANT_LABEL_V1: Final[str] = "codex_label_v1"
_OUTPUT_VARIANT_TUI_BULLET_V1: Final[str] = "codex_tui_bullet_v1"
_OUTPUT_VARIANT_WAITING_APPROVAL_V1: Final[str] = "codex_waiting_approval_v1"
_OUTPUT_VARIANT_PROMPT_IDLE_V1: Final[str] = "codex_prompt_idle_v1"


@dataclass(frozen=True)
class CodexParsingPreset:
    """Codex parsing preset contract."""

    identity: VersionedParserPreset
    supported_variants: tuple[str, ...]

@dataclass(frozen=True)
class CodexShadowStatus:
    """Classification result for one Codex scrollback snapshot."""

    status: ShadowStatus
    metadata: ShadowParserMetadata
    waiting_user_answer_excerpt: str | None = None

    @property
    def parser_preset_id(self) -> str:
        """Compatibility accessor for older runtime wiring."""

        return self.metadata.parser_preset_id

    @property
    def output_format(self) -> str:
        """Return selected output-format id."""

        return self.metadata.output_format

    @property
    def output_format_match(self) -> bool:
        """Return whether probe matched a supported variant."""

        return self.metadata.output_format_match

    @property
    def output_variant(self) -> str:
        """Return matched Codex output variant id."""

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
class CodexShadowExtractionResult:
    """Extracted answer details from one Codex scrollback snapshot."""

    answer_text: str
    metadata: ShadowParserMetadata

    @property
    def parser_preset_id(self) -> str:
        """Compatibility accessor for older runtime wiring."""

        return self.metadata.parser_preset_id

    @property
    def output_format(self) -> str:
        """Return selected output-format id."""

        return self.metadata.output_format

    @property
    def output_format_match(self) -> bool:
        """Return whether probe matched a supported variant."""

        return self.metadata.output_format_match

    @property
    def output_variant(self) -> str:
        """Return matched Codex output variant id."""

        return self.metadata.output_variant

    @property
    def baseline_invalidated(self) -> bool:
        """Return whether baseline invalidation was detected."""

        return self.metadata.baseline_invalidated

    @property
    def anomalies(self) -> tuple[ShadowParserAnomaly, ...]:
        """Return parser anomalies attached to this extraction result."""

        return self.metadata.anomalies


class CodexShadowParseError(ShadowParserError):
    """Raised when Codex answer extraction/classification fails."""


@dataclass(frozen=True)
class _AssistantMatch:
    start: int
    end: int
    first_line: str


class CodexShadowParser:
    """Parse Codex output from CAO ``mode=full`` scrollback."""

    _PRESETS: Final[dict[str, CodexParsingPreset]] = {
        "0.1.0": CodexParsingPreset(
            identity=VersionedParserPreset(
                preset_id="codex_shadow_v1",
                version="0.1.0",
            ),
            supported_variants=(
                _OUTPUT_VARIANT_LABEL_V1,
                _OUTPUT_VARIANT_PROMPT_IDLE_V1,
                _OUTPUT_VARIANT_WAITING_APPROVAL_V1,
            ),
        ),
        "0.98.0": CodexParsingPreset(
            identity=VersionedParserPreset(
                preset_id="codex_shadow_v2",
                version="0.98.0",
            ),
            supported_variants=(
                _OUTPUT_VARIANT_LABEL_V1,
                _OUTPUT_VARIANT_TUI_BULLET_V1,
                _OUTPUT_VARIANT_PROMPT_IDLE_V1,
                _OUTPUT_VARIANT_WAITING_APPROVAL_V1,
            ),
        ),
    }

    def __init__(self, *, status_tail_lines: int = _DEFAULT_STATUS_TAIL_LINES) -> None:
        if status_tail_lines <= 0:
            raise ValueError("status_tail_lines must be positive")
        self._status_tail_lines = status_tail_lines
        self._registry = VersionedPresetRegistry(
            provider_id="codex",
            override_env_var=_ENV_PRESET_OVERRIDE,
            presets=tuple(preset.identity for preset in self._PRESETS.values()),
        )

    def resolve_preset_version(self, scrollback: str) -> str:
        """Resolve Codex preset version using registry selection order."""

        preset, _ = self._resolve_preset(scrollback)
        return preset.identity.version

    def detect_output_format(self, scrollback: str) -> tuple[str, bool]:
        """Detect whether scrollback matches one supported Codex variant."""

        preset, _ = self._resolve_preset(scrollback)
        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        variant = self._detect_output_variant(clean_output)
        if variant is None or variant not in set(preset.supported_variants):
            return ("unknown", False)
        return (preset.identity.preset_id, True)

    def capture_baseline_pos(self, scrollback: str) -> int:
        """Capture the baseline marker offset for turn-level status gating."""

        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        preset, resolution = self._resolve_preset(scrollback)
        self._require_supported_variant(
            clean_output=clean_output,
            preset=preset,
            resolution=resolution,
            baseline_invalidated=False,
        )
        # Use the full scrollback length as baseline anchor. Codex TUI frames can
        # redraw in-place; anchoring to the last assistant marker can miss
        # post-turn assistant text when the frame shrinks/reflows.
        return len(clean_output)

    def classify_shadow_status(
        self,
        scrollback: str,
        *,
        baseline_pos: int = 0,
    ) -> CodexShadowStatus:
        """Classify Codex shadow status from ``mode=full`` output."""

        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        preset, resolution = self._resolve_preset(scrollback)
        baseline_invalidated = baseline_pos > 0 and len(clean_output) < baseline_pos
        metadata, variant = self._require_supported_variant(
            clean_output=clean_output,
            preset=preset,
            resolution=resolution,
            baseline_invalidated=baseline_invalidated,
        )
        _ = metadata, variant

        effective_baseline = 0 if baseline_invalidated else max(baseline_pos, 0)
        tail_lines = self._tail_lines(clean_output, max_lines=self._status_tail_lines)
        waiting_excerpt = self._waiting_user_answer_excerpt(tail_lines)
        if waiting_excerpt:
            return CodexShadowStatus(
                status="waiting_user_answer",
                metadata=metadata,
                waiting_user_answer_excerpt=waiting_excerpt,
            )

        has_processing = any(self._is_processing_line(line) for line in tail_lines)
        has_idle_prompt = any(_IDLE_PROMPT_RE.match(line) for line in tail_lines)
        assistant_matches = self._assistant_matches(
            clean_output,
            baseline_pos=effective_baseline,
        )
        has_post_baseline_assistant = bool(assistant_matches)

        if has_post_baseline_assistant and not has_processing:
            if baseline_invalidated and not any(
                self._has_stop_boundary_after(clean_output, marker_end=match.end)
                for match in assistant_matches
            ):
                return CodexShadowStatus(
                    status="processing",
                    metadata=metadata,
                )
            return CodexShadowStatus(
                status="completed",
                metadata=metadata,
            )

        if has_processing:
            return CodexShadowStatus(
                status="processing",
                metadata=metadata,
            )

        idle_status: ShadowStatus = "idle" if has_idle_prompt else "unknown"
        return CodexShadowStatus(
            status=idle_status,
            metadata=metadata,
        )

    def extract_last_answer(
        self,
        scrollback: str,
        *,
        baseline_pos: int = 0,
    ) -> CodexShadowExtractionResult:
        """Extract the last assistant answer from Codex scrollback."""

        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        preset, resolution = self._resolve_preset(scrollback)
        baseline_invalidated = baseline_pos > 0 and len(clean_output) < baseline_pos
        metadata, _ = self._require_supported_variant(
            clean_output=clean_output,
            preset=preset,
            resolution=resolution,
            baseline_invalidated=baseline_invalidated,
        )
        effective_baseline = 0 if baseline_invalidated else max(baseline_pos, 0)

        marker_matches = self._assistant_matches(
            clean_output,
            baseline_pos=effective_baseline,
        )
        if not marker_matches:
            raise CodexShadowParseError(
                "No Codex assistant marker found after baseline",
                metadata=metadata,
            )

        selected_marker = marker_matches[-1]
        user_matches = self._user_matches(clean_output, baseline_pos=effective_baseline)
        if user_matches:
            last_user_pos = user_matches[-1]
            for candidate in marker_matches:
                if candidate.start >= last_user_pos:
                    selected_marker = candidate
                    break

        segment = clean_output[selected_marker.end :]
        lines = segment.splitlines()
        collected_lines: list[str] = []
        if selected_marker.first_line.strip():
            collected_lines.append(selected_marker.first_line.rstrip())

        stop_boundary_found = False
        for raw_line in lines:
            line = raw_line.rstrip()
            if self._is_stop_boundary_line(line):
                stop_boundary_found = True
                break
            if self._is_processing_line(line):
                continue
            marker_match = _ASSISTANT_BULLET_RE.match(line) or _ASSISTANT_LABEL_RE.match(line)
            if marker_match is not None:
                payload = marker_match.group(1).rstrip()
                if _PROCESSING_RE.search(payload):
                    continue
                if payload:
                    collected_lines.append(payload)
                continue
            if line.strip():
                collected_lines.append(line)

        if baseline_invalidated and not stop_boundary_found:
            raise CodexShadowParseError(
                "Baseline was invalidated and no extraction stop boundary was found",
                metadata=metadata,
            )

        answer_text = "\n".join(collected_lines).strip()
        if not answer_text:
            raise CodexShadowParseError(
                "Extracted Codex answer is empty",
                metadata=metadata,
            )

        return CodexShadowExtractionResult(
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
    ) -> tuple[CodexParsingPreset, PresetResolution]:
        resolution = self._registry.resolve(
            scrollback,
            detect_version=self._detected_banner_version,
        )
        preset = self._PRESETS.get(resolution.preset.version)
        if preset is None:
            raise RuntimeError(
                "Codex parser preset registry selected an unknown version "
                f"{resolution.preset.version!r}."
            )
        return preset, resolution

    def _require_supported_variant(
        self,
        *,
        clean_output: str,
        preset: CodexParsingPreset,
        resolution: PresetResolution,
        baseline_invalidated: bool,
    ) -> tuple[ShadowParserMetadata, str]:
        variant = self._detect_output_variant(clean_output)
        if variant is None or variant not in set(preset.supported_variants):
            metadata = self._metadata_for(
                preset=preset,
                resolution=resolution,
                output_variant="unknown",
                output_format_match=False,
                baseline_invalidated=baseline_invalidated,
            )
            raise CodexShadowParseError(
                "unsupported_output_format: mode=full output does not match "
                f"{preset.identity.preset_id}",
                error_code="unsupported_output_format",
                metadata=metadata,
            )
        metadata = self._metadata_for(
            preset=preset,
            resolution=resolution,
            output_variant=variant,
            output_format_match=True,
            baseline_invalidated=baseline_invalidated,
        )
        return metadata, variant

    def _metadata_for(
        self,
        *,
        preset: CodexParsingPreset,
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
                        "provider": "codex",
                        "preset": preset.identity.preset_id,
                    },
                )
            )
        return ShadowParserMetadata(
            provider_id="codex",
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

    def _detect_output_variant(self, clean_output: str) -> str | None:
        tail_lines = self._tail_lines(clean_output, max_lines=self._status_tail_lines)
        has_footer = any(_FOOTER_TOKEN_RE.search(line) for line in tail_lines)
        has_prompt = any(_IDLE_PROMPT_RE.match(line) for line in tail_lines)
        has_label = (
            _ASSISTANT_LABEL_RE.search(clean_output) is not None
            or _USER_LABEL_RE.search(clean_output) is not None
        )
        has_bullet_answer = bool(self._assistant_matches(clean_output, baseline_pos=0))
        has_waiting = self._waiting_user_answer_excerpt(tail_lines) is not None

        if has_waiting:
            return _OUTPUT_VARIANT_WAITING_APPROVAL_V1
        if has_label:
            return _OUTPUT_VARIANT_LABEL_V1
        if has_bullet_answer or (has_footer and has_prompt) or _USER_TUI_RE.search(clean_output):
            return _OUTPUT_VARIANT_TUI_BULLET_V1
        if has_prompt:
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
        cleaned = [line.rstrip("\r") for line in lines]
        return cleaned[-max_lines:]

    @staticmethod
    def _is_processing_line(line: str) -> bool:
        if _TUI_PROGRESS_RE.search(line):
            return True
        if _ASSISTANT_BULLET_RE.match(line) and _PROCESSING_RE.search(line):
            return True
        return _PROCESSING_RE.search(line) is not None and not _ASSISTANT_LABEL_RE.match(line)

    @staticmethod
    def _is_stop_boundary_line(line: str) -> bool:
        if _IDLE_PROMPT_RE.match(line):
            return True
        if _WAITING_OPTION_RE.match(line):
            return True
        if _FOOTER_TOKEN_RE.search(line):
            return True
        if line.startswith("╭") or line.startswith("╰"):
            return True
        stripped = line.strip()
        if stripped.startswith("──") or stripped.startswith("---"):
            return True
        return False

    def _assistant_matches(self, clean_output: str, *, baseline_pos: int) -> list[_AssistantMatch]:
        matches: list[_AssistantMatch] = []
        for match in _ASSISTANT_LABEL_RE.finditer(clean_output):
            if match.start() < baseline_pos:
                continue
            matches.append(
                _AssistantMatch(
                    start=match.start(),
                    end=match.end(),
                    first_line=match.group(1).rstrip(),
                )
            )

        for match in _ASSISTANT_BULLET_RE.finditer(clean_output):
            if match.start() < baseline_pos:
                continue
            full_line = match.group(0)
            if _TUI_PROGRESS_RE.search(full_line):
                continue
            payload = match.group(1).rstrip()
            if _PROCESSING_RE.search(payload):
                continue
            matches.append(
                _AssistantMatch(
                    start=match.start(),
                    end=match.end(),
                    first_line=payload,
                )
            )

        matches.sort(key=lambda item: item.start)
        return matches

    @staticmethod
    def _user_matches(clean_output: str, *, baseline_pos: int) -> list[int]:
        positions: list[int] = []
        for pattern in (_USER_LABEL_RE, _USER_TUI_RE):
            for match in pattern.finditer(clean_output):
                if match.start() >= baseline_pos:
                    positions.append(match.start())
        positions.sort()
        return positions

    def _has_stop_boundary_after(self, clean_output: str, *, marker_end: int) -> bool:
        segment = clean_output[marker_end:]
        for line in segment.splitlines():
            if self._is_stop_boundary_line(line.rstrip()):
                return True
        return False

    def _waiting_user_answer_excerpt(self, clean_tail_lines: list[str]) -> str | None:
        if not clean_tail_lines:
            return None

        for index, line in enumerate(clean_tail_lines):
            if _WAITING_APPROVAL_RE.search(line) or _TRUST_PROMPT_RE.search(line):
                start = max(index - 1, 0)
                end = min(index + 3, len(clean_tail_lines))
                excerpt = "\n".join(
                    candidate.rstrip()
                    for candidate in clean_tail_lines[start:end]
                    if candidate.strip()
                )
                stripped_excerpt = excerpt.strip()
                if stripped_excerpt:
                    return stripped_excerpt

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
