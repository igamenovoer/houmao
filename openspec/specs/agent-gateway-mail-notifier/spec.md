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

### Requirement: Gateway notifier wake-up prompts summarize unread shared-mailbox work through a template-driven gateway-first contract
When the gateway mail notifier enqueues an internal reminder for unread mail, that reminder SHALL summarize the unread mailbox snapshot in shared-mailbox terms rather than nominating only one actionable target.

That reminder SHALL be rendered from a packaged Markdown template asset rather than assembled entirely from hardcoded Python string literals.

The runtime renderer SHALL fill that template through deterministic string replacement over runtime-generated values and pre-rendered blocks. The implementation SHALL NOT require a general-purpose template engine.

The rendered prompt SHALL direct the agent to discover current mailbox state through `pixi run houmao-mgr agents mail resolve-live` and to obtain the exact live shared-mailbox endpoint from the returned `gateway.base_url`.

When the shared gateway mailbox facade is available, the prompt SHALL direct the agent to use curl against that exact `gateway.base_url` for `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state`.

The prompt SHALL reference both:
- the runtime-owned common gateway mailbox skill path for shared gateway operations, and
- the active transport-specific mailbox skill path for transport-specific context and fallback guidance.

The prompt SHALL explicitly instruct the agent to use the installed runtime-owned common gateway mailbox skill for the current mailbox turn rather than presenting that skill path only as optional supporting material.

Those runtime-owned skill references SHALL use the `houmao-<skillname>` naming convention, including `skills/mailbox/houmao-email-via-agent-gateway/` for the common gateway skill.

When the prompt intends to trigger a Houmao-owned skill, it SHALL include the keyword `houmao` explicitly in the instruction text rather than relying on an implicit or shortened skill name.

For joined sessions adopted through `houmao-mgr agents join`, that installed-skill assumption SHALL apply only when the join workflow performed the default Houmao-owned mailbox skill projection. When join used an explicit opt-out, the notifier prompt SHALL NOT claim that the Houmao-owned mailbox skills are installed.

When multiple unread messages are present, the prompt SHALL include header summaries for every unread message in the current unread snapshot. Each summary entry SHALL include at minimum:
- the opaque `message_ref`,
- optional `thread_ref`,
- sender identity,
- subject,
- `created_at_utc`.

The prompt SHALL instruct the agent to determine which unread message or messages to inspect and handle after checking current mailbox state. It SHALL continue to state that read-state mutation happens only after successful processing of the corresponding message.

Notifier deduplication SHALL remain keyed to the full unread set rather than only to any single message, so unchanged unread mail does not generate repeated reminders solely because the prompt body is richer.

#### Scenario: Template-driven notifier prompt references the manager-owned resolver and gateway skill
- **WHEN** the notifier enqueues a wake-up prompt for unread mail on a mailbox-enabled session with a live shared mailbox facade
- **THEN** the prompt is rendered from a packaged Markdown template
- **AND THEN** it directs the agent to `pixi run houmao-mgr agents mail resolve-live`
- **AND THEN** it tells the agent to use the installed runtime-owned gateway mailbox skill for that mailbox turn
- **AND THEN** it references the runtime-owned gateway mailbox skill path and the current transport-specific mailbox skill path using the `houmao-<skillname>` naming convention

#### Scenario: Notifier prompt includes explicit `houmao` wording when triggering the gateway skill
- **WHEN** the notifier prompt instructs the agent to use the installed gateway mailbox skill
- **THEN** the instruction text names the skill with its `houmao-...` form
- **AND THEN** the prompt includes the keyword `houmao` explicitly instead of relying on an abbreviated or implicit trigger

#### Scenario: Joined-session notifier prompt does not claim installed Houmao skills after join opt-out
- **WHEN** a mailbox-enabled session was adopted through `houmao-mgr agents join` with the explicit opt-out for Houmao mailbox skill installation
- **AND WHEN** the notifier later enqueues a wake-up prompt for that joined session
- **THEN** the prompt does not tell the agent to use Houmao-owned mailbox skills as already-installed assets for that session
- **AND THEN** the prompt still points the agent at the manager-owned live resolver and the supported mailbox operation contract for the session

#### Scenario: Notifier prompt includes all unread message headers in one snapshot
- **WHEN** the notifier finds multiple unread messages through the shared mailbox facade
- **THEN** the enqueued wake-up prompt includes a header summary entry for every unread message in that snapshot
- **AND THEN** each entry includes the opaque message reference plus sender, subject, and creation timestamp context
- **AND THEN** the prompt does not reduce the unread set to only one nominated target

#### Scenario: Prompt teaches curl-first shared mailbox operations through the resolved gateway URL
- **WHEN** the notifier enqueues a wake-up prompt for a session with an attached live gateway
- **THEN** the prompt tells the agent to obtain `gateway.base_url` from `houmao-mgr agents mail resolve-live`
- **AND THEN** it documents curl-based use of `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state` against that exact base URL
- **AND THEN** the agent does not need to guess another localhost port or reconstruct the endpoint from unrelated process state

#### Scenario: Prompt leaves mailbox triage to the agent while preserving explicit read-state discipline
- **WHEN** the notifier enqueues a wake-up prompt for one unread snapshot
- **THEN** the prompt tells the agent to determine which unread message or messages to inspect and handle after checking current mailbox state
- **AND THEN** it still directs the agent to mark messages read only after the corresponding mailbox work succeeds

#### Scenario: Deduplication remains based on the full unread set
- **WHEN** the notifier has already delivered one wake-up prompt for a particular unread snapshot
- **AND WHEN** a later notifier poll sees the same unread set unchanged
- **THEN** the notifier suppresses a duplicate reminder for that unchanged unread snapshot
- **AND THEN** that suppression behavior does not depend on selecting or nominating only one unread target

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
