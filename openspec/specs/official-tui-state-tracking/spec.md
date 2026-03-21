## Purpose
Define the server-owned live TUI tracking contract for direct tmux/process observation, official parsing, in-memory tracked state, and stability metadata.

## Requirements

### Requirement: Live tracked-state reduction SHALL be implemented through the shared TUI tracking core
For supported parsed tmux-backed sessions, the server SHALL derive tracker-owned `surface`, `turn`, `last_turn`, detector identity, and tracker-state stability semantics through the repo-owned shared TUI tracking core rather than through a package-local reducer that replay and validation tools cannot reuse.

The server SHALL remain responsible for live tmux/process/probe observation, session identity, explicit prompt-submission capture, parsed-surface metadata, diagnostics, lifecycle readiness/completion pipelines, effective visible stability, and in-memory authority, but the tracker-owned reduction itself SHALL come from the shared standalone tracker session.

The server's live adapter SHALL feed raw captured TUI snapshot text and any explicit prompt-submission evidence into that shared tracker and SHALL then merge the resulting tracker state back into the published live contract together with server-owned diagnostics, lifecycle snapshots, and visible-stability metadata.

#### Scenario: Live cycle adapts raw TUI snapshot and diagnostics into the shared core
- **WHEN** the server records one live tracking cycle for a supported tmux-backed session
- **THEN** it supplies the captured raw TUI snapshot and any explicit prompt-submission evidence to the shared core
- **AND THEN** it keeps tmux/process/probe/parse diagnostics and lifecycle readiness/completion under server ownership
- **AND THEN** the published tracked-state response preserves the official live contract while sharing tracker reduction semantics with replay consumers

#### Scenario: Server-owned input remains authoritative through the shared core
- **WHEN** the server accepts prompt input through its owned input route
- **THEN** the live adapter arms turn authority in the shared core from that explicit input event
- **AND THEN** later tracked state can still report `last_turn.source=explicit_input`

#### Scenario: Visible stability remains server-owned when diagnostics participate
- **WHEN** the published live stability signature depends on transport/process/parse diagnostics or other host-owned fields in addition to tracker state
- **THEN** the server computes the visible stability view over the merged live contract
- **AND THEN** tracker-owned stability from the shared core remains limited to tracker-state transitions

### Requirement: Known tmux-backed sessions are tracked continuously
The system SHALL continuously track every known tmux-backed Houmao session while its tmux session exists, independent of whether any client is currently querying state and independent of whether a prompt was recently submitted.

Known sessions SHALL be seeded from `houmao-server` registration records for sessions that this server manages, enriched by manifest-backed metadata, and verified against live tmux liveness rather than by ad hoc CAO polling alone.

Shared live-agent registry records MAY be consulted as compatibility evidence or alias enrichment, but they SHALL NOT by themselves create an authoritative known-session entry for this capability.

#### Scenario: Background tracking continues without active queries
- **WHEN** a known tmux-backed session remains alive and no caller is polling its live state
- **THEN** the system continues tracking that session in the background
- **AND THEN** the latest live state remains current without requiring a request-triggered refresh

#### Scenario: Newly discovered known session enters continuous tracking
- **WHEN** the server discovers a newly known tmux-backed Houmao session through its registration or manifest-backed discovery path
- **THEN** the system starts continuous tracking for that session
- **AND THEN** the session no longer depends on a first state query to become watch-active

#### Scenario: Startup rebuild reuses server registration and live tmux verification
- **WHEN** `houmao-server` restarts and loads a server-managed registration record for a session whose tmux session is still live
- **THEN** the system re-admits that session into the known-session registry
- **AND THEN** manifest-backed metadata may enrich the tracked identity before background tracking resumes

#### Scenario: Shared registry evidence alone does not admit a watched session
- **WHEN** a shared live-agent registry record exists without an authoritative server registration record or a verifiable live tmux target for that session
- **THEN** that registry record alone does not create a primary known-session entry for this capability
- **AND THEN** the system does not start a background watch worker solely from that compatibility evidence

