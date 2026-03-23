## ADDED Requirements

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
