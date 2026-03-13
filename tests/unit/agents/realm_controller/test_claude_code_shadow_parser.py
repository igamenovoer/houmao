from __future__ import annotations

from pathlib import Path

import pytest

from gig_agents.agents.realm_controller.backends.claude_code_shadow import (
    ClaudeCodeShadowParser,
)
from gig_agents.agents.realm_controller.backends.shadow_parser_core import (
    ANOMALY_BASELINE_INVALIDATED,
    ANOMALY_PRESET_OVERRIDE_USED,
    ANOMALY_UNKNOWN_VERSION_FLOOR_USED,
)

_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "shadow_parser" / "claude"


def _fixture(name: str) -> str:
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_claude_shadow_preset_resolution_prefers_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = ClaudeCodeShadowParser()
    monkeypatch.setenv("AGENTSYS_CAO_CLAUDE_CODE_VERSION", "2.1.62")

    version = parser.resolve_preset_version("Claude Code v0.0.0\n> ")
    snapshot = parser.parse_snapshot(_fixture("exact_preset_match.txt"), baseline_pos=0)

    assert version == "2.1.62"
    anomaly_codes = {anomaly.code for anomaly in snapshot.surface_assessment.anomalies}
    assert ANOMALY_PRESET_OVERRIDE_USED in anomaly_codes


def test_claude_shadow_returns_surface_assessment_and_projection() -> None:
    parser = ClaudeCodeShadowParser()

    snapshot = parser.parse_snapshot(_fixture("exact_preset_match.txt"), baseline_pos=0)
    assessment = snapshot.surface_assessment
    projection = snapshot.dialog_projection

    assert assessment.availability == "supported"
    assert assessment.business_state == "idle"
    assert assessment.input_mode == "freeform"
    assert assessment.ui_context == "normal_prompt"
    assert assessment.parser_metadata.parser_preset_version == "2.1.62"
    assert assessment.parser_metadata.output_variant == "claude_response_marker_v1"
    assert "SUPPORTED_OUTPUT_FAMILY" in assessment.evidence
    assert "Summarize repo changes" in projection.dialog_text
    assert "Added unified parser stack." in projection.dialog_text
    assert projection.head == projection.dialog_text
    assert projection.tail == projection.dialog_text


def test_claude_shadow_reports_floor_lookup_anomaly_for_unknown_version() -> None:
    parser = ClaudeCodeShadowParser()

    snapshot = parser.parse_snapshot(
        _fixture("floor_preset_unknown_version.txt"),
        baseline_pos=0,
    )

    assert snapshot.surface_assessment.availability == "supported"
    assert snapshot.surface_assessment.parser_metadata.parser_preset_version == "2.1.62"
    anomaly_codes = {anomaly.code for anomaly in snapshot.surface_assessment.anomalies}
    assert ANOMALY_UNKNOWN_VERSION_FLOOR_USED in anomaly_codes


def test_claude_shadow_reports_unsupported_surface_for_drift() -> None:
    parser = ClaudeCodeShadowParser()

    snapshot = parser.parse_snapshot(_fixture("drifted_unknown.txt"), baseline_pos=0)

    assert snapshot.surface_assessment.availability == "unsupported"
    assert snapshot.surface_assessment.business_state == "unknown"
    assert snapshot.surface_assessment.input_mode == "unknown"
    assert snapshot.surface_assessment.parser_metadata.output_variant == "unknown"
    assert snapshot.surface_assessment.parser_metadata.output_format_match is False
    assert "<claude-output-vnext>" in snapshot.dialog_projection.dialog_text


def test_claude_shadow_status_detects_waiting_user_answer() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = (
        "Claude Code v2.1.62\n"
        "Choose an option:\n"
        "❯ 1. Keep existing changes\n"
        "2. Overwrite and continue\n"
        "Use arrow keys to move and press enter.\n"
    )

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "awaiting_operator"
    assert snapshot.surface_assessment.input_mode == "modal"
    assert snapshot.surface_assessment.ui_context == "selection_menu"
    assert snapshot.surface_assessment.operator_blocked_excerpt is not None
    assert "1. Keep existing changes" in snapshot.surface_assessment.operator_blocked_excerpt
    assert "Choose an option:" in snapshot.dialog_projection.dialog_text


def test_claude_shadow_detects_trust_prompt_context() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = "Claude Code v2.1.62\nAllow Claude to work in this folder? [y/n]\n"

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "awaiting_operator"
    assert snapshot.surface_assessment.input_mode == "modal"
    assert snapshot.surface_assessment.ui_context == "trust_prompt"


def test_claude_shadow_detects_setup_block_as_closed_operator_surface() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = "Claude Code v2.1.62\nComplete setup to continue\nPress Enter to continue\n"

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "awaiting_operator"
    assert snapshot.surface_assessment.input_mode == "closed"
    assert snapshot.surface_assessment.ui_context == "trust_prompt"
    assert snapshot.surface_assessment.operator_blocked_excerpt is not None


def test_claude_shadow_classifies_recognized_unclassifiable_snapshot_as_unknown() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = "Claude Code v2.1.62\n● Partial answer with no idle prompt\n"

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.availability == "supported"
    assert snapshot.surface_assessment.business_state == "unknown"
    assert snapshot.surface_assessment.input_mode == "unknown"
    assert snapshot.surface_assessment.parser_metadata.output_format_match is True
    assert snapshot.dialog_projection.dialog_text == "Partial answer with no idle prompt"


def test_claude_shadow_detects_active_slash_command_context() -> None:
    parser = ClaudeCodeShadowParser()

    snapshot = parser.parse_snapshot(_fixture("slash_command.txt"), baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "idle"
    assert snapshot.surface_assessment.input_mode == "modal"
    assert snapshot.surface_assessment.ui_context == "slash_command"
    assert snapshot.dialog_projection.dialog_text == "/review"


def test_claude_shadow_ignores_historical_slash_command_after_prompt_recovery() -> None:
    parser = ClaudeCodeShadowParser()

    snapshot = parser.parse_snapshot(_fixture("slash_command_recovered.txt"), baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "idle"
    assert snapshot.surface_assessment.input_mode == "freeform"
    assert snapshot.surface_assessment.ui_context == "normal_prompt"
    assert "SLASH_COMMAND_CONTEXT" not in snapshot.surface_assessment.evidence
    assert snapshot.dialog_projection.dialog_text == (
        "/model\nSet model to Default (claude-sonnet-4-6)"
    )


def test_claude_shadow_classifies_working_freeform_surface() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = "Claude Code v2.1.62\n❯ summarize repo\n✽ Razzmatazzing…\n"

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "working"
    assert snapshot.surface_assessment.input_mode == "freeform"
    assert snapshot.surface_assessment.ui_context == "normal_prompt"


def test_claude_shadow_classifies_working_modal_surface() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = "Claude Code v2.1.62\n❯ /model\n✽ Razzmatazzing…\n"

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "working"
    assert snapshot.surface_assessment.input_mode == "modal"
    assert snapshot.surface_assessment.ui_context == "slash_command"


def test_claude_shadow_reports_baseline_invalidation_on_projection() -> None:
    parser = ClaudeCodeShadowParser()

    snapshot = parser.parse_snapshot(_fixture("exact_preset_match.txt"), baseline_pos=10_000)

    anomaly_codes = {anomaly.code for anomaly in snapshot.surface_assessment.anomalies}
    assert snapshot.surface_assessment.parser_metadata.baseline_invalidated is True
    assert ANOMALY_BASELINE_INVALIDATED in anomaly_codes
    assert "Added unified parser stack." in snapshot.dialog_projection.dialog_text
