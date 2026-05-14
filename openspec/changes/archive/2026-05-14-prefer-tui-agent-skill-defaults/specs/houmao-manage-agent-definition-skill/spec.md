## ADDED Requirements

### Requirement: `houmao-agent-definition` prefers TUI-supported launch posture when unspecified
The packaged `houmao-agent-definition` skill SHALL instruct agents that omitted headless/TUI launch posture means "prefer TUI/local interactive when the selected tool or launch lane supports it."

This default SHALL apply to skill guidance for specialist-backed easy profile authoring, raw recipe-backed launch-profile authoring, create-agent-fast-forward profile preparation, and the specialist-scoped easy launch entry point.

The skill SHALL NOT tell agents to add `--headless`, persist profile `--headless`, or report headless as a stored default unless the user explicitly asks for headless posture or the selected tool/lane is known to require headless.

The skill SHALL keep prompt mode separate from launch posture: `--prompt-mode unattended` SHALL NOT imply `--headless`, and an unspecified headless/TUI posture SHALL remain TUI-preferred when supported even if prompt mode defaults to unattended.

The skill SHALL identify Gemini easy launches as a known required-headless exception and SHALL preserve explicit stored headless posture when inspecting or launching from an existing profile.

#### Scenario: Easy profile creation omits headless by default
- **WHEN** a user asks `houmao-agent-definition profiles` or `create-agent-fast-forward` to create a Codex or Claude easy profile
- **AND WHEN** the user does not request headless execution
- **THEN** the skill guidance directs the agent to omit `--headless` from `project easy profile create`
- **AND THEN** it treats the resulting profile as TUI/local-interactive preferred for later launch when supported

#### Scenario: Raw profile authoring omits headless by default
- **WHEN** a user asks `houmao-agent-definition raw-profiles` to add or update a recipe-backed launch profile
- **AND WHEN** the user does not request headless execution
- **THEN** the skill guidance directs the agent to omit `--headless`
- **AND THEN** it does not infer headless from unattended prompt mode, gateway defaults, mailbox defaults, or model defaults

#### Scenario: Fast-forward launch command stays TUI-preferred when supported
- **WHEN** `create-agent-fast-forward` prepares a launchable easy profile for a TUI-capable tool
- **AND WHEN** the user does not request headless execution
- **THEN** the workflow reports a launch command without `--headless`
- **AND THEN** it reports that launch posture is TUI/local-interactive preferred when supported

#### Scenario: Required-headless exception remains explicit
- **WHEN** `houmao-agent-definition launch-agent` prepares a Gemini easy launch command
- **THEN** the skill guidance may require `--headless`
- **AND THEN** it describes that as a selected-tool requirement rather than the default for unspecified launch posture
