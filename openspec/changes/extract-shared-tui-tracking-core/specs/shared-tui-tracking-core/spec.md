## ADDED Requirements

### Requirement: Shared core reduces normalized observations into the official tracked-state model
The repository SHALL provide a reusable tracked-state core outside server, demo, and replay-adapter ownership.

That shared core SHALL consume normalized parsed observations together with optional diagnostics and input-authority evidence and SHALL emit tracked-state snapshots aligned with the official tracked-state vocabulary for diagnostics posture, `surface`, `turn`, `last_turn`, and stability semantics.

#### Scenario: Live and replay adapters consume the same tracked-state core
- **WHEN** live server tracking and offline replay process semantically equivalent observation streams
- **THEN** both adapters can invoke the same shared tracked-state core
- **AND THEN** both receive tracked-state snapshots expressed in the same official vocabulary

### Requirement: Shared core remains independent of server, demo, and recorder adapters
The shared tracked-state core SHALL NOT depend on `houmao.server`, `houmao.demo`, or `houmao.terminal_record` adapter implementations.

Tool-specific live, replay, or dashboard adapters MAY depend on the shared core, but the dependency direction SHALL not point back upward into those adapters.

Reference demos MAY keep separate tracker implementations and SHALL NOT be required to consume the shared core merely to preserve implementation uniformity.

#### Scenario: Generic replay analyzer imports shared core without server or demo ownership
- **WHEN** a generic replay analyzer imports the shared tracked-state core
- **THEN** that import does not require importing live server adapters or demo dashboards
- **AND THEN** package initialization does not rely on server or demo runtime modules to construct tracked-state reducers

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
