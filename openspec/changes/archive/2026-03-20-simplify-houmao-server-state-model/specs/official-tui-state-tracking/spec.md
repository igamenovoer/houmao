## ADDED Requirements

### Requirement: Live tracked state exposes foundational observables and unified turn semantics for consumer dashboards
For supported parsed tmux-backed sessions, the authoritative tracked state SHALL expose a simplified state model built from foundational observables plus one unified turn lifecycle.

At minimum, that simplified model SHALL include:

- `surface.accepting_input`: whether typed input would currently land in the prompt area
- `surface.editing_input`: whether prompt-area input is actively being edited now
- `surface.ready_posture`: whether the visible surface looks ready for immediate submit
- `turn.phase`: whether the current turn posture is `ready`, `active`, or `unknown`
- `last_turn.result`: whether the most recent completed turn ended in `success`, `interrupted`, `known_failure`, or `none`
- `last_turn.source`: whether the most recent completed turn came from `explicit_input`, `surface_inference`, or `none`

The system SHALL treat those fields as the primary consumer-facing state contract instead of requiring dashboards to interpret reducer-internal readiness, completion, or anchor-bookkeeping terms.

The system SHALL NOT distinguish chat turns from slash commands in the public tracked-state contract. Submitted input is modeled as one turn lifecycle because command-looking prompt text is not a reliable semantic discriminator.

The system SHALL NOT assume that every visible TUI change has a known cause. Surface churn such as prompt repaint, cursor movement, tab handling, left/right navigation, local prompt editing, or other unexplained UI changes MAY alter the visible sample without starting, advancing, or completing a tracked turn.

Such unexplained surface churn MAY update diagnostics, `surface`, generic stability, or recent transitions, but it SHALL NOT by itself create `turn.phase=active` or emit a new `last_turn` unless the stricter turn-evidence rules are satisfied.

Visible progress or spinner signals SHALL be treated as supporting evidence only. When present, they are sufficient evidence for active-turn inference. When absent, they SHALL NOT by themselves negate the possibility of an active turn.

Ambiguous menus, selection boxes, permission prompts, slash-command UI, and similar tool-specific interactive surfaces SHALL NOT create a dedicated public ask-user state or terminal outcome. Unless stronger active or terminal evidence exists, those observations SHALL be folded into `turn.phase=unknown`.

The system SHALL NOT publish a generic catch-all failure outcome. Only specifically recognized failure signatures SHALL produce `last_turn.result=known_failure`. Failure-like but unmatched surfaces SHALL degrade to `turn.phase=unknown` unless stronger evidence supports another state.

#### Scenario: Ready posture surfaces a ready turn
- **WHEN** the parsed live surface is supported, accepting prompt input, and visibly ready for immediate submit
- **THEN** the tracked state reports `surface.accepting_input=yes`
- **AND THEN** the tracked state reports `surface.ready_posture=yes`
- **AND THEN** the tracked state reports `turn.phase=ready`

#### Scenario: Response-region growth surfaces an active turn without spinner evidence
- **WHEN** the parsed live surface shows scrolling dialog or tool-response growth that satisfies the tracker's active-turn evidence rules
- **AND WHEN** no spinner or progress banner is currently visible
- **THEN** the tracked state reports `turn.phase=active`
- **AND THEN** the tracked state does not require spinner visibility to recognize that the turn is in flight

#### Scenario: Spinner evidence is sufficient for an active turn
- **WHEN** the parsed live surface shows a visible spinner, progress signal, or equivalent activity banner during a tracked turn
- **THEN** the tracked state may report `turn.phase=active` from that evidence
- **AND THEN** the same contract does not require such a signal to exist on every active turn

#### Scenario: Slash-looking input does not create a separate lifecycle kind
- **WHEN** the visible prompt text is shaped like `/<command-name>` or another slash-looking token
- **THEN** the tracked state does not create a separate public command lifecycle from that text shape alone
- **AND THEN** the tracked state continues to treat submitted input through the unified turn model

