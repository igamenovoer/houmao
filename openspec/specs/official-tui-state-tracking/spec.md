## Purpose
Define the server-owned live TUI tracking contract for direct tmux/process observation, official parsing, in-memory tracked state, and stability metadata.
## Requirements
### Requirement: Live tracked-state reduction SHALL be implemented through the shared TUI tracking core
For supported tmux-backed TUI sessions, the active per-agent control plane SHALL derive tracker-owned `surface`, `turn`, `last_turn`, detector identity, and tracker-state stability semantics through the repo-owned shared TUI tracking core rather than through a package-local reducer or parser-owned reduction path.

Any reusable tracking ownership or supervision helpers needed by both the attached gateway and the direct `houmao-server` fallback SHALL live in neutral shared modules layered over the shared tracking core rather than requiring the gateway to import `houmao.server.tui` package-local ownership code.

The active per-agent control plane SHALL be:

- the attached per-agent gateway, when an eligible live gateway is attached for that managed agent, or
- the direct `houmao-server` fallback tracker, when no eligible live gateway is attached.

That active control plane SHALL remain responsible for live tmux or process observation for tracker authority, session identity, explicit prompt-submission capture, diagnostics, visible-stability metadata over the authoritative tracked response, and in-memory tracker authority for that agent.

`houmao-server` SHALL remain the public HTTP authority for managed-agent and terminal-facing route families, but it SHALL project gateway-owned tracked state for attached agents rather than duplicating tracker authority for those agents inside the central server.

The active control-plane adapter SHALL feed raw captured TUI snapshot text and any explicit prompt-submission evidence into the shared tracker. Parser-derived data MAY still exist as sidecar evidence, but it SHALL NOT replace raw snapshot text as tracker input and SHALL NOT arm tracker authority through parser-derived surface-inference heuristics.

#### Scenario: Attached gateway owns tracker reduction for an attached managed TUI agent
- **WHEN** a managed TUI agent has an eligible attached live gateway and that gateway records one live tracking cycle
- **THEN** the gateway supplies the captured raw TUI snapshot and any explicit prompt-submission evidence to the shared tracking core for that agent
- **AND THEN** `houmao-server` projects that gateway-owned tracked state rather than running a second authoritative tracker for the same attached agent

#### Scenario: Direct server fallback remains the tracker owner when no gateway is attached
- **WHEN** a managed TUI agent has no eligible live gateway attached
- **THEN** the direct `houmao-server` fallback tracker remains the active control plane for tracked-state reduction for that agent
- **AND THEN** the tracked-state contract exposed to callers remains the same even though no gateway is present

#### Scenario: Prompt submission still arms explicit-input tracking through the active control plane
- **WHEN** a caller submits prompt input through a server-owned managed-agent or terminal-facing route for a managed TUI agent
- **THEN** the system forwards that explicit prompt-submission evidence to the active control plane for that agent
- **AND THEN** later tracked state can still report `last_turn.source=explicit_input`

### Requirement: Known tmux-backed sessions are tracked continuously
The system SHALL continuously track every known tmux-backed managed TUI session while its tmux session exists, independent of whether any client is currently querying state and independent of whether a prompt was recently submitted.

For server-managed sessions, `houmao-server` SHALL continue seeding known-session identity from authoritative registration or admission records and SHALL determine whether an eligible attached gateway exists for that agent.

When an eligible attached gateway exists for a managed TUI agent, the system SHALL assign continuous tracking authority for that agent to the gateway. When no eligible gateway exists, the direct `houmao-server` fallback tracker SHALL continue tracking that agent.

When tracking authority changes because a gateway attaches, detaches, or becomes unhealthy, the system SHALL maintain exactly one active authoritative tracking owner for that agent at a time.

In this phase, the system MAY serve last-known tracked state during a brief transition window while the next tracking owner becomes current, but it SHALL NOT require atomic cross-process state transfer for attach or detach handoff.

Shared live-agent registry records MAY be consulted as compatibility evidence or alias enrichment, but they SHALL NOT by themselves create an authoritative tracked-session entry for this capability.

#### Scenario: Attached gateway becomes the continuous tracking owner
- **WHEN** a managed TUI agent already admitted by `houmao-server` later gains an eligible attached live gateway
- **THEN** the system assigns continuous tracked-state authority for that agent to the gateway
- **AND THEN** the central server no longer needs to remain the authoritative continuous tracker for that attached agent

#### Scenario: Direct fallback continues tracking when no gateway is attached
- **WHEN** a known managed TUI session remains live and no eligible live gateway is attached for that agent
- **THEN** the direct `houmao-server` fallback tracker continues tracking that session in the background
- **AND THEN** callers can still query current tracked state without requiring a gateway sidecar

#### Scenario: Shared registry evidence alone does not admit a tracked session
- **WHEN** a shared live-agent registry record exists without authoritative server registration or admission for a managed TUI session
- **THEN** that registry record alone does not create a primary tracked-session entry for this capability
- **AND THEN** the system does not start continuous tracking solely from that compatibility evidence

