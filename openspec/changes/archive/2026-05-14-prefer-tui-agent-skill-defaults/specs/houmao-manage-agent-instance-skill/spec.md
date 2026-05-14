## ADDED Requirements

### Requirement: `houmao-agent-instance` prefers TUI-supported launch posture when unspecified
The packaged `houmao-agent-instance` launch guidance SHALL instruct agents that omitted headless/TUI launch posture means "prefer TUI/local interactive when the selected tool or launch lane supports it."

For direct role or preset launch, raw-profile-backed launch, and specialist-backed easy launch, the skill SHALL NOT add a one-shot `--headless` flag unless the user explicitly asks for headless execution or the selected tool/lane is known to require headless.

For profile-backed launch, the skill SHALL preserve explicit stored profile posture: an existing stored headless profile MAY launch headless, but the skill SHALL NOT add headless on top of an unspecified user request.

The skill SHALL keep prompt mode separate from launch posture and SHALL NOT treat unattended prompt mode, gateway attachment, mailbox defaults, output rendering, or automation-oriented wording as evidence that the user requested headless execution.

#### Scenario: Direct managed launch does not add headless by default
- **WHEN** a user asks `houmao-agent-instance launch` to launch from a role or preset for a TUI-capable tool
- **AND WHEN** the user does not request headless execution
- **THEN** the skill guidance directs the agent to omit `--headless`
- **AND THEN** the resulting command leaves launch posture TUI/local-interactive preferred when supported

#### Scenario: Raw-profile-backed launch does not add a headless override by default
- **WHEN** a user asks `houmao-agent-instance launch` to launch through an existing raw profile
- **AND WHEN** the user does not request a headless one-shot override
- **THEN** the skill guidance directs the agent to omit `--headless`
- **AND THEN** it preserves whatever explicit posture is already stored on the selected profile

#### Scenario: Specialist-backed launch does not add headless by default
- **WHEN** a user asks `houmao-agent-instance launch` to launch from an existing Codex or Claude easy specialist
- **AND WHEN** the user does not request headless execution
- **THEN** the skill guidance directs the agent to omit `--headless`
- **AND THEN** it treats the launch as TUI/local-interactive preferred when supported

#### Scenario: Required-headless launch is not treated as the default
- **WHEN** a selected specialist or launch lane is known to require headless execution
- **THEN** the skill guidance may include the required headless flag or report the requirement
- **AND THEN** it explains that this is a tool or lane constraint rather than the default for unspecified launch posture
