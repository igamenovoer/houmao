"""Runtime-owned Codex shadow parser for CAO ``mode=full`` output."""

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

_DEFAULT_STATUS_TAIL_LINES: Final[int] = 100
_DEFAULT_PROJECTION_SLICE_LINES: Final[int] = 12
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
_IDLE_PROMPT_RE: Final[re.Pattern[str]] = re.compile(r"(?im)^\s*(?:❯|›|>|codex>)\s*(?:$|\S.*)$")
_IDLE_PROMPT_STRICT_RE: Final[re.Pattern[str]] = re.compile(r"(?im)^\s*(?:❯|›|>|codex>)\s*$")
_WAITING_OPTION_RE: Final[re.Pattern[str]] = re.compile(r"^\s*(?:[❯›>]\s*)?\d+\.\s+\S+")
_WAITING_SELECTED_OPTION_RE: Final[re.Pattern[str]] = re.compile(r"^\s*[❯›>]\s*\d+\.\s+\S+")
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
_LOGIN_BLOCK_RE: Final[re.Pattern[str]] = re.compile(
    r"(?im)^\s*(?:sign in|log in|login|authenticate|continue in browser|complete setup|press enter to continue)\b"
)
_FOOTER_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"(?i)(?:\?\s+for shortcuts|context left)")
_PROCESSING_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(thinking|processing|generating|working|running|executing|analyzing|starting|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏)"
)
_PROCESSING_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)^\s*(?:thinking|processing|generating|working|running|executing|analyzing|starting|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏)\b"
)
_TUI_PROGRESS_RE: Final[re.Pattern[str]] = re.compile(r"(?i)^\s*•.*\(\d+s\s*•\s*esc to interrupt\)")
_ERROR_BANNER_RE: Final[re.Pattern[str]] = re.compile(r"(?im)^\s*(?:error|failed|warning)\b")
_DISCONNECTED_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:connection (?:lost|closed)|terminal detached|session ended|reconnect)"
)

_OUTPUT_VARIANT_LABEL_V1: Final[str] = "codex_label_v1"
_OUTPUT_VARIANT_TUI_BULLET_V1: Final[str] = "codex_tui_bullet_v1"
_OUTPUT_VARIANT_WAITING_APPROVAL_V1: Final[str] = "codex_waiting_approval_v1"
_OUTPUT_VARIANT_PROMPT_IDLE_V1: Final[str] = "codex_prompt_idle_v1"
_CODEX_LEGACY_PROJECTOR_ID: Final[str] = "codex_dialog_projection_legacy_v1"
_CODEX_PROJECTOR_ID: Final[str] = "codex_dialog_projection_v1"
_BOUNDARY_ANCHOR_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    _IDLE_PROMPT_RE,
    _TUI_PROGRESS_RE,
    _PROCESSING_LINE_RE,
    _WAITING_SELECTED_OPTION_RE,
    _WAITING_APPROVAL_RE,
    _TRUST_PROMPT_RE,
    _LOGIN_BLOCK_RE,
)

CodexUiContext = Literal[
    "normal_prompt",
    "selection_menu",
    "slash_command",
    "approval_prompt",
    "error_banner",
    "unknown",
]


@dataclass(frozen=True)
class CodexParsingPreset:
    """Codex parsing preset contract."""

    identity: VersionedParserPreset
    supported_variants: tuple[str, ...]


@dataclass(frozen=True)
class CodexSurfaceAssessment(SurfaceAssessment):
    """Codex-specific snapshot assessment."""

    ui_context: CodexUiContext
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class CodexDialogProjection(DialogProjection):
    """Codex-specific dialog projection."""

    evidence: tuple[str, ...] = ()


class CodexShadowParseError(ShadowParserError):
    """Raised when Codex snapshot parsing hits an unexpected internal error."""


@dataclass(frozen=True)
class _AssistantMatch:
    """One assistant message marker in normalized Codex output."""

    start: int
    end: int
    first_line: str


@dataclass(frozen=True)
class _BlockedSurfaceMatch:
    """Resolved Codex blocked-surface block within one tail snapshot."""

    start_index: int
    end_index: int
    blocked_surface_kind: str
    excerpt: str


