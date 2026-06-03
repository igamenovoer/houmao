## ADDED Requirements

### Requirement: Credential CLI surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide template entries for project-scoped and plain agent-definition credential command surfaces for Claude, Codex, and Gemini.

Template entries SHALL cover credential command verbs `add`, `set`, `login`, `list`, `get`, `rename`, and `remove` where those verbs exist in the maintained `houmao-mgr credentials` or `houmao-mgr project credentials` command surfaces.

Each credential template SHALL map structured fields to CLI options, SHALL describe required target fields, SHALL describe tool-specific credential material fields, and SHALL report conflicts between mutually exclusive credential sources.

#### Scenario: Project credential add has tool-specific metadata
- **WHEN** an agent shows `project.credentials.gemini.add`
- **THEN** the template reports Gemini credential source fields such as API key, Vertex AI key posture, OAuth credentials, and base URL
- **AND THEN** it does not report Claude-only or Codex-only credential fields

#### Scenario: Plain credential list carries agent-definition target
- **WHEN** an agent renders a plain-lane credential list template
- **THEN** the rendered argv includes the explicit plain agent-definition directory target
- **AND THEN** it does not render the project-scoped command path

#### Scenario: Credential source conflicts block rendering
- **WHEN** an agent renders a credential add template with two mutually exclusive credential sources for the same tool
- **THEN** the renderer reports a blocker
- **AND THEN** it does not return executable argv
