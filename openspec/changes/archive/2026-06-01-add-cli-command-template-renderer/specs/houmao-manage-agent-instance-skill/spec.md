## ADDED Requirements

### Requirement: `houmao-agent-instance` uses CLI-owned templates for lifecycle command authoring
The packaged `houmao-agent-instance` skill SHALL instruct agents to use `houmao-mgr internals command-templates show|render` before authoring supported lifecycle commands.

At minimum, covered lifecycle commands SHALL include:

- `agents launch`
- `agents launch --launch-profile`
- `agents join`
- `agents relaunch`
- `agents cleanup session`
- `agents cleanup logs`

The skill SHALL preserve default-sensitive omission semantics by rendering only explicit user inputs and recovered explicit context.

The skill SHALL NOT maintain independent default-bearing command skeletons for covered launch, join, relaunch, or cleanup commands.

#### Scenario: Launch uses template renderer
- **WHEN** a user asks the skill to launch an agent from an existing profile
- **AND WHEN** the user does not request headless posture
- **THEN** the skill guidance directs the agent to render the matching launch-profile launch template
- **AND THEN** the rendered intent omits headless posture

#### Scenario: Relaunch chat-session mode is explicit only
- **WHEN** a user asks the skill to relaunch an agent without naming a chat-session mode
- **THEN** the skill guidance renders relaunch intent without a chat-session override
- **AND THEN** it does not inject a preferred relaunch mode from skill prose

#### Scenario: Cleanup target conflicts are blockers
- **WHEN** a cleanup request supplies conflicting cleanup targets
- **THEN** template rendering reports the conflict before the skill runs any cleanup command
