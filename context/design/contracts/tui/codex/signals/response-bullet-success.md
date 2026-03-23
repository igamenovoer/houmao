# Response Bullet Success

**Verified CLI Version:** `codex-cli 0.116.0` for capture-backed evidence, within the maintained `0.116.x` detector family

## Chosen Signal

The current Codex signal stack treats the visible response bullet line inside the latest-turn region as the main success-content signal.

Examples observed in real captures:

- `• READY`
- `• RECOVERED`

Completion markers such as `─ Worked for ...` are useful supporting context, but the visible response bullet plus ready posture remains the more important visible completion cue for the maintained fixtures.

## Why This Signal Is Chosen

- It is the clearest visible success content in the Codex maintained fixture family.
- It works for both the initial success and final recovered success phases.
- It keeps success tied to the current visible turn instead of to older transcript content.
- It supports surface-inference success when explicit input authority is absent.

## Why The Alternatives Were Rejected

### Reject: treating visible typed draft plus earlier response bullet as a success candidate

Why rejected:

- a current real draft means a newer turn is already authoritative
- earlier success-looking transcript content must not rearm success while a newer draft is on screen

Observed failure mode:

- stale success content above a visible newer draft can wrongly reassert success unless the detector blocks it

### Reject: treating stale interrupted scrollback as stronger than a later response bullet

Why rejected:

- stale interrupted transcript should not block a later final recovered success

Observed failure mode:

- a later valid `• RECOVERED` surface can be overshadowed if stale interrupted text is allowed to dominate the whole pane

## Evidence

### Real capture evidence

From `capture-20260323T115828Z`:

- `s000050` shows `• READY`
- `s000159` shows `• RECOVERED`

### Tests that lock this in

- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_tui_snapshot_only_surface_inference_can_settle_success`
- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_detector_visible_draft_does_not_count_as_success_candidate`
- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_tui_stale_interrupted_scrollback_does_not_block_final_success`
- `tests/unit/shared_tui_tracking/test_codex_tui_session.py::test_codex_detector_ignores_stale_interrupted_scrollback_above_current_success`

## Current Use

Current implementation point:

- `src/houmao/shared_tui_tracking/apps/codex_tui/profile.py`

Current rule shape:

- success candidate requires ready posture, no stronger active or interrupted authority, and an empty or placeholder prompt
- visible draft blocks success re-arming
- settled success still passes through the shared settle window before becoming `last_turn_result=success`
