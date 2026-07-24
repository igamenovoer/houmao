## ADDED Requirements

### Requirement: Messaging skill selects explicit gateway prompt admission policy

The packaged `houmao-agent-messaging` skill SHALL teach agents to map caller intent to the maintained gateway prompt admission policies:

- use `ready-only` when the prompt must be processed immediately and the agent SHALL back off while the CLI is busy,
- use `if-no-pending` when the prompt may enter a busy provider CLI but SHALL back off if a submitted prompt is already pending or pending state is unknown,
- use `always` when the caller explicitly wants submission regardless of tracked readiness or pending-input state.

The skill SHALL explain that non-default policies apply to TUI-backed targets, that structural gateway failures still reject every policy, and that if-no-pending is observational rather than an atomic queue reservation.

The skill SHALL use `--admission-policy` in current `houmao-mgr agents single|self ... gateway prompt` examples and SHALL NOT instruct agents to use the removed `--force` option.

#### Scenario: Busy-sensitive caller intent selects ready-only

- **WHEN** the caller says to submit only if the target will process the prompt immediately
- **THEN** the messaging skill directs the agent to `--admission-policy ready-only`
- **AND THEN** it explains that a busy TUI causes the command to back off

#### Scenario: Empty-queue caller intent selects if-no-pending

- **WHEN** the caller allows submission while the TUI is busy but does not want to add behind an existing provider-native queued prompt
- **THEN** the messaging skill directs the agent to `--admission-policy if-no-pending`
- **AND THEN** it explains that both `pending_input=yes` and `pending_input=unknown` cause refusal

#### Scenario: Explicit unconditional caller intent selects always

- **WHEN** the caller explicitly requests prompt submission regardless of busy and pending posture
- **THEN** the messaging skill directs the agent to `--admission-policy always`
- **AND THEN** it does not claim that this bypasses detachment, reconciliation, validation, or unsupported-target failures

#### Scenario: Skill does not promise one-winner concurrency

- **WHEN** an agent considers multiple closely spaced if-no-pending submissions
- **THEN** the skill explains that each call uses the latest observed TUI state independently
- **AND THEN** it does not promise that only one call can reach the CLI before repaint
