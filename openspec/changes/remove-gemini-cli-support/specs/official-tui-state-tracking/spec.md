## ADDED Requirements

### Requirement: Official TUI ownership does not recognize Gemini processes
Official TUI tracking ownership and profile selection SHALL NOT treat Gemini CLI as a supported process or tool family.

#### Scenario: Gemini process is unsupported for tracked TUI ownership
- **WHEN** ownership inspection observes a `gemini` process
- **THEN** it does not claim a maintained Gemini tracker profile or supported TUI session
