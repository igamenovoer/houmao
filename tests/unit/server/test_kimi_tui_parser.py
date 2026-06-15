from __future__ import annotations

from pathlib import Path

import pytest

from houmao.server.tui import OfficialTuiParserAdapter


_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2] / "fixtures" / "shared_tui_tracking" / "kimi_code"
)


def _fixture(name: str) -> str:
    """Return one recorded Kimi visible-surface fixture."""

    return (_FIXTURE_ROOT / name).read_text(encoding="utf-8")


def test_kimi_parser_bypasses_shadow_parser_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_shadow_stack(*args: object, **kwargs: object) -> object:
        raise AssertionError("Kimi parser must not instantiate ShadowParserStack")

    monkeypatch.setattr("houmao.server.tui.parser.ShadowParserStack", _raise_shadow_stack)
    adapter = OfficialTuiParserAdapter()

    assert adapter.supports_tool(tool="kimi") is True
    assert (
        adapter.capture_baseline(tool="kimi", output_text=_fixture("idle_welcome_editor.txt")) == 0
    )
    result = adapter.parse(
        tool="kimi",
        output_text=_fixture("idle_welcome_editor.txt"),
        baseline_pos=0,
    )

    assert result.parse_error is None
    assert result.parsed_surface is not None
    assert result.parsed_surface.parser_family == "kimi_code_tui"
    assert result.parsed_surface.availability == "supported"
    assert result.parsed_surface.business_state == "idle"
    assert result.parsed_surface.input_mode == "freeform"


def test_kimi_parser_maps_active_surface() -> None:
    result = OfficialTuiParserAdapter().parse(
        tool="kimi",
        output_text=_fixture("active_response.txt"),
        baseline_pos=0,
    )

    assert result.parsed_surface is not None
    assert result.parsed_surface.business_state == "working"
    assert result.parsed_surface.input_mode == "closed"


def test_kimi_parser_maps_approval_dialog_and_excerpt() -> None:
    result = OfficialTuiParserAdapter().parse(
        tool="kimi",
        output_text=_fixture("command_approval.txt"),
        baseline_pos=0,
    )

    assert result.parsed_surface is not None
    assert result.parsed_surface.business_state == "awaiting_operator"
    assert result.parsed_surface.input_mode == "modal"
    assert result.parsed_surface.ui_context == "approval_dialog"
    assert result.parsed_surface.operator_blocked_excerpt is not None
    assert "Run this command?" in result.parsed_surface.operator_blocked_excerpt
    assert "$ pwd" in result.parsed_surface.operator_blocked_excerpt


def test_kimi_parser_ignores_footer_thinking_as_activity() -> None:
    result = OfficialTuiParserAdapter().parse(
        tool="kimi",
        output_text=_fixture("footer_thinking_ready_prompt.txt"),
        baseline_pos=0,
    )

    assert result.parsed_surface is not None
    assert result.parsed_surface.business_state == "idle"
    assert result.parsed_surface.input_mode == "freeform"


def test_kimi_parser_maps_startup_modal_surface() -> None:
    result = OfficialTuiParserAdapter().parse(
        tool="kimi",
        output_text="Kimi Code update available\nInstall update now? [Y/n]\n",
        baseline_pos=0,
    )

    assert result.parsed_surface is not None
    assert result.parsed_surface.business_state == "awaiting_operator"
    assert result.parsed_surface.input_mode == "modal"
    assert result.parsed_surface.ui_context == "startup_modal"
