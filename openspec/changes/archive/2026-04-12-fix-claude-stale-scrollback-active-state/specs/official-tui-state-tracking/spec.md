## MODIFIED Requirements

### Requirement: Live tracked state exposes foundational observables and unified turn semantics for consumer dashboards
For supported tmux-backed sessions whose raw pane capture is available to the shared tracker, the authoritative tracked state SHALL expose a simplified state model built from foundational observables plus one unified turn lifecycle.

At minimum, that simplified model SHALL include:

- `surface.accepting_input`: whether typed input would currently land in the prompt area
- `surface.editing_input`: whether prompt-area input is actively being edited now
- `surface.ready_posture`: whether the visible surface looks ready for immediate submit
- `turn.phase`: whether the current turn posture is `ready`, `active`, or `unknown`
- `last_turn.result`: whether the most recent completed turn ended in `success`, `interrupted`, `known_failure`, or `none`
- `last_turn.source`: whether the most recent completed turn came from `explicit_input`, `surface_inference`, or `none`

The system SHALL treat those fields as the primary consumer-facing state contract instead of requiring dashboards to interpret reducer-internal readiness, completion, parser heuristics, or anchor-bookkeeping terms.

The system SHALL NOT distinguish chat turns from slash commands in the public tracked-state contract. Submitted input is modeled as one turn lifecycle because command-looking prompt text is not a reliable semantic discriminator.

The system SHALL NOT assume that every visible TUI change has a known cause. Surface churn such as prompt repaint, cursor movement, tab handling, left/right navigation, local prompt editing, or other unexplained UI changes MAY alter the visible sample without starting, advancing, or completing a tracked turn.

Such unexplained surface churn MAY update diagnostics, parser-owned sidecar evidence, `surface`, generic stability, or recent transitions, but it SHALL NOT by itself create `turn.phase=active` or emit a new `last_turn` unless the stricter turn-evidence rules are satisfied.

Visible progress or spinner signals SHALL be treated as supporting evidence only. When present in the current live turn region, they are sufficient evidence for active-turn inference. When absent, they SHALL NOT by themselves negate the possibility of an active turn.

Historical progress or spinner signals outside the current live turn region SHALL NOT by themselves keep `turn.phase=active` or downgrade `surface.ready_posture` when the current supported surface is accepting prompt input, not editing input, visibly ready for immediate submit, and lacks current active-turn evidence.

Ambiguous menus, selection boxes, permission prompts, slash-command UI, and similar tool-specific interactive surfaces SHALL NOT create a dedicated public ask-user state or terminal outcome. Unless stronger active or terminal evidence exists, those observations SHALL be folded into `turn.phase=unknown`.

The system SHALL NOT publish a generic catch-all failure outcome. Only specifically recognized failure signatures SHALL produce `last_turn.result=known_failure`. Failure-like but unmatched surfaces SHALL degrade to `turn.phase=unknown` unless stronger evidence supports another state.

#### Scenario: Ready posture surfaces a ready turn
- **WHEN** the live TUI surface is supported, accepting prompt input, and visibly ready for immediate submit
- **THEN** the tracked state reports `surface.accepting_input=yes`
- **AND THEN** the tracked state reports `surface.ready_posture=yes`
- **AND THEN** the tracked state reports `turn.phase=ready`

#### Scenario: Response-region growth surfaces an active turn without spinner evidence
- **WHEN** the live TUI surface shows scrolling dialog or tool-response growth that satisfies the tracker's active-turn evidence rules
- **AND WHEN** no spinner or progress banner is currently visible
- **THEN** the tracked state reports `turn.phase=active`
- **AND THEN** the tracked state does not require spinner visibility to recognize that the turn is in flight

#### Scenario: Spinner evidence is sufficient for an active turn
- **WHEN** the live TUI surface shows a visible spinner, progress signal, or equivalent activity banner during a tracked turn
- **THEN** the tracked state may report `turn.phase=active` from that evidence
- **AND THEN** the same contract does not require such a signal to exist on every active turn

#### Scenario: Historical Claude spinner does not block a ready prompt
- **WHEN** captured tmux scrollback still contains older Claude thinking, spinner, or progress rows above the current live turn region
- **AND WHEN** the current Claude surface is supported, accepting prompt input, not editing input, visibly ready for immediate submit, and lacks current active-turn evidence
- **THEN** the tracked state reports `surface.accepting_input=yes`
- **AND THEN** the tracked state reports `surface.ready_posture=yes`
- **AND THEN** the tracked state reports `turn.phase=ready`

#### Scenario: Unexplained prompt-area churn does not create a turn
- **WHEN** the visible prompt area changes because of tab, cursor navigation, repaint, or other unexplained UI-local churn
- **AND WHEN** no explicit input route, strict surface-inference threshold, active-turn evidence, interrupt, or known-failure signal is present
- **THEN** the tracked state does not create a new active turn from that churn alone
- **AND THEN** any resulting state change is limited to diagnostics, parser-owned sidecar evidence, `surface`, generic stability, or recent transitions

#### Scenario: Settled return to ready records a success outcome
- **WHEN** an active tracked turn returns to a stable ready posture after observable post-submit activity that satisfies the tracker’s turn-evidence rules
- **THEN** the tracked state returns `turn.phase=ready` for the next turn
- **AND THEN** the tracked state records `last_turn.result=success` for the completed turn
- **AND THEN** the caller does not need to interpret public `candidate_complete` or `completed` states to know the turn ended successfully
