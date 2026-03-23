# Footer Lines As Supporting Context

**Verified CLI Version:** `Claude Code 2.1.81` for capture-backed evidence, within the maintained `2.1.x` detector family

## Chosen Position

The current Claude signal stack treats footer lines such as these as supporting context only, not decisive state authority:

- `⏵⏵ bypass permissions on (shift+tab to cycle)`
- `⏵⏵ bypass permissions on (shift+tab to cycle) · esc to…`
- `Claude Code has switched from npm to native installer.`

## Why This Position Is Chosen

- the permission footer remains visible in both ready and active surfaces
- the installer advisory can coexist with a valid response-block success surface
- footer text helps explain the operator environment, but it is not the strongest state cue

## Why Stronger Use Was Rejected

### Reject: using the footer as the decisive active signal

Why rejected:

- the footer can look similar across ready and active spans
- ready and active distinction is better captured by the current-turn spinner line

Observed evidence:

- the footer `⏵⏵ bypass permissions on ...` is visible in both ready and active samples from the complex captures

### Reject: using the installer advisory as a success blocker

Why rejected:

- the advisory is informational UI drift, not failure or incompletion
- blocking success on it caused a real false negative

Observed failure:

- in the successful Claude complex recapture, the final `● RECOVERED` span was initially suppressed because the detector treated the installer advisory as blocking success

## Evidence

### Ready vs active ambiguity

From `capture-20260323T123329Z`:

- ready-success sample `s000056` still shows the permission footer
- active-overlap sample `s000069` also shows the permission footer

That means the footer cannot by itself separate ready from active.

### Success-with-advisory evidence

From `capture-20260323T124200Z`:

- `s000131` shows `● RECOVERED`
- `s000132` through `s000141` continue showing a valid ready-success posture
- the installer advisory remains visible below the prompt during that span

This is evidence that the advisory belongs in context notes, not in success rejection logic.

### Tests that lock this in

- `tests/unit/explore/test_claude_code_state_tracking.py::test_detector_allows_response_block_success_with_installer_notice`
- `tests/unit/explore/test_claude_code_state_tracking.py::test_replay_allows_success_to_settle_with_ready_footer_advisory`

## Current Use

Current implementation point:

- `src/houmao/shared_tui_tracking/apps/claude_code/profile.py`

Current rule shape:

- footer lines may still contribute notes such as `ready_footer_advisory`
- footer `esc to…` can be supporting activity context
- stronger signals such as the spinner line, interrupted-ready status, and response block decide current state
