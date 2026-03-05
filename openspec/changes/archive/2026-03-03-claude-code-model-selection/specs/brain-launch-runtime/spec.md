## ADDED Requirements

### Requirement: Claude model selection env vars are propagated to launched sessions
For Claude Code launches, the system SHALL preserve Claude Code model-selection
environment variables in the tool process environment for both:

- `backend=claude_headless` (subprocess launches)
- `backend=cao_rest` (tmux-isolated CAO-backed launches)

At minimum, the system SHALL support `ANTHROPIC_MODEL` for selecting the
effective model, and SHALL allow pinning alias resolution via:

- `ANTHROPIC_DEFAULT_OPUS_MODEL`
- `ANTHROPIC_DEFAULT_SONNET_MODEL`
- `ANTHROPIC_DEFAULT_HAIKU_MODEL`

The system SHALL additionally support:

- `CLAUDE_CODE_SUBAGENT_MODEL`
- `ANTHROPIC_SMALL_FAST_MODEL` (when unset, the system SHALL NOT synthesize it and Claude Code defaults apply)

#### Scenario: CAO-backed session inherits caller model env vars
- **WHEN** a developer starts a CAO-backed Claude session with `ANTHROPIC_MODEL` set in the caller environment
- **THEN** the created tmux session environment SHALL include `ANTHROPIC_MODEL` with the same value
- **AND THEN** if the caller environment defines `CLAUDE_CODE_SUBAGENT_MODEL`, the created tmux session environment SHALL include `CLAUDE_CODE_SUBAGENT_MODEL` with the same value
- **AND THEN** if the caller environment defines `ANTHROPIC_SMALL_FAST_MODEL`, the created tmux session environment SHALL include `ANTHROPIC_SMALL_FAST_MODEL` with the same value

#### Scenario: Headless session includes allowlisted model env vars from credential profile
- **WHEN** a developer starts a Claude headless session and the selected credential profile env file defines `ANTHROPIC_MODEL` (and/or `ANTHROPIC_SMALL_FAST_MODEL` and/or `CLAUDE_CODE_SUBAGENT_MODEL` and/or one of the `ANTHROPIC_DEFAULT_*_MODEL` pinning vars)
- **THEN** the headless Claude subprocess environment SHALL include the corresponding model-selection env var(s)
