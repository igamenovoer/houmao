## MODIFIED Requirements

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
