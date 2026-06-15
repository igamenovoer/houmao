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
_GHOST_STYLE_PREFIX = "\x1b[38;5;239m\x1b[48;5;237m❯ \x1b[38;5;231m"
_FOOTER = "\x1b[39m  \x1b[38;5;211m⏵⏵ bypass permissions on\x1b[39m\n"
_SEPARATOR = "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"


def _surface(prompt_line: str) -> str:
    return f"{_SEPARATOR}{prompt_line}\n{_SEPARATOR}{_FOOTER}"


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


def test_claude_prompt_behavior_classifies_arbitrary_ghost_suggestion_from_style() -> None:
    snapshot = build_prompt_area_snapshot(
        SurfaceView.from_text(_surface(f"{_GHOST_STYLE_PREFIX}Review the latest mailbox item"))
    )

    classification = ClaudePromptBehaviorVariantV2_1_X().classify(snapshot)

    assert classification.kind == "placeholder"
    assert classification.prompt_text is None
    assert "ghost_suggestion_style" in classification.notes


def test_claude_prompt_behavior_ignores_changed_ghost_suggestion_wording() -> None:
    snapshot = build_prompt_area_snapshot(
        SurfaceView.from_text(_surface(f"{_GHOST_STYLE_PREFIX}Summarize today cautiously"))
    )

    classification = ClaudePromptBehaviorVariantV2_1_X().classify(snapshot)

    assert classification.kind == "placeholder"
    assert classification.prompt_text is None
    assert "ghost_suggestion_style" in classification.notes


def test_claude_prompt_behavior_keeps_mixed_typed_prefix_and_suggestion_as_draft() -> None:
    snapshot = build_prompt_area_snapshot(
        SurfaceView.from_text(
            _surface("\x1b[39m❯ Review\x1b[38;5;239m\x1b[48;5;237m\x1b[38;5;231m the mailbox")
        )
    )

    classification = ClaudePromptBehaviorVariantV2_1_X().classify(snapshot)

    assert classification.kind == "draft"
    assert classification.prompt_text == "Review the mailbox"


def test_claude_prompt_behavior_degrades_unrecognized_nonempty_styling() -> None:
    snapshot = build_prompt_area_snapshot(
        SurfaceView.from_text(_surface("\x1b[39m❯ \x1b[4mReview staged changes\x1b[0m"))
    )

    classification = ClaudePromptBehaviorVariantV2_1_X().classify(snapshot)

    assert classification.kind == "unknown"
    assert "unrecognized_prompt_presentation" in classification.notes


def test_fallback_claude_prompt_behavior_stays_conservative_for_ghost_suggestion() -> None:
    snapshot = build_prompt_area_snapshot(
        SurfaceView.from_text(_surface(f"{_GHOST_STYLE_PREFIX}Review the latest mailbox item"))
    )

    classification = FallbackClaudePromptBehaviorVariant().classify(snapshot)

    assert classification.kind == "unknown"
    assert "unrecognized_prompt_presentation" in classification.notes
