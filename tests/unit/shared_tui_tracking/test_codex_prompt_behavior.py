from __future__ import annotations

from houmao.shared_tui_tracking.apps.codex_tui.signals.prompt_behavior import (
    CodexPromptBehaviorVariantV0_116_X,
    FallbackCodexPromptBehaviorVariant,
    build_prompt_area_snapshot,
)
from houmao.shared_tui_tracking.surface import SurfaceView


_PROMPT_REGION_SURFACE = "\n".join(
    [
        "• Prior turn summary",
        "  detail line",
        "\x1b[1m›\x1b[0m Run the targeted tests",
        "",
        "  gpt-5.4 xhigh · 100% left · /tmp/demo/workdir",
    ]
)
_DYNAMIC_PLACEHOLDER_SURFACE = (
    "\x1b[1m›\x1b[0m \x1b[2mPlan the next three refactors\x1b[0m\n\n"
    "\x1b[2m  gpt-5.4 xhigh · 100% left · /tmp/demo/workdir\x1b[0m\n"
)
_DISABLED_INPUT_SURFACE = (
    "\x1b[2m› Input disabled for test.\x1b[0m\n\n"
    "\x1b[2m  gpt-5.4 xhigh · 100% left · /tmp/demo/workdir\x1b[0m\n"
)
_PLAIN_DRAFT_SURFACE = (
    "\x1b[1m›\x1b[0m Find and fix a bug in @filename\n\n"
    "  gpt-5.4 xhigh · 100% left · /tmp/demo/workdir\n"
)
_UNRECOGNIZED_STYLED_SURFACE = (
    "\x1b[1m›\x1b[0m \x1b[33mReview staged changes\x1b[0m\n\n"
    "  gpt-5.4 xhigh · 100% left · /tmp/demo/workdir\n"
)


def test_build_prompt_area_snapshot_preserves_bounded_prompt_region() -> None:
    surface = SurfaceView.from_text(_PROMPT_REGION_SURFACE)

    snapshot = build_prompt_area_snapshot(surface)

    assert snapshot.prompt_visible is True
    assert snapshot.prompt_index == 2
    assert snapshot.payload_text == "Run the targeted tests"
    assert snapshot.raw_prompt_region_lines == tuple(_PROMPT_REGION_SURFACE.splitlines())
    assert snapshot.stripped_prompt_region_lines == tuple(
        SurfaceView.from_text(_PROMPT_REGION_SURFACE).stripped_lines
    )


def test_codex_prompt_behavior_0_116_classifies_dynamic_dim_placeholder() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_DYNAMIC_PLACEHOLDER_SURFACE))

    classification = CodexPromptBehaviorVariantV0_116_X().classify(snapshot)

    assert classification.kind == "placeholder"
    assert classification.prompt_text is None


def test_codex_prompt_behavior_0_116_classifies_disabled_input_placeholder() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_DISABLED_INPUT_SURFACE))

    classification = CodexPromptBehaviorVariantV0_116_X().classify(snapshot)

    assert classification.kind == "placeholder"
    assert classification.prompt_text is None


def test_codex_prompt_behavior_0_116_keeps_real_draft_even_for_old_placeholder_phrase() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_PLAIN_DRAFT_SURFACE))

    classification = CodexPromptBehaviorVariantV0_116_X().classify(snapshot)

    assert classification.kind == "draft"
    assert classification.prompt_text == "Find and fix a bug in @filename"


def test_codex_prompt_behavior_0_116_degrades_unrecognized_styled_prompt() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_UNRECOGNIZED_STYLED_SURFACE))

    classification = CodexPromptBehaviorVariantV0_116_X().classify(snapshot)

    assert classification.kind == "unknown"
    assert "unrecognized_prompt_presentation" in classification.notes


def test_fallback_codex_prompt_behavior_stays_conservative_for_nonempty_prompt() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_PLAIN_DRAFT_SURFACE))

    classification = FallbackCodexPromptBehaviorVariant().classify(snapshot)

    assert classification.kind == "unknown"
    assert "unrecognized_prompt_presentation" in classification.notes
