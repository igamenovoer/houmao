"""Codex prompt-area snapshot extraction and behavior-variant classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

from houmao.shared_tui_tracking.surface import SurfaceView


PromptKind = Literal["placeholder", "draft", "empty", "unknown"]
_CODEX_PROMPT_RE = re.compile(r"^\s*›(.*)$")
_ANSI_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")
_PROMPT_REGION_RADIUS = 2
_LATEST_TURN_WINDOW = 24


@dataclass(frozen=True)
class PromptAreaSnapshot:
    """Prompt-local surface snapshot for one Codex frame."""

    prompt_visible: bool
    prompt_index: int | None
    raw_prompt_line: str | None
    stripped_prompt_line: str | None
    payload_text: str | None
    raw_prompt_region_lines: tuple[str, ...]
    stripped_prompt_region_lines: tuple[str, ...]


@dataclass(frozen=True)
class PromptClassification:
    """Coarse prompt behavior result for one prompt-area snapshot."""

    kind: PromptKind
    prompt_text: str | None
    notes: tuple[str, ...] = ()


class CodexPromptBehaviorVariant(Protocol):
    """Profile-private Codex prompt classifier contract."""

    @property
    def variant_name(self) -> str:
        """Return the stable debug name for this prompt behavior variant."""

    def classify(self, snapshot: PromptAreaSnapshot) -> PromptClassification:
        """Classify one prompt-area snapshot into a coarse prompt kind."""


@dataclass(frozen=True)
class _PromptPayloadRenderState:
    """Rendered payload-style summary for one prompt line."""

    payload_text: str
    all_dim: bool
    all_plain: bool


class CodexPromptBehaviorVariantV0_116_X:
    """Prompt behavior variant for the current `codex-cli 0.116.x` family."""

    @property
    def variant_name(self) -> str:
        """Return the version-family debug name."""

        return "0.116.x"

    def classify(self, snapshot: PromptAreaSnapshot) -> PromptClassification:
        """Classify prompt presentation for the `0.116.x` family."""

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
        if render_state.all_dim:
            return PromptClassification(kind="placeholder", prompt_text=None)
        if render_state.all_plain:
            return PromptClassification(kind="draft", prompt_text=render_state.payload_text)
        return PromptClassification(
            kind="unknown",
            prompt_text=None,
            notes=("unrecognized_prompt_presentation",),
        )


class FallbackCodexPromptBehaviorVariant:
    """Conservative prompt behavior variant for unmatched Codex versions."""

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
        if render_state is not None and render_state.all_dim:
            return PromptClassification(kind="placeholder", prompt_text=None)
        return PromptClassification(
            kind="unknown",
            prompt_text=None,
            notes=("unrecognized_prompt_presentation",),
        )


def build_prompt_area_snapshot(surface: SurfaceView) -> PromptAreaSnapshot:
    """Return a bounded prompt-area snapshot from one Codex surface."""

    prompt_index: int | None = None
    raw_prompt_line: str | None = None
    stripped_prompt_line: str | None = None
    payload_text: str | None = None
    for index, (raw_line, line) in enumerate(
        zip(surface.raw_lines, surface.stripped_lines, strict=True)
    ):
        match = _CODEX_PROMPT_RE.match(line)
        if match is None:
            continue
        prompt_index = index
        raw_prompt_line = raw_line
        stripped_prompt_line = line
        payload_text = match.group(1).strip() or None

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

    start_index = max(prompt_index - _PROMPT_REGION_RADIUS, 0)
    end_index = min(prompt_index + _PROMPT_REGION_RADIUS + 1, len(surface.raw_lines))
    return PromptAreaSnapshot(
        prompt_visible=True,
        prompt_index=prompt_index,
        raw_prompt_line=raw_prompt_line,
        stripped_prompt_line=stripped_prompt_line,
        payload_text=payload_text,
        raw_prompt_region_lines=surface.raw_lines[start_index:end_index],
        stripped_prompt_region_lines=surface.stripped_lines[start_index:end_index],
    )


def latest_turn_lines(
    *,
    surface: SurfaceView,
    prompt_index: int | None,
) -> tuple[str, ...]:
    """Return the bounded stripped latest-turn text region for one surface."""

    non_empty_lines = [line.strip() for line in surface.stripped_lines if line.strip()]
    if prompt_index is None:
        return tuple(non_empty_lines[-_LATEST_TURN_WINDOW:])
    start_index = max(prompt_index - _LATEST_TURN_WINDOW, 0)
    for index in range(prompt_index - 1, -1, -1):
        if _CODEX_PROMPT_RE.match(surface.stripped_lines[index]) is None:
            continue
        start_index = index
        break
    return tuple(
        line.strip() for line in surface.stripped_lines[start_index:prompt_index] if line.strip()
    )


def latest_turn_live_edge_lines(*, surface: SurfaceView) -> tuple[str, ...]:
    """Return the bounded live-edge subset for current-turn activity checks."""

    non_empty_lines = [line.strip() for line in surface.stripped_lines if line.strip()]
    return tuple(non_empty_lines[-_LATEST_TURN_WINDOW:])


def prompt_behavior_notes(
    *,
    variant: CodexPromptBehaviorVariant,
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
    """Return rendered style facts for the visible prompt payload."""

    raw_prompt_line = snapshot.raw_prompt_line
    if raw_prompt_line is None or snapshot.payload_text is None:
        return None

    active_dim = False
    active_nondefault_style = False
    payload_chars: list[str] = []
    payload_dim_flags: list[bool] = []
    payload_plain_flags: list[bool] = []
    seen_prompt = False
    skipped_prompt_gap = False
    index = 0

    while index < len(raw_prompt_line):
        sgr_match = _ANSI_SGR_RE.match(raw_prompt_line, index)
        if sgr_match is not None:
            active_dim, active_nondefault_style = _apply_sgr_codes(
                sgr_match.group(1),
                active_dim=active_dim,
                active_nondefault_style=active_nondefault_style,
            )
            index = sgr_match.end()
            continue

        char = raw_prompt_line[index]
        index += 1
        if not seen_prompt:
            if char == "›":
                seen_prompt = True
            continue
        if not skipped_prompt_gap and char.isspace():
            continue
        skipped_prompt_gap = True
        payload_chars.append(char)
        payload_dim_flags.append(active_dim)
        payload_plain_flags.append(not active_nondefault_style)

    if not payload_chars:
        return None

    payload_text = "".join(payload_chars).strip()
    if payload_text != snapshot.payload_text:
        return None
    return _PromptPayloadRenderState(
        payload_text=payload_text,
        all_dim=all(payload_dim_flags),
        all_plain=all(payload_plain_flags),
    )


def _apply_sgr_codes(
    codes_text: str,
    *,
    active_dim: bool,
    active_nondefault_style: bool,
) -> tuple[bool, bool]:
    """Return the next style state after applying one SGR escape."""

    codes = [int(item) if item else 0 for item in codes_text.split(";")] if codes_text else [0]
    next_dim = active_dim
    next_nondefault_style = active_nondefault_style
    for code in codes:
        if code == 0:
            next_dim = False
            next_nondefault_style = False
            continue
        if code == 2:
            next_dim = True
            next_nondefault_style = True
            continue
        if code == 22:
            next_dim = False
            next_nondefault_style = False
            continue
        if code in {39, 49}:
            continue
        next_nondefault_style = True
    return next_dim, next_nondefault_style
