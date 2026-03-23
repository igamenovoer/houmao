## MODIFIED Requirements

### Requirement: Profiles may delegate drift-prone surface regions to behavior variants
The shared versioned TUI profile contract SHALL allow a selected app profile to delegate interpretation of one drift-prone prompt or surface region to a profile-owned behavior variant.

That behavior variant SHALL consume raw snapshot-derived region content and MAY rely on rendering or style evidence, including raw ANSI/SGR state, when stripped text alone is insufficient to classify the region safely.

The behavior variant SHALL return a coarse profile-local classification that the selected profile can translate into normalized tracker signals.

The shared tracker engine SHALL remain unaware of behavior-variant internals and SHALL continue to depend only on the selected profile's normalized outputs.

For prompt-area interpretation, behavior variants SHALL remain profile-private implementation details of the selected app profile rather than separate shared registry entries.

#### Scenario: Codex prompt interpretation is delegated through the selected profile
- **WHEN** the tracker resolves a Codex TUI profile for an observed Codex version
- **AND WHEN** that profile needs to interpret the prompt area for editing semantics
- **THEN** the selected profile may invoke its profile-owned prompt behavior variant for that version family
- **AND THEN** the shared tracker engine still consumes only normalized Codex signals

#### Scenario: Claude prompt interpretation can use style-aware placeholder classification
- **WHEN** the tracker resolves a Claude Code profile for an observed Claude version family
- **AND WHEN** that profile needs to distinguish styled placeholder text from real draft input on the visible prompt line
- **THEN** the selected profile may invoke a profile-owned prompt behavior variant that uses raw prompt rendering and style evidence for that version family
- **AND THEN** the shared tracker engine still consumes only normalized Claude signals

#### Scenario: Drifted prompt behavior is updated without rewriting the shared engine
- **WHEN** a future supported TUI version changes how placeholder and draft content appear in one prompt or surface region
- **THEN** maintainers can update the affected behavior variant or add a new version-family profile that selects a different variant
- **AND THEN** unrelated shared tracker engine logic and other app profiles do not require a coordinated rewrite

#### Scenario: Prompt behavior variants remain profile-private in v1
- **WHEN** the repository introduces or updates version-selected prompt behavior variants for Codex, Claude, or another supported interactive TUI profile
- **THEN** those variants remain owned by the selected app detector profile
- **AND THEN** the shared registry does not grow separate top-level entries for prompt behavior variants in this change
