## ADDED Requirements

### Requirement: Headless gateway wake-up demo supports Claude and Codex only
The maintained single-agent gateway wake-up headless demo SHALL expose Claude Code and Codex lanes and SHALL NOT accept Gemini.

#### Scenario: Demo rejects Gemini lane
- **WHEN** an operator selects `--tool gemini`
- **THEN** demo argument validation rejects the tool
- **AND THEN** the demo does not import Gemini auth or start a Gemini specialist
