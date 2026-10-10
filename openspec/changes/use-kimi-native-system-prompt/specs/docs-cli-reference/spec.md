## MODIFIED Requirements

### Requirement: CLI reference retains supported provider boundaries at pack level
The reference SHALL document pack projection for Claude, Codex, Copilot, Kimi, and universal targets, including the Kimi 0.34.0 managed-launch floor and absence of an upper version limit.

It SHALL state that Gemini is not a supported system-skill projection target and that provider-native role-prompt files are not system-skill pack members or lifecycle targets. The CLI reference SHALL not document `houmao-auto-system-prompt` or `houmao-mgr agents self system-prompt show` as current surfaces.

#### Scenario: Reader checks Copilot or Gemini support
- **WHEN** a reader compares system-skill targets
- **THEN** Copilot is identified as a pack projection target rather than a launch backend
- **AND THEN** Gemini is not presented as a supported pack target

#### Scenario: Reader checks Kimi role-prompt ownership
- **WHEN** a reader compares Kimi system-skill packs with managed role injection
- **THEN** the reference places native `SYSTEM.md` under brain construction and provenance
- **AND THEN** it exposes no auto-skill install unit or self-prompt retrieval command