#### Scenario: Unexplained prompt-area churn does not create a turn
- **WHEN** the visible prompt area changes because of tab, cursor navigation, repaint, or other unexplained UI-local churn
- **AND WHEN** no explicit input route, strict surface-inference threshold, active-turn evidence, interrupt, or known-failure signal is present
- **THEN** the tracked state does not create a new active turn from that churn alone
- **AND THEN** any resulting state change is limited to diagnostics, `surface`, generic stability, or recent transitions

#### Scenario: Ambiguous interactive UI degrades to unknown rather than a dedicated operator state
- **WHEN** the live surface shows a menu, selection box, permission prompt, slash-command picker, or similar interactive UI whose semantics are not stable enough for a dedicated public state
- **THEN** the tracked state reports `turn.phase=unknown` unless stronger active or terminal evidence is present
- **AND THEN** the tracked state does not emit a dedicated operator-handoff terminal outcome
- **AND THEN** the caller is not required to interpret tool-specific operator-gate styling as a stable API contract

#### Scenario: Unmatched failure-like UI degrades to unknown rather than known-failure
- **WHEN** the live surface shows failure-looking text or layout churn that does not match a supported known-failure rule
- **THEN** the tracked state reports `turn.phase=unknown` unless stronger active or terminal evidence is present
- **AND THEN** the tracked state does not emit `last_turn.result=known_failure` from that observation alone

#### Scenario: Recognized failure signature records known-failure
- **WHEN** the live surface shows a specifically recognized failure signature for the supported tool
- **THEN** the tracked state records `last_turn.result=known_failure`
- **AND THEN** the caller can distinguish that explicit known failure from generic unknown posture

#### Scenario: Settled return to ready records a success outcome
- **WHEN** an active tracked turn returns to a stable ready posture after observable post-submit activity that satisfies the tracker’s turn-evidence rules
- **THEN** the tracked state returns `turn.phase=ready` for the next turn
- **AND THEN** the tracked state records `last_turn.result=success` for the completed turn
- **AND THEN** the caller does not need to interpret public `candidate_complete` or `completed` states to know the turn ended successfully

## MODIFIED Requirements

### Requirement: Timer-driven live lifecycle semantics use ReactiveX observation streams
For supported parsed tmux-backed sessions, all timed behavior in this capability SHALL be implemented over ordered observation streams using ReactiveX operators rather than hand-rolled mutable timestamp reducers, ad hoc polling arithmetic, or manual wall-clock timers.

That ReactiveX timing layer SHALL remain authoritative for:

- unknown-duration and degraded-visibility timing,
- success settle timing before the tracker records `last_turn.result=success`,
- cancellation or reset when later observations invalidate a pending timed outcome, and
- deterministic scheduler-driven tests for those timing rules.

#### Scenario: Known observation cancels pending unknown timing
- **WHEN** the live observation stream enters an unknown-or-degraded timed path
- **AND WHEN** the corresponding timeout has not yet elapsed
- **AND WHEN** a later known observation arrives before that timeout
- **THEN** the pending timed transition is canceled
- **AND THEN** the tracked state continues from the returned known observation instead of entering a degraded timed outcome

#### Scenario: Success settle timing resets on later observation change
- **WHEN** an active tracked turn has already reached a ready-looking post-activity posture
- **AND WHEN** a later observation changes the settle signature before the success settle window elapses
- **THEN** the pending success recording resets
- **AND THEN** the tracked state does not record `last_turn.result=success` until the settle signature remains stable for the full configured window

#### Scenario: Later surface growth invalidates an earlier premature success
- **WHEN** the tracker has already recorded `last_turn.result=success` from an earlier answer-bearing ready surface
- **AND WHEN** a later observation shows that the latest-turn surface kept growing or otherwise changed to a newer success-candidate signature
- **THEN** the tracker may retract that premature success and continue waiting for the final stable candidate surface
- **AND THEN** the tracked state does not treat the earlier settled signature as final if later observations prove it was not the last stable success surface

