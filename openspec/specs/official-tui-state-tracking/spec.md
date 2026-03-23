## Purpose
Define the server-owned live TUI tracking contract for direct tmux/process observation, official parsing, in-memory tracked state, and stability metadata.
## Requirements
### Requirement: Live tracked-state reduction SHALL be implemented through the shared TUI tracking core
For supported tmux-backed TUI sessions, the server SHALL derive tracker-owned `surface`, `turn`, `last_turn`, detector identity, and tracker-state stability semantics through the repo-owned shared TUI tracking core rather than through a package-local reducer or parser-owned reduction path.

The server SHALL remain responsible for live tmux/process/probe observation, session identity, explicit prompt-submission capture, optional parser-derived surface metadata, optional parser-fed lifecycle/operator enrichment, diagnostics, visible-stability metadata over the published response, and in-memory authority, but the tracker-owned reduction itself SHALL come from the shared standalone tracker session.

The server's live adapter SHALL feed raw captured TUI snapshot text and any explicit prompt-submission evidence into that shared tracker. Parser-derived data MAY be computed from the same raw capture for server-owned features, but SHALL NOT be required tracker input, SHALL NOT replace raw snapshot text as the authoritative tracking source, and SHALL NOT arm tracker authority through parser-derived surface-inference heuristics.

Optional server-owned `operator_state`, `lifecycle_timing`, and `lifecycle_authority` fields MAY continue to derive from parser-fed lifecycle monitoring and explicit-input server anchors, but those fields SHALL remain sidecar server evidence and SHALL NOT redefine tracker-owned `surface`, `turn`, or `last_turn`.

#### Scenario: Live cycle adapts raw TUI snapshot and diagnostics into the shared core
- **WHEN** the server records one live tracking cycle for a supported tmux-backed session
- **THEN** it supplies the captured raw TUI snapshot and any explicit prompt-submission evidence to the shared core
- **AND THEN** it keeps tmux/process/probe diagnostics and any parser-owned sidecar data under server ownership
- **AND THEN** the published tracked-state response preserves the official live contract while sharing tracker reduction semantics with the standalone tracker module

#### Scenario: Server-owned input remains authoritative through the shared core
- **WHEN** the server accepts prompt input through its owned input route
- **THEN** the live adapter arms turn authority in the shared core from that explicit input event
- **AND THEN** later tracked state can still report `last_turn.source=explicit_input`

#### Scenario: Surface-inference authority comes from the shared raw-snapshot tracker
- **WHEN** a tracked live TUI session shows enough raw-snapshot evidence for a newer turn without an explicit input event
- **THEN** the shared tracker may infer `last_turn.source=surface_inference` from raw snapshot evidence
- **AND THEN** the live adapter does not arm tracker authority from parser-derived submit-ready heuristics for that turn

#### Scenario: Observed tool version informs live profile selection when available
- **WHEN** the server has observed tool-version metadata for a tracked live TUI session
- **THEN** the live adapter supplies that version metadata to the shared tracker during profile resolution
- **AND THEN** the live server does not default to an unspecified tracker profile merely because the session is live rather than standalone

#### Scenario: Missing observed tool version falls back gracefully
- **WHEN** the server lacks observed tool-version metadata for a tracked live TUI session
- **THEN** the live adapter still resolves the shared tracker through its compatible fallback profile behavior
- **AND THEN** missing version metadata alone does not fail live tracking or invent a parser-owned warning state

#### Scenario: Parsed surface does not replace raw tracker input
- **WHEN** the server also computes parsed-surface data from the captured tmux snapshot for server-owned functionality
- **THEN** the live adapter still feeds the shared tracker from the raw captured snapshot text
- **AND THEN** it does not synthesize or substitute tracker input from parser-owned fields during normal live execution

#### Scenario: Parser-fed lifecycle sidecar does not override tracker-owned state
- **WHEN** the server also computes parser-fed lifecycle or operator fields for that cycle
- **THEN** those fields remain server-owned enrichment
- **AND THEN** they do not override tracker-owned `surface`, `turn`, or `last_turn`

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
For supported live TUI tools, when the system computes parser-owned surface evidence it SHALL parse pane content directly captured from tmux through the repo-owned official parser stack for server-owned functionality such as structured diagnostics, parser metadata, or operator-facing surface evidence.

That parser path SHALL remain separate from state-tracking authority. Parsed live surface data SHALL be server-owned sidecar enrichment derived from the same raw tmux capture, and the shared tracked-state reduction SHALL NOT require parsed-surface output as its input contract.

The parsing and state-tracking paths SHALL NOT require `cao-server` terminal-status or terminal-output endpoints as the authoritative source for either live TUI interpretation or tracked-state reduction.

