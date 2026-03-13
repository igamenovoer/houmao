from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.realm_controller.backends.codex_shadow import (
    CodexShadowParser,
)
from houmao.agents.realm_controller.backends.shadow_parser_core import (
    ANOMALY_BASELINE_INVALIDATED,
    ANOMALY_UNKNOWN_VERSION_FLOOR_USED,
)

_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "shadow_parser" / "codex"


def _fixture(name: str) -> str:
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("fixture_name", ["label_completed.txt", "tui_completed.txt"])
def test_codex_shadow_detects_supported_output_formats(fixture_name: str) -> None:
    parser = CodexShadowParser()
    output_format, matched = parser.detect_output_format(_fixture(fixture_name))

    assert output_format.startswith("codex_shadow_v")
    assert matched is True


def test_codex_shadow_projection_preserves_visible_dialog() -> None:
    parser = CodexShadowParser()

    snapshot = parser.parse_snapshot(_fixture("label_completed.txt"), baseline_pos=0)

    assert snapshot.surface_assessment.availability == "supported"
    assert snapshot.surface_assessment.business_state == "idle"
    assert snapshot.surface_assessment.input_mode == "freeform"
    assert snapshot.surface_assessment.ui_context == "normal_prompt"
    assert (
        snapshot.dialog_projection.dialog_text
        == "You summarize this module\nfirst line\nsecond line"
    )


def test_codex_shadow_projection_strips_footer_and_header_chrome() -> None:
    parser = CodexShadowParser()

    snapshot = parser.parse_snapshot(_fixture("tui_completed.txt"), baseline_pos=0)

    assert snapshot.surface_assessment.parser_metadata.output_variant == "codex_tui_bullet_v1"
    assert "OpenAI Codex" not in snapshot.dialog_projection.dialog_text
    assert "? for shortcuts" not in snapshot.dialog_projection.dialog_text
    assert snapshot.dialog_projection.dialog_text == (
        "summarize recent changes\nUpdated parser stack wiring.\nAdded explicit output probes."
    )


def test_codex_shadow_handles_redraw_shrink_after_baseline() -> None:
    parser = CodexShadowParser()

    before_turn = (
        "OpenAI Codex (v0.98.0)\n"
        "› Write tests for @filename\n"
        "• Previous answer line.\n"
        "Tip: New 2x rate limits until April 2nd.\n"
        "additional padding to force a longer pre-turn frame\n"
    )
    baseline = parser.capture_baseline_pos(before_turn)

    after_turn = (
        "OpenAI Codex (v0.98.0)\n"
        '› Give a one-sentence greeting that includes the word "runtime".\n'
        "• Hello! Great to work with you in this runtime.\n"
        "› Write tests for @filename\n"
    )

    snapshot = parser.parse_snapshot(after_turn, baseline_pos=baseline)

    assert snapshot.surface_assessment.parser_metadata.baseline_invalidated is True
    assert snapshot.dialog_projection.dialog_text == (
        'Give a one-sentence greeting that includes the word "runtime".\n'
        "Hello! Great to work with you in this runtime.\n"
        "Write tests for @filename"
    )