#### Scenario: Success does not require a tool-specific completion marker on every turn
- **WHEN** the latest turn returns to a fresh ready prompt with visible answer content from the latest turn
- **AND WHEN** no current interrupt, known-failure, or tool-specific success blocker remains
- **AND WHEN** that answer-bearing ready surface remains stable for the full configured settle window
- **THEN** the tracked state may record `last_turn.result=success`
- **AND THEN** the capability does not require a `Worked for <duration>`-style marker on every successful turn

#### Scenario: Timed behavior is testable without real sleeps
- **WHEN** unit tests exercise unknown-duration handling, timed recovery, or success settle timing for this capability
- **THEN** the implementation can drive those cases with deterministic scheduler control
- **AND THEN** the tests do not require real wall-clock sleeps to verify the timed behavior

### Requirement: Live tracked state distinguishes transport, process, and parse outcomes explicitly
The tracked-state contract SHALL expose low-level diagnostics separately from the simplified turn model.

At minimum, the tracked-state contract SHALL expose:

- tracked session identity,
- any `terminal_id` compatibility alias used by the public route surface,
- `transport_state`,
- `process_state`,
- `parse_status`,
- optional `probe_error` detail,
- optional `parse_error` detail,
- nullable parsed TUI surface,
- diagnostic availability/health metadata for the current sample, and
- the simplified foundational/turn/last-turn state defined by this capability.

For supported parsed tools, parse failure SHALL be represented explicitly rather than fabricated as a successful parsed surface.

#### Scenario: Parser failure is explicit in live tracked state
- **WHEN** the tmux session is live, the supported TUI process is up, and the official parser fails for that cycle
- **THEN** the live tracked state records an explicit parse-failure status
- **AND THEN** the parsed-surface field is absent or null for that cycle
- **AND THEN** the simplified turn state degrades through diagnostic availability rather than fabricating a successful turn interpretation

#### Scenario: TUI-down cycle still exposes transport and process state
- **WHEN** the tmux session remains live but the expected supported TUI process is down
- **THEN** the live tracked state still exposes the transport and process fields for that session
- **AND THEN** the parse stage is represented as skipped or unavailable for that cycle
- **AND THEN** the simplified turn state does not fabricate a ready or active posture for that cycle

### Requirement: Live tracking exposes stability metadata over the visible state signature
The system SHALL track how long the operator-visible tracked-state signature remains unchanged and SHALL expose stability metadata for that signature as diagnostic evidence in the in-memory tracked state.

At minimum, that stability metadata SHALL include whether the current signature is considered stable and how long it has remained unchanged.

That stability metadata SHALL support operator validation and internal settle logic, but it SHALL NOT be the primary consumer-facing lifecycle vocabulary for this capability.

#### Scenario: Unchanged live signature accumulates stability duration
- **WHEN** the operator-visible tracked state signature remains unchanged across successive observations
- **THEN** the system increases the tracked stability duration for that signature
- **AND THEN** the live state reflects that unchanged duration in its stability metadata

#### Scenario: Changed live signature resets stability duration
- **WHEN** any operator-visible component of the tracked state signature changes
- **THEN** the system resets the stability duration for the new signature
- **AND THEN** the live state no longer reports the prior signature's accumulated duration

## REMOVED Requirements

### Requirement: Live tracked state exposes lifecycle timing and stalled classification for consumer dashboards
**Reason**: The old public readiness/completion/authority-heavy lifecycle surface exposed reducer internals rather than the simpler foundational observables and unified turn contract the server now intends to publish.

**Migration**: Consumer dashboards and docs SHALL read `surface`, `turn`, and `last_turn` from tracked-state responses as the primary state contract. Deep timing or reducer-debug needs SHALL move to diagnostic stability/parsed-surface evidence and the existing tracking-debug workflow rather than to public `candidate_complete`, `completed`, `stalled`, or anchor-authority fields.
