# Spec Delta

## MODIFIED Requirements

### Requirement: Versioned TUI profile compatibility is bounded
Each maintained detector registration SHALL define the version interval supported by its recorded evidence, either as a bounded interval or as an open-ended floor for a maintained minimum-only registration. The registry SHALL select a profile only when the observed CLI version falls inside that interval.

Versions in gaps or outside every maintained interval SHALL resolve to the conservative app fallback when the app registers one; an app with a floor-gated maintained profile and no fallback (currently `kimi_code` and `codex_tui`) SHALL raise an explicit unsupported-version error instead. An explicit experimental override MAY bypass interval matching.

#### Scenario: Newer unvalidated CLI uses fallback
- **WHEN** an observed TUI version is newer than the maximum validated version of every maintained profile for an app that registers a fallback
- **THEN** the registry selects the app's conservative fallback profile
- **AND THEN** it does not silently label the oldest semver-floor profile as compatible

#### Scenario: Below-floor version for a fallback-less app raises
- **WHEN** an observed TUI version falls below the floor of an app that registers no fallback
- **THEN** resolution raises an explicit unsupported-version error naming the observed version and the floor
- **AND THEN** no detector is selected for that session

### Requirement: Current Codex and Kimi releases have evidence-backed profiles
The registry SHALL provide a Codex 0.162.x profile qualified against labeled Codex 0.162.1 recordings and a Kimi 2.1.x profile qualified against labeled kimi-code 2.1.1 recordings. Older Codex 0.116.x and 0.144.x profiles SHALL NOT remain registered because Codex support is floor-gated at 0.162.1 with no fallback; older Kimi profiles SHALL NOT remain registered because Kimi support is floor-gated at 2.1.1 with no fallback.

#### Scenario: Current installed tools resolve current profiles
- **WHEN** tracking observes Codex 0.162.1 or Kimi 2.1.1
- **THEN** it selects the matching current-version profile
- **AND THEN** detector provenance reports that current profile version

## ADDED Requirements

### Requirement: Codex profile resolution errors below the support floor
Codex tracker profile resolution SHALL support only codex at or above the qualified floor (0.162.1), through exactly one maintained profile with an open-ended semver floor and no codex fallback. An observed version below the floor, or unparseable version metadata, SHALL produce an explicit unsupported-version error at tracker resolution naming the observed (or missing) version, the floor, and the migration action (upgrade codex); no detector SHALL be selected for such a session.

#### Scenario: Codex at the floor resolves the maintained profile
- **WHEN** the tracker resolves app `codex_tui` with observed version `0.162.1`
- **THEN** resolution selects the maintained codex 0.162.x profile
- **AND THEN** tracked-state reduction proceeds normally

#### Scenario: Codex below the floor raises an unsupported-version error
- **WHEN** the tracker resolves app `codex_tui` with observed version `0.144.0`
- **THEN** resolution produces an explicit unsupported-version error naming the observed version and the `0.162.1` floor
- **AND THEN** no codex detector is selected and no tracked state is manufactured for that session

#### Scenario: Unparseable codex version raises an unsupported-version error
- **WHEN** the tracker resolves app `codex_tui` with missing or unparseable version metadata
- **THEN** resolution produces the same explicit unsupported-version error surface
- **AND THEN** no fallback detector silently scrapes the surface

### Requirement: Codex profile carries code-side qualified-version metadata
An observed codex version above the qualified floor SHALL resolve to the maintained codex profile silently, without any user-facing warning. The codex registration and profile SHALL carry developer-visible qualified-version metadata (for example, a `qualified_through_version` field or profile note) recording which codex version the profile was qualified against.

#### Scenario: Codex above the qualified floor resolves silently
- **WHEN** the tracker resolves app `codex_tui` with observed version `0.163.0`
- **THEN** resolution selects the maintained codex 0.162.x profile without a user-facing warning
- **AND THEN** developer-visible profile metadata records the version the profile was qualified through
