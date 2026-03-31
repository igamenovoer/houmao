"""Runtime-owned Claude Code shadow parser for CAO ``mode=full`` output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

from .shadow_parser_core import (
    ANOMALY_BASELINE_INVALIDATED,
    DialogProjectorResult,
    DialogProjection,
    ParsedShadowSnapshot,
    PresetResolution,
    ProjectionMetadata,
    ShadowDialogProjector,
    ShadowAvailability,
    ShadowBusinessState,
    ShadowInputMode,
    ShadowParserAnomaly,
    ShadowParserError,
    ShadowParserMetadata,
    SnapshotSignalSet,
    SurfaceAssessment,
    VersionedParserPreset,
    VersionedPresetRegistry,
    ansi_stripped_tail_excerpt,
    find_prompt_boundary,
    finalize_projected_dialog,
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
_TRUST_PROMPT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:trust this (?:folder|directory)|allow claude|yes,\s*i trust)"
)
_SETUP_BLOCK_RE: Final[re.Pattern[str]] = re.compile(
    r"(?im)^\s*(?:sign in|log in|login|complete setup|finish onboarding|continue in browser|press enter to continue|authenticate)\b"
)
_ERROR_BANNER_RE: Final[re.Pattern[str]] = re.compile(r"(?im)^\s*(?:error|failed|warning)\b")
_DISCONNECTED_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:connection (?:lost|closed)|terminal detached|session ended|reconnect)"
)

_DEFAULT_STATUS_TAIL_LINES: Final[int] = 100
_DEFAULT_PROJECTION_SLICE_LINES: Final[int] = 12
_ENV_PRESET_OVERRIDE: Final[str] = "HOUMAO_CAO_CLAUDE_CODE_VERSION"

_OUTPUT_VARIANT_PROMPT_IDLE_V1: Final[str] = "claude_prompt_idle_v1"
_OUTPUT_VARIANT_RESPONSE_MARKER_V1: Final[str] = "claude_response_marker_v1"
_OUTPUT_VARIANT_WAITING_MENU_V1: Final[str] = "claude_waiting_menu_v1"
_OUTPUT_VARIANT_SPINNER_V1: Final[str] = "claude_spinner_v1"
_CLAUDE_LEGACY_PROJECTOR_ID: Final[str] = "claude_dialog_projection_legacy_v1"
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
    idle_prompt_pattern: re.Pattern[str]
    boundary_anchor_patterns: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class _ResponseMatch:
    """One Claude response-marker match in normalized output."""

    start: int
    end: int
    first_line: str


@dataclass(frozen=True)
class _BlockedSurfaceMatch:
    """Resolved Claude blocked-surface block within one tail snapshot."""

    start_index: int
    end_index: int
    blocked_surface_kind: str
    excerpt: str


@dataclass(frozen=True)
class _SurfaceAxes:
    """Derived shared axes plus provider context for one Claude snapshot."""

    business_state: ShadowBusinessState
    input_mode: ShadowInputMode
    ui_context: ClaudeUiContext


@dataclass(frozen=True)
class ClaudeProjectionContext:
    """Provider-owned projection context for one normalized Claude snapshot."""

    compiled: _CompiledPreset


ClaudeDialogProjector = ShadowDialogProjector[ClaudeProjectionContext]


@dataclass(frozen=True)
class _ClaudeRegexDialogProjector:
    """Best-effort regex projector over normalized Claude TUI snapshots."""

    projector_id: str

    def project(
        self,
        *,
        normalized_text: str,
        context: ClaudeProjectionContext,
    ) -> DialogProjectorResult:
        projected_lines: list[str] = []
        evidence: list[str] = []

        for line in normalized_text.splitlines():
            projected_line = self._project_line(
                line=line,
                compiled=context.compiled,
                evidence=evidence,
            )
            _append_projection_line(projected_lines, projected_line)

        return DialogProjectorResult(
            dialog_text="\n".join(projected_lines),
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
        if ClaudeCodeShadowParser._contains_processing_spinner([clean_line], compiled):
            evidence.append("DROP_PROCESSING_SPINNER")
            return None

        response_payload = ClaudeCodeShadowParser._response_payload(clean_line, compiled)
        if response_payload is not None:
            evidence.append("KEEP_RESPONSE_MARKER_PAYLOAD")
            return response_payload

        prompt_payload = ClaudeCodeShadowParser._prompt_payload(clean_line, compiled.preset)
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

    def __init__(
        self,
        *,
        status_tail_lines: int = _DEFAULT_STATUS_TAIL_LINES,
        projector_override: ClaudeDialogProjector | None = None,
    ) -> None:
        if status_tail_lines <= 0:
            raise ValueError("status_tail_lines must be positive")

        self._status_tail_lines = status_tail_lines
        self._projector_override = projector_override
        self._registry = VersionedPresetRegistry(
            provider_id="claude",
            override_env_var=_ENV_PRESET_OVERRIDE,
            presets=tuple(preset.identity for preset in self._PRESETS.values()),
        )
        self._compiled_preset_cache: dict[str, _CompiledPreset] = {}
        self._projector_by_preset_version: dict[str, ClaudeDialogProjector] = {
            "0.0.0": _ClaudeRegexDialogProjector(projector_id=_CLAUDE_LEGACY_PROJECTOR_ID),
            "2.1.0": _ClaudeRegexDialogProjector(projector_id=_CLAUDE_LEGACY_PROJECTOR_ID),
            "2.1.62": _ClaudeRegexDialogProjector(projector_id=_CLAUDE_PROJECTOR_ID),
        }

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
        projector = self._select_projector(
            preset=preset,
            output_variant=output_variant,
        )
        dialog_projection = self._build_dialog_projection(
            raw_text=scrollback,
            clean_output=clean_output,
            metadata=metadata,
            projector=projector,
            context=ClaudeProjectionContext(compiled=compiled),
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

        prompt_tokens = "|".join(
            re.escape(token) for token in sorted(set(preset.idle_prompts), key=len, reverse=True)
        )
        idle_prompt_pattern = re.compile(rf"^\s*(?:{prompt_tokens})(?:$|\s+.*)$")
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
            idle_prompt_pattern=idle_prompt_pattern,
            boundary_anchor_patterns=(
                idle_prompt_pattern,
                spinner_pattern,
                _WAITING_SELECTED_OPTION_RE,
                _WAITING_APPROVAL_RE,
                _TRUST_PROMPT_RE,
                _SETUP_BLOCK_RE,
            ),
        )
        self._compiled_preset_cache[preset.identity.version] = compiled
        return compiled

    def _select_projector(
        self,
        *,
        preset: ClaudeCodeParsingPreset,
        output_variant: str | None,
    ) -> ClaudeDialogProjector:
        del output_variant
        if self._projector_override is not None:
            return self._projector_override

        projector = self._projector_by_preset_version.get(preset.identity.version)
        if projector is not None:
            return projector
        return self._projector_by_preset_version["2.1.62"]

    def _build_surface_assessment(
        self,
        *,
        clean_output: str,
        compiled: _CompiledPreset,
        metadata: ShadowParserMetadata,
    ) -> ClaudeSurfaceAssessment:
        tail_lines = self._tail_lines(clean_output, max_lines=self._status_tail_lines)
        signals = self._extract_signals(tail_lines=tail_lines, compiled=compiled)
        active_zone_text = "\n".join(signals.active_zone_lines)
        is_disconnected = _DISCONNECTED_RE.search(active_zone_text) is not None
        has_trust_prompt = signals.blocked_surface_kind == "trust_prompt"
        has_setup_block = signals.blocked_surface_kind == "setup_block"
        has_response_marker = signals.has_response_marker

        evidence: list[str] = []
        if is_disconnected:
            evidence.append("DISCONNECTED_SIGNAL")
        if metadata.output_format_match:
            evidence.append("SUPPORTED_OUTPUT_FAMILY")
        if signals.has_operator_blocked:
            evidence.append("OPERATOR_BLOCKED_SURFACE")
        if has_trust_prompt:
            evidence.append("TRUST_PROMPT_BLOCK")
        if has_setup_block:
            evidence.append("SETUP_BLOCK_SURFACE")
        if signals.has_processing_spinner:
            evidence.append("PROCESSING_SPINNER_LINE")
        if signals.has_idle_prompt:
            evidence.append("IDLE_PROMPT_LINE")
        if signals.has_slash_command:
            evidence.append("SLASH_COMMAND_CONTEXT")
        if signals.has_error_banner:
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

        axes = self._classify_surface_axes(availability=availability, signals=signals)

        return ClaudeSurfaceAssessment(
            availability=availability,
            business_state=axes.business_state,
            input_mode=axes.input_mode,
            ui_context=axes.ui_context,
            parser_metadata=metadata,
            anomalies=metadata.anomalies,
            operator_blocked_excerpt=signals.operator_blocked_excerpt,
            evidence=tuple(evidence),
        )

    def _build_dialog_projection(
        self,
        *,
        raw_text: str,
        clean_output: str,
        metadata: ShadowParserMetadata,
        projector: ClaudeDialogProjector,
        context: ClaudeProjectionContext,
    ) -> ClaudeDialogProjection:
        projector_result = projector.project(
            normalized_text=clean_output,
            context=context,
        )
        dialog_text = finalize_projected_dialog(
            normalized_text=clean_output,
            dialog_text=projector_result.dialog_text,
        )

        head, tail = projection_head_tail(
            dialog_text,
            max_lines=_DEFAULT_PROJECTION_SLICE_LINES,
        )
        projection_metadata = ProjectionMetadata(
            provider_id="claude",
            source_kind="tui_snapshot",
            projector_id=projector.projector_id,
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
            anomalies=tuple([*metadata.anomalies, *projector_result.anomalies]),
            evidence=projector_result.evidence,
        )

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
        if self._operator_blocked_excerpt(
            clean_tail_lines=tail_lines,
            preset=compiled.preset,
        ):
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

    @staticmethod
    def _extract_signals(
        *,
        tail_lines: list[str],
        compiled: _CompiledPreset,
    ) -> SnapshotSignalSet:
        """Return Claude active-zone signals for one bounded tail snapshot."""

        blocked_match = ClaudeCodeShadowParser._blocked_surface_match(
            clean_tail_lines=tail_lines,
            preset=compiled.preset,
        )
        prompt_boundary_index, anchor_type = ClaudeCodeShadowParser._resolve_prompt_boundary(
            clean_tail_lines=tail_lines,
            compiled=compiled,
            blocked_match=blocked_match,
        )
        if prompt_boundary_index is None:
            historical_zone_lines: tuple[str, ...] = ()
            active_zone_lines = tuple(tail_lines)
        else:
            historical_zone_lines = tuple(tail_lines[:prompt_boundary_index])
            active_zone_lines = tuple(tail_lines[prompt_boundary_index:])

        active_prompt_payload: str | None = None
        if prompt_boundary_index is not None and anchor_type == "idle_prompt":
            active_prompt_payload = ClaudeCodeShadowParser._prompt_payload(
                tail_lines[prompt_boundary_index],
                compiled.preset,
            )

        active_lines_list = list(active_zone_lines)
        active_text = "\n".join(active_zone_lines)
        operator_blocked_excerpt = ClaudeCodeShadowParser._operator_blocked_excerpt(
            clean_tail_lines=active_lines_list,
            preset=compiled.preset,
        )
        has_idle_prompt = active_prompt_payload is not None
        has_processing_spinner = ClaudeCodeShadowParser._contains_processing_spinner(
            active_lines_list,
            compiled,
        )
        has_response_marker = any(
            ClaudeCodeShadowParser._response_payload(line, compiled) is not None
            for line in active_zone_lines
        )
        has_slash_command = bool(
            active_prompt_payload is not None and active_prompt_payload.startswith("/")
        )
        has_error_banner = _ERROR_BANNER_RE.search(active_text) is not None

        blocked_surface_kind = None
        if blocked_match is not None and operator_blocked_excerpt is not None:
            blocked_surface_kind = blocked_match.blocked_surface_kind

        return SnapshotSignalSet(
            prompt_boundary_index=prompt_boundary_index,
            active_zone_lines=active_zone_lines,
            historical_zone_lines=historical_zone_lines,
            has_idle_prompt=has_idle_prompt,
            has_processing_spinner=has_processing_spinner,
            has_response_marker=has_response_marker,
            has_operator_blocked=operator_blocked_excerpt is not None,
            has_slash_command=has_slash_command,
            has_error_banner=has_error_banner,
            operator_blocked_excerpt=operator_blocked_excerpt,
            active_prompt_payload=active_prompt_payload,
            anchor_type=anchor_type,
            blocked_surface_kind=blocked_surface_kind,
        )

    @staticmethod
    def _resolve_prompt_boundary(
        *,
        clean_tail_lines: list[str],
        compiled: _CompiledPreset,
        blocked_match: _BlockedSurfaceMatch | None,
    ) -> tuple[int | None, str | None]:
        """Resolve the start of Claude's latest active interaction block."""

        raw_anchor_index = find_prompt_boundary(
            clean_tail_lines,
            compiled.boundary_anchor_patterns,
        )
        if blocked_match is not None and (
            raw_anchor_index is None
            or blocked_match.start_index <= raw_anchor_index < blocked_match.end_index
            or blocked_match.start_index > raw_anchor_index
        ):
            return (blocked_match.start_index, blocked_match.blocked_surface_kind)
        if raw_anchor_index is None:
            return (None, None)

        if compiled.spinner_pattern.search(clean_tail_lines[raw_anchor_index]) is not None:
            owning_prompt_index = ClaudeCodeShadowParser._owning_prompt_index(
                clean_tail_lines=clean_tail_lines,
                spinner_index=raw_anchor_index,
                compiled=compiled,
            )
            if owning_prompt_index is not None:
                return (owning_prompt_index, "idle_prompt")
            return (raw_anchor_index, "spinner")

        if ClaudeCodeShadowParser._is_idle_prompt_line(
            clean_tail_lines[raw_anchor_index],
            compiled.preset,
        ):
            return (raw_anchor_index, "idle_prompt")

        if _SETUP_BLOCK_RE.search(clean_tail_lines[raw_anchor_index]) is not None:
            return (raw_anchor_index, "setup_block")
        if (
            _WAITING_APPROVAL_RE.search(clean_tail_lines[raw_anchor_index]) is not None
            or _TRUST_PROMPT_RE.search(clean_tail_lines[raw_anchor_index]) is not None
        ):
            return (raw_anchor_index, "trust_prompt")
        if _WAITING_SELECTED_OPTION_RE.match(clean_tail_lines[raw_anchor_index]) is not None:
            return (raw_anchor_index, "selection_menu")
        return (raw_anchor_index, None)

    @staticmethod
    def _owning_prompt_index(
        *,
        clean_tail_lines: list[str],
        spinner_index: int,
        compiled: _CompiledPreset,
    ) -> int | None:
        """Return the prompt line that owns the visible Claude spinner block."""

        for index in range(spinner_index - 1, -1, -1):
            line = clean_tail_lines[index]
            if not line.strip():
                continue
            if not ClaudeCodeShadowParser._is_idle_prompt_line(line, compiled.preset):
                return None

            trailing_lines = [
                candidate
                for candidate in clean_tail_lines[index + 1 : spinner_index + 1]
                if candidate.strip()
            ]
            if trailing_lines and all(
                compiled.spinner_pattern.search(candidate) is not None
                for candidate in trailing_lines
            ):
                return index
            return None
        return None

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

    @staticmethod
    def _response_payload(
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
    def _blocked_surface_match(
        *,
        clean_tail_lines: list[str],
        preset: ClaudeCodeParsingPreset,
    ) -> _BlockedSurfaceMatch | None:
        """Return Claude blocked-surface boundaries within the provided lines."""

        if not clean_tail_lines:
            return None

        for index, line in enumerate(clean_tail_lines):
            blocked_surface_kind: str | None = None
            if _SETUP_BLOCK_RE.search(line) is not None:
                blocked_surface_kind = "setup_block"
            elif (
                _WAITING_APPROVAL_RE.search(line) is not None
                or _TRUST_PROMPT_RE.search(line) is not None
            ):
                blocked_surface_kind = "trust_prompt"

            if blocked_surface_kind is None:
                continue

            excerpt_start = max(index - 1, 0)
            excerpt_end = min(index + 3, len(clean_tail_lines))
            excerpt = "\n".join(
                candidate.rstrip()
                for candidate in clean_tail_lines[excerpt_start:excerpt_end]
                if candidate.strip()
            ).strip()
            if excerpt:
                return _BlockedSurfaceMatch(
                    start_index=index,
                    end_index=excerpt_end,
                    blocked_surface_kind=blocked_surface_kind,
                    excerpt=excerpt,
                )

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

        start_index = option_indices[0]
        if start_index > 0:
            previous_line = clean_tail_lines[start_index - 1]
            if previous_line.strip() and not ClaudeCodeShadowParser._is_idle_prompt_line(
                previous_line,
                preset,
            ):
                start_index -= 1
        excerpt_end = min(option_indices[-1] + 2, len(clean_tail_lines))
        excerpt = "\n".join(
            line.rstrip() for line in clean_tail_lines[start_index:excerpt_end] if line.strip()
        ).strip()
        if not excerpt:
            return None
        return _BlockedSurfaceMatch(
            start_index=start_index,
            end_index=excerpt_end,
            blocked_surface_kind="selection_menu",
            excerpt=excerpt,
        )

    @staticmethod
    def _operator_blocked_excerpt(
        *,
        clean_tail_lines: list[str],
        preset: ClaudeCodeParsingPreset,
    ) -> str | None:
        """Return Claude blocked-surface excerpt from the provided lines."""

        blocked_match = ClaudeCodeShadowParser._blocked_surface_match(
            clean_tail_lines=clean_tail_lines,
            preset=preset,
        )
        if blocked_match is None:
            return None
        return blocked_match.excerpt

    @staticmethod
    def _classify_surface_axes(
        *,
        availability: ShadowAvailability,
        signals: SnapshotSignalSet,
    ) -> _SurfaceAxes:
        """Co-derive shared surface axes from one Claude evidence pass."""

        has_trust_prompt = signals.blocked_surface_kind == "trust_prompt"
        has_setup_block = signals.blocked_surface_kind == "setup_block"
        ui_context: ClaudeUiContext
        input_mode: ShadowInputMode
        if signals.has_operator_blocked:
            ui_context = (
                "trust_prompt" if (has_trust_prompt or has_setup_block) else "selection_menu"
            )
            input_mode = "closed" if has_setup_block and not signals.has_idle_prompt else "modal"
        elif signals.has_slash_command:
            ui_context = "slash_command"
            input_mode = "modal"
        elif signals.has_idle_prompt:
            ui_context = "normal_prompt"
            input_mode = "freeform"
        elif signals.has_error_banner:
            ui_context = "error_banner"
            input_mode = "closed"
        elif signals.has_processing_spinner:
            ui_context = "normal_prompt"
            input_mode = "closed"
        else:
            ui_context = "unknown"
            input_mode = "unknown"

        business_state: ShadowBusinessState
        if availability != "supported":
            business_state = "unknown"
        elif signals.has_operator_blocked:
            business_state = "awaiting_operator"
        elif signals.has_processing_spinner:
            business_state = "working"
        elif signals.has_idle_prompt or signals.has_slash_command or signals.has_error_banner:
            business_state = "idle"
        elif signals.has_response_marker:
            business_state = "unknown"
        else:
            business_state = "unknown"

        return _SurfaceAxes(
            business_state=business_state,
            input_mode=input_mode,
            ui_context=ui_context,
        )


def _append_projection_line(lines: list[str], value: str | None) -> None:
    """Append one projected dialog line while collapsing repeated blanks."""

    if value is None:
        return
    if value == "":
        if lines and lines[-1] != "":
            lines.append("")
        return
    lines.append(value)
