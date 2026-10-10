"""Measure: per-signal survival audit over raw frozen snapshots.

Re-applies every hardcoded detector signal from
``src/houmao/shared_tui_tracking/apps/kimi_code/profile.py`` (and the
candidate 2.1.x additions) to the frozen escape-preserving snapshot stream,
then scores fired/missed against the labeled families where that signal is
expected and false-fired elsewhere. Feeds the KQ-1 survival table
(surviving >= 95% / broken < 50% / degraded). Always ``pass: true``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    load_label_ranges,
    load_ndjson,
    result,
    sample_family_map,
)

_ACT_LEGACY = re.compile(r"\b(?:working|thinking)\.\.\.")
_ACT_2_1 = re.compile(
    r"(?:working|thinking)(?:\.\.\.|…)|Retrying \(\d+/\d+\)|Compacting context…|Orchestrating…",
    re.IGNORECASE,
)
_BRAILLE = tuple("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
_MOON = ("🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘")
_APPROVAL_HEADERS = (
    "Run this command?",
    "Write this file?",
    "Apply these edits?",
    "Stop this task?",
    "Ready to build with this plan?",
)
_APPROVAL_CHOICE = re.compile(r"\b\d+\.\s+(?:Approve|Reject|Revise)\b")
_PROMPT_TOKEN = re.compile(r"^\s*[│┃]\s*>\s?", re.MULTILINE)
_QUEUE_HINT = "↑ to edit ·"
_INTERRUPTED = ("interrupted by user", "step interrupted")
_TRUST = "trust this folder?"
_QUESTION_TITLE = re.compile(r"^\s*question\s*$", re.IGNORECASE | re.MULTILINE)
_QUESTION_OPTION = re.compile(r"^\s*\[\d+\]", re.MULTILINE)
_GOAL = "Approve CreateGoal?"
_PLACEHOLDER_DIM = "\x1b[2m"
_OSC_133 = "\x1b]133;"
_OSC_9_4 = "\x1b]9;4;"

_ACTIVE_FAMILIES = {"active", "queue_pending", "compaction"}


def _signals() -> list[tuple[str, set[str], object]]:
    """Return (name, expected families, matcher) rows for the audit."""

    def text_matcher(needle: str):
        return lambda text: needle in text

    def regex_matcher(pattern: re.Pattern[str]):
        return lambda text: pattern.search(text) is not None

    def spinner_matcher(frames: tuple[str, ...]):
        return lambda text: any(
            line.strip().startswith(frames) for line in text.splitlines() if line.strip()
        )

    def question_matcher(text: str) -> bool:
        return _QUESTION_TITLE.search(text) is not None and (
            _QUESTION_OPTION.search(text) is not None or "esc cancel" in text.lower()
        )

    def interrupted_matcher(text: str) -> bool:
        lowered = text.lower()
        return any(needle in lowered for needle in _INTERRUPTED)

    return [
        ("activity_label_legacy", _ACTIVE_FAMILIES, regex_matcher(_ACT_LEGACY)),
        ("activity_label_2_1", _ACTIVE_FAMILIES, regex_matcher(_ACT_2_1)),
        ("braille_spinner", _ACTIVE_FAMILIES, spinner_matcher(_BRAILLE)),
        ("moon_spinner", _ACTIVE_FAMILIES, spinner_matcher(_MOON)),
        ("approval_headers", {"approval_modal"}, lambda t: any(h in t for h in _APPROVAL_HEADERS)),
        ("approval_choice_re", {"approval_modal"}, regex_matcher(_APPROVAL_CHOICE)),
        ("prompt_token", {"ready", "editing"}, regex_matcher(_PROMPT_TOKEN)),
        ("queue_hint", {"queue_pending"}, text_matcher(_QUEUE_HINT)),
        ("interrupt_strings", {"interrupted"}, interrupted_matcher),
        ("trust_modal_needle", {"startup_modal"}, lambda t: _TRUST in t.lower()),
        ("question_dialog", {"question_dialog"}, question_matcher),
        ("goal_prompt_needle", {"goal_prompt"}, text_matcher(_GOAL)),
        ("placeholder_dim_escape", {"ready", "editing"}, text_matcher(_PLACEHOLDER_DIM)),
        ("osc_133", set(), text_matcher(_OSC_133)),
        ("osc_9_4", set(), text_matcher(_OSC_9_4)),
    ]


def get_assert(output: dict, context) -> dict:  # noqa: ARG001 - promptfoo contract
    """Score every detector signal against labeled families."""

    recording_root = Path(output["recording_root"])
    labels_path = Path(output["labels_path"])
    snapshots = load_ndjson(recording_root / "pane_snapshots.ndjson")
    sample_order = [row["sample_id"] for row in snapshots]
    families = sample_family_map(load_label_ranges(labels_path), sample_order)
    present_families = set(families.values())

    named_scores: dict[str, float] = {}
    components: list[dict] = []
    for name, expected_families, matcher in _signals():
        fired = missed = false_fired = 0
        applicable = expected_families & present_families
        for row in snapshots:
            family = families.get(row["sample_id"])
            if family is None:
                continue
            hit = bool(matcher(row.get("output_text") or ""))
            if family in applicable:
                if hit:
                    fired += 1
                else:
                    missed += 1
            elif hit:
                false_fired += 1
        total_expected = fired + missed
        fire_rate = fired / total_expected if total_expected else 0.0
        named_scores[f"{name}_fired"] = float(fired)
        named_scores[f"{name}_missed"] = float(missed)
        named_scores[f"{name}_false_fired"] = float(false_fired)
        named_scores[f"{name}_fire_rate"] = round(fire_rate, 4)
        if not applicable:
            verdict = "unresolved (family not captured)"
        elif fire_rate >= 0.95 and false_fired == 0:
            verdict = "surviving"
        elif fire_rate < 0.5:
            verdict = "broken"
        else:
            verdict = "degraded"
        components.append(
            {
                "pass": True,
                "reason": (
                    f"{name}: fired={fired} missed={missed} false_fired={false_fired} -> {verdict}"
                ),
                "named_scores": {
                    "fired": float(fired),
                    "missed": float(missed),
                    "false_fired": float(false_fired),
                    "fire_rate": round(fire_rate, 4),
                },
            }
        )

    return result(
        passed=True,
        reason=f"signal audit over {len(snapshots)} samples, {len(present_families)} families",
        named_scores=named_scores,
        component_results=components,
    )
