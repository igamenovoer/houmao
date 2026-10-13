# Spec Delta

## REMOVED Requirements

### Requirement: Newer-turn evidence invalidates stale terminal outcomes
**Reason**: The requirement's authoritative-evidence list includes a visible non-placeholder composer draft, and two of its scenarios clear a latched terminal outcome on any draft. Blind-labeled claude 2.1.296 recordings contradict both: the provider restores an aborted turn's prompt into the composer as a draft, and the most recent completed turn's outcome remains correct while the operator edits.
**Migration**: Replaced by `Newer-turn submission or activity invalidates stale terminal outcomes`, which keeps explicit-submission and active-turn invalidation and the maintenance-turn carve-out. Consumers see `last_turn` outcomes persist across draft editing instead of clearing; kimi and codex recorded corpora never exercised the removed path.

## ADDED Requirements

### Requirement: Newer-turn submission or activity invalidates stale terminal outcomes
For supported parsed tmux-backed sessions, the tracked state SHALL clear `last_turn.result` and `last_turn.source` back to `none` only on authoritative newer-turn evidence: explicit input submission, or newer active-turn evidence attributable to the latest-turn region. A visible composer draft SHALL NOT by itself clear a latched outcome. Provider maintenance activity such as context compaction SHALL NOT clear or settle over the previous prompt turn's outcome.

#### Scenario: Draft editing preserves the previous terminal result
- **WHEN** the most recent completed turn ended with `last_turn.result=interrupted` or `last_turn.result=success`
- **AND WHEN** the operator edits a visible non-placeholder draft without submitting it
- **THEN** the tracked state continues to report that terminal outcome
- **AND THEN** it reports `surface.editing_input=yes` while the draft is visible

#### Scenario: Restored post-abort draft preserves the interrupted outcome
- **WHEN** a turn aborts without a transcript interrupt line and the provider restores the aborted prompt into the composer as a draft
- **THEN** the tracked state reports `last_turn.result=interrupted`
- **AND THEN** the restored draft does not clear that outcome before the next submission or active-turn evidence

#### Scenario: Second active turn clears the previous interrupted outcome
- **WHEN** one tracked turn has already ended as `interrupted`
- **AND WHEN** the tracker observes authoritative active-turn evidence for the next turn
- **THEN** the tracked state reports `turn.phase=active`
- **AND THEN** the tracked state does not continue reporting the prior interrupted turn as the current `last_turn`

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

### Requirement: Claude Code tracked state models 2.1.296 signal surfaces
For supported Claude Code sessions at or above 2.1.296, the selected Claude profile SHALL follow the 2.1.296 surface contract: modal surfaces force the four surface booleans to `no` with activity suppressed; completion reads from the `✻`-anchored verb dock scoped to the latest-turn region; busy evidence uses the `esc to interrupt` footer as primary; interruption matches `⎿ Interrupted` and `⎿ User rejected` status lines; and `surface.ready_posture` asserts `no` while busy.

#### Scenario: Approval dialog blocks the four booleans
- **WHEN** a Claude approval panel (`Do you want to …` with its cancel/amend footer) holds the surface mid-turn
- **THEN** the tracked state reports `surface.accepting_input=no`, `surface.ready_posture=no`, `surface.pending_input=no`, and `turn.phase=unknown`
- **AND THEN** the panel's `❯`-option rows do not read as a usable composer

#### Scenario: Stale dock in scrollback does not complete a busy turn
- **WHEN** a previous turn's `✻ <Verb> for <dur>` dock persists in scrollback while a newer turn is active
- **THEN** the tracked state does not settle success from that stale dock
- **AND THEN** completion is recognized only from a dock inside the latest-turn region

#### Scenario: Busy turn asserts not-ready instead of unknown
- **WHEN** the `esc to interrupt` footer or the spinner line is visible
- **THEN** the tracked state reports `surface.ready_posture=no` and `turn.phase=active`
- **AND THEN** it does not degrade readiness to `unknown` while busy evidence holds

### Requirement: Claude Code 2.1.296 profile infers silent aborts and modal restores temporally
For supported Claude Code sessions at or above 2.1.296, the selected profile SHALL contribute temporal inference over a recent frame window: an active-to-idle transition with no modal, no interrupt line, and no freshly appeared region dock latches `interrupted` (the silent Esc abort); an autocomplete busy-evidence blink does not end the turn; and a modal opened from an idle interrupted surface restores the interrupted outcome on dismissal.

#### Scenario: Silent Esc abort latches interrupted across the restored draft
- **WHEN** an active Claude turn goes idle with no modal, no interrupt line, and no freshly appeared region dock, and the aborted prompt reappears as a composer draft
- **THEN** the tracked state reports `last_turn.result=interrupted` and `surface.editing_input=yes`
- **AND THEN** that outcome persists until the next submission or active-turn evidence

#### Scenario: Picker dismissal restores the pre-modal interrupted outcome
- **WHEN** the model picker opens from an idle surface whose last completed turn ended `interrupted` and then closes
- **THEN** the tracked state reports `last_turn.result=interrupted` again even though the picker command's echo re-anchored the latest-turn region
