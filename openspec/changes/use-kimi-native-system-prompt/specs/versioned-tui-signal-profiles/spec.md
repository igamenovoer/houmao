## MODIFIED Requirements

### Requirement: Kimi Code TUI has a versioned shared signal profile
The shared versioned TUI profile registry SHALL include a Kimi Code TUI app family identified as `kimi_code`.

The Kimi app profile SHALL convert raw Kimi TUI snapshot text into normalized shared tracker signals for prompt readiness, draft editing, active-turn evidence, success-candidate posture, approval-blocked posture, interruption, and known terminal failure families when those families are specifically recognized.

The maintained Kimi Code profile SHALL resolve for every observed version at or above 0.34.0 with no upper version limit. Labeled 0.34.x corpus evidence SHALL establish the baseline signal contract. Pre-0.34 Kimi profiles SHALL NOT remain selectable as maintained or compatibility profiles.

#### Scenario: Kimi tool resolves to Kimi tracker app id
- **WHEN** the shared tracker is constructed for tool `kimi` at version 0.34.0 or later
- **THEN** the tracker resolves the supported TUI app family as `kimi_code`
- **AND THEN** it does not use the `kimi_headless` backend name as the tracker app id

#### Scenario: Kimi idle snapshot emits ready posture
- **WHEN** the maintained Kimi profile receives a raw snapshot with the editor prompt ready and no current active or blocking surface
- **THEN** it emits normalized ready-posture signals for the shared tracker

#### Scenario: Kimi approval snapshot emits blocked posture
- **WHEN** the maintained Kimi profile receives a raw snapshot with a current command approval dialog
- **THEN** it emits normalized blocking evidence rather than ready-posture evidence

#### Scenario: Kimi active snapshot emits active evidence
- **WHEN** the maintained Kimi profile receives a raw snapshot with current response activity, spinner evidence, or a current tool-use surface
- **THEN** it emits normalized active-turn evidence for the shared tracker

#### Scenario: Kimi footer thinking text is ignored as activity evidence
- **WHEN** the maintained Kimi profile receives a raw snapshot whose only thinking-like text is footer model metadata
- **THEN** it does not emit active-turn evidence solely from that footer text

#### Scenario: Pre-0.34 Kimi has no maintained profile
- **WHEN** tracking observes a Kimi version earlier than 0.34.0
- **THEN** the registry does not select a maintained Kimi profile
- **AND THEN** the caller receives an unsupported-version result rather than legacy compatibility

### Requirement: Current Codex and Kimi releases have evidence-backed profiles
The registry SHALL provide a Codex 0.144.x profile derived from labeled Codex 0.144.x recordings and a Kimi `>=0.34.0` profile whose baseline evidence comes from labeled Kimi 0.34.x recordings. Kimi profiles for releases earlier than 0.34.0 SHALL be removed from the supported registry rather than retained behind upper bounds.

#### Scenario: Current installed tools resolve current profiles
- **WHEN** tracking observes Codex 0.144.x or any Kimi version at or above 0.34.0
- **THEN** it selects the matching current-version profile
- **AND THEN** detector provenance reports that current profile version

#### Scenario: Old Kimi recording cannot qualify current support
- **WHEN** only a Kimi 0.23.x or earlier labeled recording exists for a detector rule
- **THEN** that evidence does not qualify the `>=0.34.0` maintained profile
- **AND THEN** support remains incomplete until 0.34.x evidence exists

### Requirement: Versioned TUI profile compatibility is bounded
Each maintained detector registration SHALL define the version range supported by its contract. Registrations MAY use a finite interval or a minimum-only interval. The maintained Kimi registration SHALL use `>=0.34.0` with no upper version limit; other providers MAY retain finite evidence bounds.

Versions in gaps or below a minimum SHALL resolve to the conservative app fallback unless an explicit experimental override is used. A Kimi version newer than the baseline 0.34.x evidence SHALL continue to resolve the maintained Kimi profile.

#### Scenario: Newer unvalidated CLI uses fallback
- **WHEN** an observed non-Kimi TUI version is newer than the maximum validated version of every maintained finite-range profile
- **THEN** the registry selects the app's conservative fallback profile
- **AND THEN** it does not silently label a finite semver-floor profile as compatible

#### Scenario: Newer Kimi release uses the maintained floor profile
- **WHEN** tracking observes a parseable Kimi version later than 0.34.x
- **THEN** the registry selects the maintained `>=0.34.0` Kimi profile
- **AND THEN** detector provenance reports the minimum-only profile contract and its baseline evidence
