## ADDED Requirements

### Requirement: Newer-turn evidence invalidates stale terminal outcomes
For supported parsed tmux-backed sessions, the tracked state SHALL clear `last_turn.result` and `last_turn.source` back to `none` as soon as the surface shows authoritative evidence that a newer turn has begun.

Authoritative newer-turn evidence SHALL include at least:

- a visible non-placeholder draft for the current prompt while input is being accepted,
- explicit input submission for the newer turn, or
- newer active-turn evidence attributable to the latest-turn region.

Older terminal transcript text that remains visible on screen SHALL NOT keep `last_turn.result` or `last_turn.source` attached to the newer turn once such evidence exists.
The system SHALL apply the same stale-terminal invalidation rule to explicit input-authority events and to snapshot-driven newer-turn authority rather than limiting interrupted or known-failure clearing to success-settle or surface-signature-specific logic.

#### Scenario: Draft after interruption clears the previous terminal result
- **WHEN** the most recent completed turn ended with `last_turn.result=interrupted`
- **AND WHEN** the operator begins a visible non-placeholder draft for the next turn
- **THEN** the tracked state reports `last_turn.result=none`
- **AND THEN** the tracked state reports `last_turn.source=none`

#### Scenario: Second active turn clears the previous interrupted outcome
- **WHEN** one tracked turn has already ended as `interrupted`
- **AND WHEN** the tracker observes authoritative active-turn evidence for the next turn
- **THEN** the tracked state reports `turn.phase=active`
- **AND THEN** the tracked state does not continue reporting the prior interrupted turn as the current `last_turn`

#### Scenario: Draft after success clears the previous success outcome
- **WHEN** the most recent completed turn ended with `last_turn.result=success`
- **AND WHEN** the operator begins a visible non-placeholder draft for the next turn
- **THEN** the tracked state reports `last_turn.result=none`
- **AND THEN** the tracked state does not preserve the old success outcome into the new draft span

#### Scenario: Explicit input submission clears the previous terminal outcome
- **WHEN** the most recent completed turn ended with `last_turn.result=success`, `interrupted`, or `known_failure`
- **AND WHEN** the system records explicit input submission for the next turn
- **THEN** the tracked state does not continue reporting that prior terminal outcome as current `last_turn`
- **AND THEN** later newer-turn snapshots continue from the cleared `last_turn` state unless fresh terminal evidence appears

### Requirement: Current draft editing remains visible during overlapping turn activity
When the visible prompt area contains current user-authored draft input, the tracked state SHALL report that draft through `surface.editing_input=yes` even if a previous turn is still visibly active or old terminal status text remains visible in transcript history.

Selected profiles MAY still classify visible placeholder or suggestion text as `surface.editing_input=no` or `unknown`, but prompt-marker styling or stale transcript status lines SHALL NOT by themselves downgrade a real current draft to `unknown`.

#### Scenario: Follow-up draft typed while the previous turn is still active
- **WHEN** the tool is still visibly active on an earlier turn
- **AND WHEN** the operator types real draft text into the current prompt area for the next turn
- **THEN** the tracked state reports `surface.editing_input=yes`
- **AND THEN** the tracked state does not downgrade that draft solely because earlier-turn activity remains visible

#### Scenario: Stale interrupted transcript text does not suppress current draft editing
- **WHEN** an older interrupted status line remains visible in transcript history
- **AND WHEN** the current prompt area contains real draft text for the next turn
- **THEN** the tracked state reports `surface.editing_input=yes`
- **AND THEN** the stale interrupted transcript text does not force `surface.editing_input=unknown`