@dataclass(frozen=True)
class _SurfaceAxes:
    """Derived shared axes plus provider context for one Codex snapshot."""

    business_state: ShadowBusinessState
    input_mode: ShadowInputMode
    ui_context: CodexUiContext


@dataclass(frozen=True)
class CodexProjectionContext:
    """Provider-owned projection context for one normalized Codex snapshot."""

    output_variant: str | None


CodexDialogProjector = ShadowDialogProjector[CodexProjectionContext]


@dataclass(frozen=True)
class _CodexRegexDialogProjector:
    """Best-effort regex projector over normalized Codex TUI snapshots."""

    projector_id: str

    def project(
        self,
        *,
        normalized_text: str,
        context: CodexProjectionContext,
    ) -> DialogProjectorResult:
        del context
        projected_lines: list[str] = []
        evidence: list[str] = []

        for line in normalized_text.splitlines():
            projected_line = self._project_line(line=line, evidence=evidence)
            _append_projection_line(projected_lines, projected_line)

        return DialogProjectorResult(
            dialog_text="\n".join(projected_lines),
            evidence=tuple(evidence),
        )

    def _project_line(self, *, line: str, evidence: list[str]) -> str | None:
        clean_line = line.rstrip("\r")
        stripped = clean_line.strip()
        if not stripped:
            return ""
        if _BANNER_VERSION_RE.search(clean_line):
            evidence.append("DROP_BANNER_VERSION")
            return None
        if clean_line.startswith(("╭", "╰", "│")):
            evidence.append("DROP_TUI_FRAME")
            return None
        if _FOOTER_TOKEN_RE.search(clean_line):
            evidence.append("DROP_FOOTER_CHROME")
            return None
        if CodexShadowParser._is_processing_line(clean_line):
            evidence.append("DROP_PROCESSING_SIGNAL")
            return None
        if _IDLE_PROMPT_STRICT_RE.match(clean_line):
            evidence.append("DROP_IDLE_PROMPT")
            return None

        label_match = _ASSISTANT_LABEL_RE.match(clean_line)
        if label_match is not None:
            evidence.append("KEEP_ASSISTANT_LABEL_PAYLOAD")
            return label_match.group(1).rstrip()

        bullet_match = _ASSISTANT_BULLET_RE.match(clean_line)
        if bullet_match is not None:
            payload = bullet_match.group(1).rstrip()
            if _PROCESSING_RE.search(payload):
                evidence.append("DROP_ASSISTANT_PROGRESS_BULLET")
                return None
            evidence.append("KEEP_ASSISTANT_BULLET_PAYLOAD")
            return payload

        prompt_payload = CodexShadowParser._prompt_payload(clean_line)
        if prompt_payload is not None:
            if not prompt_payload:
                evidence.append("DROP_IDLE_PROMPT")
                return None
            evidence.append("KEEP_PROMPT_PAYLOAD")
            return prompt_payload

        if _WAITING_SELECTED_OPTION_RE.match(clean_line):
            evidence.append("KEEP_SELECTED_WAITING_OPTION")
            return clean_line.replace("❯", "", 1).replace("›", "", 1).replace(">", "", 1).strip()

        if _WAITING_OPTION_RE.match(clean_line):
            evidence.append("KEEP_WAITING_OPTION")
            return clean_line.strip()

        evidence.append("KEEP_VISIBLE_DIALOG_LINE")
        return clean_line.rstrip()


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

    def __init__(
        self,
        *,
        status_tail_lines: int = _DEFAULT_STATUS_TAIL_LINES,
        projector_override: CodexDialogProjector | None = None,
    ) -> None:
        if status_tail_lines <= 0:
            raise ValueError("status_tail_lines must be positive")
        self._status_tail_lines = status_tail_lines
        self._projector_override = projector_override
        self._registry = VersionedPresetRegistry(
            provider_id="codex",
            override_env_var=_ENV_PRESET_OVERRIDE,
            presets=tuple(preset.identity for preset in self._PRESETS.values()),
        )
        self._projector_by_preset_version: dict[str, CodexDialogProjector] = {
            "0.1.0": _CodexRegexDialogProjector(projector_id=_CODEX_LEGACY_PROJECTOR_ID),
            "0.98.0": _CodexRegexDialogProjector(projector_id=_CODEX_PROJECTOR_ID),
        }

    def resolve_preset_version(self, scrollback: str) -> str:
        """Resolve Codex preset version using registry selection order."""

        preset, _ = self._resolve_preset(scrollback)
        return preset.identity.version

    def detect_output_format(self, scrollback: str) -> tuple[str, bool]:
        """Detect whether scrollback matches one supported Codex variant."""

        parsed = self.parse_snapshot(scrollback, baseline_pos=0)
        metadata = parsed.surface_assessment.parser_metadata
        if not metadata.output_format_match:
            return ("unknown", False)
        return (metadata.output_format, True)

    def capture_baseline_pos(self, scrollback: str) -> int:
        """Capture a baseline offset for future baseline-reset diagnostics."""

        parsed = self.parse_snapshot(scrollback, baseline_pos=0)
        if parsed.surface_assessment.availability != "supported":
            raise CodexShadowParseError(
                "unsupported_output_format: cannot capture Codex baseline from unsupported output",
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
        """Return Codex state assessment and dialog projection for one snapshot."""

        clean_output = normalize_shadow_output(strip_ansi(scrollback))
        preset, resolution = self._resolve_preset(scrollback)
        baseline_invalidated = baseline_pos > 0 and len(clean_output) < baseline_pos
        output_variant = self._detect_output_variant(clean_output)
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
            context=CodexProjectionContext(output_variant=output_variant),
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

    def _select_projector(
        self,
        *,
        preset: CodexParsingPreset,
        output_variant: str | None,
    ) -> CodexDialogProjector:
        del output_variant
        if self._projector_override is not None:
            return self._projector_override

        projector = self._projector_by_preset_version.get(preset.identity.version)
        if projector is not None:
            return projector
        return self._projector_by_preset_version["0.98.0"]

    def _build_surface_assessment(
        self,
        *,
        clean_output: str,
        metadata: ShadowParserMetadata,
    ) -> CodexSurfaceAssessment:
        tail_lines = self._tail_lines(clean_output, max_lines=self._status_tail_lines)
        signals = self._extract_signals(tail_lines=tail_lines)
        active_zone_text = "\n".join(signals.active_zone_lines)
        is_disconnected = _DISCONNECTED_RE.search(active_zone_text) is not None
        has_approval_prompt = signals.blocked_surface_kind == "approval_prompt"
        has_login_block = signals.blocked_surface_kind == "login_block"
        has_assistant_output = self._has_active_assistant_output(signals)

        evidence: list[str] = []
        if is_disconnected:
            evidence.append("DISCONNECTED_SIGNAL")
        if metadata.output_format_match:
            evidence.append("SUPPORTED_OUTPUT_FAMILY")
        if signals.has_operator_blocked:
            evidence.append("CODEX_OPERATOR_BLOCKED_SURFACE")
        if has_approval_prompt:
            evidence.append("CODEX_APPROVAL_PROMPT")
        if has_login_block:
            evidence.append("CODEX_LOGIN_BLOCK")
        if signals.has_processing_spinner:
            evidence.append("CODEX_PROCESSING_SIGNAL")
        if signals.has_idle_prompt:
            evidence.append("CODEX_IDLE_PROMPT")
        if signals.has_slash_command:
            evidence.append("CODEX_SLASH_COMMAND_CONTEXT")
        if signals.has_error_banner:
            evidence.append("CODEX_ERROR_BANNER")
        if has_assistant_output:
            evidence.append("CODEX_ASSISTANT_DIALOG_VISIBLE")

        availability: ShadowAvailability
        if is_disconnected:
            availability = "disconnected"
        elif metadata.output_format_match:
            availability = "supported"
        else:
            availability = "unsupported"

        axes = self._classify_surface_axes(availability=availability, signals=signals)

        return CodexSurfaceAssessment(
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
        projector: CodexDialogProjector,
        context: CodexProjectionContext,
    ) -> CodexDialogProjection:
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
            provider_id="codex",
            source_kind="tui_snapshot",
            projector_id=projector.projector_id,
            parser_metadata=metadata,
            dialog_line_count=len(dialog_text.splitlines()) if dialog_text else 0,
            head_line_count=len(head.splitlines()) if head else 0,
            tail_line_count=len(tail.splitlines()) if tail else 0,
        )
        return CodexDialogProjection(
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
        has_waiting = self._operator_blocked_excerpt(tail_lines) is not None

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
        stripped = line.strip().lower()
        if stripped.startswith(
            (
                "thinking",
                "processing",
                "generating",
                "working",
                "running",
                "executing",
                "analyzing",
                "starting",
            )
        ):
            return True
        return any(
            token in stripped for token in ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
        )

    @staticmethod
    def _extract_signals(*, tail_lines: list[str]) -> SnapshotSignalSet:
        """Return Codex active-zone signals for one bounded tail snapshot."""

        blocked_match = CodexShadowParser._blocked_surface_match(clean_tail_lines=tail_lines)
        prompt_boundary_index, anchor_type = CodexShadowParser._resolve_prompt_boundary(
            clean_tail_lines=tail_lines,
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
            active_prompt_payload = CodexShadowParser._prompt_payload(
                tail_lines[prompt_boundary_index]
            )

        active_lines_list = list(active_zone_lines)
        active_zone_text = "\n".join(active_zone_lines)
        operator_blocked_excerpt = CodexShadowParser._operator_blocked_excerpt(active_lines_list)
        has_idle_prompt = active_prompt_payload is not None
        has_processing_spinner = any(
            CodexShadowParser._is_processing_line(line) for line in active_zone_lines
        )
        has_response_marker = False
        has_slash_command = bool(
            active_prompt_payload is not None and active_prompt_payload.startswith("/")
        )
        has_error_banner = _ERROR_BANNER_RE.search(active_zone_text) is not None

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
        blocked_match: _BlockedSurfaceMatch | None,
    ) -> tuple[int | None, str | None]:
        """Resolve the start of Codex's latest active interaction block."""

        raw_anchor_index = find_prompt_boundary(clean_tail_lines, _BOUNDARY_ANCHOR_PATTERNS)
        if blocked_match is not None and (
            raw_anchor_index is None
            or blocked_match.start_index <= raw_anchor_index < blocked_match.end_index
            or blocked_match.start_index > raw_anchor_index
        ):
            return (blocked_match.start_index, blocked_match.blocked_surface_kind)
        if raw_anchor_index is None:
            return (None, None)

        raw_line = clean_tail_lines[raw_anchor_index]
        if CodexShadowParser._is_processing_line(raw_line):
            owning_prompt_index = CodexShadowParser._owning_prompt_index(
                clean_tail_lines=clean_tail_lines,
                processing_index=raw_anchor_index,
            )
            if owning_prompt_index is not None:
                return (owning_prompt_index, "idle_prompt")
            return (raw_anchor_index, "spinner")

        if _LOGIN_BLOCK_RE.search(raw_line) is not None:
            return (raw_anchor_index, "login_block")
        if (
            _WAITING_APPROVAL_RE.search(raw_line) is not None
            or _TRUST_PROMPT_RE.search(raw_line) is not None
        ):
            return (raw_anchor_index, "approval_prompt")
        if _WAITING_SELECTED_OPTION_RE.match(raw_line) is not None:
            return (raw_anchor_index, "selection_menu")
        if _IDLE_PROMPT_RE.match(raw_line) is not None:
            return (raw_anchor_index, "idle_prompt")
        return (raw_anchor_index, None)

    @staticmethod
    def _owning_prompt_index(
        *,
        clean_tail_lines: list[str],
        processing_index: int,
    ) -> int | None:
        """Return the prompt line that owns the visible Codex progress block."""

        for index in range(processing_index - 1, -1, -1):
            line = clean_tail_lines[index]
            if not line.strip():
                continue
            if not _IDLE_PROMPT_RE.match(line):
                return None

            trailing_lines = [
                candidate
                for candidate in clean_tail_lines[index + 1 : processing_index + 1]
                if candidate.strip()
            ]
            if trailing_lines and all(
                CodexShadowParser._is_processing_line(candidate) for candidate in trailing_lines
            ):
                return index
            return None
        return None

    @staticmethod
    def _next_real_idle_prompt_index(
        clean_tail_lines: list[str],
        *,
        start_index: int,
    ) -> int | None:
        """Return the next actual prompt line after one blocked surface."""

        for index in range(start_index, len(clean_tail_lines)):
            line = clean_tail_lines[index]
            if _WAITING_OPTION_RE.match(line):
                continue
            if _IDLE_PROMPT_RE.match(line):
                return index
        return None

    def _has_active_assistant_output(self, signals: SnapshotSignalSet) -> bool:
        """Return whether the active zone still shows assistant output."""

        active_zone_text = "\n".join(signals.active_zone_lines)
        return bool(self._assistant_matches(active_zone_text, baseline_pos=0))

    @staticmethod
    def _prompt_payload(line: str) -> str | None:
        if not _IDLE_PROMPT_RE.match(line):
            return None
        trimmed = line.lstrip()
        if trimmed.startswith("codex>"):
            return trimmed[len("codex>") :].strip()
        return trimmed[1:].strip()

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
    def _blocked_surface_match(clean_tail_lines: list[str]) -> _BlockedSurfaceMatch | None:
        """Return Codex blocked-surface boundaries within the provided lines."""

        if not clean_tail_lines:
            return None

        for index, line in enumerate(clean_tail_lines):
            blocked_surface_kind: str | None = None
            if _LOGIN_BLOCK_RE.search(line) is not None:
                blocked_surface_kind = "login_block"
            elif (
                _WAITING_APPROVAL_RE.search(line) is not None
                or _TRUST_PROMPT_RE.search(line) is not None
            ):
                blocked_surface_kind = "approval_prompt"

            if blocked_surface_kind is None:
                continue

            excerpt_start = max(index - 1, 0)
            next_prompt_index = CodexShadowParser._next_real_idle_prompt_index(
                clean_tail_lines,
                start_index=index + 1,
            )
            block_end_index = next_prompt_index if next_prompt_index is not None else len(clean_tail_lines)
            excerpt_end = min(index + 3, block_end_index)
            excerpt = "\n".join(
                candidate.rstrip()
                for candidate in clean_tail_lines[excerpt_start:excerpt_end]
                if candidate.strip()
            ).strip()
            if excerpt:
                return _BlockedSurfaceMatch(
                    start_index=index,
                    end_index=block_end_index,
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
            if previous_line.strip() and not _IDLE_PROMPT_RE.match(previous_line):
                start_index -= 1
        next_prompt_index = CodexShadowParser._next_real_idle_prompt_index(
            clean_tail_lines,
            start_index=option_indices[-1] + 1,
        )
        block_end_index = next_prompt_index if next_prompt_index is not None else len(clean_tail_lines)
        excerpt_end = min(option_indices[-1] + 2, block_end_index)
        excerpt = "\n".join(
            line.rstrip()
            for line in clean_tail_lines[start_index:excerpt_end]
            if line.strip()
        ).strip()
        if not excerpt:
            return None
        return _BlockedSurfaceMatch(
            start_index=start_index,
            end_index=block_end_index,
            blocked_surface_kind="selection_menu",
            excerpt=excerpt,
        )

    @staticmethod
    def _operator_blocked_excerpt(clean_tail_lines: list[str]) -> str | None:
        """Return Codex blocked-surface excerpt from the provided lines."""

        blocked_match = CodexShadowParser._blocked_surface_match(clean_tail_lines)
        if blocked_match is None:
            return None
        return blocked_match.excerpt

    @staticmethod
    def _classify_surface_axes(
        *,
        availability: ShadowAvailability,
        signals: SnapshotSignalSet,
    ) -> _SurfaceAxes:
        """Co-derive shared surface axes from one Codex evidence pass."""

        has_approval_prompt = signals.blocked_surface_kind == "approval_prompt"
        has_login_block = signals.blocked_surface_kind == "login_block"
        has_assistant_output = bool(
            _ASSISTANT_LABEL_RE.search("\n".join(signals.active_zone_lines))
        ) or any(
            _ASSISTANT_BULLET_RE.match(line) and not CodexShadowParser._is_processing_line(line)
            for line in signals.active_zone_lines
        )

        ui_context: CodexUiContext
        input_mode: ShadowInputMode
        if signals.has_operator_blocked:
            ui_context = (
                "approval_prompt" if (has_approval_prompt or has_login_block) else "selection_menu"
            )
            input_mode = "closed" if has_login_block and not signals.has_idle_prompt else "modal"
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
        elif has_assistant_output:
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
