# Spec Delta

## RENAMED Requirements

- FROM: `Current Codex and Kimi releases have evidence-backed profiles`
  TO: `Current Codex, Kimi, and Claude releases have evidence-backed profiles`

## REMOVED Requirements

### Requirement: Claude pending-input detection uses bounded structure and rendering semantics rather than suggestion literals
**Reason**: The requirement's queued-preview ghost-cell structure (an indented, semantically styled user-input cell inspected against intervening cells above the composer) is dead at claude 2.1.296: the queue surface moved into the composer's own placeholder payload. Its scenarios pin a structure that no longer renders.
**Migration**: Replaced by `Claude pending-input detection uses the queued composer placeholder`, which reads the bounded queue-editing hint label on the current composer payload.

## MODIFIED Requirements

### Requirement: Versioned TUI profile compatibility is bounded
Each maintained detector registration SHALL define the version interval supported by its recorded evidence, either as a bounded interval or as an open-ended floor for a maintained minimum-only registration. The registry SHALL select a profile only when the observed CLI version falls inside that interval.

Versions in gaps or outside every maintained interval SHALL resolve to the conservative app fallback when the app registers one; an app with a floor-gated maintained profile and no fallback (currently `kimi_code`, `codex_tui`, and `claude_code`) SHALL raise an explicit unsupported-version error instead. An explicit experimental override MAY bypass interval matching.

#### Scenario: Newer unvalidated CLI uses fallback
- **WHEN** an observed TUI version is newer than the maximum validated version of every maintained profile for an app that registers a fallback
- **THEN** the registry selects the app's conservative fallback profile
- **AND THEN** it does not silently label the oldest semver-floor profile as compatible

#### Scenario: Below-floor version for a fallback-less app raises
- **WHEN** an observed TUI version falls below the floor of an app that registers no fallback
- **THEN** resolution raises an explicit unsupported-version error naming the observed version and the floor
- **AND THEN** no detector is selected for that session

### Requirement: Current Codex and Kimi releases have evidence-backed profiles
The registry SHALL provide a Codex 0.162.x profile qualified against labeled Codex 0.162.1 recordings, a Kimi 2.1.x profile qualified against labeled kimi-code 2.1.1 recordings, and a Claude 2.1.x profile qualified against labeled Claude 2.1.296 recordings. Older Codex 0.116.x and 0.144.x profiles SHALL NOT remain registered because Codex support is floor-gated at 0.162.1 with no fallback; older Kimi profiles SHALL NOT remain registered because Kimi support is floor-gated at 2.1.1 with no fallback; older Claude profiles qualified around 2.1.81 SHALL NOT remain registered because Claude support is floor-gated at 2.1.296 with no fallback.

#### Scenario: Current installed tools resolve current profiles
- **WHEN** tracking observes Codex 0.162.1, Kimi 2.1.1, or Claude 2.1.296
- **THEN** it selects the matching current-version profile
- **AND THEN** detector provenance reports that current profile version

## ADDED Requirements

### Requirement: Claude pending-input detection uses the queued composer placeholder
For supported Claude Code profiles, pending-input detection SHALL read the queue state from the current composer's own placeholder payload: `pending_input=yes` when the placeholder carries the bounded queue-editing hint label (`Press up to edit queued messages`), and `pending_input=no` on a complete composer without the hint or on a blocked no-composer surface. The dead queued-preview ghost-cell structure SHALL NOT be used as pending-input evidence.

#### Scenario: Queued placeholder reports pending input
- **WHEN** a Claude turn is active and the composer placeholder payload carries the queue-editing hint label
- **THEN** the selected Claude profile emits `pending_input=yes`
- **AND THEN** the read needs no ghost-cell structure above the composer

#### Scenario: Placeholder-free composer reports no pending input
- **WHEN** the composer is visible with an empty, suggestion, or draft payload and no queue-editing hint
- **THEN** the selected Claude profile emits `pending_input=no`

#### Scenario: Missing composer reports blocked, not unknown
- **WHEN** no Claude composer is visible in the captured surface
- **THEN** the selected Claude profile emits `pending_input=no` along with the other blocked surface booleans

### Requirement: Claude profile resolution errors below the support floor
Claude tracker profile resolution SHALL support only claude at or above the qualified floor (2.1.296), through exactly one maintained profile with an open-ended semver floor and no claude fallback. An observed version below the floor, or unparseable version metadata, SHALL produce an explicit unsupported-version error at tracker resolution naming the observed (or missing) version, the floor, and the migration action (upgrade claude); no detector SHALL be selected for such a session.

#### Scenario: Claude at the floor resolves the maintained profile
- **WHEN** the tracker resolves app `claude_code` with observed version `2.1.296`
- **THEN** resolution selects the maintained claude 2.1.x profile
- **AND THEN** tracked-state reduction proceeds normally

#### Scenario: Claude below the floor raises an unsupported-version error
- **WHEN** the tracker resolves app `claude_code` with observed version `2.1.81`
- **THEN** resolution produces an explicit unsupported-version error naming the observed version and the `2.1.296` floor
- **AND THEN** no claude detector is selected and no tracked state is manufactured for that session

#### Scenario: Unparseable claude version raises an unsupported-version error
- **WHEN** the tracker resolves app `claude_code` with missing or unparseable version metadata
- **THEN** resolution produces the same explicit unsupported-version error surface
- **AND THEN** no fallback detector silently scrapes the surface

### Requirement: Claude profile carries code-side qualified-version metadata
An observed claude version above the qualified floor SHALL resolve to the maintained claude profile silently, without any user-facing warning. The claude registration and profile SHALL carry developer-visible qualified-version metadata (for example, a `qualified_through_version` field or profile note) recording which claude version the profile was qualified against.

#### Scenario: Claude above the qualified floor resolves silently
- **WHEN** the tracker resolves app `claude_code` with observed version `2.1.300`
- **THEN** resolution selects the maintained claude 2.1.x profile without a user-facing warning
- **AND THEN** developer-visible profile metadata records the version the profile was qualified through