@pytest.mark.parametrize(
    ("fixture_name", "expected_context", "expected_line"),
    [
        ("waiting_approval.txt", "approval_prompt", "Approve this command? [y/n]"),
        (
            "waiting_trust_prompt.txt",
            "approval_prompt",
            "Allow Codex to work in this folder? [y/n]",
        ),
        (
            "waiting_trust_prompt_v2.txt",
            "approval_prompt",
            "Do you trust the contents of this directory?",
        ),
        ("waiting_menu.txt", "selection_menu", "1. Keep existing changes"),
    ],
)
def test_codex_shadow_detects_waiting_user_answer_prompts(
    fixture_name: str,
    expected_context: str,
    expected_line: str,
) -> None:
    parser = CodexShadowParser()

    snapshot = parser.parse_snapshot(_fixture(fixture_name), baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "awaiting_operator"
    assert snapshot.surface_assessment.input_mode == "modal"
    assert snapshot.surface_assessment.ui_context == expected_context
    assert snapshot.surface_assessment.operator_blocked_excerpt is not None
    assert expected_line in snapshot.surface_assessment.operator_blocked_excerpt
    assert expected_line in snapshot.dialog_projection.dialog_text


def test_codex_shadow_reports_unsupported_surface_for_drift() -> None:
    parser = CodexShadowParser()

    snapshot = parser.parse_snapshot(_fixture("drifted_unknown.txt"), baseline_pos=0)

    assert snapshot.surface_assessment.availability == "unsupported"
    assert snapshot.surface_assessment.parser_metadata.output_variant == "unknown"
    assert snapshot.surface_assessment.parser_metadata.output_format_match is False
    assert "payload_start" in snapshot.dialog_projection.dialog_text


def test_codex_shadow_reports_floor_preset_anomaly_for_unknown_banner_version() -> None:
    parser = CodexShadowParser()
    scrollback = "OpenAI Codex (v9.9.9)\nYou summarize\nassistant: done\n❯ \n"

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    anomaly_codes = {anomaly.code for anomaly in snapshot.surface_assessment.anomalies}
    assert ANOMALY_UNKNOWN_VERSION_FLOOR_USED in anomaly_codes


def test_codex_shadow_classifies_recognized_unclassifiable_snapshot_as_unknown() -> None:
    parser = CodexShadowParser()
    scrollback = "OpenAI Codex (v0.98.0)\nYou requested a repo summary\n"

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.availability == "supported"
    assert snapshot.surface_assessment.business_state == "unknown"
    assert snapshot.surface_assessment.input_mode == "unknown"
    assert snapshot.surface_assessment.parser_metadata.output_format_match is True
    assert snapshot.dialog_projection.dialog_text == "You requested a repo summary"


def test_codex_shadow_detects_active_slash_command_context() -> None:
    parser = CodexShadowParser()

    snapshot = parser.parse_snapshot(_fixture("slash_command.txt"), baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "idle"
    assert snapshot.surface_assessment.input_mode == "modal"
    assert snapshot.surface_assessment.ui_context == "slash_command"
    assert snapshot.dialog_projection.dialog_text == "/review"


def test_codex_shadow_ignores_historical_slash_command_after_prompt_recovery() -> None:
    parser = CodexShadowParser()

    snapshot = parser.parse_snapshot(_fixture("slash_command_recovered.txt"), baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "idle"
    assert snapshot.surface_assessment.input_mode == "freeform"
    assert snapshot.surface_assessment.ui_context == "normal_prompt"
    assert "CODEX_SLASH_COMMAND_CONTEXT" not in snapshot.surface_assessment.evidence
    assert snapshot.dialog_projection.dialog_text == (
        "/model\nSwitched model to gpt-5.3-codex high"
    )


def test_codex_shadow_reports_baseline_invalidation_anomaly() -> None:
    parser = CodexShadowParser()

    snapshot = parser.parse_snapshot(
        _fixture("label_completed.txt"),
        baseline_pos=10_000,
    )

    anomaly_codes = {anomaly.code for anomaly in snapshot.surface_assessment.anomalies}
    assert snapshot.surface_assessment.parser_metadata.baseline_invalidated is True
    assert ANOMALY_BASELINE_INVALIDATED in anomaly_codes


def test_codex_shadow_detects_login_block_as_closed_operator_surface() -> None:
    parser = CodexShadowParser()
    scrollback = "OpenAI Codex (v0.98.0)\nSign in to continue in browser\n"

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "awaiting_operator"
    assert snapshot.surface_assessment.input_mode == "closed"
    assert snapshot.surface_assessment.ui_context == "approval_prompt"
    assert snapshot.surface_assessment.operator_blocked_excerpt is not None


def test_codex_shadow_classifies_working_freeform_surface() -> None:
    parser = CodexShadowParser()
    scrollback = (
        "OpenAI Codex (v0.98.0)\n› summarize repo\n• Thinking about files (2s • esc to interrupt)\n"
    )

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "working"
    assert snapshot.surface_assessment.input_mode == "freeform"
    assert snapshot.surface_assessment.ui_context == "normal_prompt"


def test_codex_shadow_classifies_working_modal_surface() -> None:
    parser = CodexShadowParser()
    scrollback = (
        "OpenAI Codex (v0.98.0)\n› /model\n• Thinking about files (2s • esc to interrupt)\n"
    )

    snapshot = parser.parse_snapshot(scrollback, baseline_pos=0)

    assert snapshot.surface_assessment.business_state == "working"
    assert snapshot.surface_assessment.input_mode == "modal"
    assert snapshot.surface_assessment.ui_context == "slash_command"
