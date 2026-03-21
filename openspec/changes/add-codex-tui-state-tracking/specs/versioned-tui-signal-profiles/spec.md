## ADDED Requirements

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
