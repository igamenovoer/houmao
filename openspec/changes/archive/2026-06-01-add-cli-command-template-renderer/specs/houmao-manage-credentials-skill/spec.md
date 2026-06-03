## ADDED Requirements

### Requirement: `houmao-credential-mgr` uses CLI-owned templates for credential command authoring
The packaged `houmao-credential-mgr` skill SHALL instruct agents to use `houmao-mgr internals command-templates show|render` before authoring supported credential commands for Claude, Codex, and Gemini.

At minimum, covered credential verbs SHALL include:

- `add`
- `set`
- `login`
- `list`
- `get`
- `rename`
- `remove`

The skill SHALL use CLI-owned template metadata for project-vs-plain agent-definition lane selection and tool-specific option shapes.

The skill SHALL NOT maintain independent default-bearing command skeletons or tool-specific credential option menus for covered command authoring.

#### Scenario: Codex credential add uses template renderer
- **WHEN** a user asks the skill to add project Codex credential `main`
- **THEN** the skill guidance directs the agent to render `project.credentials.codex.add`
- **AND THEN** Codex-specific fields come from the rendered template metadata rather than a skill-owned option menu

#### Scenario: Claude login update uses template renderer
- **WHEN** a user asks the skill to update an existing Claude login credential
- **THEN** the skill guidance directs the agent to render the matching Claude login template with the explicit update field
- **AND THEN** omitted login options remain absent from the rendered argv

#### Scenario: Plain agent-definition lane stays explicit
- **WHEN** a user targets a plain agent-definition directory instead of the active project
- **THEN** the skill guidance renders a plain-lane credential template with the explicit `agent_def_dir`
- **AND THEN** it does not silently switch to `project credentials`
