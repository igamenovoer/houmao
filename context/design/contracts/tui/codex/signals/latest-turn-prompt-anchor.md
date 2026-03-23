# Latest-Turn Prompt Anchor

**Verified CLI Version:** `codex-cli 0.116.0` for capture-backed evidence, within the maintained `0.116.x` detector family

## Chosen Signal

The current Codex signal stack uses the latest visible prompt anchor line beginning with `›` as the primary boundary for the latest turn.

When a current prompt is visible:

- the latest `› ...` line is the current prompt anchor
- the previous visible prompt anchor above it bounds the start of the latest-turn region

When no current prompt is visible:

- Codex falls back to a bounded recent non-empty window rather than whole-pane scrollback

## Why This Signal Is Chosen

- It gives the detector a directly visible current-turn boundary.
- It is the simplest way to stop stale interrupted transcript text from dominating a later turn.
- It lets the detector judge success and interruption against the current turn instead of the entire pane.
- It keeps ready-draft and active-draft semantics tied to the visible current prompt, not to older transcript content.

## Why The Alternatives Were Rejected

### Reject: whole-pane interrupted scanning

Why rejected:

- older interrupted banners can remain visible above the current prompt
- whole-pane matching lets stale interrupted text block later success or later draft transitions

Observed failure mode:

- stale interrupted scrollback above a later success-looking turn can falsely keep the surface interrupted

### Reject: unbounded transcript tail

Why rejected:

- an unbounded tail still mixes older interrupted transcript with the latest turn
- the detector needs a region tied to the current prompt, not just "recent enough"

## Evidence

### Real capture evidence

From `capture-20260323T115828Z`:

- `s000069` shows the first interrupted-ready banner
- `s000081` shows the second interrupted-ready banner
- `s000159` later shows final `• RECOVERED`

This proves an older interrupted banner can stay visible above a later prompt and later success surface.

### Tests that lock this in

- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_detector_ignores_stale_interrupted_scrollback_above_current_success`
- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_tui_visible_draft_overrides_stale_interrupted_signal_after_first_sample`

## Current Use

Current implementation points:

- `src/houmao/shared_tui_tracking/apps/codex_tui/signals/prompt_behavior.py`
  - `build_prompt_area_snapshot(...)`
  - `latest_turn_lines(...)`

What this boundary is used for:

- scoping interrupted banner detection
- scoping activity detection
- scoping success candidate evaluation
- preserving visible draft authority over stale terminal outcomes
