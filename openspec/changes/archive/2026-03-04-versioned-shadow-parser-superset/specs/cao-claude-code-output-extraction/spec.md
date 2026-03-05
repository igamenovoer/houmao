## ADDED Requirements

### Requirement: Claude Code shadow parsing fails explicitly on unsupported output formats
For CAO provider `claude_code`, when a session runs in `parsing_mode=shadow_only`, the runtime-owned Claude Code shadow parser SHALL explicitly detect when `output?mode=full` does not match any supported output format variant for the selected preset family.

If no supported variant matches, the system SHALL fail the turn with an explicit `unsupported_output_format`-class error and include an ANSI-stripped tail excerpt for diagnostics. The system SHALL NOT treat this condition as normal `processing` indefinitely.

#### Scenario: Drifted output fails explicitly with diagnostics
- **WHEN** a Claude Code CAO-backed session runs in `parsing_mode=shadow_only`
- **AND WHEN** `output?mode=full` does not match any supported Claude Code output format variant
- **THEN** the turn fails with an explicit `unsupported_output_format`-class error
- **AND THEN** the error includes an ANSI-stripped tail excerpt suitable for debugging

### Requirement: Claude Code version floor lookup is reported as an explicit anomaly
When resolving a Claude Code parsing preset based on a detected version signature `V`, if no exact preset exists and the system uses a previous (floor) preset for best-effort parsing, the system SHALL report an explicit anomaly indicating that the output version did not match a known preset exactly.

#### Scenario: Unknown version uses floor preset and is reported
- **WHEN** `output?mode=full` includes a banner version `V`
- **AND WHEN** no exact parsing preset exists for `V`
- **AND WHEN** the system selects a previous preset for compatibility
- **THEN** the system uses the selected floor preset for parsing
- **AND THEN** parser metadata includes an explicit anomaly indicating the version mismatch

