## ADDED Requirements

### Requirement: Agent cleanup CLI surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide template entries for:

- `houmao-mgr agents cleanup session`
- `houmao-mgr agents cleanup logs`

Cleanup templates SHALL describe supported cleanup targets, dry-run behavior, purge-registry behavior where available, and conflicts between target selectors.

#### Scenario: Cleanup session renders manifest target
- **WHEN** an agent renders `agents.cleanup.session` with an explicit manifest path
- **THEN** the rendered argv includes the manifest-path target
- **AND THEN** omitted purge and dry-run flags remain absent unless explicitly requested

#### Scenario: Cleanup logs rejects conflicting targets
- **WHEN** an agent renders `agents.cleanup.logs` with both manifest path and session root targets
- **THEN** the renderer reports a conflict blocker
- **AND THEN** it does not return executable argv
