## Why

The current `shadow_only` lifecycle treats parser-classified activity and one-way projection change as the main transition cues, but it does not model a basic signal that tmux snapshots already provide: whether the visible TUI is still changing over time or has gone quiet. That gap makes idle/completion/stall detection brittle in cases where the surface keeps updating without landing cleanly in `working`, or briefly looks ready before the output has actually settled.

## What Changes

- Refine `shadow_only` runtime lifecycle rules so tmux/TUI change activity is treated as a first-class runtime cue alongside parser activity and projection change.
- Add restartable quiescence semantics for readiness, completion, and stalled handling: fresh TUI changes keep the turn active, while a sufficiently quiet window allows runtime to treat the surface as settled.
- Distinguish transport-level change from projection-level change so spinner/progress churn and transcript changes can influence runtime decisions differently.
- Preserve the parser/runtime ownership boundary: provider parsers still classify one snapshot, while runtime interprets ordered snapshots and time-based quiescence.
- Document the new shadow lifecycle contract and diagnostic expectations for quiet-window timing, recovery, and countdown resets.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Change `shadow_only` readiness/completion/stall behavior so runtime uses restartable quiescence windows over tmux snapshot changes instead of relying only on instantaneous parser state plus continuous `unknown` timing.

## Impact

- Affected code: `src/gig_agents/agents/realm_controller/backends/cao_rest.py` and supporting shadow-mode runtime modules/tests.
- Affected docs: shadow parsing architecture/lifecycle docs and runtime reference guidance for `shadow_only`.
- Dependency/runtime impact: the existing `reactivex` dependency becomes part of the intended implementation approach for timer-driven transition logic.
