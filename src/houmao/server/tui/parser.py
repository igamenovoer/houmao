"""Official parser adapter for server-owned live TUI tracking."""

from __future__ import annotations

from dataclasses import dataclass

from houmao.agents.realm_controller.backends.shadow_parser_core import ParsedShadowSnapshot
from houmao.agents.realm_controller.backends.shadow_parser_stack import (
    ShadowParserStack,
    as_shadow_parser_error,
)
from houmao.agents.realm_controller.launch_plan import tool_supports_cao_shadow_parser
from houmao.server.models import HoumaoErrorDetail, HoumaoParsedSurface
from houmao.shared_tui_tracking.apps.kimi_code.profile import (
    KimiSurfaceAnalysis,
    analyze_kimi_surface,
)
from houmao.shared_tui_tracking.surface import SurfaceView


@dataclass(frozen=True)
class OfficialParseResult:
    """One official parser cycle result."""

    parsed_surface: HoumaoParsedSurface | None
    parse_error: HoumaoErrorDetail | None


class OfficialTuiParserAdapter:
    """Thin adapter over the shared parser stack using server-owned naming."""

    def supports_tool(self, *, tool: str) -> bool:
        """Return whether the shared parser stack supports the tool."""

        return tool == "kimi" or tool_supports_cao_shadow_parser(tool)

    def capture_baseline(self, *, tool: str, output_text: str) -> int:
        """Capture the shared parser baseline offset for one tool."""

        if tool == "kimi":
            del output_text
            return 0
        stack = ShadowParserStack(tool=tool)
        return stack.capture_baseline_pos(output_text)

    def parse(
        self,
        *,
        tool: str,
        output_text: str,
        baseline_pos: int,
    ) -> OfficialParseResult:
        """Parse one tmux snapshot through the shared parser stack."""

        if tool == "kimi":
            return OfficialParseResult(
                parsed_surface=_parse_kimi_surface(output_text=output_text),
                parse_error=None,
            )

        stack = ShadowParserStack(tool=tool)
        try:
            snapshot = stack.parse_snapshot(output_text, baseline_pos=baseline_pos)
        except Exception as exc:
            normalized = as_shadow_parser_error(exc)
            details = {"error_code": normalized.error_code, "parser_family": stack.parser_family}
            if normalized.metadata is not None:
                details["parser_preset_id"] = normalized.metadata.parser_preset_id
                details["parser_preset_version"] = normalized.metadata.parser_preset_version
                details["output_format"] = normalized.metadata.output_format
                details["output_variant"] = normalized.metadata.output_variant
            return OfficialParseResult(
                parsed_surface=None,
                parse_error=HoumaoErrorDetail(
                    kind="parse_error",
                    message=str(normalized),
                    details=details,
                ),
            )

        return OfficialParseResult(
            parsed_surface=_parsed_surface_from_snapshot(
                snapshot=snapshot,
                parser_family=stack.parser_family,
            ),
            parse_error=None,
        )


def _parsed_surface_from_snapshot(
    *,
    snapshot: ParsedShadowSnapshot,
    parser_family: str,
) -> HoumaoParsedSurface:
    """Convert one shared parser snapshot into the public route model."""

    assessment = snapshot.surface_assessment
    projection = snapshot.dialog_projection
    return HoumaoParsedSurface(
        parser_family=parser_family,
        parser_preset_id=assessment.parser_metadata.parser_preset_id,
        parser_preset_version=assessment.parser_metadata.parser_preset_version,
        availability=assessment.availability,
        business_state=assessment.business_state,
        input_mode=assessment.input_mode,
        ui_context=assessment.ui_context,
        normalized_projection_text=projection.normalized_text,
        dialog_text=projection.dialog_text,
        dialog_head=projection.head,
        dialog_tail=projection.tail,
        anomaly_codes=[
            anomaly.code
            for anomaly in (
                *assessment.parser_metadata.anomalies,
                *assessment.anomalies,
                *projection.anomalies,
            )
        ],
        baseline_invalidated=assessment.parser_metadata.baseline_invalidated,
        operator_blocked_excerpt=assessment.operator_blocked_excerpt,
    )


