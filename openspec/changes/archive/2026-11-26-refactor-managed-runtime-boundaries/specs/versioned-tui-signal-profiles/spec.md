# Spec Delta

## ADDED Requirements

### Requirement: Managed observers use the qualified detector for parsed terminal state
For a parser-backed managed TUI with a version-qualified profile, Houmao SHALL apply the same detector eligibility and select the same profile across local manager inspection, gateway observation, and passive observation. Qualification SHALL use version evidence for the recorded managed runtime.

#### Scenario: A qualified version produces consistent parsed state
- **WHEN** maintained observers evaluate the same supported managed TUI version and terminal evidence
- **THEN** they use the profile selected for that version and identify its provenance in parsed diagnostics

#### Scenario: Version evidence does not qualify a parser
- **WHEN** managed version evidence is missing, unparseable, or outside the qualified range and profile resolution requires a qualified version
- **THEN** each maintained observer reports `unsupported_tool_version` through its existing diagnostics
- **AND THEN** it leaves the parsed terminal surface unavailable

#### Scenario: Structured native observation is independent of terminal qualification
- **WHEN** a managed runtime uses structured native observation, including Hermes TUI
- **THEN** observer diagnostics continue to derive from native evidence
