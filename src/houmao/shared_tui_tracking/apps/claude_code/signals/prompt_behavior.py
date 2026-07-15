"""Claude prompt-area snapshot extraction and behavior-variant classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

from houmao.shared_tui_tracking.surface import SurfaceView


PromptKind = Literal["placeholder", "draft", "empty", "unknown"]
_CLAUDE_PROMPT_RE = re.compile(r"^\s*❯(.*)$")
_ANSI_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")
_PROMPT_REGION_RADIUS = 2
_GHOST_SUGGESTION_FOREGROUND_CODES = frozenset({231})
_GHOST_SUGGESTION_BACKGROUND_CODES = frozenset({237})
_NEUTRAL_SIMPLE_COLOR_CODES = frozenset(
    {
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        39,
        40,
        41,
        42,
        43,
        44,
        45,
        46,
        47,
        49,
        90,
        91,
        92,
        93,
        94,
        95,
        96,
        97,
        100,
        101,
        102,
        103,
        104,
        105,
        106,
        107,
    }
)


@dataclass(frozen=True)
class PromptAreaSnapshot:
    """Prompt-local surface snapshot for one Claude frame."""

    prompt_visible: bool
    prompt_index: int | None
    raw_prompt_line: str | None
    stripped_prompt_line: str | None
    payload_text: str | None
    raw_prompt_region_lines: tuple[str, ...]
    stripped_prompt_region_lines: tuple[str, ...]


@dataclass(frozen=True)
class PromptClassification:
    """Coarse prompt behavior result for one Claude prompt-area snapshot."""

    kind: PromptKind
    prompt_text: str | None
    notes: tuple[str, ...] = ()


class ClaudePromptBehaviorVariant(Protocol):
    """Profile-private Claude prompt classifier contract."""

    @property
    def variant_name(self) -> str:
        """Return the stable debug name for this prompt behavior variant."""

    def classify(self, snapshot: PromptAreaSnapshot) -> PromptClassification:
        """Classify one prompt-area snapshot into a coarse prompt kind."""


@dataclass(frozen=True)
class _PromptPayloadRenderState:
    """Rendered payload-style summary for one Claude prompt line."""

    payload_text: str
    any_plain: bool
    any_dim: bool
    all_ghost_suggestion: bool


@dataclass(frozen=True)
class _PromptStyleState:
    """Current SGR style state while scanning one Claude prompt line."""

    active_dim: bool = False
    active_inverse: bool = False
    active_other_style: bool = False
    foreground_color: int | None = None
    background_color: int | None = None


class ClaudePromptBehaviorVariantV2_1_X:
    """Prompt behavior variant for the current `Claude Code 2.1.x` family."""

    @property
    def variant_name(self) -> str:
        """Return the version-family debug name."""

        return "2.1.x"

    def classify(self, snapshot: PromptAreaSnapshot) -> PromptClassification:
        """Classify prompt presentation for the `2.1.x` family."""

        if not snapshot.prompt_visible:
            return PromptClassification(kind="unknown", prompt_text=None)
        if snapshot.payload_text is None:
            return PromptClassification(kind="empty", prompt_text=None)
        render_state = _prompt_payload_render_state(snapshot)
        if render_state is None:
            return PromptClassification(
                kind="unknown",
                prompt_text=None,
                notes=("unrecognized_prompt_presentation",),
            )
        if render_state.any_plain:
            return PromptClassification(kind="draft", prompt_text=render_state.payload_text)
        if render_state.all_ghost_suggestion:
            return PromptClassification(
                kind="placeholder",
                prompt_text=None,
                notes=("ghost_suggestion_style",),
            )
        if render_state.any_dim:
            return PromptClassification(kind="placeholder", prompt_text=None)
        return PromptClassification(
            kind="unknown",
            prompt_text=None,
            notes=("unrecognized_prompt_presentation",),
        )


class FallbackClaudePromptBehaviorVariant:
    """Conservative prompt behavior variant for unmatched Claude versions."""

    @property
    def variant_name(self) -> str:
        """Return the fallback debug name."""

        return "fallback"

    def classify(self, snapshot: PromptAreaSnapshot) -> PromptClassification:
        """Classify prompt presentation conservatively for fallback use."""

        if not snapshot.prompt_visible:
            return PromptClassification(kind="unknown", prompt_text=None)
        if snapshot.payload_text is None:
            return PromptClassification(kind="empty", prompt_text=None)
        render_state = _prompt_payload_render_state(snapshot)
        if render_state is not None and render_state.any_dim and not render_state.any_plain:
            return PromptClassification(kind="placeholder", prompt_text=None)
        return PromptClassification(
            kind="unknown",
            prompt_text=None,
            notes=("unrecognized_prompt_presentation",),
        )


def build_prompt_area_snapshot(surface: SurfaceView) -> PromptAreaSnapshot:
    """Return a bounded prompt-area snapshot from one Claude surface."""

    prompt_index = surface.last_prompt_index()
    if prompt_index is None:
        return PromptAreaSnapshot(
            prompt_visible=False,
            prompt_index=None,
            raw_prompt_line=None,
            stripped_prompt_line=None,
            payload_text=None,
            raw_prompt_region_lines=(),
            stripped_prompt_region_lines=(),
        )

    raw_prompt_line = surface.raw_lines[prompt_index]
    stripped_prompt_line = surface.stripped_lines[prompt_index]
    match = _CLAUDE_PROMPT_RE.match(stripped_prompt_line)
    if match is None:
        payload_text = None
    else:
        payload_text = match.group(1).strip() or None
    raw_prompt_region_lines, stripped_prompt_region_lines = surface.bounded_region_lines(
        center_index=prompt_index,
        radius=_PROMPT_REGION_RADIUS,
    )
    return PromptAreaSnapshot(
        prompt_visible=True,
        prompt_index=prompt_index,
        raw_prompt_line=raw_prompt_line,
        stripped_prompt_line=stripped_prompt_line,
        payload_text=payload_text,
        raw_prompt_region_lines=raw_prompt_region_lines,
        stripped_prompt_region_lines=stripped_prompt_region_lines,
    )


def prompt_behavior_notes(
    *,
    variant: ClaudePromptBehaviorVariant,
    classification: PromptClassification,
) -> tuple[str, ...]:
    """Return stable debug notes for one prompt classification result."""

    return (
        f"prompt_behavior_variant={variant.variant_name}",
        f"prompt_kind={classification.kind}",
        *classification.notes,
    )


def payload_uses_ghost_render_style(snapshot: PromptAreaSnapshot) -> bool | None:
    """Return whether a prompt-like payload uses Claude's semantic ghost style.

    ``None`` means the payload styling could not be classified.  The helper is
    shared by composer suggestion and queued-preview detection so neither path
    depends on the rendered suggestion wording.
    """

    render_state = _prompt_payload_render_state(snapshot)
    if render_state is None:
        return None
    return render_state.all_ghost_suggestion


def _prompt_payload_render_state(
    snapshot: PromptAreaSnapshot,
) -> _PromptPayloadRenderState | None:
    """Return rendered style facts for the visible Claude prompt payload."""

    raw_prompt_line = snapshot.raw_prompt_line
    if raw_prompt_line is None or snapshot.payload_text is None:
        return None

    style_state = _PromptStyleState()
    payload_chars: list[str] = []
    payload_plain_flags: list[bool] = []
    payload_dim_flags: list[bool] = []
    payload_ghost_suggestion_flags: list[bool] = []
    seen_prompt = False
    skipped_prompt_gap = False
    index = 0

    while index < len(raw_prompt_line):
        sgr_match = _ANSI_SGR_RE.match(raw_prompt_line, index)
        if sgr_match is not None:
            style_state = _apply_sgr_codes(sgr_match.group(1), style_state=style_state)
            index = sgr_match.end()
            continue

        char = raw_prompt_line[index]
        index += 1
        if not seen_prompt:
            if char == "❯":
                seen_prompt = True
            continue
        if not skipped_prompt_gap and char.isspace():
            continue
        skipped_prompt_gap = True
        payload_chars.append(char)
        if not char.isspace():
            ghost_suggestion = _is_ghost_suggestion_style(style_state)
            payload_dim_flags.append(style_state.active_dim)
            payload_ghost_suggestion_flags.append(ghost_suggestion)
            payload_plain_flags.append(
                not (
                    style_state.active_dim
                    or style_state.active_inverse
                    or style_state.active_other_style
                    or ghost_suggestion
                )
            )

    if not payload_chars:
        return None

    payload_text = "".join(payload_chars).strip()
    if payload_text != snapshot.payload_text:
        return None
    if not payload_dim_flags and not payload_plain_flags:
        return None
    return _PromptPayloadRenderState(
        payload_text=payload_text,
        any_plain=any(payload_plain_flags),
        any_dim=any(payload_dim_flags),
        all_ghost_suggestion=all(payload_ghost_suggestion_flags),
    )


def _apply_sgr_codes(
    codes_text: str,
    *,
    style_state: _PromptStyleState,
) -> _PromptStyleState:
    """Return the next style state after applying one SGR escape."""

    codes = [int(item) if item else 0 for item in codes_text.split(";")] if codes_text else [0]
    next_dim = style_state.active_dim
    next_inverse = style_state.active_inverse
    next_other_style = style_state.active_other_style
    next_foreground_color = style_state.foreground_color
    next_background_color = style_state.background_color
    index = 0
    while index < len(codes):
        code = codes[index]
        if code == 0:
            next_dim = False
            next_inverse = False
            next_other_style = False
            next_foreground_color = None
            next_background_color = None
            index += 1
            continue
        if code == 2:
            next_dim = True
            index += 1
            continue
        if code == 22:
            next_dim = False
            index += 1
            continue
        if code == 7:
            next_inverse = True
            index += 1
            continue
        if code == 27:
            next_inverse = False
            index += 1
            continue
        if code in _NEUTRAL_SIMPLE_COLOR_CODES:
            next_foreground_color, next_background_color = _apply_simple_color_code(
                code=code,
                foreground_color=next_foreground_color,
                background_color=next_background_color,
            )
            index += 1
            continue
        if code in {38, 48}:
            next_foreground_color, next_background_color = _apply_extended_color_code(
                codes=codes,
                start_index=index,
                foreground_color=next_foreground_color,
                background_color=next_background_color,
            )
            index += _extended_color_code_width(codes=codes, start_index=index)
            continue
        next_other_style = True
        index += 1
    return _PromptStyleState(
        active_dim=next_dim,
        active_inverse=next_inverse,
        active_other_style=next_other_style,
        foreground_color=next_foreground_color,
        background_color=next_background_color,
    )


def _apply_simple_color_code(
    *,
    code: int,
    foreground_color: int | None,
    background_color: int | None,
) -> tuple[int | None, int | None]:
    """Return foreground/background state after one simple SGR color code."""

    if code == 39:
        return None, background_color
    if code == 49:
        return foreground_color, None
    if 30 <= code <= 37 or 90 <= code <= 97:
        return code, background_color
    if 40 <= code <= 47 or 100 <= code <= 107:
        return foreground_color, code
    return foreground_color, background_color


def _apply_extended_color_code(
    *,
    codes: list[int],
    start_index: int,
    foreground_color: int | None,
    background_color: int | None,
) -> tuple[int | None, int | None]:
    """Return foreground/background state after one extended SGR color code."""

    if start_index + 2 >= len(codes):
        return foreground_color, background_color

    mode = codes[start_index + 1]
    if mode != 5:
        if codes[start_index] == 38:
            return None, background_color
        return foreground_color, None

    color_code = codes[start_index + 2]
    if codes[start_index] == 38:
        return color_code, background_color
    return foreground_color, color_code


def _is_ghost_suggestion_style(style_state: _PromptStyleState) -> bool:
    """Return whether the current style matches Claude's ghost suggestion payload."""

    return (
        not style_state.active_dim
        and not style_state.active_inverse
        and not style_state.active_other_style
        and style_state.foreground_color in _GHOST_SUGGESTION_FOREGROUND_CODES
        and style_state.background_color in _GHOST_SUGGESTION_BACKGROUND_CODES
    )


def _extended_color_code_width(*, codes: list[int], start_index: int) -> int:
    """Return the width of one `38` or `48` extended-color SGR family."""

    if start_index + 1 >= len(codes):
        return 1
    mode = codes[start_index + 1]
    if mode == 5:
        return min(len(codes) - start_index, 3)
    if mode == 2:
        return min(len(codes) - start_index, 5)
    return min(len(codes) - start_index, 2)
