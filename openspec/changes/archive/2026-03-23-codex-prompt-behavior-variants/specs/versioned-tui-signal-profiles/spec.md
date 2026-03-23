## ADDED Requirements

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