### Requirement: TUI liveliness is derived from process inspection
For each tracked tmux-backed session, the system SHALL determine whether the supported interactive TUI is up or down by inspecting the live process tree attached to the tracked tmux pane rather than by inferring that state only from captured pane text.

#### Scenario: TUI process is down while tmux remains alive
- **WHEN** a tracked tmux session still exists but the expected supported TUI process is no longer running in the tracked pane process tree
- **THEN** the tracked live state records that the TUI is down
- **AND THEN** the session remains under background tracking instead of being dropped immediately

#### Scenario: TUI process is up and eligible for parsing
- **WHEN** a tracked tmux session exists and the expected supported TUI process is running in the tracked pane process tree
- **THEN** the system treats the TUI as up for that cycle
- **AND THEN** the parsing stage may consume directly captured pane text for live state reduction

### Requirement: Parsed TUI state comes from direct tmux capture through the official parser
For supported live TUI tools, the system SHALL capture pane content directly from tmux and SHALL derive parsed live state through the repo-owned official parser stack for that tool.

The parsing and state-tracking path SHALL NOT require `cao-server` terminal-status or terminal-output endpoints as the authoritative source for live TUI interpretation.

#### Scenario: Supported live TUI snapshot is parsed directly from tmux capture
- **WHEN** a tracked supported TUI session is up and the server captures pane content directly from tmux
- **THEN** the system parses that captured content through the official parser stack
- **AND THEN** the resulting parsed state becomes the live interpretation surface for that cycle

#### Scenario: CAO is not the parsing authority for tracked state
- **WHEN** the system updates live tracked state for a supported tmux-backed session
- **THEN** it does not rely on child `cao-server` output or status polling as the parsing authority
- **AND THEN** the tracked state remains available even when the CAO parsing path is intentionally bypassed

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
- diagnostic availability or health metadata for the current sample, and
- the simplified foundational/turn/last-turn state defined by this capability.

For supported parsed tools, parse failure SHALL be represented explicitly rather than fabricated as a successful parsed surface.

#### Scenario: Parser failure is explicit in live tracked state
- **WHEN** the tmux session is live, the supported TUI process is up, and the official parser fails for that cycle
- **THEN** the live tracked state records an explicit parse-failure status
- **AND THEN** the parsed-surface field is absent or null for that cycle

#### Scenario: TUI-down cycle still exposes transport and process state
- **WHEN** the tmux session remains live but the expected supported TUI process is down
- **THEN** the live tracked state still exposes the transport and process fields for that session
- **AND THEN** the parse stage is represented as skipped or unavailable for that cycle
- **AND THEN** the simplified turn state does not fabricate a ready or active posture for that cycle

### Requirement: Live tracked state is authoritative in memory
The authoritative live tracked state for this capability SHALL live in server memory.

That in-memory state SHALL include at minimum:

- tracked session identity,
- `terminal_id` compatibility aliases,
- tmux transport state,
- TUI process liveliness,
- parse-stage status plus any probe or parse error detail,
- latest parsed TUI surface state when available,
- simplified foundational, turn, and last-turn state, and
- bounded recent transitions or recent-state history.

The system SHALL NOT require per-session watch snapshot files or append-only watch logs as part of the authoritative contract for this capability.

#### Scenario: State query reads the current in-memory authority
- **WHEN** a caller requests live tracked state for a watched session
- **THEN** the system returns the latest state held in server memory
- **AND THEN** that result does not depend on reading a persisted watch snapshot file first

#### Scenario: Restart rebuilds live state from rediscovery
- **WHEN** the server restarts while some previously tracked tmux sessions are still alive
- **THEN** the system rebuilds live tracked state by rediscovering those live known sessions
- **AND THEN** it does not claim prior watch files as the authoritative source for the rebuilt state

### Requirement: Live tracking exposes stability metadata over the visible state signature
The system SHALL track how long the operator-visible live state signature remains unchanged and SHALL expose stability metadata for that signature as part of the in-memory tracked state.

At minimum, that stability metadata SHALL include whether the current signature is considered stable and how long it has remained unchanged.

#### Scenario: Unchanged live signature accumulates stability duration
- **WHEN** the operator-visible tracked state signature remains unchanged across successive observations
- **THEN** the system increases the tracked stability duration for that signature
- **AND THEN** the live state reflects that unchanged duration in its stability metadata

