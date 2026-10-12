"""Codex 0.162.x prompt-behavior variant classification tests."""

from __future__ import annotations

from houmao.shared_tui_tracking.apps.codex_tui.signals.prompt_behavior import (
    CodexPromptBehaviorVariantV0_162_X,
    build_prompt_area_snapshot,
)
from houmao.shared_tui_tracking.surface import SurfaceView


_PROMPT_REGION_SURFACE = "\n".join(
    [
        "• Prior turn summary",
        "  detail line",
        "\x1b[1m›\x1b[0m Run the targeted tests",
        "",
        "  GPT-6.1-Sol medium · /tmp/demo/workdir",
    ]
)
# 0.162.1 placeholder composer: bold `›`, dim payload (captured form).
_DYNAMIC_PLACEHOLDER_SURFACE = (
    "\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m\n\n"
    "  GPT-6.1-Sol medium · /tmp/demo/workdir\n"
)
_DISABLED_INPUT_SURFACE = (
    "\x1b[2m› Input disabled for test.\x1b[0m\n\n  GPT-6.1-Sol medium · /tmp/demo/workdir\n"
)
_PLAIN_DRAFT_SURFACE = (
    "\x1b[1m›\x1b[0m Find and fix a bug in @filename\n\n  GPT-6.1-Sol medium · /tmp/demo/workdir\n"
)
_UNRECOGNIZED_STYLED_SURFACE = (
    "\x1b[1m›\x1b[0m \x1b[33mReview staged changes\x1b[0m\n\n"
    "  GPT-6.1-Sol medium · /tmp/demo/workdir\n"
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


def test_codex_prompt_behavior_0_162_classifies_dynamic_dim_placeholder() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_DYNAMIC_PLACEHOLDER_SURFACE))

    classification = CodexPromptBehaviorVariantV0_162_X().classify(snapshot)

    assert classification.kind == "placeholder"
    assert classification.prompt_text is None


def test_codex_prompt_behavior_0_162_classifies_disabled_input_placeholder() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_DISABLED_INPUT_SURFACE))

    classification = CodexPromptBehaviorVariantV0_162_X().classify(snapshot)

    assert classification.kind == "placeholder"
    assert classification.prompt_text is None


def test_codex_prompt_behavior_0_162_keeps_real_draft_even_for_placeholder_phrase() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_PLAIN_DRAFT_SURFACE))

    classification = CodexPromptBehaviorVariantV0_162_X().classify(snapshot)

    assert classification.kind == "draft"
    assert classification.prompt_text == "Find and fix a bug in @filename"


def test_codex_prompt_behavior_0_162_degrades_unrecognized_styled_prompt() -> None:
    snapshot = build_prompt_area_snapshot(SurfaceView.from_text(_UNRECOGNIZED_STYLED_SURFACE))

    classification = CodexPromptBehaviorVariantV0_162_X().classify(snapshot)

    assert classification.kind == "unknown"
    assert "unrecognized_prompt_presentation" in classification.notes
