## ADDED Requirements

### Requirement: Specialist creation skill does not teach Gemini
The specialist creation system skill SHALL teach only maintained provider choices and SHALL contain no Gemini setup, credential, or launch workflow.

#### Scenario: Agent follows specialist creation guidance
- **WHEN** an agent reads the packaged specialist creation guidance
- **THEN** it can select Claude, Codex, or Kimi
- **AND THEN** it is not offered Gemini as a supported choice
