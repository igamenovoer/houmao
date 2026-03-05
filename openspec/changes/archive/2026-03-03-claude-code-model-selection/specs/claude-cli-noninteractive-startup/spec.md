## ADDED Requirements

### Requirement: Orchestrated Claude Code launches support env-based model selection
The system SHALL support selecting the Claude Code model for orchestrated
launches by supplying Claude Code model-selection environment variables.

At minimum, the system SHALL support:

- `ANTHROPIC_MODEL` (select effective model via alias or fully qualified name)

The system SHALL additionally support alias pinning variables so teams can
stabilize what an alias (for example `opus`) resolves to:

- `ANTHROPIC_DEFAULT_OPUS_MODEL`
- `ANTHROPIC_DEFAULT_SONNET_MODEL`
- `ANTHROPIC_DEFAULT_HAIKU_MODEL`

The system SHALL additionally support:

- `CLAUDE_CODE_SUBAGENT_MODEL`
- `ANTHROPIC_SMALL_FAST_MODEL` (when unset, the system SHALL NOT synthesize it and Claude Code defaults apply)

#### Scenario: Model env vars from credential profile are available to headless Claude
- **WHEN** a Claude brain is constructed and the credential profile env file defines `ANTHROPIC_MODEL` and/or `ANTHROPIC_SMALL_FAST_MODEL` and/or `CLAUDE_CODE_SUBAGENT_MODEL`
- **THEN** the constructed launch plan SHALL include the corresponding model env var(s) in the selected env var set for headless launches

#### Scenario: Model env vars are preserved for tmux-isolated launches
- **WHEN** a Claude CAO-backed session is started and the caller environment defines `ANTHROPIC_MODEL` and/or `ANTHROPIC_SMALL_FAST_MODEL` and/or `CLAUDE_CODE_SUBAGENT_MODEL`
- **THEN** the tmux session environment SHALL include the corresponding model env var(s) for the Claude Code process to consume
