## ADDED Requirements

### Requirement: Kimi official tracking support SHALL be verified from recorded evidence
Before official live TUI tracking reports Kimi Code TUI as a maintained supported surface, Kimi parser and tracker behavior SHALL be verified against the labeled recorded Kimi signal corpus.

The verification SHALL include public tracked-state output and any parser-owned sidecar state used to expose operator-facing Kimi readiness or approval posture.

The verification SHALL include held-out Kimi test sessions that were not used during signal design or detector implementation.

#### Scenario: Kimi official tracking is backed by replay validation
- **WHEN** Kimi Code TUI is added to official supported TUI tracking
- **THEN** the implementation includes replay-validation evidence from labeled Kimi captures
- **AND THEN** supported Kimi state is not based only on source inspection, development captures, or one-off live observation

#### Scenario: Kimi maintained support requires held-out validation
- **WHEN** official Kimi tracking is declared maintained
- **THEN** held-out Kimi test sessions pass replay validation for both high-rate and derived low-rate streams
- **AND THEN** those held-out sessions were not used to tune the detector

#### Scenario: Kimi approval tracking has recorded evidence
- **WHEN** official Kimi tracking reports an approval prompt as operator-blocked
- **THEN** that behavior is covered by at least one labeled recorded approval scenario
- **AND THEN** replay validation confirms both parser state and public tracked-state posture for the approval range
