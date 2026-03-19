## MODIFIED Requirements

### Requirement: Gateway mail notifier polls gateway-owned mailbox state and only schedules notifications when the agent is idle
The gateway mail notifier SHALL inspect unread-mail state through the gateway-owned shared mailbox facade for the managed session rather than by reading filesystem mailbox-local SQLite directly.

For this change, that notifier polling contract SHALL be limited to the mailbox functions supported by both the filesystem transport and the `stalwart` transport, using unread `check` behavior plus normalized message references and metadata.

When unread mail is present, the notifier SHALL enqueue a gateway-owned internal notification request only if:

- request admission is open,
- no gateway request is actively executing,
- queue depth is zero.

When those conditions are not satisfied, the notifier SHALL skip that interval and retry on a later poll rather than enqueueing a stale reminder behind unrelated work.

The notifier SHALL execute notifications through the gateway's durable internal request path rather than by bypassing the queue with direct terminal injection.

When the notifier enqueues a reminder prompt, that prompt SHALL describe unread mailbox work in transport-neutral shared-mailbox terms and SHALL NOT label the unread set as "filesystem mailbox messages" for a `stalwart` session.

#### Scenario: Filesystem-backed notifier poll uses the shared gateway mailbox facade
- **WHEN** the notifier polls unread mail for a filesystem mailbox-enabled session
- **THEN** the gateway determines unread state through the shared mailbox facade rather than direct mailbox-local SQLite reads
- **AND THEN** the rest of the notifier scheduling rules remain unchanged

#### Scenario: Stalwart-backed notifier poll uses the same shared gateway mailbox facade
- **WHEN** the notifier polls unread mail for a `stalwart` mailbox-enabled session
- **THEN** the gateway determines unread state through the same shared mailbox facade used by the filesystem transport
- **AND THEN** notifier wake-up behavior does not require a transport-specific unread polling path

#### Scenario: Stalwart-backed notifier reminder stays transport-neutral
- **WHEN** the notifier enqueues a reminder for unread mail discovered through a `stalwart` mailbox binding
- **THEN** the reminder prompt describes shared mailbox work without labeling the unread messages as filesystem-specific
- **AND THEN** the reminder still points the managed agent at the runtime-owned mailbox skill flow

### Requirement: Gateway mail notifier keeps notification bookkeeping separate from mailbox read state
The gateway SHALL treat notification bookkeeping and mailbox read state as separate concerns.

The notifier MAY persist gateway-owned metadata such as last poll time, last notification attempt, or reminder deduplication state under gateway-owned persistence, but it SHALL NOT redefine mailbox read state from that metadata.

Mailbox read or unread truth SHALL come from the selected mailbox transport through the gateway mailbox facade rather than from gateway-owned transport-local persistence.

The gateway SHALL NOT mark a message read merely because:

- unread mail was detected,
- a notifier prompt was accepted into the queue,
- a notifier prompt was delivered successfully to the managed agent.

#### Scenario: Delivered reminder does not auto-mark unread mail as read
- **WHEN** the gateway successfully delivers a mail notification prompt to the managed agent
- **THEN** the underlying unread messages remain unread until mailbox state is updated explicitly through the selected transport
- **AND THEN** notifier bookkeeping does not itself change mailbox read state

#### Scenario: Notification history survives gateway restart without becoming mailbox truth
- **WHEN** the gateway restarts after previously notifying the managed agent about unread mail
- **THEN** the gateway may recover notifier bookkeeping needed to avoid immediate duplicate reminders
- **AND THEN** mailbox read or unread truth still comes from the selected mailbox transport through the gateway mailbox facade rather than from gateway-owned notifier records
