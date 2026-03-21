## ADDED Requirements

### Requirement: Shared core is scoped to screen-scraped interactive TUI surfaces
The shared tracked-TUI core SHALL model interactive screen-scraped TUI surface contracts rather than structured headless tool protocols.

Supported tracker app families at this boundary SHALL represent visible interactive TUI surfaces whose state must be inferred from raw captured snapshots. Structured upstream machine contracts MAY bypass the shared tracked-TUI core instead of being re-modeled through TUI-reduction rules.

#### Scenario: Interactive TUI surface is admitted to the shared core
- **WHEN** a repo-owned host has raw snapshots from an interactive supported TUI surface
- **THEN** that host may reduce tracked state through the shared tracked-TUI core
- **AND THEN** the shared core treats the app family as a screen-scraped TUI contract rather than a backend-control label

#### Scenario: Structured headless protocol stays outside the shared core
- **WHEN** a repo-owned flow already has a structured upstream machine contract that does not require screen scraping
- **THEN** that flow is not required to model its state through the shared tracked-TUI core
- **AND THEN** the tracked-TUI subsystem does not become the generic state layer for non-TUI headless control paths

### Requirement: Shared core accepts profile-owned temporal hints over sliding recent windows
The shared tracked-TUI core SHALL allow a resolved TUI profile to derive temporal hints from recent ordered snapshots in addition to per-snapshot normalized facts.

Those temporal hints SHALL be profile-owned, SHALL be produced through a separate temporal-hint callback, and MAY use the injected scheduler plus a sliding time window over recent profile frames.

The shared core SHALL own the session-local recent-frame window, SHALL preserve `DetectedTurnSignals` as the single-snapshot signal contract, and SHALL merge separate temporal hints with the current snapshot signals before public state reduction.

The shared core SHALL remain the owner of public tracked-state transitions, settle timers, and the stable public session API.

#### Scenario: Profile contributes temporal active evidence without changing public tracker API
- **WHEN** a supported TUI profile needs recent ordered snapshot history to infer active work correctly
- **THEN** that profile may emit temporal hints into the shared tracked-TUI core
- **AND THEN** callers still use the same public tracker-session API of raw snapshots plus explicit input events

#### Scenario: Sliding recent window is available without caller-managed timestamps
- **WHEN** a supported TUI profile derives temporal hints from a sliding time window over recent snapshots
- **THEN** the shared core can support that profile through its injected scheduler and ordered event stream
- **AND THEN** normal live callers do not need to pass timestamps into the public snapshot API

#### Scenario: Temporal hints remain separate from single-snapshot signals
- **WHEN** a supported TUI profile derives temporal lifecycle evidence from recent frames
- **THEN** that evidence is provided to the shared core through a temporal-hint path that is separate from single-snapshot `DetectedTurnSignals`
- **AND THEN** the shared core explicitly merges those temporal hints before state reduction rather than redefining the meaning of the single-snapshot signal type

### Requirement: Shared core can guard ready-return success with prior armed turn authority
When a tracked-TUI profile models success as a stable ready return, the shared tracked-TUI core SHALL be able to gate success settlement on prior armed turn authority maintained by the session.

That prior armed turn authority MAY come from either an explicit input event or from stronger active-turn evidence that armed the session through surface inference. A ready posture without prior armed turn authority SHALL NOT settle success for that turn.

#### Scenario: Surface-inferred authority supports snapshot-only success settlement
- **WHEN** a supported TUI host replays or streams ordered snapshots without explicit input events
- **AND WHEN** the shared core has already armed the turn through stronger active-turn evidence from those snapshots
- **THEN** a later stable ready-return success may still settle for that turn
- **AND THEN** the shared core does not require explicit input events for all ready-return success cases

#### Scenario: Initial idle ready posture does not settle success
- **WHEN** the newest tracked-TUI snapshot shows a ready posture
- **AND WHEN** the shared session has not armed prior turn authority for that turn
- **THEN** the shared core does not settle the turn as `success`
- **AND THEN** the tracker remains idle or unknown until stronger evidence appears