#### Scenario: Gateway attach uses single-owner handoff semantics
- **WHEN** a managed TUI agent transitions from direct fallback tracking to an attached healthy gateway tracker
- **THEN** the system flips authoritative tracking ownership to the gateway without keeping both trackers authoritative at the same time
- **AND THEN** `houmao-server` may serve last-known tracked state briefly while the gateway-owned tracker becomes current

#### Scenario: Gateway detach or gateway health loss returns ownership to direct fallback
- **WHEN** a managed TUI agent loses its healthy attached gateway and direct fallback tracking remains supported
- **THEN** the system returns authoritative tracking ownership to the direct `houmao-server` fallback tracker
- **AND THEN** the transition does not require atomic cross-process state transfer to preserve the v1 tracked-state contract

### Requirement: Attached gateways can own live tracked state for runtime-owned local interactive sessions
For a runtime-owned `local_interactive` TUI session outside `houmao-server`, when an attached gateway is present and healthy, that gateway SHALL be allowed to act as the active control plane for live tracked-state authority for that session.

For this runtime-owned path, the active control plane SHALL be allowed to use the runtime-owned session identifier as the tracked-session identity and SHALL NOT require a CAO-style terminal alias so long as the public compatibility alias can fall back to the tracked session id.

#### Scenario: Gateway becomes the tracking owner for runtime-owned local interactive session
- **WHEN** a runtime-owned `local_interactive` TUI session outside `houmao-server` has an attached healthy gateway
- **THEN** the gateway owns continuous live tracked-state reduction for that session
- **AND THEN** the tracked identity for that session may be anchored by the runtime session id rather than by a CAO terminal id

### Requirement: Gateway-owned local interactive tracking preserves explicit-input authority
When prompt input for a runtime-owned `local_interactive` session is accepted through an attached gateway, the active gateway-owned control plane SHALL preserve that explicit-input evidence for tracked turn reduction in the same way as other gateway-owned tracked TUI flows.

#### Scenario: Gateway prompt note preserves explicit-input provenance for runtime-owned local interactive session
- **WHEN** an attached gateway accepts and executes prompt input for a runtime-owned `local_interactive` session outside `houmao-server`
- **THEN** the gateway forwards that explicit prompt-submission evidence to the active tracking control plane for that session
- **AND THEN** later tracked state for that session can report explicit-input provenance for the resulting completed turn

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
The authoritative live tracked state for this capability SHALL live in memory of the active per-agent control plane.

For an attached managed TUI agent, that authoritative in-memory tracked state SHALL live in the attached gateway for that agent.

For a managed TUI agent with no eligible attached gateway, that authoritative in-memory tracked state SHALL live in the direct `houmao-server` fallback tracker.

The system SHALL NOT require per-session watch snapshot files or append-only watch logs as part of the authoritative tracked-state contract for this capability.

`houmao-server` MAY project gateway-owned tracked state through its public routes, but those route responses SHALL read from the active control plane's current in-memory authority rather than reconstructing authoritative tracked state from persisted watch artifacts.

#### Scenario: Server projects gateway-owned in-memory tracked state
- **WHEN** a caller requests tracked managed-agent or terminal state for a TUI agent whose eligible live gateway is attached
- **THEN** `houmao-server` serves that request from the gateway-owned current tracked state for that agent
- **AND THEN** the public response does not depend on a separate server-owned persisted watch snapshot

#### Scenario: No-gateway fallback reads direct server memory
- **WHEN** a caller requests tracked state for a managed TUI agent with no eligible live gateway attached
- **THEN** the direct `houmao-server` fallback tracker returns the latest state held in its own memory
- **AND THEN** that result does not require persisted watch artifacts to become authoritative

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

### Requirement: Multi-window tracked TUI sessions resolve an explicit observation surface
For tmux-backed tracked TUI sessions, when the active control plane has explicit pane or window identity for the intended observed surface, it SHALL resolve capture and process inspection from that explicit tmux surface rather than from current-window or current-pane heuristics.

Session-scoped tmux pane discovery used by the active control plane SHALL span all panes in the tracked session, including panes in non-current windows.

When multiple candidate panes exist and the tracked contract does not include explicit pane or window identity for the intended surface, the active control plane SHALL fail explicitly or surface non-authoritative diagnostics rather than silently rebinding to the current active window.

#### Scenario: Tracked local interactive session stays bound to the agent surface
- **WHEN** a tracked runtime-owned `local_interactive` session gains an auxiliary gateway window in the same tmux session
- **AND WHEN** the active control plane knows the contractual agent surface identity
- **THEN** live capture and process inspection continue targeting the agent surface
- **AND THEN** the tracking owner does not silently switch to the auxiliary gateway window because it became current

#### Scenario: Ambiguous tracked multi-window session does not guess from current focus
- **WHEN** a tracked tmux session has multiple candidate panes across multiple windows
- **AND WHEN** the tracked identity lacks explicit pane or window metadata for the intended observed surface
- **THEN** the active control plane reports an explicit targeting problem or remains non-authoritative for that cycle
- **AND THEN** it does not silently choose the current active window as the observed TUI surface
