"""Measure: per-signal survival audit over raw frozen snapshots (codex v1).

Re-applies every hardcoded detector signal from
``src/houmao/shared_tui_tracking/apps/codex_tui/`` (plus candidate 0.162.x
needles) to the frozen snapshot stream and scores each against ground truth.
Text signals run on ANSI-stripped text, mirroring ``SurfaceView`` semantics;
escape-level signals (OSC sequences) intentionally inspect raw bytes.

Expected sets derive from labeled GT field values, not family names: activity
signals where ``turn_phase=active``, queue signals where
``surface_pending_input=yes``, interrupt strings where
``last_turn_result=interrupted``, prompt/placeholder signals where the composer
is usable, modal signals on their label families. Feeds the KQ-1 survival table
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

# Detector needles (0.116.x/0.144.x era, src/houmao/shared_tui_tracking/apps/codex_tui/)
_PROMPT_TOKEN = re.compile(r"^\s*›", re.MULTILINE)
_STATUS_ROW = re.compile(r"^\s*• .+ \(.+esc to interrupt.*\)\s*$", re.MULTILINE)
_WORKED_LEGACY = "─ Worked for "
_INTERRUPT_LEGACY = "Conversation interrupted - tell the model what to do differently"
_APPROVAL_HEADERS = (
    "Would you like to run the following command?",
    "Would you like to make the following edits?",
    "Would you like to grant these permissions?",
)
_APPROVAL_CONFIRM = "Press enter to confirm or esc to cancel"
_APPROVAL_OPTION_RE = re.compile(r"(?m)^\s*›\s+\d+\.\s+.+$")
_QUEUE_FOLLOWUP = "• Messages to be submitted"
_STEER_TEXT = "Model interrupted to submit steer instructions."
_OVERLAY_POPUP = "Select Model and Effort"
_PROVIDER_MARKER = "OpenAI Codex"

# Candidate 0.162.x needles (recon-observed; not in the detector)
_WORKED_0162 = "Worked for "
_INTERRUPT_0162 = "Conversation interrupted"
_PLACEHOLDER_0162 = "Ask Codex to do anything"
_TRUST_0162 = "trust this folder?"
_APPROVAL_SEND_INPUT = "Would you like to send input to the existing terminal?"
_WARNINGS_BADGE = "f2 to view"

_SPINNER_FRAMES = tuple("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
_OSC_133 = "\x1b]133;"
_OSC_9_4 = "\x1b]9;4;"


def _live_edge(text: str, n: int = 8) -> str:
    """Return the trailing non-empty lines, mirroring live-edge scoping."""

    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-n:])


def _spinner_hit(text: str) -> bool:
    return any(
        line.strip().startswith(_SPINNER_FRAMES) for line in text.splitlines() if line.strip()
    )


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
        "placeholder_0_162",
        True,
        lambda e, f: (
            e.get("surface_editing_input") == "no" and e.get("surface_accepting_input") == "yes"
        ),
        lambda t: _PLACEHOLDER_0162 in _live_edge(t),
    ),
    (
        "status_row_esc_to_interrupt",
        True,
        lambda e, f: e.get("turn_phase") == "active",
        lambda t: _STATUS_ROW.search(t) is not None,
    ),
    (
        "braille_spinner_raw",
        True,
        lambda e, f: e.get("turn_phase") == "active",
        _spinner_hit,
    ),
    (
        "worked_marker_legacy",
        True,
        lambda e, f: e.get("last_turn_result") == "success",
        lambda t: _WORKED_LEGACY in t,
    ),
    (
        "worked_marker_0_162_live_edge",
        True,
        lambda e, f: e.get("last_turn_result") == "success",
        lambda t: _WORKED_0162 in _live_edge(t),
    ),
    (
        "interrupt_string_legacy",
        True,
        lambda e, f: e.get("last_turn_result") == "interrupted",
        lambda t: _INTERRUPT_LEGACY in t,
    ),
    (
        "interrupt_0_162_live_edge",
        True,
        lambda e, f: e.get("last_turn_result") == "interrupted",
        lambda t: _INTERRUPT_0162 in _live_edge(t),
    ),
    (
        "approval_headers_detector",
        True,
        lambda e, f: f == "approval_modal",
        lambda t: any(h in t for h in _APPROVAL_HEADERS),
    ),
    (
        "approval_send_input_0_162",
        True,
        lambda e, f: f == "approval_modal",
        lambda t: _APPROVAL_SEND_INPUT in t,
    ),
    (
        "approval_confirm_hint",
        True,
        lambda e, f: f == "approval_modal",
        lambda t: _APPROVAL_CONFIRM in t,
    ),
    (
        "approval_option_re",
        True,
        lambda e, f: f == "approval_modal",
        lambda t: _APPROVAL_OPTION_RE.search(t) is not None,
    ),
    (
        "queue_followup_cell_legacy",
        True,
        lambda e, f: e.get("surface_pending_input") == "yes",
        lambda t: _QUEUE_FOLLOWUP in t,
    ),
    (
        "steer_text_legacy",
        True,
        lambda e, f: e.get("surface_pending_input") == "yes",
        lambda t: _STEER_TEXT in t,
    ),
    (
        "trust_modal_0_162",
        True,
        lambda e, f: f == "startup_modal",
        lambda t: _TRUST_0162 in t.lower(),
    ),
    (
        "model_picker_popup",
        True,
        lambda e, f: f == "model_picker",
        lambda t: _OVERLAY_POPUP in t,
    ),
    ("warnings_badge", True, lambda e, f: False, lambda t: _WARNINGS_BADGE in t),
    ("provider_marker", True, lambda e, f: False, lambda t: _PROVIDER_MARKER in t),
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
        reason=f"codex signal audit over {len(snapshots)} samples",
        named_scores=named_scores,
        component_results=components,
    )
