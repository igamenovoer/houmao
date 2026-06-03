## REMOVED Requirements

### Requirement: `houmao-agent-instance` uses CLI-owned templates for lifecycle command authoring
**Reason**: Lifecycle command templates are retired with the command-template renderer.
**Migration**: Document direct `houmao-mgr project agents launch`, `houmao-mgr agents join`, `houmao-mgr agents single ... relaunch`, `houmao-mgr agents self relaunch`, and scoped cleanup commands in fenced `bash` blocks.

#### Scenario: Lifecycle authoring does not use templates
- **WHEN** the packaged skill documents launch, join, relaunch, or cleanup
- **THEN** it shows a direct maintained `houmao-mgr` command rather than a command-template id

## ADDED Requirements

### Requirement: `houmao-agent-instance` uses direct command snippets for lifecycle commands
The packaged `houmao-agent-instance` skill SHALL document supported lifecycle commands as fenced `bash` snippets.

At minimum, covered lifecycle commands SHALL include project-profile-backed launch, specialist-backed launch, join, relaunch, cleanup session, and cleanup logs.

The skill SHALL preserve default-sensitive omission semantics by including only explicit user inputs and recovered explicit context in command snippets.

The skill SHALL NOT reference `houmao-mgr internals command-templates show`, `houmao-mgr internals command-templates render`, command-template ids, or template blockers.

#### Scenario: Launch uses direct command snippet
- **WHEN** a user asks the skill to launch an agent from an existing profile
- **AND WHEN** the user does not request headless posture
- **THEN** the skill guidance shows a direct `houmao-mgr project agents launch --profile <profile>` command
- **AND THEN** the command snippet omits `--headless`

#### Scenario: Relaunch chat-session mode is explicit only
- **WHEN** a user asks the skill to relaunch an agent without naming a chat-session mode
- **THEN** the direct relaunch command snippet omits chat-session override flags
- **AND THEN** it does not inject a preferred relaunch mode from skill prose

#### Scenario: Cleanup target conflicts stop before command execution
- **WHEN** a cleanup request supplies conflicting cleanup targets
- **THEN** the skill reports the conflict before running any cleanup command
