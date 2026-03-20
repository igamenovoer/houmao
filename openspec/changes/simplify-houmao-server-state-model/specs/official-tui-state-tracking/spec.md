## ADDED Requirements

### Requirement: Live tracked state exposes foundational observables and simplified work-cycle semantics for consumer dashboards
For supported parsed tmux-backed sessions, the authoritative tracked state SHALL expose a simplified state model built from foundational observables plus current work-cycle semantics.

At minimum, that simplified model SHALL include:

- `surface.processing`: whether the TUI is actively processing work now
- `surface.accepting_input`: whether typed input would currently land in the prompt area
- `surface.editing_input`: whether prompt-area input is actively being edited now
- `surface.input_kind`: whether the visible input posture is `chat`, `command`, `none`, or `unknown`
- `work.kind`: whether the current ready/active work is `chat`, `command`, `none`, or `unknown`
- `work.phase`: whether the current work posture is `ready`, `active`, `awaiting_user`, or `unknown`
- `last_outcome.kind`: whether the most recent completed cycle was `chat`, `command`, or `none`
- `last_outcome.result`: whether the most recent completed cycle ended in `success`, `interrupted`, `failed`, `ask_user`, or `none`

The system SHALL treat those fields as the primary consumer-facing state contract instead of requiring dashboards to interpret reducer-internal readiness, completion, or anchor-bookkeeping terms.

The tracker MAY continue using richer internal reduction and timing machinery, but the public tracked-state contract SHALL present the simplified model above as the first-class state surface.

For this capability, `surface.input_kind=command` and `work.kind=command` SHALL apply only when the current unsubmitted prompt text is exactly `/<command-name>` from the first character of the prompt, with no leading spaces, no additional arguments or text, and optional trailing spaces only.

The system SHALL NOT assume that every visible TUI change has a known cause. Surface churn such as prompt repaint, cursor movement, tab handling, left/right navigation, local prompt editing, or other unexplained UI changes MAY alter the visible sample without starting, advancing, or completing a tracked work cycle.

Such unexplained surface churn MAY update diagnostics, `surface`, generic stability, or recent transitions, but it SHALL NOT by itself create `work.phase=active`, change `work.kind`, or emit a new `last_outcome` unless the stricter cycle-evidence rules are satisfied.

#### Scenario: Idle freeform prompt surfaces a ready chat posture
- **WHEN** the parsed live surface is supported, idle, and accepting freeform prompt input
- **THEN** the tracked state reports `surface.processing=no`
- **AND THEN** the tracked state reports `surface.accepting_input=yes`
- **AND THEN** the tracked state reports `surface.input_kind=chat`
- **AND THEN** the tracked state reports `work.kind=chat` and `work.phase=ready`

#### Scenario: Active prompt processing surfaces an active chat posture
- **WHEN** the parsed live surface shows a submitted chat turn still being processed
- **THEN** the tracked state reports `work.kind=chat` and `work.phase=active`
- **AND THEN** `surface.processing=yes`
- **AND THEN** the tracked state does not require the caller to interpret `in_progress` or other reducer-internal completion labels to understand that the TUI is busy

#### Scenario: Slash-command entry surfaces a ready command posture
- **WHEN** the parsed live surface shows an unsubmitted prompt whose text is exactly `/<command-name>` with optional trailing spaces only
- **THEN** the tracked state reports `surface.accepting_input=yes`
- **AND THEN** the tracked state reports `surface.input_kind=command`
- **AND THEN** the tracked state reports `work.kind=command` and `work.phase=ready`

#### Scenario: Leading spaces or extra arguments do not count as a slash command
- **WHEN** the parsed live surface shows an unsubmitted prompt whose text has leading spaces before `/`, or contains additional non-space text after `/<command-name>`
- **THEN** the tracked state does not report `surface.input_kind=command`
- **AND THEN** the tracked state does not report `work.kind=command` from that prompt alone

#### Scenario: Unexplained prompt-area churn does not create a work cycle
- **WHEN** the visible prompt area changes because of tab, cursor navigation, repaint, or other unexplained UI-local churn
- **AND WHEN** no explicit input route, strict surface-inference threshold, active-work evidence, operator gate, interrupt, or terminal failure signal is present
- **THEN** the tracked state does not create a new active work cycle from that churn alone
- **AND THEN** any resulting state change is limited to diagnostics, `surface`, generic stability, or recent transitions

