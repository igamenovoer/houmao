## ADDED Requirements

### Requirement: `houmao-specialist-mgr` delegates supported command authoring to CLI-owned templates
The packaged `houmao-specialist-mgr` skill SHALL act as compatibility guidance for specialist-oriented work and SHALL route supported specialist command authoring to the CLI-owned templates used by `houmao-agent-definition`.

At minimum, the skill SHALL use CLI-owned templates for:

- specialist create through `project.easy.specialist.create`
- specialist update through `project.easy.specialist.set`
- specialist-backed launch through `project.easy.instance.launch`

For covered flows, the skill SHALL render sparse intent from explicit user inputs and recovered explicit context only.

The skill SHALL NOT maintain a full Markdown-owned command template for covered commands that pre-fills optional default-sensitive flags.

The skill SHALL NOT grow an independent specialist command catalog when the same command surface is already covered by `houmao-agent-definition`.

#### Scenario: Specialist create uses template renderer
- **WHEN** a user asks `houmao-specialist-mgr` to create Codex specialist `reviewer` with credential `reviewer-creds`
- **AND WHEN** the user does not request prompt-mode persistence
- **THEN** the skill guidance directs the agent to render `project.easy.specialist.create` with the explicit specialist, tool, and credential fields
- **AND THEN** the guidance does not tell the agent to add `--prompt-mode unattended`

#### Scenario: Specialist update clears prompt mode only when explicit
- **WHEN** a user asks `houmao-specialist-mgr` to clear a specialist's stored prompt mode
- **THEN** the skill guidance directs the agent to render `project.easy.specialist.set` with the explicit clear prompt-mode field
- **AND THEN** the resulting command uses the clear flag reported by the template renderer

#### Scenario: Specialist launch uses rendered argv
- **WHEN** a user asks `houmao-specialist-mgr` to launch specialist `reviewer` as instance `reviewer-1`
- **THEN** the skill guidance directs the agent to render `project.easy.instance.launch`
- **AND THEN** the launch command is based on the renderer output rather than a hand-authored Markdown command skeleton

### Requirement: `houmao-specialist-mgr` treats template blockers as user-facing recovery points
When `internals command-templates render` returns blockers for a supported `houmao-specialist-mgr` flow, the skill SHALL instruct the agent to stop before executing the target command and recover the missing or conflicting inputs.

If the blocked field is a missing required input that cannot be recovered from the current prompt or recent conversation context, the skill SHALL ask the user for that input.

If the blocked field is a conflict between explicit user instructions, the skill SHALL report the conflict and ask the user which instruction should win.

#### Scenario: Missing launch target remains a question
- **WHEN** a user asks `houmao-specialist-mgr` to launch an instance
- **AND WHEN** the specialist name cannot be recovered from prompt or recent conversation context
- **THEN** template rendering reports the missing required field
- **AND THEN** the skill asks the user for the missing specialist name before running any launch command

#### Scenario: Conflicting posture request is not guessed
- **WHEN** a user asks for both TUI and headless launch posture in the same specialist launch request
- **THEN** template rendering reports a conflict
- **AND THEN** the skill asks the user to choose the intended posture instead of guessing
