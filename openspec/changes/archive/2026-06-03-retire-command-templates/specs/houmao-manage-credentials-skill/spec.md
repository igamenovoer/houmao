## REMOVED Requirements

### Requirement: `houmao-credential-mgr` uses CLI-owned templates for credential command authoring
**Reason**: Credential command templates are retired with the command-template renderer.
**Migration**: Document direct project and native-agent credential commands in fenced `bash` blocks and keep required-input/conflict guardrails in skill prose.

#### Scenario: Credential authoring does not use templates
- **WHEN** the packaged skill documents credential add, set, login, list, get, rename, or remove
- **THEN** it shows a direct maintained credential command rather than a command-template id

## ADDED Requirements

### Requirement: `houmao-credential-mgr` uses direct command snippets for credential workflows
The packaged `houmao-credential-mgr` skill SHALL document supported credential commands as fenced `bash` snippets.

At minimum, covered credential verbs SHALL include:

- `add`
- `set`
- `login`
- `list`
- `get`
- `rename`
- `remove`

The skill SHALL document project-vs-native-agent lane selection directly and SHALL include tool-specific option shapes for Claude, Codex, and Gemini where a workflow needs credential material flags.

The skill SHALL NOT reference `houmao-mgr internals command-templates show`, `houmao-mgr internals command-templates render`, command-template ids, or template blockers.

#### Scenario: Codex credential add uses direct project command
- **WHEN** a user asks the skill to add project Codex credential `main`
- **THEN** the skill guidance shows a direct `houmao-mgr project credentials codex add --name main ...` command
- **AND THEN** Codex-specific credential material flags are documented in skill guidance rather than loaded from a command-template schema

#### Scenario: Claude login update uses direct login command
- **WHEN** a user asks the skill to update an existing Claude login credential
- **THEN** the skill guidance shows the direct Claude credential login or add command with the explicit update flag when supported
- **AND THEN** omitted login options remain absent from the command snippet

#### Scenario: Native agent-definition lane stays explicit
- **WHEN** a user targets a plain native-agent directory instead of the active project
- **THEN** the skill guidance uses a direct `houmao-mgr internals native-agent credentials <tool> ... --native-agent-root <dir>` command
- **AND THEN** it does not silently switch to `project credentials`
