# Interrupted-Ready Banner

**Verified CLI Version:** `codex-cli 0.116.0` for capture-backed evidence, within the maintained `0.116.x` detector family

## Chosen Signal

The current Codex signal stack uses the explicit interrupted banner

`■ Conversation interrupted - tell the model what to do differently. Something went wrong? Hit /feedback to report the issue.`

as the interrupted-ready signal when it appears inside the latest-turn region, the current prompt is visible, and the active status row is no longer visible.

## Why This Signal Is Chosen

- It is the explicit visible Codex interrupted-ready surface.
- It maps directly to the operator workflow after interruption.
- It remains reliable even when the banner wraps across multiple terminal lines.
- It stops the detector from inferring readiness too early from a mere prompt redraw.

## Why The Alternatives Were Rejected

### Reject: exact single-line literal matching without whitespace normalization

Why rejected:

- Codex commonly wraps the interrupted banner across multiple terminal lines
- strict single-line matching would miss real interrupted-ready surfaces

### Reject: interrupted banner anywhere in the pane

Why rejected:

- stale interrupted banners may remain visible above a newer prompt
- interruption must be scoped to the latest-turn region and suppressed when a newer visible draft is already authoritative

## Evidence

### Real capture evidence

From `capture-20260323T115828Z`:

- `s000069` shows the first interrupted-ready banner
- `s000081` shows the second interrupted-ready banner

### Tests that lock this in

- `tests/unit/demo/test_shared_tui_tracking_demo_pack.py::test_codex_detector_recognizes_wrapped_interrupted_banner`
- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_tui_exact_interruption_wins_over_ready_return`
- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_tui_visible_draft_overrides_stale_interrupted_signal_after_first_sample`

## Current Use

Current implementation points:

- `src/houmao/shared_tui_tracking/apps/codex_tui/signals/interrupted.py`
- `src/houmao/shared_tui_tracking/apps/codex_tui/profile.py`

Current rule shape:

- normalize wrapped whitespace before matching the banner
- require prompt visibility
- require absence of the active status row
- suppress stale interrupted semantics when a newer visible draft already owns the surface
