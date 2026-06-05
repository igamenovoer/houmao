## ADDED Requirements

### Requirement: Kimi Code TUI has a versioned shared signal profile
The shared versioned TUI profile registry SHALL include a Kimi Code TUI app family identified as `kimi_code`.

The Kimi app profile SHALL convert raw Kimi TUI snapshot text into normalized shared tracker signals for prompt readiness, draft editing, active-turn evidence, success-candidate posture, approval-blocked posture, interruption, and known terminal failure families when those families are specifically recognized.

The profile SHALL resolve observed Kimi versions through the same versioned profile selection contract used by other supported TUI apps.

#### Scenario: Kimi tool resolves to Kimi tracker app id
- **WHEN** the shared tracker is constructed for tool `kimi`
- **THEN** the tracker resolves the supported TUI app family as `kimi_code`
- **AND THEN** it does not use the `kimi_headless` backend name as the tracker app id

#### Scenario: Kimi idle snapshot emits ready posture
- **WHEN** the Kimi profile receives a raw snapshot with the Kimi editor prompt ready and no current active or blocking surface
- **THEN** it emits normalized ready-posture signals for the shared tracker

#### Scenario: Kimi approval snapshot emits blocked posture
- **WHEN** the Kimi profile receives a raw snapshot with a current command approval dialog
- **THEN** it emits normalized blocking evidence rather than ready-posture evidence

#### Scenario: Kimi active snapshot emits active evidence
- **WHEN** the Kimi profile receives a raw snapshot with current response activity, spinner evidence, or a current tool-use surface
- **THEN** it emits normalized active-turn evidence for the shared tracker

#### Scenario: Kimi footer thinking text is ignored as activity evidence
- **WHEN** the Kimi profile receives a raw snapshot whose only thinking-like text is footer model metadata
- **THEN** it does not emit active-turn evidence solely from that footer text