#### Scenario: Operator gate surfaces awaiting-user work plus terminal ask-user outcome
- **WHEN** an active tracked cycle reaches a parser-recognized operator gate that requires user action
- **THEN** the tracked state reports `work.phase=awaiting_user`
- **AND THEN** the most recent terminal outcome recorded for that cycle becomes `last_outcome.result=ask_user`
- **AND THEN** the caller does not need to interpret separate blocked-versus-authority fields to know user attention is required

#### Scenario: Settled return to ready records a success outcome
- **WHEN** an active tracked cycle returns to a stable ready posture after observable post-submit activity that satisfies the tracker’s cycle-evidence rules
- **THEN** the tracked state returns `work.phase=ready` for the next cycle
- **AND THEN** the tracked state records `last_outcome.result=success` for the completed cycle
- **AND THEN** the caller does not need to interpret public `candidate_complete` or `completed` states to know the cycle ended successfully

## MODIFIED Requirements

### Requirement: Timer-driven live lifecycle semantics use ReactiveX observation streams
For supported parsed tmux-backed sessions, all timed behavior in this capability SHALL be implemented over ordered observation streams using ReactiveX operators rather than hand-rolled mutable timestamp reducers, ad hoc polling arithmetic, or manual wall-clock timers.

That ReactiveX timing layer SHALL remain authoritative for:

- unknown-duration and degraded-visibility timing,
- success settle timing before the tracker records `last_outcome.result=success`,
- cancellation or reset when later observations invalidate a pending timed outcome, and
- deterministic scheduler-driven tests for those timing rules.

#### Scenario: Known observation cancels pending unknown timing
- **WHEN** the live observation stream enters an unknown-or-degraded timed path
- **AND WHEN** the corresponding timeout has not yet elapsed
- **AND WHEN** a later known observation arrives before that timeout
- **THEN** the pending timed transition is canceled
- **AND THEN** the tracked state continues from the returned known observation instead of entering a degraded timed outcome

#### Scenario: Success settle timing resets on later observation change
- **WHEN** an active tracked cycle has already reached a ready-looking post-activity posture
- **AND WHEN** a later observation changes the settle signature before the success settle window elapses
- **THEN** the pending success recording resets
- **AND THEN** the tracked state does not record `last_outcome.result=success` until the settle signature remains stable for the full configured window

#### Scenario: Timed behavior is testable without real sleeps
- **WHEN** unit tests exercise unknown-duration handling, timed recovery, or success settle timing for this capability
- **THEN** the implementation can drive those cases with deterministic scheduler control
- **AND THEN** the tests do not require real wall-clock sleeps to verify the timed behavior

### Requirement: Live tracked state distinguishes transport, process, and parse outcomes explicitly
The tracked-state contract SHALL expose low-level diagnostics separately from the simplified work model.

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
- the simplified foundational/work/outcome state defined by this capability.

For supported parsed tools, parse failure SHALL be represented explicitly rather than fabricated as a successful parsed surface.

#### Scenario: Parser failure is explicit in live tracked state
- **WHEN** the tmux session is live, the supported TUI process is up, and the official parser fails for that cycle
- **THEN** the live tracked state records an explicit parse-failure status
- **AND THEN** the parsed-surface field is absent or null for that cycle
- **AND THEN** the simplified work state degrades through diagnostic availability rather than fabricating a successful work-phase interpretation

#### Scenario: TUI-down cycle still exposes transport and process state
- **WHEN** the tmux session remains live but the expected supported TUI process is down
- **THEN** the live tracked state still exposes the transport and process fields for that session
- **AND THEN** the parse stage is represented as skipped or unavailable for that cycle
- **AND THEN** the simplified work state does not fabricate a ready or active posture for that cycle

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
**Reason**: The old public readiness/completion/authority-heavy lifecycle surface exposed reducer internals rather than the simpler foundational observables and work-cycle contract the server now intends to publish.

**Migration**: Consumer dashboards and docs SHALL read `surface`, `work`, and `last_outcome` from tracked-state responses as the primary state contract. Deep timing or reducer-debug needs SHALL move to diagnostic stability/parsed-surface evidence and the existing tracking-debug workflow rather than to public `candidate_complete`, `completed`, `stalled`, or anchor-authority fields.
