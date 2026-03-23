# Response Block Success

**Verified CLI Version:** `Claude Code 2.1.81` for capture-backed evidence, within the maintained `2.1.x` detector family

## Chosen Signal

The current Claude signal stack treats a response block line beginning with `● ` inside the latest-turn region as the visible success-content signal. It is used as success-candidate evidence and then passes through the normal settle window before becoming settled success.

Examples observed in real captures:

- `● READY`
- `● RECOVERED`

## Why This Signal Is Chosen

- It is the clearest visible assistant-completion content on the current turn.
- It remains visible even after Claude redraws the empty prompt row below it.
- It survives footer drift and installer notices that are present but not semantically equal to completion.
- It lets the tracker preserve success semantics without depending on older terminal-result state from previous turns.

## Why The Alternatives Were Rejected

### Reject: footer advisory lines

Why rejected:

- footer advisory text is context, not completion
- installer and permission footer text can remain visible after a valid completion

Observed failure:

- the final `● RECOVERED` span in the successful complex capture initially failed to settle because the detector treated the native-installer footer advisory as a success blocker

### Reject: prompt visibility alone

Why rejected:

- a ready prompt by itself does not prove the prior turn completed successfully
- ready prompt surfaces also appear during draft and interrupted-ready spans

## Evidence

### Real capture evidence

From `capture-20260323T123329Z`:

- `s000056` and `s000061` show `● READY`

From `capture-20260323T124200Z`:

- `s000131` shows `● RECOVERED` while the native-installer footer notice is still present
- `s000137` through `s000141` are the final settled-success span after the success-block rule was fixed

### Bug evidence

The successful recapture showed that `● RECOVERED` was the correct success evidence even while:

- an empty prompt row was visible below it
- the installer advisory remained visible in the footer

The detector rule was adjusted so the advisory stays in notes but no longer blocks a real stable response block.

### Tests that lock this in

- `tests/unit/explore/test_claude_code_state_tracking.py::test_detector_allows_response_block_success_with_installer_notice`
- `tests/unit/explore/test_claude_code_state_tracking.py::test_replay_allows_success_to_settle_with_ready_footer_advisory`

## Current Use

Current implementation point:

- `src/houmao/shared_tui_tracking/apps/claude_code/profile.py`

Current rule shape:

- response block inside latest-turn region can create `success_candidate`
- success still requires no stronger active or interrupted authority
- success still passes through the settle window before `last_turn_result=success`
