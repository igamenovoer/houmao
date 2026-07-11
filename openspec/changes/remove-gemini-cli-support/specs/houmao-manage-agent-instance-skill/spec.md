## ADDED Requirements

### Requirement: Agent-instance skill excludes Gemini
The agent-instance skill SHALL NOT teach Gemini launch, join, relaunch, prompt, state, or cleanup workflows.

#### Scenario: Instance launch guidance has no Gemini branch
- **WHEN** an agent reads the packaged instance launch action
- **THEN** no supported provider example or caveat names Gemini
