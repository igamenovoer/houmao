## ADDED Requirements

### Requirement: System-skills CLI excludes Gemini targets
System-skill list, install, status, and uninstall tool validation SHALL NOT accept Gemini or resolve a Gemini home.

#### Scenario: Gemini system-skill install is rejected
- **WHEN** an operator requests system-skill installation with `--tool gemini`
- **THEN** command validation rejects the tool
- **AND THEN** no `.gemini/skills` path is created
