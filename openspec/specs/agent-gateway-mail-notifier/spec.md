# agent-gateway-mail-notifier Specification

## Purpose
TBD - created by archiving change add-mailbox-local-state-and-gateway-notifier. Update Purpose after archive.

## Requirements

### Requirement: Gateway mail notifier can be configured through dedicated HTTP control routes
The system SHALL provide a gateway-owned mail notifier capability for mailbox-enabled sessions through dedicated HTTP routes served by the gateway sidecar.

That notifier surface SHALL include:

- `PUT /v1/mail-notifier` to enable or reconfigure notifier behavior,
- `GET /v1/mail-notifier` to inspect notifier configuration and runtime status,
- `DELETE /v1/mail-notifier` to disable notifier behavior.

Notifier configuration SHALL include at minimum:

- whether notifier is enabled,
- the unread-mail polling interval in seconds.

If the managed session is not mailbox-enabled, notifier enablement SHALL fail explicitly rather than silently enabling a broken poll loop.

The gateway SHALL determine whether notifier behavior is supported by loading the runtime-owned session manifest referenced by the gateway attach contract's `manifest_path` and inspecting `payload.launch_plan.mailbox`.

The gateway SHALL NOT introduce a second persisted mailbox-capability flag in gateway-owned attach or notifier state.

If that manifest pointer is missing, unreadable, unparsable, or its launch plan has no mailbox binding, enabling notifier behavior SHALL fail explicitly and SHALL leave notifier inactive.

#### Scenario: Mail notifier is enabled with an explicit interval
- **WHEN** a caller sends `PUT /v1/mail-notifier` with `enabled=true` and `interval_seconds=60`
- **THEN** the gateway stores that notifier configuration durably
- **AND THEN** subsequent notifier status reads report notifier as enabled with the configured interval

#### Scenario: Mail notifier can be disabled explicitly
- **WHEN** a caller sends `DELETE /v1/mail-notifier` for a gateway-managed session whose notifier is enabled
- **THEN** the gateway disables further notifier polling for that session
- **AND THEN** subsequent notifier status reads report notifier as disabled

#### Scenario: Mail notifier enablement fails for a session without mailbox support
- **WHEN** a caller attempts to enable the mail notifier for a gateway-managed session whose launch plan has no mailbox binding
- **THEN** the gateway rejects that notifier enablement explicitly
- **AND THEN** it does not claim that notifier polling is active for that session

#### Scenario: Mail notifier enablement fails when manifest-backed capability discovery is unavailable
- **WHEN** a caller attempts to enable the mail notifier for a gateway-managed session whose attach contract lacks a readable runtime-owned session manifest
- **THEN** the gateway rejects that notifier enablement explicitly
- **AND THEN** it does not treat any gateway-owned attach or notifier artifact as a substitute mailbox-capability source

### Requirement: Gateway mail notifier polls local mailbox state and only schedules notifications when the agent is idle
The gateway mail notifier SHALL inspect unread-mail state from the mailbox's resolved local mailbox SQLite database rather than from shared-root aggregate recipient state.

When unread mail is present, the notifier SHALL enqueue a gateway-owned internal notification request only if:

- request admission is open,
- no gateway request is actively executing,
- queue depth is zero.

When those conditions are not satisfied, the notifier SHALL skip that interval and retry on a later poll rather than enqueueing a stale reminder behind unrelated work.

The notifier SHALL execute notifications through the gateway's durable internal request path rather than by bypassing the queue with direct terminal injection.

#### Scenario: Idle gateway schedules one internal mail notification request
- **WHEN** the notifier poll finds unread messages in the mailbox-local SQLite state
- **AND WHEN** gateway request admission is open, active execution is idle, and queue depth is zero
- **THEN** the gateway inserts one internal mail notification request into its durable execution path
- **AND THEN** the reminder reaches the managed agent through the same serialized execution model used for other gateway-managed work

#### Scenario: Busy gateway defers mail notification
- **WHEN** the notifier poll finds unread messages but the gateway is already running or queueing work
- **THEN** the notifier does not enqueue a new reminder for that interval
- **AND THEN** the unread messages remain eligible for a later notifier poll when the gateway becomes idle again

### Requirement: Gateway mail notifier keeps notification bookkeeping separate from mailbox read state
The gateway SHALL treat notification bookkeeping and mailbox read state as separate concerns.

The notifier MAY persist gateway-owned metadata such as last poll time, last notification attempt, or reminder deduplication state under gateway-owned persistence, but it SHALL NOT redefine mailbox read state from that metadata.

The gateway SHALL NOT mark a message read merely because:

- unread mail was detected,
- a notifier prompt was accepted into the queue,
- a notifier prompt was delivered successfully to the managed agent.

#### Scenario: Delivered reminder does not auto-mark unread mail as read
- **WHEN** the gateway successfully delivers a mail notification prompt to the managed agent
- **THEN** the underlying unread messages remain unread until mailbox state is updated explicitly
- **AND THEN** notifier bookkeeping does not itself change mailbox read state

#### Scenario: Notification history survives gateway restart without becoming mailbox truth
- **WHEN** the gateway restarts after previously notifying the managed agent about unread mail
- **THEN** the gateway may recover notifier bookkeeping needed to avoid immediate duplicate reminders
- **AND THEN** mailbox read or unread truth still comes from mailbox-local mailbox state rather than from gateway-owned notifier records
