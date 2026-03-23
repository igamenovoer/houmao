# Latest-Turn Prompt Anchor

**Verified CLI Version:** `Claude Code 2.1.81` for capture-backed evidence, within the maintained `2.1.x` detector family

## Chosen Signal

The current Claude signal stack uses the latest visible prompt anchor line beginning with `❯` as the primary boundary for the latest turn, and it treats an empty current input row as a valid anchor.

## Why This Signal Is Chosen

- It is stateless and visible directly in the pane snapshot.
- It provides a current-turn boundary even when the prompt is empty after success.
- It lets the detector distinguish stale transcript status above the current prompt from current-turn status near the current prompt.
- It works in the overlap case where Claude shows an interrupted line from the previous turn while the next draft is already visible below it.

## Why The Alternatives Were Rejected

### Reject: whole-pane status scanning

Why rejected:

- Claude keeps older transcript text on screen for a long time.
- Whole-pane scanning can revive a stale interrupted or failure-like line from an earlier turn.

Observed failure:

- stale interrupted text could dominate the current draft posture even after the next prompt was already visible

### Reject: a fixed trailing line window without prompt anchoring

Why rejected:

- a fixed trailing window is too loose when earlier transcript text and the current prompt share the viewport
- it does not reliably separate the previous turn from the current turn

## Evidence

### Real capture evidence

- In `capture-20260323T123329Z`, sample `s000075` shows:
  - previous-turn interrupted line:
    `⎿ Interrupted · What should Claude do instead?`
  - current draft prompt already visible below it:
    `❯ Now search this repository for files related to terminal recording ...`
- In `capture-20260323T124200Z`, samples `s000132` through `s000141` show:
  - `● RECOVERED`
  - an empty current prompt row below the response block

Those two cases require the current prompt anchor to remain usable even when the prompt row is empty and even when older status remains visible above it.

### Tests that lock this in

- `tests/unit/shared_tui_tracking/test_claude_code_session.py::test_claude_detector_matches_interrupted_signal_above_current_draft`
- `tests/unit/shared_tui_tracking/test_claude_code_session.py::test_claude_detector_ignores_stale_interrupted_scrollback_above_current_draft`

## Current Use

Current implementation points:

- `src/houmao/shared_tui_tracking/apps/claude_code/profile.py`
  - `_latest_turn_prompt_anchor_index(...)`
  - `_latest_turn_status_line(...)`

What this boundary is used for:

- scoping interrupted detection
- scoping known-failure-like status detection
- preserving response-block success evidence inside the current turn while ignoring stale earlier status
