from __future__ import annotations

from pathlib import Path

import pytest

from gig_agents.agents.brain_launch_runtime.backends.claude_code_shadow import (
    ClaudeCodeShadowParseError,
    ClaudeCodeShadowParser,
)
from gig_agents.agents.brain_launch_runtime.backends.shadow_parser_core import (
    ANOMALY_BASELINE_INVALIDATED,
    ANOMALY_PRESET_OVERRIDE_USED,
    ANOMALY_UNKNOWN_VERSION_FLOOR_USED,
)

_FIXTURES_DIR = (
    Path(__file__).resolve().parents[3] / "fixtures" / "shadow_parser" / "claude"
)


def _fixture(name: str) -> str:
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_claude_shadow_preset_resolution_prefers_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = ClaudeCodeShadowParser()
    monkeypatch.setenv("AGENTSYS_CAO_CLAUDE_CODE_VERSION", "2.1.62")

    version = parser.resolve_preset_version("Claude Code v0.0.0\n> ")
    status = parser.classify_shadow_status(_fixture("exact_preset_match.txt"), baseline_pos=0)

    assert version == "2.1.62"
    anomaly_codes = {anomaly.code for anomaly in status.metadata.anomalies}
    assert ANOMALY_PRESET_OVERRIDE_USED in anomaly_codes


def test_claude_shadow_exact_preset_match() -> None:
    parser = ClaudeCodeShadowParser()

    status = parser.classify_shadow_status(_fixture("exact_preset_match.txt"), baseline_pos=0)
    extraction = parser.extract_last_answer(_fixture("exact_preset_match.txt"), baseline_pos=0)

    assert status.status == "completed"
    assert status.metadata.parser_preset_version == "2.1.62"
    assert status.metadata.output_variant == "claude_response_marker_v1"
    assert extraction.answer_text == "Added unified parser stack."


def test_claude_shadow_reports_floor_lookup_anomaly_for_unknown_version() -> None:
    parser = ClaudeCodeShadowParser()

    status = parser.classify_shadow_status(
        _fixture("floor_preset_unknown_version.txt"),
        baseline_pos=0,
    )

    assert status.status == "completed"
    assert status.metadata.parser_preset_version == "2.1.62"
    anomaly_codes = {anomaly.code for anomaly in status.metadata.anomalies}
    assert ANOMALY_UNKNOWN_VERSION_FLOOR_USED in anomaly_codes


def test_claude_shadow_raises_explicit_unsupported_output_format_for_drift() -> None:
    parser = ClaudeCodeShadowParser()

    with pytest.raises(ClaudeCodeShadowParseError) as exc_info:
        parser.classify_shadow_status(_fixture("drifted_unknown.txt"), baseline_pos=0)

    error = exc_info.value
    assert error.error_code == "unsupported_output_format"
    assert error.metadata is not None
    assert error.metadata.output_variant == "unknown"
    assert "unsupported_output_format" in str(error)


def test_claude_shadow_status_detects_waiting_user_answer() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = (
        "Claude Code v2.1.62\n"
        "Choose an option:\n"
        "❯ 1. Keep existing changes\n"
        "2. Overwrite and continue\n"
        "Use arrow keys to move and press enter.\n"
    )

    status = parser.classify_shadow_status(scrollback, baseline_pos=0)

    assert status.status == "waiting_user_answer"
    assert status.waiting_user_answer_excerpt is not None
    assert "1. Keep existing changes" in status.waiting_user_answer_excerpt


def test_claude_shadow_classifies_recognized_unclassifiable_snapshot_as_unknown() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = "Claude Code v2.1.62\n● Partial answer with no idle prompt\n"

    status = parser.classify_shadow_status(scrollback, baseline_pos=0)

    assert status.status == "unknown"
    assert status.metadata.output_format_match is True


def test_claude_shadow_extracts_answer_stopping_at_ansi_prefixed_idle_prompt() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = (
        "Claude Code v2.1.62\n"
        "❯ Reply with exactly: OK\n"
        "● OK\n"
        "\x1b[38;2;153;153;153m❯\xa0\x1b[7m\x1b[39m \x1b[0m\n"
    )

    result = parser.extract_last_answer(scrollback, baseline_pos=0)

    assert result.answer_text == "OK"


def test_claude_shadow_extraction_handles_baseline_invalidation() -> None:
    parser = ClaudeCodeShadowParser()

    result = parser.extract_last_answer(_fixture("exact_preset_match.txt"), baseline_pos=10_000)

    anomaly_codes = {anomaly.code for anomaly in result.metadata.anomalies}
    assert result.metadata.baseline_invalidated is True
    assert ANOMALY_BASELINE_INVALIDATED in anomaly_codes
    assert result.answer_text == "Added unified parser stack."


def test_claude_shadow_extraction_fails_when_baseline_resets_without_boundary() -> None:
    parser = ClaudeCodeShadowParser()
    scrollback = "Claude Code v2.1.62\n● Answer without stop boundary"

    with pytest.raises(ClaudeCodeShadowParseError):
        parser.extract_last_answer(scrollback, baseline_pos=10_000)
