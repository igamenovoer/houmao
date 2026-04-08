## ADDED Requirements

### Requirement: Launch profiles may store optional memory-directory intent
The shared launch-profile object family SHALL support optional memory-directory intent as reusable birth-time launch configuration.

At minimum, a launch profile SHALL support these memory-directory authoring outcomes:

- one explicit absolute memory directory path
- explicit disabled memory binding
- no stored memory preference

Launch-profile inspection SHALL report whether the profile stores an explicit absolute path, stores disabled memory binding, or stores no memory preference.

#### Scenario: Launch-profile inspection reports one stored exact memory directory
- **WHEN** launch profile `alice` stores memory directory `/shared/alice-memory`
- **AND WHEN** an operator inspects that launch profile
- **THEN** the inspection output reports `/shared/alice-memory` as profile-owned memory configuration
- **AND THEN** the output distinguishes that stored exact path from disabled or absent memory configuration

#### Scenario: Launch-profile inspection reports explicit disabled memory binding
- **WHEN** launch profile `alice` stores disabled memory binding
- **AND WHEN** an operator inspects that launch profile
- **THEN** the inspection output reports that the profile intentionally disables memory binding
- **AND THEN** the output distinguishes that disabled state from an absent memory preference

### Requirement: Launch-profile memory-directory intent participates in launch precedence
When a managed launch resolves effective memory binding from a launch profile, the system SHALL apply profile-owned memory-directory intent after the system default behavior and before direct launch-time overrides.

Direct `--memory-dir <path>` SHALL override profile-owned disabled memory binding or profile-owned exact-path binding.

Direct `--no-memory-dir` SHALL override any profile-owned memory configuration.

When a launch profile stores no memory preference, the effective launch SHALL fall back to the system default behavior for that launch surface.

#### Scenario: Direct exact-path override wins over a profile that disables memory
- **WHEN** launch profile `alice` stores disabled memory binding
- **AND WHEN** an operator launches from `alice` with `--memory-dir /tmp/alice-memory`
- **THEN** the resulting managed launch uses `/tmp/alice-memory` as the resolved memory directory
- **AND THEN** the stored launch profile still records disabled memory binding as its reusable default

#### Scenario: Absent profile memory configuration falls back to the system default
- **WHEN** launch profile `alice` stores no memory preference
- **AND WHEN** an operator launches from `alice` without `--memory-dir` or `--no-memory-dir`
- **THEN** the resulting managed launch resolves memory binding from the launch surface's system default behavior
- **AND THEN** the launch profile is not treated as disabling memory only because it omitted that field
