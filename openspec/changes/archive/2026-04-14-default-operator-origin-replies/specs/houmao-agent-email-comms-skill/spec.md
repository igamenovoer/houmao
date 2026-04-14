## ADDED Requirements

### Requirement: `houmao-agent-email-comms` teaches reply-enabled operator-origin post default
The packaged `houmao-agent-email-comms` skill SHALL describe operator-origin `post` as reply-enabled by default.

That skill SHALL explain that callers may omit reply-policy input for the default `operator_mailbox` behavior, and SHALL present `reply_policy=none` as the explicit no-reply opt-out.

The skill SHALL NOT describe default operator-origin post behavior as one-way or no-reply.

When showing gateway-backed post examples, the skill SHALL either omit `reply_policy` or set it to `operator_mailbox` for the default case.

When showing manager CLI post examples, the skill SHALL either omit `--reply-policy` or use `--reply-policy operator_mailbox` for the default case, and SHALL reserve `--reply-policy none` for explicit no-reply examples.

#### Scenario: Skill user sees reply-enabled default
- **WHEN** an agent opens the `houmao-agent-email-comms` operator-origin post action guidance
- **THEN** the skill explains that operator-origin posts default to replies through `HOUMAO-operator@houmao.localhost`
- **AND THEN** it identifies `reply_policy=none` as the way to request a one-way operator-origin note
