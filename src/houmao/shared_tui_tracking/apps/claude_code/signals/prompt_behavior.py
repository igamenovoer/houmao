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


def _prompt_payload_render_state(
    snapshot: PromptAreaSnapshot,
) -> _PromptPayloadRenderState | None:
    """Return rendered style facts for the visible Claude prompt payload."""

    raw_prompt_line = snapshot.raw_prompt_line
    if raw_prompt_line is None or snapshot.payload_text is None:
        return None

    active_dim = False
    active_inverse = False
    active_other_style = False
    payload_chars: list[str] = []
    payload_plain_flags: list[bool] = []
    payload_dim_flags: list[bool] = []
    seen_prompt = False
    skipped_prompt_gap = False
    index = 0

    while index < len(raw_prompt_line):
        sgr_match = _ANSI_SGR_RE.match(raw_prompt_line, index)
        if sgr_match is not None:
            active_dim, active_inverse, active_other_style = _apply_sgr_codes(
                sgr_match.group(1),
                active_dim=active_dim,
                active_inverse=active_inverse,
                active_other_style=active_other_style,
            )
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
            payload_dim_flags.append(active_dim)
            payload_plain_flags.append(not (active_dim or active_inverse or active_other_style))

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
    )


def _apply_sgr_codes(
    codes_text: str,
    *,
    active_dim: bool,
    active_inverse: bool,
    active_other_style: bool,
) -> tuple[bool, bool, bool]:
    """Return the next style state after applying one SGR escape."""

    codes = [int(item) if item else 0 for item in codes_text.split(";")] if codes_text else [0]
    next_dim = active_dim
    next_inverse = active_inverse
    next_other_style = active_other_style
    for code in codes:
        if code == 0:
            next_dim = False
            next_inverse = False
            next_other_style = False
            continue
        if code == 2:
            next_dim = True
            continue
        if code == 22:
            next_dim = False
            continue
        if code == 7:
            next_inverse = True
            continue
        if code == 27:
            next_inverse = False
            continue
        if code in {39, 49}:
            continue
        next_other_style = True
    return next_dim, next_inverse, next_other_style
