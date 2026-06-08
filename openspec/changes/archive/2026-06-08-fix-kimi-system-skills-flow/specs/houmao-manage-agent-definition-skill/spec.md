# houmao-manage-agent-definition-skill Specification

## ADDED Requirements

### Requirement: `houmao-agent-definition` supports Kimi specialists, profiles, and launch posture

The packaged `houmao-agent-definition` skill SHALL describe Kimi as a supported tool for project specialist authoring, project profile authoring, create-agent-fast-forward preparation, and the limited launch-agent handoff.

When guidance creates or edits Kimi specialists, examples and config-draft inputs SHALL use tool `kimi` rather than using another provider as a placeholder.

When guidance creates or edits Kimi-backed project profiles, omitted headless/TUI launch posture SHALL mean TUI/local-interactive preferred when supported. Kimi launch examples SHALL omit `--headless` unless the user explicitly asks for headless posture or an existing profile already stores headless posture.

The skill SHALL keep Gemini as the known required-headless exception for project easy launch. The skill SHALL NOT describe Kimi as required-headless on the project easy launch surface.

The skill SHALL provide resolvable credential-reference links for Claude, Codex, Gemini, and Kimi credential selection guidance. Those links MAY point to local references within `houmao-agent-definition` or to packaged `houmao-credential-mgr` references, but installed skill content SHALL NOT contain broken relative links for credential references.

#### Scenario: Kimi specialist authoring uses Kimi as the selected tool

- **WHEN** a user asks `houmao-agent-definition specialists` to create a reusable Kimi specialist
- **THEN** the guidance routes to `houmao-mgr project specialist create --tool kimi` or a `project.specialist` config draft with tool `kimi`
- **AND THEN** it does not show a Kimi-named example whose tool field is Claude, Codex, or Gemini

#### Scenario: Kimi profile authoring omits headless by default

- **WHEN** a user asks `houmao-agent-definition profiles` or `create-agent-fast-forward` to create a Kimi-backed project profile
- **AND WHEN** the user does not request headless execution
- **THEN** the guidance omits `--headless`
- **AND THEN** it describes the resulting launch posture as TUI/local-interactive preferred when supported

#### Scenario: Kimi launch-agent guidance omits headless by default

- **WHEN** a user asks `houmao-agent-definition launch-agent` to launch an existing Kimi specialist or Kimi-backed profile
- **AND WHEN** no explicit headless posture is requested or stored
- **THEN** the reported launch command omits `--headless`
- **AND THEN** it does not claim that Kimi must launch headless on the project easy surface

#### Scenario: Gemini remains the explicit required-headless exception

- **WHEN** `houmao-agent-definition launch-agent` prepares a Gemini project easy launch command
- **THEN** the guidance may require `--headless`
- **AND THEN** it describes that requirement as Gemini-specific rather than applying it to Kimi

#### Scenario: Credential reference links are resolvable

- **WHEN** an installed `houmao-agent-definition` page links to credential reference material for Claude, Codex, Gemini, or Kimi
- **THEN** the referenced Markdown file exists in the installed skill tree or is a valid packaged relative link
- **AND THEN** the linked reference explains how to select or create credentials without directing the agent to hand-edit credential files
