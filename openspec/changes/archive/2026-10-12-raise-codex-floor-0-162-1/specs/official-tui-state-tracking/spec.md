# Spec Delta

## MODIFIED Requirements

### Requirement: Newer-turn evidence invalidates stale terminal outcomes
For supported parsed tmux-backed sessions, the tracked state SHALL clear `last_turn.result` and `last_turn.source` back to `none` as soon as the surface shows authoritative evidence that a newer turn has begun.

Authoritative newer-turn evidence SHALL include at least:

- a visible non-placeholder draft for the current prompt while input is being accepted,
- explicit input submission for the newer turn, or
- newer active-turn evidence attributable to the latest-turn region.

Provider maintenance activity that is not operator prompt work — in particular context compaction surfaces — SHALL NOT by itself count as authoritative newer-turn evidence, SHALL NOT clear the previous prompt turn's terminal outcome, and SHALL NOT settle a success outcome over it. The previous prompt turn's `last_turn.result` and `last_turn.source` SHALL persist unchanged across such maintenance activity until a prompt-originated turn provides newer-turn evidence.

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

#### Scenario: Compaction after interruption preserves the interrupted outcome
- **WHEN** the most recent completed prompt turn ended with `last_turn.result=interrupted`
- **AND WHEN** a context compaction surface runs and completes without any prompt-originated newer-turn evidence
- **THEN** the tracked state continues to report `last_turn.result=interrupted` throughout and after the compaction
- **AND THEN** the compaction's completion does not settle `last_turn.result=success` over the interrupted record
