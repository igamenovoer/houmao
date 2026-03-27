## MODIFIED Requirements

### Requirement: Gateway notifier wake-up prompts nominate one actionable shared-mailbox task
When the gateway mail notifier enqueues an internal reminder for unread mail, that reminder SHALL nominate one actionable unread mailbox message rather than surfacing only a generic unread digest.

The nominated task SHALL be described in shared-mailbox terms and SHALL include at minimum:

- the target opaque `message_ref`,
- optional `thread_ref` plus enough sender and subject context to identify the task,
- the remaining unread count beyond the nominated target, and
- the rule that the target message is marked read only after successful processing.

When the shared gateway mailbox facade is available for the session, the notifier prompt SHALL direct the agent to complete that task through shared mailbox operations rather than by reconstructing direct transport-local delivery or threading details.

For attached tmux-backed sessions, that prompt SHALL provide an actionable runtime-owned discovery path to the exact current live gateway mail-facade endpoint for the current turn. The prompt MAY inline the exact live `base_url` as bounded redundancy, but it SHALL NOT require the agent to infer localhost defaults, rediscover the port from provider-process env, or scrape tmux state directly in order to use `/v1/mail/*`.

The notifier MAY continue to summarize other unread messages for operator visibility, but it SHALL keep the managed turn bounded to one actionable target at a time.

When multiple unread messages are present, the notifier SHALL nominate the oldest unread message by `created_at_utc`, using a stable tie-breaker when timestamps collide, rather than relying on transport iteration order.

Notifier deduplication SHALL remain keyed to the full unread set rather than only to the nominated target so unchanged unread mail does not generate repeated reminders after prompt-shape changes.

#### Scenario: Filesystem-backed notifier prompt stays gateway-first
- **WHEN** the notifier enqueues a wake-up prompt for unread mail on a filesystem mailbox session with a live shared mailbox facade
- **THEN** the prompt identifies one actionable unread target by opaque `message_ref`
- **AND THEN** the prompt tells the agent to use shared mailbox operations instead of reconstructing `deliver_message.py` or raw threading payloads
- **AND THEN** the prompt exposes an actionable runtime-owned path to the exact current live gateway endpoint for that turn

#### Scenario: Attached notifier prompt stays actionable without provider gateway env
- **WHEN** an attached tmux-backed mailbox session has a live gateway but the provider process env snapshot does not include `AGENTSYS_AGENT_GATEWAY_HOST` or `AGENTSYS_AGENT_GATEWAY_PORT`
- **THEN** the notifier prompt still provides a runtime-owned way to resolve the exact current live gateway mail-facade endpoint
- **AND THEN** the agent does not need to inspect tmux env directly or guess another host or port

#### Scenario: Multiple unread messages yield one nominated target plus summary
- **WHEN** the notifier finds multiple unread messages through the shared mailbox facade
- **THEN** the enqueued wake-up prompt nominates one actionable unread target for the current turn
- **AND THEN** the notifier chooses the oldest unread target deterministically
- **AND THEN** the prompt may summarize the remaining unread count without requiring the agent to process every unread message in that same bounded turn