#### Scenario: Changed live signature resets stability duration
- **WHEN** any operator-visible component of the tracked state signature changes
- **THEN** the system resets the stability duration for the new signature
- **AND THEN** the live state no longer reports the prior signature's accumulated duration

### Requirement: Timer-driven live lifecycle semantics use ReactiveX observation streams
For supported parsed tmux-backed sessions, all timed behavior in this capability SHALL be implemented over ordered observation streams using ReactiveX operators rather than hand-rolled mutable timestamp reducers, ad hoc polling arithmetic, or manual wall-clock timers.

That ReactiveX timing layer SHALL be authoritative for:

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

#### Scenario: Lifecycle timing is testable without real sleeps
- **WHEN** unit tests exercise unknown-duration handling, timed recovery, or success settle timing for this capability
- **THEN** the implementation can drive those cases with deterministic scheduler control
- **AND THEN** the tests do not require real wall-clock sleeps to verify the lifecycle semantics

### Requirement: Interactive Codex live tracking resolves through the Codex TUI tracker family
When the server tracks an interactive Codex session from raw captured TUI snapshots, the live tracked-TUI adapter SHALL resolve the shared tracker through the `codex_tui` tracker app family rather than through a headless backend label.

That tracker-family resolution SHALL apply only to the interactive screen-scraped Codex TUI case. Structured headless Codex control flows SHALL remain outside the official tracked-TUI live path unless they are explicitly re-expressed as interactive raw-snapshot sources.

This tracker-facing resolution change SHALL NOT rename runtime/backend identifiers outside the live tracked-TUI adapter boundary.

#### Scenario: Interactive Codex tmux session uses codex_tui in live tracking
- **WHEN** the server captures raw snapshots from an interactive Codex tmux pane for live tracked-state reduction
- **THEN** the live adapter resolves the shared tracker through `codex_tui`
- **AND THEN** the resulting live tracked state uses the standalone tracked-TUI contract rather than a backend-specific headless label

#### Scenario: Headless Codex control path is not routed through live TUI tracking
- **WHEN** a repo-owned Codex flow uses a structured headless contract instead of interactive raw TUI snapshots
- **THEN** the official live tracked-TUI path does not require that flow to resolve through `codex_tui`
- **AND THEN** the server does not model that headless control path as an interactive tracked-TUI session by default

#### Scenario: Tracker-facing Codex app-family resolution leaves backend names unchanged
- **WHEN** the live tracked-TUI adapter resolves an interactive Codex session through `codex_tui`
- **THEN** that resolution changes only the tracker-facing app-family identity used by the tracked-TUI subsystem
- **AND THEN** runtime/backend identifiers such as `codex_app_server` outside that boundary remain unchanged

### Requirement: Live Codex TUI tracking preserves ordered snapshots for profile-owned temporal inference
When the server feeds interactive Codex TUI snapshots into the shared tracker, it SHALL preserve their observation order so the selected `codex_tui` profile can derive temporal hints over its recent sliding window.

The live adapter SHALL NOT require callers or clients to manage that recent-window logic directly.

The live adapter MAY emit explicit input events when they are available, but snapshot-only tracking SHALL remain compatible with success settlement that relies on surface-inferred turn authority.

#### Scenario: Ordered Codex snapshots support temporal active inference
- **WHEN** the newest interactive Codex snapshot alone lacks a visible running row
- **AND WHEN** the selected `codex_tui` profile can still infer active work from the recent ordered snapshot window
- **THEN** the live adapter preserves the snapshot order needed for that temporal inference
- **AND THEN** the shared tracker may still publish `turn.phase=active` for the current live turn

#### Scenario: Snapshot-only live tracking can still settle ready-return success
- **WHEN** the live adapter streams ordered interactive Codex snapshots without a matching explicit input event
- **AND WHEN** the shared tracker has already armed turn authority through stronger active-turn evidence from those snapshots
- **THEN** a later stable ready-return completion may still settle as `success`
- **AND THEN** the live adapter does not need explicit keystroke reporting to support Codex TUI completion tracking
