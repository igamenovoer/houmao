# Supporting Context Only Lines

**Verified CLI Version:** `codex-cli 0.116.0` for capture-backed evidence, within the maintained `0.116.x` detector family

## Chosen Position

The current Codex signal stack treats lines such as these as supporting context only, not decisive current-turn authority:

- the top-of-screen bubblewrap warning
- generic tip lines
- completion-marker-only context without the rest of the success conditions

Typical examples:

- `⚠ Codex could not find system bubblewrap at /usr/bin/bwrap.`
- `Tip: New Use /fast to enable our fastest inference at 2X plan usage.`
- `─ Worked for ...`

## Why This Position Is Chosen

- these lines are visible environment or session context, not reliable current-turn state boundaries
- they can persist across multiple different turn states
- they are too coarse to separate ready, active, interrupted, and settled success on their own

## Why Stronger Use Was Rejected

### Reject: treating environment warnings as latest-turn authority

Why rejected:

- the bubblewrap warning sits at the top of the pane and is unrelated to the current turn lifecycle
- it remains visible across ready, active, interrupted, and success spans

### Reject: treating completion marker alone as full success authority

Why rejected:

- Codex success still needs current-turn ready posture and the absence of stronger conflicting active or interrupted authority
- a marker without the rest of the current-turn conditions is weaker than the response bullet plus ready posture

### Reject: treating generic tip lines as state authority

Why rejected:

- tips are informational and can remain constant while the actual turn state changes beneath them

## Evidence

### Real capture evidence

From `capture-20260323T115828Z`:

- the bubblewrap warning is present across the initial success, both interrupted spans, and the final recovered success
- generic tip lines remain present while the actual latest-turn state changes

This shows those lines cannot define current-turn state.

### Implementation evidence

Current Codex tracking rules key off:

- latest-turn prompt anchor
- active status row or temporal transcript growth
- interrupted banner
- response bullet plus ready conditions

Those stronger signals are what actually move public state.

## Current Use

Current implementation points:

- `src/houmao/shared_tui_tracking/apps/codex_tui/profile.py`
- `src/houmao/shared_tui_tracking/apps/codex_tui/signals/activity.py`
- `src/houmao/shared_tui_tracking/apps/codex_tui/signals/interrupted.py`

Current rule shape:

- supporting-only lines may remain visible in the pane
- they are not used as the decisive boundary for current active, interrupted-ready, or settled-success classification
