## Purpose
Define the shared plugin/profile contract for versioned raw-text TUI signal detection across supported tracker apps.

## Requirements

### Requirement: Supported TUI apps share one plugin and profile contract
The repository SHALL provide one shared plugin/profile contract for official/runtime tracked-TUI detection across supported TUI apps.

That contract SHALL allow each supported app to register:

- an app identifier,
- one or more versioned profiles,
- exact-match or closest-compatible semver-floor profile resolution from observed version metadata, and
- a detection entrypoint that converts one raw TUI snapshot into normalized signals for the shared tracker engine.

The shared tracker boundary SHALL resolve supported apps through this contract rather than through public `tool == ...` branching alone. It SHALL NOT require direct dependency on parser/backend preset registries to resolve tracker profiles.

#### Scenario: Claude Code and Codex use the same tracker extension boundary
- **WHEN** the repository tracks one Claude Code session and one Codex session through the official/runtime tracker
- **THEN** both sessions use the same shared plugin/profile contract to resolve detection behavior
- **AND THEN** the shared tracker engine does not require a separate state-machine implementation per app

### Requirement: Versioned profiles encapsulate app-specific detector suites
Each supported TUI app SHALL be able to define multiple versioned signal profiles under the shared plugin/profile contract.

Each profile SHALL encapsulate the signal-detector set used for that app/version family, and the shared tracker engine SHALL depend only on the profile's normalized detection result rather than on app-specific detector internals.

Profile detection at the shared tracker boundary SHALL derive normalized signals from raw snapshot text, including externally captured direct tmux pane text. Host-provided parsed-surface context SHALL NOT be required by the public tracker contract.

#### Scenario: Closest-compatible profile is selected for an observed version
- **WHEN** the tracker is constructed for a supported app with an observed version that does not require an exact profile match
- **THEN** the plugin resolves the closest-compatible profile for that version
- **AND THEN** the tracker can continue reducing state without requiring a profile per exact patch version

#### Scenario: Host parser metadata is not required for profile detection
- **WHEN** a host already has parser-produced surface metadata for unrelated subsystems
- **THEN** the shared tracker still invokes the selected profile from raw snapshot text alone
- **AND THEN** the host does not need to pass parsed-surface context into the public tracker session

### Requirement: Profile-owned signal evidence remains encapsulated from the shared engine
Signal rules that are specific to one app or version family SHALL remain encapsulated inside that app's selected profile rather than being spread across the shared tracker engine.

The shared engine SHALL consume normalized signals such as active-turn evidence, interruption, known-failure, success-candidate posture, and ready posture, while profile-owned matched-signal details MAY remain available as debugging or testing evidence.
Those profile-owned matched-signal details SHALL NOT be required in the stable public tracker state contract initially.

#### Scenario: Signal drift is corrected by updating a profile rather than the engine
- **WHEN** a supported TUI app changes one visible signal pattern in a new version family
- **THEN** maintainers can update the affected profile-owned detector suite
- **AND THEN** the shared tracker engine does not need an unrelated state-machine rewrite to absorb that drift

### Requirement: Profiles may delegate drift-prone surface regions to behavior variants
The shared versioned TUI profile contract SHALL allow a selected app profile to delegate interpretation of one drift-prone surface region to a profile-owned behavior variant.

That behavior variant SHALL consume raw snapshot-derived region content and return a coarse profile-local classification that the selected profile can translate into normalized tracker signals.

The shared tracker engine SHALL remain unaware of behavior-variant internals and SHALL continue to depend only on the selected profile's normalized outputs.

For v1 Codex prompt-area interpretation, that prompt behavior variant SHALL remain a profile-private implementation detail of the selected Codex detector profile rather than a second shared registry entry.

#### Scenario: Codex prompt interpretation is delegated through the selected profile
- **WHEN** the tracker resolves a Codex TUI profile for an observed Codex version
- **AND WHEN** that profile needs to interpret the prompt area for editing semantics
- **THEN** the selected profile may invoke its profile-owned prompt behavior variant for that version family
- **AND THEN** the shared tracker engine still consumes only normalized Codex signals

