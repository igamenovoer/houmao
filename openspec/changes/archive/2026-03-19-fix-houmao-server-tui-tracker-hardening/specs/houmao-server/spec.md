## ADDED Requirements

### Requirement: `houmao-server` keeps registration bridge storage contained under the server-owned sessions root
When `houmao-server` persists or removes server-owned registration records for tracked sessions, it SHALL treat the registration storage key as a validated server-owned identifier rather than as a raw filesystem path fragment.

`houmao-server` SHALL reject registration or deletion inputs whose session identifier cannot be represented safely inside the configured `sessions/` root.

`houmao-server` SHALL verify that the resolved registration path remains under the configured `sessions/` root before writing or removing any registration directory.

#### Scenario: Invalid registration identifier is rejected before write
- **WHEN** a caller sends a registration request whose session identifier would escape or otherwise violate the server-owned `sessions/` storage namespace
- **THEN** `houmao-server` rejects that request before creating or modifying any registration directory
- **AND THEN** the server does not write a registration file outside the configured `sessions/` root

#### Scenario: Registration cleanup remains root-contained
- **WHEN** `houmao-server` removes a server-owned registration record during session or terminal cleanup
- **THEN** it resolves the cleanup target within the same validated server-owned `sessions/` namespace
- **AND THEN** the server does not remove directories outside the configured `sessions/` root

### Requirement: `houmao-server` keeps background tracking resilient across unexpected runtime failures
`houmao-server` SHALL keep the tracking supervisor and per-session watch workers resilient against unexpected runtime exceptions.

Unexpected reconcile failures SHALL NOT permanently terminate the supervisor thread for the lifetime of the server process.

Unexpected session-poll failures SHALL NOT permanently terminate the corresponding watch worker unless the tracked session has actually left live authority.

When such failures affect live-state observation, `houmao-server` SHALL surface an explicit error state for that session or otherwise record the failure for operator diagnosis rather than silently ceasing background tracking.

#### Scenario: Reconcile failure does not permanently stop the supervisor
- **WHEN** one reconcile pass raises an unexpected runtime exception while loading or reconciling live known sessions
- **THEN** `houmao-server` records or logs that failure and keeps the supervisor available for later reconcile passes
- **AND THEN** continuous background tracking can resume without restarting the server process

#### Scenario: Session poll failure does not permanently stop the worker
- **WHEN** one watch-worker cycle raises an unexpected runtime exception while polling a still-live tracked session
- **THEN** `houmao-server` records an explicit failure for that session and keeps the worker eligible to poll again on a later cycle
- **AND THEN** one bad poll does not permanently disable live tracking for that session

### Requirement: `houmao-server` removes live-state aliases when a tracked session leaves live authority
The terminal-keyed Houmao live-state routes SHALL resolve only through terminal aliases that remain bound to a currently live known session.

When a tracked session leaves the live known-session registry, loses tmux liveness, or is otherwise released from background watch authority, `houmao-server` SHALL evict the corresponding in-memory worker binding, tracker state, and terminal alias from its live authority maps.

#### Scenario: Tmux loss removes stale live-state authority
- **WHEN** a watched tracked session loses tmux liveness and a later reconcile pass no longer admits that session into the live known-session registry
- **THEN** `houmao-server` removes the corresponding in-memory tracker and terminal alias from live authority
- **AND THEN** terminal-keyed live-state lookup no longer succeeds only from stale in-memory residue

#### Scenario: Registry removal releases the live terminal alias
- **WHEN** a tracked session is removed from the authoritative known-session registry even if an older in-memory tracker still exists
- **THEN** `houmao-server` evicts the existing terminal alias and tracker from the live route authority
- **AND THEN** the live-state routes reflect that the session is no longer known to the server

### Requirement: `houmao-server` preserves tracked pane identity during registration-seeded admission
When `houmao-server` admits a tracked session from its registration bridge, it SHALL preserve available tmux pane-targeting metadata needed to select the intended tracked pane on the first live polling cycles.

That registration-seeded identity SHALL include tmux window metadata when the caller provides it, and `houmao-server` SHALL enrich the identity from manifest-backed metadata during admission when a manifest path is available and the registration payload omits that metadata.

The initial tracker state SHALL use that preserved or enriched pane identity rather than falling back blindly to whichever tmux pane is active for the session.

#### Scenario: Registration-supplied window metadata is used immediately
- **WHEN** a registration request includes tmux window identity for the tracked session
- **THEN** `houmao-server` persists and applies that window identity when creating the initial tracked-session record
- **AND THEN** the first live polling cycles target that registered window instead of choosing an arbitrary active pane

#### Scenario: Manifest-backed window metadata enriches the initial tracker
- **WHEN** a registration request omits tmux window identity but supplies a manifest path whose metadata identifies the tracked tmux window
- **THEN** `houmao-server` enriches the initial tracked-session record from that manifest before the first live polling cycles
- **AND THEN** registration-seeded tracking does not need to wait for a later reconcile pass to recover the correct pane target
