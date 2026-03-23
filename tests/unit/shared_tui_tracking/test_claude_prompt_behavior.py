from __future__ import annotations

from houmao.shared_tui_tracking.apps.claude_code.signals.prompt_behavior import (
    ClaudePromptBehaviorVariantV2_1_X,
    FallbackClaudePromptBehaviorVariant,
    build_prompt_area_snapshot,
)
from houmao.shared_tui_tracking.surface import SurfaceView


_PROMPT_REGION_SURFACE = "\n".join(
    [
        "● Prior turn summary",
        "",
        "\x1b[39m❯ Review staged change\x1b[7ms\x1b[0m",
        "────────────────────────────────────────────────────────────────",
        "  ⏵⏵ bypass permissions on (shift+tab to cycle)",
    ]
)
_PLACEHOLDER_SURFACE = (
    '\x1b[39m❯\xa0\x1b[7mT\x1b[0;2mry\x1b[0m \x1b[2m"fix\x1b[0m '
    '\x1b[2mtypecheck\x1b[0m \x1b[2merrors"\x1b[0m\n'
)
_EMPTY_PROMPT_SURFACE = "\x1b[39m❯\xa0\x1b[7m \x1b[0m\n"
_PLAIN_DRAFT_SURFACE = "\x1b[39m❯ Review staged change\x1b[7ms\x1b[0m\n"
_COLOR_STYLED_DRAFT_SURFACE = "\x1b[39m❯\xa0\x1b[38;5;33mReview staged changes\x1b[49m\x1b[0m\n"
_UNRECOGNIZED_NON_COLOR_STYLED_SURFACE = "\x1b[39m❯\xa0\x1b[4mReview staged changes\x1b[0m\n"


def test_build_claude_prompt_area_snapshot_preserves_bounded_prompt_region() -> None:
    surface = SurfaceView.from_text(_PROMPT_REGION_SURFACE)

    snapshot = build_prompt_area_snapshot(surface)

    assert snapshot.prompt_visible is True
    assert snapshot.prompt_index == 2
    assert snapshot.payload_text == "Review staged changes"
    assert snapshot.raw_prompt_region_lines == tuple(_PROMPT_REGION_SURFACE.splitlines())
    assert snapshot.stripped_prompt_region_lines == tuple(
        SurfaceView.from_text(_PROMPT_REGION_SURFACE).stripped_lines
    )


def test_claude_prompt_behavior_2_1_classifies_dim_placeholder() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_PLACEHOLDER_SURFACE))

    classification = ClaudePromptBehaviorVariantV2_1_X().classify(snapshot)

    assert classification.kind == "placeholder"
    assert classification.prompt_text is None


def test_claude_prompt_behavior_2_1_classifies_empty_prompt() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_EMPTY_PROMPT_SURFACE))

    classification = ClaudePromptBehaviorVariantV2_1_X().classify(snapshot)

    assert classification.kind == "empty"
    assert classification.prompt_text is None


def test_claude_prompt_behavior_2_1_keeps_real_draft_with_cursor_highlight() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_PLAIN_DRAFT_SURFACE))

    classification = ClaudePromptBehaviorVariantV2_1_X().classify(snapshot)

    assert classification.kind == "draft"
    assert classification.prompt_text == "Review staged changes"


def test_claude_prompt_behavior_2_1_keeps_color_styled_draft() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_COLOR_STYLED_DRAFT_SURFACE))

    classification = ClaudePromptBehaviorVariantV2_1_X().classify(snapshot)

    assert classification.kind == "draft"
    assert classification.prompt_text == "Review staged changes"


def test_claude_prompt_behavior_2_1_degrades_non_color_styled_prompt() -> None:
    snapshot = build_prompt_area_snapshot(
        SurfaceView.from_text(_UNRECOGNIZED_NON_COLOR_STYLED_SURFACE)
    )

    classification = ClaudePromptBehaviorVariantV2_1_X().classify(snapshot)

    assert classification.kind == "unknown"
    assert "unrecognized_prompt_presentation" in classification.notes


def test_fallback_claude_prompt_behavior_stays_conservative_for_nonempty_prompt() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_PLAIN_DRAFT_SURFACE))

    classification = FallbackClaudePromptBehaviorVariant().classify(snapshot)

    assert classification.kind == "unknown"
    assert "unrecognized_prompt_presentation" in classification.notes
