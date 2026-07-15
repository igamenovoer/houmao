## ADDED Requirements

### Requirement: Versioned TUI profile compatibility is bounded
Each maintained detector registration SHALL define the version interval supported by its recorded evidence. The registry SHALL select a profile only when the observed CLI version falls inside that interval; a semver floor SHALL NOT imply indefinite compatibility with every newer version.

Versions in gaps or above the newest validated interval SHALL resolve to the conservative app fallback unless an explicit experimental override is used.

#### Scenario: Newer unvalidated CLI uses fallback
- **WHEN** an observed TUI version is newer than the maximum validated version of every maintained profile
- **THEN** the registry selects the app's conservative fallback profile
- **AND THEN** it does not silently label the oldest semver-floor profile as compatible

### Requirement: Current Codex and Kimi releases have evidence-backed profiles
The registry SHALL provide a Codex 0.144.x profile derived from labeled Codex 0.144.x recordings and a Kimi 0.23.x profile derived from labeled Kimi 0.23.x recordings. Older Codex 0.116.x and Kimi 0.11.x profiles MAY remain registered only with upper bounds matching their evidence.

#### Scenario: Current installed tools resolve current profiles
- **WHEN** tracking observes Codex 0.144.x or Kimi 0.23.x
- **THEN** it selects the matching current-version profile
- **AND THEN** detector provenance reports that current profile version

