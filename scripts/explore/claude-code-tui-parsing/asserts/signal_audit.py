"""Measure: per-signal survival audit over raw frozen snapshots (claude v1).

Re-applies every hardcoded detector signal from
``src/houmao/shared_tui_tracking/apps/claude_code/`` (plus binary-audit
candidate needles for 2.1.296) to the frozen snapshot stream and scores each
against ground truth. Text signals run on ANSI-stripped text, mirroring
``SurfaceView`` semantics; escape-level signals (OSC sequences, ghost-style
SGR codes) intentionally inspect raw bytes.

Expected sets derive from labeled GT field values, not family names: activity
signals where ``turn_phase=active``, queue signals where
``surface_pending_input=yes``, interrupt strings where
``last_turn_result=interrupted``, prompt/composer signals where the composer
is usable, modal signals on their label families. Feeds the KQ-1 survival
table (surviving >= 95% and zero false fires / broken < 50% / degraded).
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

# Detector needles (2.1.x era, src/houmao/shared_tui_tracking/apps/claude_code/)
_PROMPT_TOKEN = re.compile(r"^\s*❯", re.MULTILINE)
_COMPOSER_RULE = re.compile(r"(?m)^\s*─{8,}\s*$")
_SPINNER_LINE = re.compile(r"^[✢✻✽✶·*]\s+.+…(?:\s+\(.+\))?$", re.MULTILINE)
_FOOTER_INTERRUPT = re.compile(r"esc to(?: interrupt|…|\.\.\.)?")
_COMPLETION_LEGACY = re.compile(r"Worked for \d+[smh]")
_INTERRUPT_LEGACY = re.compile(
    r"^\s*⎿\s+Interrupted · What should Claude do instead\?$", re.MULTILINE
)
_INTERRUPT_PREFIX = re.compile(r"^\s*⎿\s+Interrupted", re.MULTILINE)
_RESPONSE_BLOCK = re.compile(r"^● ", re.MULTILINE)
_ADVISORY_NPM = "Claude Code has switched from npm to native installer."
_ADVISORY_INSTALL = "Run `claude install`"
_QUEUED_ECHO_PROXY = re.compile(r"(?m)^\s{2,}❯\s*\S")

# Ghost-suggestion SGR codes (raw escape-level; prompt_behavior.py fg 231 / bg 237)
_GHOST_FG = "\x1b[38;5;231m"
_GHOST_BG = "\x1b[48;5;237m"

# Candidate 2.1.296 needles (binary audit 2026-10-12; not in the detector)
_COMPLETION_VERBS = re.compile(
    r"(?:Baked|Brewed|Churned|Cogitated|Cooked|Crunched|Sautéed|Worked) for \d"
)
_TRUST_TITLE = "Quick safety check"
_TRUST_CONFIRM = "Yes, I trust this folder"
_APPROVAL_QUESTION = "Do you want to proceed?"
_APPROVAL_PERSISTENT = "Yes, and don't ask again"
_FOOTER_SHORTCUTS = "? for shortcuts"
_FOOTER_BYPASS = "bypass permissions on"
_PLACEHOLDER_TIP = 'Try "'

_OSC_133 = "\x1b]133;"
_OSC_9_4 = "\x1b]9;4;"


def _live_edge(text: str, n: int = 8) -> str:
    """Return the trailing non-empty lines, mirroring live-edge scoping."""

    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-n:])


# (name, stripped?, GT predicate (expectations, family) -> expected, matcher)
_SIGNALS: list[tuple[str, bool, object, object]] = [
    (
        "prompt_token_re",
        True,
        lambda e, f: (
            e.get("surface_accepting_input") == "yes" or e.get("surface_editing_input") == "yes"
        ),
        lambda t: _PROMPT_TOKEN.search(t) is not None,
    ),
    (
        "composer_rules",
        True,
        lambda e, f: e.get("surface_accepting_input") == "yes",
        lambda t: len(_COMPOSER_RULE.findall(t)) >= 2,
    ),
    (
        "placeholder_tip",
        True,
        lambda e, f: (
            e.get("surface_editing_input") == "no" and e.get("surface_accepting_input") == "yes"
        ),
        lambda t: _PLACEHOLDER_TIP in t,
    ),
    (
        "ghost_suggestion_sgr_raw",
        False,
        lambda e, f: (
            e.get("surface_editing_input") == "no" and e.get("surface_accepting_input") == "yes"
        ),
        lambda t: _GHOST_FG in t or _GHOST_BG in t,
    ),
    (
        "spinner_line_re",
        True,
        lambda e, f: e.get("turn_phase") == "active",
        lambda t: _SPINNER_LINE.search(t) is not None,
    ),
    (
        "footer_esc_to_interrupt",
        True,
        lambda e, f: e.get("turn_phase") == "active",
        lambda t: _FOOTER_INTERRUPT.search(t) is not None,
    ),
    (
        "completion_marker_legacy_worked",
        True,
        lambda e, f: e.get("last_turn_result") == "success",
        lambda t: _COMPLETION_LEGACY.search(t) is not None,
    ),
    (
        "completion_marker_verb_set",
        True,
        lambda e, f: e.get("last_turn_result") == "success",
        lambda t: _COMPLETION_VERBS.search(t) is not None,
    ),
    (
        "interrupt_regex_legacy",
        True,
        lambda e, f: e.get("last_turn_result") == "interrupted",
        lambda t: _INTERRUPT_LEGACY.search(t) is not None,
    ),
    (
        "interrupt_prefix_live_edge",
        True,
        lambda e, f: e.get("last_turn_result") == "interrupted",
        lambda t: _INTERRUPT_PREFIX.search(_live_edge(t)) is not None,
    ),
    (
        "response_block_marker",
        True,
        lambda e, f: e.get("last_turn_result") == "success",
        lambda t: _RESPONSE_BLOCK.search(t) is not None,
    ),
    (
        "queued_echo_proxy",
        True,
        lambda e, f: e.get("surface_pending_input") == "yes",
        lambda t: _QUEUED_ECHO_PROXY.search(t) is not None,
    ),
    (
        "approval_question_2_1_296",
        True,
        lambda e, f: f == "approval_modal",
        lambda t: _APPROVAL_QUESTION in t,
    ),
    (
        "approval_persistent_option",
        True,
        lambda e, f: f == "approval_modal",
        lambda t: _APPROVAL_PERSISTENT in t,
    ),
    (
        "trust_dialog_title",
        True,
        lambda e, f: f == "startup_modal",
        lambda t: _TRUST_TITLE in t,
    ),
    (
        "trust_dialog_confirm_option",
        True,
        lambda e, f: f == "startup_modal",
        lambda t: _TRUST_CONFIRM in t,
    ),
    ("advisory_npm_installer", True, lambda e, f: False, lambda t: _ADVISORY_NPM in t),
    ("advisory_claude_install", True, lambda e, f: False, lambda t: _ADVISORY_INSTALL in t),
    ("footer_shortcuts", True, lambda e, f: False, lambda t: _FOOTER_SHORTCUTS in t),
    ("footer_bypass_mode", True, lambda e, f: False, lambda t: _FOOTER_BYPASS in t),
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
        reason=f"claude signal audit over {len(snapshots)} samples",
        named_scores=named_scores,
        component_results=components,
    )