def _parse_kimi_surface(*, output_text: str) -> HoumaoParsedSurface:
    """Convert one Kimi visible pane snapshot into an official parsed surface."""

    analysis = analyze_kimi_surface(output_text)
    normalized_text = _normalized_kimi_text(output_text)
    dialog_text = _kimi_dialog_text(
        output_text=output_text,
        normalized_text=normalized_text,
        analysis=analysis,
    )
    business_state, input_mode, ui_context = _kimi_state_fields(
        normalized_text=normalized_text,
        analysis=analysis,
    )
    operator_blocked_excerpt = dialog_text if analysis.approval_visible else None
    return HoumaoParsedSurface(
        parser_family="kimi_code_tui",
        parser_preset_id="kimi_code",
        parser_preset_version="0.23.x",
        availability="supported",
        business_state=business_state,
        input_mode=input_mode,
        ui_context=ui_context,
        normalized_projection_text=normalized_text,
        dialog_text=dialog_text,
        dialog_head=_text_head(dialog_text),
        dialog_tail=_text_tail(dialog_text),
        anomaly_codes=[],
        baseline_invalidated=False,
        operator_blocked_excerpt=operator_blocked_excerpt,
    )


def _kimi_state_fields(
    *,
    normalized_text: str,
    analysis: KimiSurfaceAnalysis,
) -> tuple[str, str, str]:
    """Return parser-owned state fields for one Kimi surface analysis."""

    if analysis.approval_visible:
        return "awaiting_operator", "modal", "approval_dialog"
    if analysis.activity_visible:
        return "working", "closed", "normal_prompt"
    if analysis.prompt.prompt_visible:
        return "idle", "freeform", "normal_prompt"
    if _kimi_startup_modal_visible(normalized_text):
        return "awaiting_operator", "modal", "startup_modal"
    return "unknown", "unknown", "unknown"


def _normalized_kimi_text(output_text: str) -> str:
    """Return ANSI-stripped Kimi pane text."""

    return "\n".join(SurfaceView.from_text(output_text).stripped_lines)


def _kimi_dialog_text(
    *,
    output_text: str,
    normalized_text: str,
    analysis: KimiSurfaceAnalysis,
) -> str:
    """Return operator-useful Kimi dialog text for the parsed surface."""

    if analysis.approval_visible and analysis.approval_header is not None:
        approval_text = _kimi_approval_dialog_text(
            output_text=output_text,
            approval_header=analysis.approval_header,
        )
        if approval_text:
            return approval_text
    return normalized_text


def _kimi_approval_dialog_text(*, output_text: str, approval_header: str) -> str:
    """Return the visible Kimi approval dialog region when present."""

    surface = SurfaceView.from_text(output_text)
    lines = [line.strip() for line in surface.stripped_lines if line.strip()]
    header_index = next(
        (index for index, line in enumerate(lines) if approval_header in line),
        None,
    )
    if header_index is None:
        return ""

    end_index = header_index
    for index, line in enumerate(lines[header_index + 1 :], start=header_index + 1):
        if _kimi_prompt_or_editor_line(line):
            break
        end_index = index
    start_index = max(0, header_index - 1)
    return "\n".join(lines[start_index : end_index + 1])


def _kimi_prompt_or_editor_line(line: str) -> bool:
    """Return whether one stripped line belongs to the Kimi editor box."""

    return line.startswith(("╭", "╰", "│ >"))


def _kimi_startup_modal_visible(normalized_text: str) -> bool:
    """Return whether text looks like a Kimi startup or blocking modal surface."""

    lowered = normalized_text.lower()
    startup_needles = (
        "log in",
        "login",
        "sign in",
        "update",
        "upgrade",
        "install update",
        "select a session",
        "choose a session",
        "session picker",
    )
    return any(needle in lowered for needle in startup_needles)


def _text_head(text: str, *, line_count: int = 20) -> str:
    """Return the first lines of one parsed text block."""

    return "\n".join(text.splitlines()[:line_count])


def _text_tail(text: str, *, line_count: int = 20) -> str:
    """Return the last lines of one parsed text block."""

    return "\n".join(text.splitlines()[-line_count:])
