## MODIFIED Requirements

### Requirement: Direct agent-definition-dir credential actions manage named auth directories
When the resolved target is a plain agent-definition directory, such as a copied temp root derived from `tests/fixtures/plain-agent-def/`, `list|get|add|set|remove` SHALL manage named auth directories under `tools/<tool>/auth/<name>/`.

For the direct-dir backend:

- the directory basename SHALL remain the stored credential identity,
- add SHALL create a new named auth directory and fail on duplicate names,
- set SHALL update an existing named auth directory and fail when the target does not exist,
- remove SHALL delete the named auth directory,
- list SHALL enumerate the existing credential directory names for the selected tool lane.

The direct-dir backend SHALL still enforce the adapter-defined env/file contract for the selected tool lane.

Maintained examples for this backend SHALL use generic direct-dir paths or copied temp roots rather than the removed `tests/fixtures/agents/` path.

#### Scenario: Direct-dir add creates one named credential directory
- **WHEN** an operator runs `houmao-mgr credentials codex add --agent-def-dir /tmp/agents --name sandbox --api-key sk-test --auth-json /tmp/auth.json`
- **THEN** the command creates `/tmp/agents/tools/codex/auth/sandbox/`
- **AND THEN** the selected Codex env values and supported auth file are stored under that named directory

#### Scenario: Direct-dir list reports directory-backed credential names
- **WHEN** an operator runs `houmao-mgr credentials gemini list --agent-def-dir /tmp/agents`
- **THEN** the command reports the Gemini credential names discovered under `/tmp/agents/tools/gemini/auth/`
- **AND THEN** the command does not require a project overlay or project catalog for that inspection
