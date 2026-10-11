# Spec Delta

## ADDED Requirements

### Requirement: Kimi Code profile resolution errors below the support floor
Kimi Code tracker profile resolution SHALL support only kimi-code versions at or above the current qualified floor (2.1.1), through exactly one maintained profile with an open-ended semver floor and no kimi fallback profile. An observed version below the floor, or unparseable version metadata, SHALL produce an explicit unsupported-version error at tracker resolution time naming the observed (or missing) version, the required floor, and the migration action (upgrade kimi-code); no detector SHALL be selected for such a session.

#### Scenario: Kimi at the floor resolves the maintained profile
- **WHEN** the tracker resolves app `kimi_code` with observed version `2.1.1`
- **THEN** resolution selects the maintained kimi 2.1.x profile
- **AND THEN** tracked-state reduction proceeds normally

#### Scenario: Kimi below the floor raises an unsupported-version error
- **WHEN** the tracker resolves app `kimi_code` with observed version `0.34.0`
- **THEN** resolution produces an explicit unsupported-version error naming the observed version and the `2.1.1` floor
- **AND THEN** no kimi detector is selected and no tracked state is manufactured for that session

#### Scenario: Unparseable kimi version raises an unsupported-version error
- **WHEN** the tracker resolves app `kimi_code` with missing or unparseable version metadata
- **THEN** resolution produces the same explicit unsupported-version error surface
- **AND THEN** no fallback detector silently scrapes the surface

### Requirement: Kimi profile carries code-side qualified-version metadata
An observed kimi version above the qualified floor SHALL resolve to the maintained kimi profile silently, without any user-facing warning. The kimi registration and profile SHALL carry developer-visible qualified-version metadata (for example, a `qualified_through_version` field or profile note) recording which kimi version the profile was qualified against.

#### Scenario: Kimi above the qualified floor resolves silently
- **WHEN** the tracker resolves app `kimi_code` with observed version `2.3.0`
- **THEN** resolution selects the maintained kimi 2.1.x profile without a user-facing warning
- **AND THEN** developer-visible profile metadata records the version the profile was qualified through
