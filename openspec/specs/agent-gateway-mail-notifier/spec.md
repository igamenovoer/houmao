# agent-gateway-mail-notifier Specification

## Purpose
Define the gateway-owned mail notifier control and polling contract for shared mailbox sessions.
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

The gateway SHALL determine notifier support from two inputs:

- the durable mailbox capability published in the runtime-owned session manifest referenced by the attach contract's `manifest_path`,
- the current actionable mailbox state derived from that durable mailbox binding.

The gateway SHALL continue using the manifest as the durable mailbox capability source and SHALL NOT introduce a second persisted mailbox-capability flag in gateway-owned attach or notifier state.

For tmux-backed sessions, current mailbox actionability SHALL be evaluated from runtime-owned validation of the manifest-backed mailbox binding rather than from mailbox-specific `AGENTSYS_MAILBOX_*` projection in the owning tmux session environment.

For joined tmux-backed sessions, notifier support SHALL NOT treat unavailable relaunch posture as an additional readiness precondition once durable mailbox capability and actionable mailbox validation are both satisfied.

If that manifest pointer is missing, unreadable, unparsable, or its launch plan has no mailbox binding, enabling notifier behavior SHALL fail explicitly and SHALL leave notifier inactive.

If the manifest exposes durable mailbox capability but the resulting mailbox binding cannot be validated as actionable for notifier work, notifier enablement SHALL fail explicitly and SHALL leave notifier inactive.

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

#### Scenario: Tmux-backed late registration becomes notifier-ready after durable binding validation
- **WHEN** a tmux-backed managed session has a durable mailbox binding in its manifest
- **AND WHEN** runtime-owned mailbox validation reports that binding as actionable for notifier work
- **THEN** the gateway treats notifier support as available for that session without requiring provider relaunch or mailbox-specific tmux env refresh
- **AND THEN** notifier enablement may proceed using that durable-plus-validated mailbox contract

#### Scenario: Joined tmux session without relaunch posture becomes notifier-ready after late registration
- **WHEN** a joined tmux-backed managed session has a durable mailbox binding in its manifest
- **AND WHEN** that joined session's relaunch posture is unavailable
- **AND WHEN** runtime-owned mailbox validation reports that binding as actionable for notifier work
- **THEN** the gateway treats notifier support as available for that joined session
- **AND THEN** notifier enablement may proceed without requiring joined-session relaunch posture

#### Scenario: Durable mailbox presence without actionable validation rejects notifier enablement
- **WHEN** a tmux-backed managed session has a durable mailbox binding in its manifest
- **AND WHEN** runtime-owned mailbox validation fails or required transport-local prerequisite material is unavailable for notifier work
- **THEN** the gateway rejects notifier enablement explicitly
- **AND THEN** notifier status reports that the session is not yet actionable for notifier work

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

#### Scenario: Idle gateway schedules one internal mail notification request
- **WHEN** the notifier poll finds unread messages through the gateway-owned shared mailbox facade
- **AND WHEN** gateway request admission is open, active execution is idle, and queue depth is zero
- **THEN** the gateway inserts one internal mail notification request into its durable execution path
- **AND THEN** the reminder reaches the managed agent through the same serialized execution model used for other gateway-managed work

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

#### Scenario: Busy gateway defers mail notification
- **WHEN** the notifier poll finds unread messages but the gateway is already running or queueing work
- **THEN** the notifier does not enqueue a new reminder for that interval
- **AND THEN** the unread messages remain eligible for a later notifier poll when the gateway becomes idle again

### Requirement: Gateway notifier wake-up prompts nominate one actionable shared-mailbox task
When the gateway mail notifier enqueues an internal reminder for unread mail, that reminder SHALL nominate one actionable unread mailbox message rather than surfacing only a generic unread digest.

The nominated task SHALL be described in shared-mailbox terms and SHALL include at minimum:

- the target opaque `message_ref`,
- optional `thread_ref` plus enough sender and subject context to identify the task,
- the remaining unread count beyond the nominated target, and
- the rule that the target message is marked read only after successful processing.

When the shared gateway mailbox facade is available for the session, the notifier prompt SHALL direct the agent to complete that task through shared mailbox operations rather than by reconstructing direct transport-local delivery or threading details.

For attached tmux-backed sessions, that prompt SHALL provide an actionable path to the exact current live gateway mail-facade endpoint for the current turn. That path SHALL follow the current-session discovery order of current process env first and owning tmux session env second, with validation before use. The prompt MAY inline the exact live `base_url` as bounded redundancy, but it SHALL NOT require the agent to infer localhost defaults or rediscover the port from unrelated process listings in order to use `/v1/mail/*`.

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
- **THEN** the notifier prompt still provides a way to resolve the exact current live gateway mail-facade endpoint from the owning tmux session env for that session
- **AND THEN** the agent does not need to guess another host or port

#### Scenario: Multiple unread messages yield one nominated target plus summary
- **WHEN** the notifier finds multiple unread messages through the shared mailbox facade
- **THEN** the enqueued wake-up prompt nominates one actionable unread target for the current turn
- **AND THEN** the notifier chooses the oldest unread target deterministically
- **AND THEN** the prompt may summarize the remaining unread count without requiring the agent to process every unread message in that same bounded turn

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

### Requirement: Server-managed notifier control projects the same gateway-owned notifier state
When notifier control is exposed through server-owned managed-agent gateway routes, those server routes SHALL read and write the same gateway-owned notifier configuration and runtime state used by the direct gateway `/v1/mail-notifier` routes.

The server projection SHALL NOT create a second notifier state store, a second unread-state source, or a second deduplication history separate from the gateway-owned notifier records.

The gateway sidecar SHALL remain the source of truth for notifier configuration, polling history, and per-poll audit evidence.

#### Scenario: Enabling notifier through the server route is visible through the direct gateway route
- **WHEN** a caller enables notifier behavior through a server-owned managed-agent gateway route
- **THEN** the corresponding direct gateway `/v1/mail-notifier` read returns the same enabled configuration
- **AND THEN** the system does not maintain separate server-only and gateway-only notifier state

#### Scenario: Disabling notifier through the direct gateway route is visible through the server route
- **WHEN** a caller disables notifier behavior through the direct gateway `/v1/mail-notifier` surface
- **THEN** a later read through the server-owned managed-agent gateway route reports notifier as disabled
- **AND THEN** both surfaces continue reflecting the same gateway-owned notifier truth
