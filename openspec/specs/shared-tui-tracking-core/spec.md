# shared-tui-tracking-core Specification

## Purpose
Define the repo-owned shared tracked-TUI core for the official/runtime path, including neutral tracked-state models, reducer semantics, detector ownership, and explicit-input authority handling.

## Requirements

### Requirement: Shared core exposes a raw-snapshot tracker session for tracker-owned state
The repository SHALL provide a reusable tracked-state core outside server, demo, replay-adapter, and recorder ownership.

That shared core SHALL expose a thread-safe standalone tracker-session boundary whose public input surface is limited to raw TUI snapshot strings together with explicit input-authority evidence.

That session boundary SHALL provide, at minimum:

- `on_snapshot(raw_text: str) -> None`
- `on_input_submitted() -> None`
- `current_state() -> TrackedStateSnapshot`
- `drain_events() -> list[TrackedStateTransition]`

That shared core SHALL emit tracker-owned state aligned with the official tracked-state vocabulary for `surface`, `turn`, `last_turn`, detector identity, and tracker-state stability semantics. It SHALL NOT require callers to pass parsed-surface context, transport/process diagnostics, or timestamps on normal live snapshot delivery.

The shared core SHALL own timer-driven transitions such as settle windows internally through Rx and an injected scheduler rather than requiring normal live callers to pass timestamps on every snapshot event.

#### Scenario: Live and replay adapters consume the same tracked-state core
- **WHEN** live server tracking and offline replay process semantically equivalent raw TUI snapshot streams
- **THEN** both adapters can invoke the same shared tracked-state core through the same tracker-session contract
- **AND THEN** both receive tracked-state snapshots expressed in the same official vocabulary
- **AND THEN** live hosts may use a realtime scheduler while replay hosts may use a virtual scheduler without changing the shared state-machine contract

#### Scenario: Generic host feeds raw snapshots without source-specific contracts
- **WHEN** a repo-owned host feeds raw TUI strings from tmux, a recorded artifact, or another capture source into the shared tracker
- **THEN** the shared core accepts that input without requiring tmux-specific, recorder-specific, or server-owned snapshot models
- **AND THEN** the resulting tracked-state semantics do not depend on the capture source being tmux

#### Scenario: Externally captured direct tmux pane text is accepted unchanged
- **WHEN** a host captures one pane snapshot directly from tmux and supplies that raw pane text to the shared tracker
- **THEN** the shared core accepts that direct tmux-captured string through the normal snapshot API without requiring a tmux-specific input type
- **AND THEN** app/profile detection runs against that externally captured raw string rather than requiring a host-side semantic normalization pass

#### Scenario: Concurrent readers and writers use the same tracker session safely
- **WHEN** one repo-owned caller feeds snapshots or input events while another caller reads current state or drains transition events
- **THEN** the shared core permits those public operations without requiring single-threaded caller discipline
- **AND THEN** the resulting tracker state and emitted events still reflect one coherent internal reduction order

### Requirement: Shared core remains independent of server, demo, and recorder adapters
The shared tracked-state core SHALL NOT depend on `houmao.server`, `houmao.demo`, or `houmao.terminal_record` adapter implementations.

Tool-specific live, replay, or dashboard adapters MAY depend on the shared core, but the dependency direction SHALL not point back upward into those adapters.

Reference demos MAY keep separate tracker implementations and SHALL NOT be required to consume the shared core merely to preserve implementation uniformity.

The shared core SHALL also remain independent of transport ownership. It SHALL NOT embed tmux discovery, process probing, host lifecycle readiness/completion pipelines, snapshot persistence, or HTTP-route semantics into the tracker contract.

#### Scenario: Generic replay analyzer imports shared core without server or demo ownership
- **WHEN** a generic replay analyzer imports the shared tracked-state core
- **THEN** that import does not require importing live server adapters or demo dashboards
- **AND THEN** package initialization does not rely on server or demo runtime modules to construct tracked-state reducers

#### Scenario: Non-tmux host uses the same shared tracker boundary
- **WHEN** a repo-owned host that is not tmux-backed needs tracked-TUI reduction over captured raw strings
- **THEN** that host can consume the shared tracker without first pretending to be a tmux or terminal-recorder adapter
- **AND THEN** the shared core does not require tmux lifecycle or recorder artifact ownership to function

#### Scenario: Host parser metadata remains outside the public tracker boundary
- **WHEN** a repo-owned host already computes parsed-surface metadata for other subsystems
- **THEN** that host still invokes the shared tracker through raw snapshot and explicit-input events only
- **AND THEN** parsed-surface metadata remains host-owned rather than becoming required tracker input

#### Scenario: Host lifecycle monitoring remains outside the shared core
- **WHEN** a live host also computes readiness or completion state from parsed surfaces or transport/process diagnostics
- **THEN** that lifecycle monitoring can remain outside the shared tracker session
- **AND THEN** the shared core does not require `LifecycleObservation`-style host diagnostics to reduce tracker-owned turn state

#### Scenario: Independent reference demo remains separate from the shared core
- **WHEN** the repository maintains a demo intended to show the correct tracking approach independently from the official/runtime implementation
- **THEN** that demo may keep its own tracker implementation
- **AND THEN** the shared core does not require the demo to become an adapter over official/runtime tracking code

### Requirement: Shared core owns the official/runtime detector boundary
The shared official/runtime tracking stack SHALL own the detector boundary used by live server tracking, recorder replay, and harness replay for supported tools.

Bundled detector implementations used by that official/runtime path SHALL live at or below the shared-core boundary and SHALL NOT import from `houmao.server` or `houmao.explore` adapter packages.

Reference or validation paths MAY keep separate detector implementations when they are intentionally modeling an independent groundtruth or demo/reference path rather than the official/runtime reducer.

#### Scenario: Official/runtime replay and live tracking select detectors without upward adapter imports
- **WHEN** the repository selects a supported-tool detector for live tracking, recorder replay, or harness replay
- **THEN** it resolves that detector from the shared official/runtime detector boundary
- **AND THEN** that path does not require importing `houmao.server` or `houmao.explore` adapter modules

#### Scenario: Groundtruth path may keep a separate detector implementation
- **WHEN** the explore harness computes its independent content-first groundtruth timeline
- **THEN** it may use a separate detector implementation outside the shared official/runtime detector boundary
- **AND THEN** that separate detector does not become the implementation dependency for live or replay tracked-state reduction

### Requirement: Shared core supports explicit-input and inferred turn authority
The shared tracked-state core SHALL allow callers to supply explicit prompt-submission evidence when authoritative input events are available, and SHALL otherwise support surface-inference reduction when only parsed surface observations exist.

When that input evidence is available, the emitted tracked-state output SHALL preserve whether the last completed turn came from explicit input or surface inference.

#### Scenario: Active-mode replay preserves explicit-input turn source
- **WHEN** replay artifacts include authoritative managed input events for a recorded turn
- **THEN** the shared core can arm turn authority from that input evidence
- **AND THEN** the resulting tracked-state output can report `last_turn.source=explicit_input` for the completed turn

#### Scenario: Passive replay degrades to inferred or unknown turn source
- **WHEN** replay artifacts contain only pane snapshots without authoritative input events
- **THEN** the shared core reduces the run without requiring explicit input authority
- **AND THEN** the resulting tracked-state output uses `surface_inference` or `none` rather than fabricating explicit-input provenance

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
