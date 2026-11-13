## MODIFIED Requirements

### Requirement: Kimi Code TUI has a versioned shared signal profile
The shared versioned TUI profile registry SHALL include a Kimi Code TUI app family identified as `kimi_code`.

The Kimi app profile SHALL convert raw Kimi TUI snapshot text into normalized shared tracker signals for prompt readiness, draft editing, active-turn evidence, success-candidate posture, approval-blocked posture, interruption, and known terminal failure families when those families are specifically recognized.

The maintained Kimi Code profile SHALL resolve for every observed version at or above 2.1.1 with no upper version limit. Labeled evidence at the current qualified floor SHALL establish the baseline signal contract; cancellation of change-local capture or replay tasks SHALL NOT count as qualification evidence. Below-floor Kimi profiles SHALL NOT remain selectable as maintained or compatibility profiles.

#### Scenario: Kimi tool resolves to Kimi tracker app id
- **WHEN** the shared tracker is constructed for tool `kimi` at version 2.1.1 or later
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

#### Scenario: Below-floor Kimi has no maintained profile
- **WHEN** tracking observes a Kimi version earlier than 2.1.1
- **THEN** the registry does not select a maintained Kimi profile
- **AND THEN** the caller receives an unsupported-version result rather than legacy compatibility

### Requirement: Current Codex, Kimi, and Claude releases have evidence-backed profiles
The registry SHALL provide a Codex 0.162.x profile qualified against labeled Codex 0.162.1 recordings, a Kimi 2.1.x profile qualified against labeled kimi-code 2.1.1 recordings, and a Claude 2.1.x profile qualified against labeled Claude 2.1.296 recordings. Older Codex 0.116.x and 0.144.x profiles SHALL NOT remain registered because Codex support is floor-gated at 0.162.1 with no fallback; older Kimi profiles SHALL NOT remain registered because Kimi support is floor-gated at 2.1.1 with no fallback; older Claude profiles qualified around 2.1.81 SHALL NOT remain registered because Claude support is floor-gated at 2.1.296 with no fallback.

#### Scenario: Current installed tools resolve current profiles
- **WHEN** tracking observes Codex 0.162.1, Kimi 2.1.1, or Claude 2.1.296
- **THEN** it selects the matching current-version profile
- **AND THEN** detector provenance reports that current profile version

#### Scenario: Old Kimi recording cannot qualify current support
- **WHEN** only a Kimi recording from below the current 2.1.1 support floor exists for a detector rule
- **THEN** that recording does not qualify the maintained minimum-only Kimi profile
- **AND THEN** qualification requires labeled evidence at or above the current floor

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

#### Scenario: Newer Kimi release uses the maintained floor profile
- **WHEN** tracking observes a parseable Kimi version above the current 2.1.1 support floor
- **THEN** the registry selects the maintained minimum-only Kimi profile
- **AND THEN** the registry retains developer-visible qualified-version metadata without imposing an upper compatibility bound