#### Scenario: Drifted prompt behavior is updated without rewriting the shared engine
- **WHEN** a future Codex version changes how placeholder and draft content appear in the prompt area
- **THEN** maintainers can update the affected Codex prompt behavior variant or add a new version-family profile that selects a different variant
- **AND THEN** unrelated shared tracker engine logic and other app profiles do not require a coordinated rewrite

#### Scenario: Codex prompt behavior variants remain profile-private in v1
- **WHEN** the repository introduces version-selected prompt behavior variants for Codex prompt-area interpretation
- **THEN** those variants remain owned by the selected Codex detector profile
- **AND THEN** the shared registry does not grow separate top-level entries for prompt behavior variants in this change

### Requirement: Tracker app identifiers describe interactive TUI surface families
Tracker app identifiers under the shared profile contract SHALL describe interactive TUI surface families rather than runtime backend names.

For tools that offer both interactive TUI and structured headless control modes, the tracked-TUI profile contract SHALL identify only the interactive surface family that is actually reduced from raw snapshots.

Changing a tracker app identifier SHALL NOT by itself require renaming runtime/backend identifiers that remain outside the tracked-TUI subsystem.

#### Scenario: Codex interactive TUI uses a surface-family app id
- **WHEN** the repository resolves the standalone tracker profile for an interactive Codex TUI session
- **THEN** it resolves that session through a TUI surface-family identifier such as `codex_tui`
- **AND THEN** it does not use a headless backend name as the tracker app identifier

#### Scenario: Headless backend naming does not define tracked-TUI app families
- **WHEN** a runtime backend name exists for a headless or structured Codex control mode
- **THEN** that backend name does not by itself become a tracked-TUI app family in the shared profile registry
- **AND THEN** the tracked-TUI profile contract remains scoped to visible interactive surfaces

#### Scenario: Tracker app-family rename does not imply backend rename
- **WHEN** the tracked-TUI subsystem renames a tracker-facing app identifier from a backend-leaking label to a surface-family label
- **THEN** that rename applies to tracker-facing registry resolution, docs, and tests for the tracked-TUI subsystem
- **AND THEN** runtime/backend identifiers outside the tracked-TUI subsystem remain unchanged unless a separate change targets them

### Requirement: Profiles may contribute temporal hint logic over sliding recent windows
The shared profile contract SHALL allow a profile to contribute temporal hint logic in addition to single-snapshot analysis.

That temporal hint logic SHALL be exposed through a separate temporal-hint callback rather than by changing the meaning of the single-snapshot signal contract.

The temporal callback MAY consume recent ordered profile frames and the injected scheduler to derive profile-owned lifecycle hints from a sliding time window. The contract SHALL NOT require profiles to rely on adjacent-snapshot comparison only.

Profile-specific frame details such as latest-turn-region signatures MAY remain private to the selected profile in v1 rather than widening the shared normalized-signal contract.

#### Scenario: Single-snapshot and temporal profile logic coexist under one profile
- **WHEN** a supported TUI app needs both current-surface matching and recent-window inference
- **THEN** the selected profile may provide both forms of logic under the same shared app/profile contract
- **AND THEN** the shared tracker engine still consumes only normalized profile outputs

#### Scenario: Sliding recent-window inference is preferred over pairwise-only assumptions
- **WHEN** a supported TUI app cannot safely infer state from pairwise-only snapshot comparison because snapshot cadence is externally controlled
- **THEN** its selected profile may use a sliding recent time window for temporal inference
- **AND THEN** the contract does not require profile logic to assume fixed snapshot frequency

#### Scenario: Separate temporal-hint callback preserves the single-snapshot signal contract
- **WHEN** a selected profile derives temporal lifecycle evidence from recent frames
- **THEN** it emits that evidence through a separate temporal-hint callback instead of overloading single-snapshot `DetectedTurnSignals`
- **AND THEN** the shared tracker can trace snapshot facts and temporal hints as distinct inputs before merging them
