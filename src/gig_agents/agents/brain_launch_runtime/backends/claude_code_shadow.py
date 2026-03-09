"""Runtime-owned Claude Code shadow parser for CAO ``mode=full`` output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

from .shadow_parser_core import (
    ANOMALY_BASELINE_INVALIDATED,
    DialogProjection,
    ParsedShadowSnapshot,
    PresetResolution,
    ProjectionMetadata,
    ShadowActivity,
    ShadowAvailability,
    ShadowParserAnomaly,
    ShadowParserError,
    ShadowParserMetadata,
    SurfaceAssessment,
    VersionedParserPreset,
    VersionedPresetRegistry,
    ansi_stripped_tail_excerpt,
    normalize_shadow_output,
    projection_head_tail,
    strip_ansi,
)

_BANNER_VERSION_RE: Final[re.Pattern[str]] = re.compile(r"(?im)Claude Code v(\d+\.\d+\.\d+)")
_WAITING_OPTION_RE: Final[re.Pattern[str]] = re.compile(r"^\s*(?:❯\s*)?\d+\.\s+\S+")
_WAITING_SELECTED_OPTION_RE: Final[re.Pattern[str]] = re.compile(r"^\s*❯\s*\d+\.\s+\S+")
_WAITING_HINT_RE: Final[re.Pattern[str]] = re.compile(
    r"(select (?:an )?option|choose (?:an )?option|arrow keys|press enter)",
    flags=re.IGNORECASE,
)
_WAITING_APPROVAL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?im)^\s*(?:allow|trust)\b.*(?:\[(?:y/n|yes/no)\]|\b(?:y/n|yes/no)\b)"
)
_SLASH_COMMAND_RE: Final[re.Pattern[str]] = re.compile(r"(?m)^\s*(?:❯\s*)?/[A-Za-z0-9_-]+\b")
_TRUST_PROMPT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:trust this (?:folder|directory)|allow claude|yes,\s*i trust)"
)
_ERROR_BANNER_RE: Final[re.Pattern[str]] = re.compile(r"(?im)^\s*(?:error|failed|warning)\b")
_DISCONNECTED_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:connection (?:lost|closed)|terminal detached|session ended|reconnect)"
)

_DEFAULT_STATUS_TAIL_LINES: Final[int] = 100
_DEFAULT_PROJECTION_SLICE_LINES: Final[int] = 12
_ENV_PRESET_OVERRIDE: Final[str] = "AGENTSYS_CAO_CLAUDE_CODE_VERSION"

_OUTPUT_VARIANT_PROMPT_IDLE_V1: Final[str] = "claude_prompt_idle_v1"
_OUTPUT_VARIANT_RESPONSE_MARKER_V1: Final[str] = "claude_response_marker_v1"
_OUTPUT_VARIANT_WAITING_MENU_V1: Final[str] = "claude_waiting_menu_v1"
_OUTPUT_VARIANT_SPINNER_V1: Final[str] = "claude_spinner_v1"
_CLAUDE_PROJECTOR_ID: Final[str] = "claude_dialog_projection_v1"

ClaudeUiContext = Literal[
    "normal_prompt",
    "selection_menu",
    "slash_command",
    "trust_prompt",
    "error_banner",
    "unknown",
]


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
class ClaudeSurfaceAssessment(SurfaceAssessment):
    """Claude-specific snapshot assessment."""

    ui_context: ClaudeUiContext
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaudeDialogProjection(DialogProjection):
    """Claude-specific dialog projection."""

    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class _CompiledPreset:
    """Cached compiled regex bundle for one preset."""

    preset: ClaudeCodeParsingPreset
    response_patterns: tuple[re.Pattern[str], ...]
    spinner_pattern: re.Pattern[str]


@dataclass(frozen=True)
class _ResponseMatch:
    """One Claude response-marker match in normalized output."""

    start: int
    end: int
    first_line: str


class ClaudeCodeShadowParseError(ShadowParserError):
    """Raised when Claude snapshot parsing hits an unexpected internal error."""


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

        parsed = self.parse_snapshot(scrollback, baseline_pos=0)
        metadata = parsed.surface_assessment.parser_metadata
        if not metadata.output_format_match:
            return ("unknown", False)
        return (metadata.output_format, True)

    def capture_baseline_pos(self, scrollback: str) -> int:
        """Capture a baseline offset for future baseline-reset diagnostics."""

        parsed = self.parse_snapshot(scrollback, baseline_pos=0)
        if parsed.surface_assessment.availability != "supported":
            raise ClaudeCodeShadowParseError(
                "unsupported_output_format: cannot capture Claude baseline from unsupported output",
                error_code="unsupported_output_format",
                metadata=parsed.surface_assessment.parser_metadata,
            )
        return len(parsed.dialog_projection.normalized_text)

    def parse_snapshot(
        self,
        scrollback: str,
        *,
        baseline_pos: int = 0,
    ) -> ParsedShadowSnapshot:
        """Return Claude state assessment and dialog projection for one snapshot."""

        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        preset, resolution = self._resolve_preset(scrollback)
        compiled = self._compiled_for_preset(preset)
        baseline_invalidated = baseline_pos > 0 and len(clean_output) < baseline_pos
        output_variant = self._detect_output_variant(clean_output, compiled)
        output_format_match = output_variant in set(preset.supported_variants)
        metadata = self._metadata_for(
            preset=preset,
            resolution=resolution,
            output_variant=output_variant or "unknown",
            output_format_match=output_format_match,
            baseline_invalidated=baseline_invalidated,
        )

        surface_assessment = self._build_surface_assessment(
            clean_output=clean_output,
            compiled=compiled,
            metadata=metadata,
        )
        dialog_projection = self._build_dialog_projection(
            raw_text=scrollback,
            clean_output=clean_output,
            compiled=compiled,
            metadata=metadata,
        )
        return ParsedShadowSnapshot(
            surface_assessment=surface_assessment,
            dialog_projection=dialog_projection,
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

    def _build_surface_assessment(
        self,
        *,
        clean_output: str,
        compiled: _CompiledPreset,
        metadata: ShadowParserMetadata,
    ) -> ClaudeSurfaceAssessment:
        tail_lines = self._tail_lines(clean_output, max_lines=self._status_tail_lines)
        waiting_excerpt = self._waiting_user_answer_excerpt(tail_lines)
        has_processing = self._contains_processing_spinner(tail_lines, compiled)
        has_idle_prompt = any(
            self._is_idle_prompt_line(line, compiled.preset) for line in tail_lines
        )
        has_trust_prompt = _TRUST_PROMPT_RE.search(clean_output) is not None
        has_slash_command = _SLASH_COMMAND_RE.search(clean_output) is not None
        has_error_banner = _ERROR_BANNER_RE.search(clean_output) is not None
        is_disconnected = _DISCONNECTED_RE.search(clean_output) is not None
        has_response_marker = bool(
            self._response_marker_matches(
                clean_output=clean_output,
                compiled=compiled,
                baseline_pos=0,
            )
        )

        evidence: list[str] = []
        if is_disconnected:
            evidence.append("DISCONNECTED_SIGNAL")
        if metadata.output_format_match:
            evidence.append("SUPPORTED_OUTPUT_FAMILY")
        if waiting_excerpt:
            evidence.append("WAITING_MENU_BLOCK")
        if has_trust_prompt:
            evidence.append("TRUST_PROMPT_BLOCK")
        if has_processing:
            evidence.append("PROCESSING_SPINNER_LINE")
        if has_idle_prompt:
            evidence.append("IDLE_PROMPT_LINE")
        if has_slash_command:
            evidence.append("SLASH_COMMAND_CONTEXT")
        if has_error_banner:
            evidence.append("ERROR_BANNER_BLOCK")
        if has_response_marker:
            evidence.append("RESPONSE_MARKER_LINE")

        availability: ShadowAvailability
        if is_disconnected:
            availability = "disconnected"
        elif metadata.output_format_match:
            availability = "supported"
        else:
            availability = "unsupported"

        ui_context: ClaudeUiContext = "unknown"
        if waiting_excerpt:
            ui_context = "trust_prompt" if has_trust_prompt else "selection_menu"
        elif has_slash_command:
            ui_context = "slash_command"
        elif has_error_banner:
            ui_context = "error_banner"
        elif has_idle_prompt or has_processing or has_response_marker:
            ui_context = "normal_prompt"

        activity: ShadowActivity
        if availability != "supported":
            activity = "unknown"
            accepts_input = False
        elif waiting_excerpt:
            activity = "waiting_user_answer"
            accepts_input = False
        elif has_processing:
            activity = "working"
            accepts_input = False
        elif has_idle_prompt:
            activity = "ready_for_input"
            accepts_input = ui_context == "normal_prompt"
        else:
            activity = "unknown"
            accepts_input = False

        return ClaudeSurfaceAssessment(
            availability=availability,
            activity=activity,
            accepts_input=accepts_input,
            ui_context=ui_context,
            parser_metadata=metadata,
            anomalies=metadata.anomalies,
            waiting_user_answer_excerpt=waiting_excerpt,
            evidence=tuple(evidence),
        )

    def _build_dialog_projection(
        self,
        *,
        raw_text: str,
        clean_output: str,
        compiled: _CompiledPreset,
        metadata: ShadowParserMetadata,
    ) -> ClaudeDialogProjection:
        projected_lines: list[str] = []
        evidence: list[str] = []

        for line in clean_output.splitlines():
            projected_line = self._project_line(line=line, compiled=compiled, evidence=evidence)
            _append_projection_line(projected_lines, projected_line)

        dialog_text = "\n".join(projected_lines).strip()
        if not dialog_text and clean_output.strip():
            dialog_text = clean_output.strip()

        head, tail = projection_head_tail(
            dialog_text,
            max_lines=_DEFAULT_PROJECTION_SLICE_LINES,
        )
        projection_metadata = ProjectionMetadata(
            provider_id="claude",
            source_kind="tui_snapshot",
            projector_id=_CLAUDE_PROJECTOR_ID,
            parser_metadata=metadata,
            dialog_line_count=len(dialog_text.splitlines()) if dialog_text else 0,
            head_line_count=len(head.splitlines()) if head else 0,
            tail_line_count=len(tail.splitlines()) if tail else 0,
        )
        return ClaudeDialogProjection(
            raw_text=raw_text,
            normalized_text=clean_output,
            dialog_text=dialog_text,
            head=head,
            tail=tail,
            projection_metadata=projection_metadata,
            anomalies=metadata.anomalies,
            evidence=tuple(evidence),
        )

    def _project_line(
        self,
        *,
        line: str,
        compiled: _CompiledPreset,
        evidence: list[str],
    ) -> str | None:
        clean_line = line.rstrip("\r")
        stripped = clean_line.strip()
        if not stripped:
            return ""
        if _BANNER_VERSION_RE.search(clean_line):
            evidence.append("DROP_BANNER_VERSION")
            return None
        if compiled.preset.separator_token in clean_line:
            evidence.append("DROP_SEPARATOR")
            return None
        if self._contains_processing_spinner([clean_line], compiled):
            evidence.append("DROP_PROCESSING_SPINNER")
            return None

        response_payload = self._response_payload(clean_line, compiled)
        if response_payload is not None:
            evidence.append("KEEP_RESPONSE_MARKER_PAYLOAD")
            return response_payload

        prompt_payload = self._prompt_payload(clean_line, compiled.preset)
        if prompt_payload is not None:
            if not prompt_payload:
                evidence.append("DROP_IDLE_PROMPT")
                return None
            evidence.append("KEEP_PROMPT_PAYLOAD")
            return prompt_payload

        if _WAITING_SELECTED_OPTION_RE.match(clean_line):
            evidence.append("KEEP_SELECTED_WAITING_OPTION")
            return clean_line.replace("❯", "", 1).strip()

        if _WAITING_OPTION_RE.match(clean_line):
            evidence.append("KEEP_WAITING_OPTION")
            return clean_line.strip()

        evidence.append("KEEP_VISIBLE_DIALOG_LINE")
        return clean_line.rstrip()

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

    def _response_payload(
        self,
        clean_line: str,
        compiled: _CompiledPreset,
    ) -> str | None:
        for pattern in compiled.response_patterns:
            match = pattern.match(clean_line)
            if match is not None:
                return match.group(1).rstrip()
        return None

    @staticmethod
    def _prompt_payload(
        clean_line: str,
        preset: ClaudeCodeParsingPreset,
    ) -> str | None:
        trimmed = clean_line.lstrip()
        if not trimmed:
            return None
        if trimmed[0] not in set(preset.idle_prompts):
            return None
        return trimmed[1:].strip()

    @staticmethod
    def _waiting_user_answer_excerpt(clean_tail_lines: list[str]) -> str | None:
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
            index for index, line in enumerate(clean_tail_lines) if _WAITING_OPTION_RE.match(line)
        ]
        if len(option_indices) < 2:
            return None

        has_selected_option = any(
            _WAITING_SELECTED_OPTION_RE.match(clean_tail_lines[index]) for index in option_indices
        )
        has_hint = any(_WAITING_HINT_RE.search(line) for line in clean_tail_lines)
        if not has_selected_option and not has_hint:
            return None

        start = max(option_indices[0] - 1, 0)
        end = min(option_indices[-1] + 2, len(clean_tail_lines))
        excerpt = "\n".join(line.rstrip() for line in clean_tail_lines[start:end] if line.strip())
        return excerpt.strip() or None


def _append_projection_line(lines: list[str], value: str | None) -> None:
    """Append one projected dialog line while collapsing repeated blanks."""

    if value is None:
        return
    if value == "":
        if lines and lines[-1] != "":
            lines.append("")
        return
    lines.append(value)
