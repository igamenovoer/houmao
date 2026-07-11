## ADDED Requirements

### Requirement: Project agent-tool administration excludes Gemini
Project agent-tool inspection and setup administration SHALL expose only maintained tool subtrees and SHALL NOT expose Gemini.

#### Scenario: Gemini project tool lookup is unavailable
- **WHEN** an operator requests `project agents tools gemini get`
- **THEN** command validation rejects the tool
- **AND THEN** no Gemini starter subtree is materialized
