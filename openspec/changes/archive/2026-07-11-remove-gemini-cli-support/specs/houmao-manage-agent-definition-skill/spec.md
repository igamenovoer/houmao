## ADDED Requirements

### Requirement: Agent-definition skill excludes Gemini
The unified agent-definition skill SHALL contain no Gemini credential routing, specialist flags, profiles, recipes, or launch examples.

#### Scenario: Agent-definition provider routing excludes Gemini
- **WHEN** an agent uses the packaged definition skill to choose a provider lane
- **THEN** the guidance routes only to maintained Claude, Codex, or Kimi instructions
