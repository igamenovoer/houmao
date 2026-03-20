## ADDED Requirements

### Requirement: Tracked-state routes expose simplified work-cycle and last-outcome semantics
When `houmao-server` returns server-owned tracked-state payloads for watched sessions, it SHALL expose the simplified state model as the primary consumer-facing route contract.

At minimum, the tracked-state response SHALL include:

- low-level diagnostics and parsed-surface evidence for the current sample,
- foundational observables under `surface`,
- current work posture under `work`, and
- the most recent terminal result under `last_outcome`.

For `last_outcome`, the route SHALL identify whether the result came from an explicit server-owned input path, inferred direct interaction, or no completed cycle yet.

The route SHALL NOT require callers to interpret public turn-anchor states, completion authority states, or completion debounce states in order to understand what the terminal is doing now or what the last cycle did.

The route SHALL NOT imply that every visible TUI change has a known cause. If the watched surface changes for unexplained reasons and does not satisfy the server's stricter cycle-evidence rules, the route MAY reflect diagnostic or surface churn without manufacturing a new `work` transition or `last_outcome`.

#### Scenario: Background ready surface exposes a simplified ready state
- **WHEN** a caller requests tracked state for a watched terminal whose TUI is idle and ready for freeform input
- **THEN** `houmao-server` returns `surface` and `work` fields that identify a ready chat posture
- **AND THEN** the caller can understand that state without reading public readiness/completion/authority fields

#### Scenario: Explicit server input produces a terminal outcome with explicit source
- **WHEN** `houmao-server` accepts a terminal input submission for a tracked session and that cycle later settles successfully
- **THEN** a later tracked-state response records `last_outcome.result=success`
- **AND THEN** the response records `last_outcome.source=explicit_input`

#### Scenario: Direct tmux prompting can still produce an inferred terminal outcome
- **WHEN** a watched session is prompted directly through tmux instead of the supported server input route
- **AND WHEN** the server safely infers the start and end of that cycle from live observation
- **THEN** a later tracked-state response may record the terminal result for that cycle
- **AND THEN** the response records `last_outcome.source=surface_inference` rather than requiring the caller to inspect turn-anchor internals

#### Scenario: Unexplained surface churn does not manufacture an inferred outcome
- **WHEN** a watched session shows visible surface changes whose cause is not safely attributable to a tracked cycle
- **AND WHEN** those changes do not satisfy the server's cycle-start or cycle-terminal inference rules
- **THEN** the tracked-state response does not manufacture a new `last_outcome`
- **AND THEN** the response does not claim a new `work.phase=active` from that churn alone

## MODIFIED Requirements

### Requirement: `houmao-server` publishes Houmao-owned terminal state and history as explicit extension routes
`houmao-server` SHALL expose Houmao-specific HTTP extension routes for live terminal state and bounded recent transition history in addition to the CAO-compatible core API.

In v1, those live-state and recent-history routes SHALL remain terminal-keyed compatibility routes, and `houmao-server` SHALL resolve `terminal_id` lookups through a compatibility alias map to its Houmao-owned internal tracked-session identity.

Those extension routes SHALL keep Houmao-owned features explicit rather than using breaking changes on CAO-compatible payloads.

At minimum, the Houmao-owned live terminal state contract SHALL distinguish:

- tmux transport state,
- TUI process state,
- parse status,
- optional probe or parse error detail,
- the latest parsed TUI surface when available,
- diagnostic availability or health for the current sample,
- foundational observables under `surface`,
- current work posture under `work`,
- the most recent terminal result under `last_outcome`,
- generic stability metadata as diagnostic evidence, and
- bounded recent transition or recent-state history when requested.

Those extension routes SHALL be backed by in-memory live state rather than persisted watch files. If recent history is exposed, it SHALL be a bounded in-memory view rather than an append-only persisted log.

#### Scenario: Terminal-keyed route resolves through a compatibility alias
- **WHEN** a caller requests Houmao-owned live state by `terminal_id`
- **THEN** `houmao-server` resolves that lookup through the terminal compatibility alias bound to its internal tracked-session identity
- **AND THEN** the internal known-session registry does not need to be keyed primarily by `terminal_id`

#### Scenario: Callers can inspect Houmao-owned terminal state without scraping raw output
- **WHEN** a caller needs the latest Houmao-owned live state for a watched terminal
- **THEN** the caller can query a dedicated `houmao-server` extension route for that state
- **AND THEN** the caller does not need to reconstruct that state by scraping raw terminal output alone

#### Scenario: Parser or probe failure stays explicit on the extension route
- **WHEN** a watched terminal reaches the extension route with a probe failure or parse failure in the latest cycle
- **THEN** the returned live state distinguishes that failure from a normal TUI-down or successfully parsed cycle
- **AND THEN** the route does not fabricate a parsed surface for that failed cycle

#### Scenario: Recent transitions are exposed from memory rather than persisted watch logs
- **WHEN** a watched terminal has experienced multiple recent observed state changes during the current server lifetime
- **THEN** `houmao-server` may expose those recent transitions through its extension routes
- **AND THEN** that recent-history view is served from bounded in-memory state rather than from append-only persisted watch logs

#### Scenario: Restart rebuilds live state instead of replaying stale watch files
- **WHEN** `houmao-server` restarts and resumes watching still-live known sessions
- **THEN** it rebuilds the extension-route live state from fresh observation of those sessions
- **AND THEN** it does not treat old watch snapshot files or old append-only watch logs as the authoritative rebuilt state

## REMOVED Requirements

### Requirement: Tracked-state routes expose lifecycle authority for background and turn-anchored monitoring
**Reason**: Lifecycle authority, turn anchors, and public completion debounce states are reducer-internal mechanics that complicate the tracked-state route contract and force callers to interpret server bookkeeping rather than foundational observable state.

**Migration**: Route consumers SHALL use `surface`, `work`, and `last_outcome` as the primary state contract. When they need to know whether the last recorded cycle came from explicit server input or inferred interactive observation, they SHALL read `last_outcome.source` instead of public completion-authority or turn-anchor fields.