#### Scenario: Supported live TUI snapshot can be parsed as sidecar server evidence
- **WHEN** a tracked supported TUI session is up and the server captures pane content directly from tmux
- **THEN** the system may parse that captured content through the official parser stack
- **AND THEN** the resulting parsed state is available as server-owned structured evidence for that cycle
- **AND THEN** the tracker-reduction path continues to depend on the raw captured snapshot rather than on parsed-surface output

#### Scenario: CAO is not the parsing or tracking authority for live state
- **WHEN** the system updates live tracked state for a supported tmux-backed session
- **THEN** it does not rely on child `cao-server` output or status polling as the parsing authority
- **AND THEN** it does not rely on child `cao-server` as the authoritative source for tracker input or live tracked-state interpretation

#### Scenario: Parser failure remains explicit without becoming tracker input
- **WHEN** the server captures raw pane text successfully but the official parser fails for that cycle
- **THEN** the server records explicit parser failure in server-owned diagnostics
- **AND THEN** it does not fabricate parser-derived tracker input in order to continue state reduction

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

Visible progress or spinner signals SHALL be treated as supporting evidence only. When present, they are sufficient evidence for active-turn inference. When absent, they SHALL NOT by themselves negate the possibility of an active turn.

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

### Requirement: Styled placeholder prompt text does not imply editing input
For supported interactive TUI surfaces, the tracked state SHALL treat visible placeholder or suggestion text on the prompt line as non-editing posture when the selected profile classifies that prompt payload as placeholder content rather than user-authored draft input.

The system SHALL continue to report real draft prompt content as `surface.editing_input=yes` when the selected profile classifies the same prompt region as active draft input.

#### Scenario: Claude startup suggestion remains non-editing
- **WHEN** Claude Code renders styled suggestion text on the visible `❯` prompt line before the operator types anything
- **THEN** the tracked state reports `surface.accepting_input=yes`
- **AND THEN** the tracked state reports `surface.ready_posture=yes`
- **AND THEN** the tracked state reports `surface.editing_input=no`
- **AND THEN** the tracked state reports `turn.phase=ready`

#### Scenario: Real Claude draft text still reports editing
- **WHEN** the operator types real draft text into the Claude prompt area
- **AND WHEN** the selected Claude profile classifies the visible prompt payload as draft input rather than placeholder content
- **THEN** the tracked state reports `surface.editing_input=yes`
- **AND THEN** the tracked state does not downgrade that draft to placeholder solely because the prompt line contains styling

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
- optional parsed TUI surface data when the server computes it for that cycle,
- diagnostic availability or health metadata for the current sample, and
- the simplified foundational `surface`, `turn`, and `last_turn` state defined by this capability.

For supported tools, parse failure SHALL be represented explicitly as a server-owned diagnostic outcome rather than fabricated as a successful parsed surface. Parse outcomes SHALL remain distinct from tracker-owned reduction and SHALL NOT require converting parser-owned fields back into tracker input.

#### Scenario: Parser failure is explicit in live tracked state
- **WHEN** the tmux session is live, the supported TUI process is up, raw pane capture succeeds, and the official parser fails for that cycle
- **THEN** the live tracked state records an explicit parse-failure status
- **AND THEN** the parsed-surface field is absent or null for that cycle
- **AND THEN** the server does not claim parser-owned data as the source of tracker reduction for that sample

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

### Requirement: Timer-driven server-owned lifecycle enrichment SHALL remain separate from tracker-owned success settlement
For supported tmux-backed TUI sessions, timed behavior in server-owned lifecycle enrichment SHALL remain separate from tracker-owned success settlement and SHALL remain implementable over ordered observation streams using ReactiveX operators.

That ReactiveX timing layer SHALL remain authoritative for server-owned readiness/completion enrichment such as `operator_state`, `lifecycle_timing`, and `lifecycle_authority`, but SHALL NOT redefine or delay tracker-owned `surface`, `turn`, or `last_turn`.

Shared-tracker success settlement remains owned by the standalone tracker session even when server-owned lifecycle timing is also present for the same live cycle.

#### Scenario: Tracker-owned success remains authoritative when lifecycle timing differs
- **WHEN** the shared tracker records `last_turn.result=success` for a live cycle
- **AND WHEN** the server-owned lifecycle pipeline has not yet reached its own completed posture
- **THEN** the published `last_turn.result` remains the tracker-owned success outcome
- **AND THEN** the lifecycle/operator fields remain sidecar server enrichment rather than replacing that outcome

#### Scenario: Server-owned lifecycle timing remains testable without real sleeps
- **WHEN** unit tests exercise unknown-duration handling or completion timing for server-owned lifecycle enrichment
- **THEN** the implementation can continue to drive those lifecycle cases with deterministic scheduler control
- **AND THEN** those tests do not redefine the authority boundary for tracker-owned state

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
