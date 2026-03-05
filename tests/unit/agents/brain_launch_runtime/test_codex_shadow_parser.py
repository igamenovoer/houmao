from __future__ import annotations

from pathlib import Path

import pytest

from gig_agents.agents.brain_launch_runtime.backends.codex_shadow import (
    CodexShadowParseError,
    CodexShadowParser,
)
from gig_agents.agents.brain_launch_runtime.backends.shadow_parser_core import (
    ANOMALY_BASELINE_INVALIDATED,
    ANOMALY_UNKNOWN_VERSION_FLOOR_USED,
)

_FIXTURES_DIR = (
    Path(__file__).resolve().parents[3] / "fixtures" / "shadow_parser" / "codex"
)


def _fixture(name: str) -> str:
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("fixture_name", ["label_completed.txt", "tui_completed.txt"])
def test_codex_shadow_detects_supported_output_formats(fixture_name: str) -> None:
    parser = CodexShadowParser()
    output_format, matched = parser.detect_output_format(_fixture(fixture_name))

    assert output_format.startswith("codex_shadow_v")
    assert matched is True


def test_codex_shadow_status_is_baseline_aware() -> None:
    parser = CodexShadowParser()
    prior_turn = _fixture("label_completed.txt")
    baseline = parser.capture_baseline_pos(prior_turn)

    no_new_answer = prior_turn + "\n❯ summarize again\n❯ \n"
    idle = parser.classify_shadow_status(no_new_answer, baseline_pos=baseline)
    assert idle.status == "idle"

    with_new_answer = prior_turn + "\n❯ summarize again\nassistant: fresh answer\n❯ \n"
    completed = parser.classify_shadow_status(with_new_answer, baseline_pos=baseline)
    assert completed.status == "completed"


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
        "› Give a one-sentence greeting that includes the word \"runtime\".\n"
        "• Hello! Great to work with you in this runtime.\n"
        "› Write tests for @filename\n"
    )

    status = parser.classify_shadow_status(after_turn, baseline_pos=baseline)
    extraction = parser.extract_last_answer(after_turn, baseline_pos=baseline)

    assert status.status == "completed"
    assert extraction.answer_text == "Hello! Great to work with you in this runtime."
    assert status.metadata.baseline_invalidated is True
    assert extraction.metadata.baseline_invalidated is True


def test_codex_shadow_extracts_label_style_answer() -> None:
    parser = CodexShadowParser()

    result = parser.extract_last_answer(_fixture("label_completed.txt"), baseline_pos=0)

    assert result.answer_text == "first line\nsecond line"
    assert result.metadata.output_variant == "codex_label_v1"


def test_codex_shadow_extracts_tui_style_answer_without_footer_chrome() -> None:
    parser = CodexShadowParser()

    result = parser.extract_last_answer(_fixture("tui_completed.txt"), baseline_pos=0)

    assert result.answer_text == "Updated parser stack wiring.\nAdded explicit output probes."
    assert result.metadata.output_variant == "codex_tui_bullet_v1"


@pytest.mark.parametrize(
    ("fixture_name", "expected_line"),
    [
        ("waiting_approval.txt", "Approve this command? [y/n]"),
        ("waiting_trust_prompt.txt", "Allow Codex to work in this folder? [y/n]"),
        (
            "waiting_trust_prompt_v2.txt",
            "Do you trust the contents of this directory?",
        ),
        ("waiting_menu.txt", "1. Keep existing changes"),
    ],
)
def test_codex_shadow_detects_waiting_user_answer_prompts(
    fixture_name: str,
    expected_line: str,
) -> None:
    parser = CodexShadowParser()

    status = parser.classify_shadow_status(_fixture(fixture_name), baseline_pos=0)

    assert status.status == "waiting_user_answer"
    assert status.waiting_user_answer_excerpt is not None
    assert expected_line in status.waiting_user_answer_excerpt


def test_codex_shadow_raises_explicit_unsupported_output_format_for_drift() -> None:
    parser = CodexShadowParser()
    with pytest.raises(CodexShadowParseError) as exc_info:
        parser.classify_shadow_status(_fixture("drifted_unknown.txt"), baseline_pos=0)

    error = exc_info.value
    assert error.error_code == "unsupported_output_format"
    assert error.metadata is not None
    assert error.metadata.output_variant == "unknown"
    assert "unsupported_output_format" in str(error)


def test_codex_shadow_reports_floor_preset_anomaly_for_unknown_banner_version() -> None:
    parser = CodexShadowParser()
    scrollback = "OpenAI Codex (v9.9.9)\nYou summarize\nassistant: done\n❯ \n"

    status = parser.classify_shadow_status(scrollback, baseline_pos=0)

    anomaly_codes = {anomaly.code for anomaly in status.metadata.anomalies}
    assert ANOMALY_UNKNOWN_VERSION_FLOOR_USED in anomaly_codes


def test_codex_shadow_classifies_recognized_unclassifiable_snapshot_as_unknown() -> None:
    parser = CodexShadowParser()
    scrollback = "OpenAI Codex (v0.98.0)\nYou requested a repo summary\n"

    status = parser.classify_shadow_status(scrollback, baseline_pos=0)

    assert status.status == "unknown"
    assert status.metadata.output_format_match is True


def test_codex_shadow_reports_baseline_invalidation_anomaly() -> None:
    parser = CodexShadowParser()

    status = parser.classify_shadow_status(
        _fixture("label_completed.txt"),
        baseline_pos=10_000,
    )

    anomaly_codes = {anomaly.code for anomaly in status.metadata.anomalies}
    assert status.metadata.baseline_invalidated is True
    assert ANOMALY_BASELINE_INVALIDATED in anomaly_codes
