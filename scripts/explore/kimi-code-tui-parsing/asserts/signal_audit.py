"""Measure: per-signal survival audit over raw frozen snapshots (v2).

Re-applies every hardcoded detector signal from
``src/houmao/shared_tui_tracking/apps/kimi_code/profile.py`` (and the
candidate 2.1.x additions) to the frozen snapshot stream and scores each
against ground truth. Text signals run on ANSI-stripped text, mirroring
``SurfaceView`` semantics (the detector never sees raw escapes); escape-level
signals (placeholder dim, OSC sequences) intentionally inspect raw bytes.

Expected sets derive from labeled GT field values, not family names:
activity signals where ``turn_phase=active``, queue hints where
``surface_pending_input=yes``, interrupt strings where
``last_turn_result=interrupted``, prompt token where the composer is usable
(``surface_accepting_input=yes`` or ``surface_editing_input=yes``), modal
signals on their label families. Feeds the KQ-1 survival table
(surviving >= 95% and zero false fires / broken < 50% / degraded).
Always ``pass: true``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    expand_range_samples,
    load_label_ranges,
    load_ndjson,
    result,
    sample_label_map,
)

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")

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


def _spinner_hit(frames: tuple[str, ...]):
    def check(text: str) -> bool:
        return any(line.strip().startswith(frames) for line in text.splitlines() if line.strip())

    return check


def _question_hit(text: str) -> bool:
    return _QUESTION_TITLE.search(text) is not None and (
        _QUESTION_OPTION.search(text) is not None or "esc cancel" in text.lower()
    )


def _interrupted_hit(text: str) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in _INTERRUPTED)


# (name, stripped?, GT predicate (expectations, family) -> expected, matcher)
_SIGNALS: list[tuple[str, bool, object, object]] = [
    (
        "activity_label_legacy",
        True,
        lambda e, f: e.get("turn_phase") == "active",
        lambda t: _ACT_LEGACY.search(t) is not None,
    ),
    (
        "activity_label_2_1",
        True,
        lambda e, f: e.get("turn_phase") == "active",
        lambda t: _ACT_2_1.search(t) is not None,
    ),
    ("braille_spinner", True, lambda e, f: e.get("turn_phase") == "active", _spinner_hit(_BRAILLE)),
    ("moon_spinner", True, lambda e, f: e.get("turn_phase") == "active", _spinner_hit(_MOON)),
    (
        "approval_headers",
        True,
        lambda e, f: f == "approval_modal",
        lambda t: any(h in t for h in _APPROVAL_HEADERS),
    ),
    (
        "approval_choice_re",
        True,
        lambda e, f: f == "approval_modal",
        lambda t: _APPROVAL_CHOICE.search(t) is not None,
    ),
    (
        "prompt_token",
        True,
        lambda e, f: (
            e.get("surface_accepting_input") == "yes" or e.get("surface_editing_input") == "yes"
        ),
        lambda t: _PROMPT_TOKEN.search(t) is not None,
    ),
    (
        "queue_hint",
        True,
        lambda e, f: e.get("surface_pending_input") == "yes",
        lambda t: _QUEUE_HINT in t,
    ),
    (
        "interrupt_strings",
        True,
        lambda e, f: e.get("last_turn_result") == "interrupted",
        _interrupted_hit,
    ),
    ("trust_modal_needle", True, lambda e, f: f == "startup_modal", lambda t: _TRUST in t.lower()),
    ("question_dialog", True, lambda e, f: f == "question_dialog", _question_hit),
    ("goal_prompt_needle", True, lambda e, f: f == "goal_prompt", lambda t: _GOAL in t),
    ("placeholder_dim_escape", False, lambda e, f: False, lambda t: _PLACEHOLDER_DIM in t),
    ("osc_133", False, lambda e, f: False, lambda t: _OSC_133 in t),
    ("osc_9_4", False, lambda e, f: False, lambda t: _OSC_9_4 in t),
]


def get_assert(output: dict, context) -> dict:  # noqa: ARG001 - promptfoo contract
    """Score every detector signal against labeled ground truth."""

    recording_root = Path(output["recording_root"])
    labels_path = Path(output["labels_path"])
    snapshots = load_ndjson(recording_root / "pane_snapshots.ndjson")
    sample_order = [row["sample_id"] for row in snapshots]
    ranges = load_label_ranges(labels_path)
    labels_by_sample = sample_label_map(ranges, sample_order)
    family_by_sample = {}
    for label_range in ranges:
        for sample_id in expand_range_samples(label_range, sample_order):
            family_by_sample[sample_id] = label_range["family"]

    named_scores: dict[str, float] = {}
    components: list[dict] = []
    for name, stripped, predicate, matcher in _SIGNALS:
        fired = missed = false_fired = expected_total = 0
        for row in snapshots:
            expectations = labels_by_sample.get(row["sample_id"])
            if expectations is None:
                continue
            family = family_by_sample[row["sample_id"]]
            text = row.get("output_text") or ""
            if stripped:
                text = _ANSI_RE.sub("", text)
            hit = bool(matcher(text))
            if predicate(expectations, family):
                expected_total += 1
                if hit:
                    fired += 1
                else:
                    missed += 1
            elif hit:
                false_fired += 1
        fire_rate = fired / expected_total if expected_total else 0.0
        named_scores[f"{name}_fired"] = float(fired)
        named_scores[f"{name}_missed"] = float(missed)
        named_scores[f"{name}_false_fired"] = float(false_fired)
        named_scores[f"{name}_fire_rate"] = round(fire_rate, 4)
        if expected_total == 0:
            verdict = "informational" if fired else "unresolved (family not captured)"
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
                    f"{name}: fired={fired} missed={missed} false_fired={false_fired} "
                    f"expected={expected_total} -> {verdict}"
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
        reason=f"signal audit v2 over {len(snapshots)} samples",
        named_scores=named_scores,
        component_results=components,
    )
