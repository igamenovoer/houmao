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


@dataclass(frozen=True)
class OfficialParseResult:
    """One official parser cycle result."""

    parsed_surface: HoumaoParsedSurface | None
    parse_error: HoumaoErrorDetail | None


class OfficialTuiParserAdapter:
    """Thin adapter over the shared parser stack using server-owned naming."""

    def supports_tool(self, *, tool: str) -> bool:
        """Return whether the shared parser stack supports the tool."""

        return tool_supports_cao_shadow_parser(tool)

    def capture_baseline(self, *, tool: str, output_text: str) -> int:
        """Capture the shared parser baseline offset for one tool."""

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
        anomaly_codes=tuple(
            anomaly.code
            for anomaly in (
                *assessment.parser_metadata.anomalies,
                *assessment.anomalies,
                *projection.anomalies,
            )
        ),
        baseline_invalidated=assessment.parser_metadata.baseline_invalidated,
        operator_blocked_excerpt=assessment.operator_blocked_excerpt,
    )
