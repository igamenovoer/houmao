# Interrupted-Ready Status

**Verified CLI Version:** `Claude Code 2.1.81` for capture-backed evidence, within the maintained `2.1.x` detector family

## Chosen Signal

The current Claude signal stack uses the explicit status line

`⎿ Interrupted · What should Claude do instead?`

as the interrupted-ready signal when it appears inside the latest-turn region.

## Why This Signal Is Chosen

- It is the explicit visible surface Claude shows after `Esc` interruption.
- It is visible on the pane itself, not inferred indirectly from transcript history.
- It can coexist with a follow-up draft prompt below it, which matches the real operator workflow for repeated turns.
- It allows one-shot interrupted detection without waiting for a repeated second sample of the same line.

## Why The Alternatives Were Rejected

### Reject: waiting for repeated stable interrupted polls

Why rejected:

- the surface can already be semantically interrupted-ready on the first visible interrupted sample
- requiring multiple identical polls slowed the authoring workflow and caused an otherwise-correct capture to stop early

Observed failure:

- `capture-20260323T123329Z` advanced to the first interrupted-ready surface but the older wait rule expected repeated stable interrupted polls and the scenario stalled out there

### Reject: footer interrupt hints

Why rejected:

- footer `esc to…` text is not equivalent to interrupted-ready
- footer hints can remain visible on non-interrupted active surfaces

## Evidence

### Real capture evidence

From `capture-20260323T123329Z`:

- `s000075` shows:
  `⎿ Interrupted · What should Claude do instead?`

From `capture-20260323T124200Z`:

- the first interrupted-ready span begins at `s000069`
- the second interrupted-ready span begins at `s000082`

Both spans occur while the current prompt remains available for follow-up input.

### Tests that lock this in

- `tests/unit/shared_tui_tracking/test_claude_code_session.py::test_claude_detector_matches_interrupted_signal_above_current_draft`
- `tests/unit/demo/test_shared_tui_tracking_demo_pack.py::test_wait_for_interrupted_signal_accepts_first_sample`

## Current Use

Current implementation points:

- `src/houmao/shared_tui_tracking/apps/claude_code/profile.py`
  - `INTERRUPTED_RE`
  - latest-turn status scoping before matching
- `src/houmao/demo/shared_tui_tracking_demo_pack/recorded.py`
  - one-shot `wait_for_interrupted_signal(...)`

Current operational meaning:

- classify the surface as `turn_phase=ready`
- set `last_turn_result=interrupted` when the interrupted-ready status is current-turn authority
