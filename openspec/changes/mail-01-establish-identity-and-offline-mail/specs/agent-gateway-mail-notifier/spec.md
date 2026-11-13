# Spec Delta

## MODIFIED Requirements

### Requirement: Gateway mail notifier can be configured through dedicated HTTP control routes
The system SHALL provide a gateway-owned mail notifier capability for each configured mail channel through dedicated HTTP routes served by the gateway sidecar.

That notifier surface SHALL include:

- `PUT /v1/mail-notifier/{channel}` to enable or reconfigure notifier behavior,
- `GET /v1/mail-notifier/{channel}` to inspect notifier configuration and runtime status,
- `DELETE /v1/mail-notifier/{channel}` to disable notifier behavior.

Notifier configuration SHALL include at minimum:

- whether notifier is enabled,
- the unread-mail polling interval in seconds,
- the effective notification mode,
- the effective appendix text as a string, defaulting to the empty string.

If the selected channel has no configured binding, notifier enablement SHALL fail explicitly rather than silently enabling a broken poll loop.

The gateway SHALL determine notifier support from two inputs:

- the selected channel binding published in the runtime-owned session manifest referenced by the attach contract's `manifest_path`,
- the current actionable mailbox state derived from that durable mailbox binding.

The gateway SHALL continue using the manifest as the durable mailbox capability source and SHALL NOT introduce a second persisted mailbox-capability flag in gateway-owned attach or notifier state.

For tmux-backed sessions, current mailbox actionability SHALL be evaluated from runtime-owned validation of the manifest-backed mailbox binding rather than from mailbox-specific `AGENTSYS_MAILBOX_*` projection in the owning tmux session environment.

For joined tmux-backed sessions, notifier support SHALL NOT treat unavailable relaunch posture as an additional readiness precondition once durable mailbox capability and actionable mailbox validation are both satisfied.

If that manifest pointer is missing, unreadable, unparsable, or its launch plan has no binding for the selected channel, enabling notifier behavior SHALL fail explicitly and SHALL leave notifier inactive.

If the manifest exposes durable mailbox capability but the resulting mailbox binding cannot be validated as actionable for notifier work, notifier enablement SHALL fail explicitly and SHALL leave notifier inactive.

When a caller omits `appendix_text` from `PUT /v1/mail-notifier/{channel}`, the gateway SHALL preserve the currently stored appendix text unchanged.

When a caller provides non-empty `appendix_text`, the gateway SHALL replace the stored appendix text with that exact string.

When a caller provides `appendix_text=""`, the gateway SHALL clear the stored appendix text.

`DELETE /v1/mail-notifier/{channel}` SHALL disable polling without erasing the stored appendix text.

The channel SHALL be explicit and SHALL be `offline` or `online`. Each channel SHALL keep its own configuration, appendix, polling observations, compaction eligibility, and audit scope. Changing one channel SHALL preserve the other. Mailbox binding discovery SHALL use the current revision-owned runtime state rather than process environment snapshots.

#### Scenario: Mail notifier is enabled with an explicit interval
- **WHEN** a caller sends `PUT /v1/mail-notifier/{channel}` with `enabled=true` and `interval_seconds=60`
- **THEN** the gateway stores that notifier configuration durably
- **AND THEN** subsequent notifier status reads report notifier as enabled with the configured interval

#### Scenario: Mail notifier can be disabled explicitly
- **WHEN** a caller sends `DELETE /v1/mail-notifier/{channel}` for a gateway-managed session whose notifier is enabled
- **THEN** the gateway disables further notifier polling for that session
- **AND THEN** subsequent notifier status reads report notifier as disabled

#### Scenario: Mail notifier enablement fails for a session without mailbox support
- **WHEN** a caller attempts to enable the mail notifier for a gateway-managed session whose launch plan has no binding for the selected channel
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

#### Scenario: Omitted appendix preserves stored notifier appendix
- **WHEN** a caller has previously stored non-empty `appendix_text`
- **AND WHEN** the caller sends `PUT /v1/mail-notifier/{channel}` without an `appendix_text` field
- **THEN** the gateway preserves the previously stored appendix text unchanged
- **AND THEN** subsequent `GET /v1/mail-notifier/{channel}` responses return that preserved appendix text

#### Scenario: Provided appendix replaces stored notifier appendix
- **WHEN** a caller sends `PUT /v1/mail-notifier/{channel}` with non-empty `appendix_text`
- **THEN** the gateway stores that exact appendix text in notifier state
- **AND THEN** subsequent `GET /v1/mail-notifier/{channel}` responses return the updated appendix text

#### Scenario: Empty appendix clears stored notifier appendix
- **WHEN** a caller sends `PUT /v1/mail-notifier/{channel}` with `appendix_text=""`
- **THEN** the gateway clears the stored appendix text
- **AND THEN** subsequent `GET /v1/mail-notifier/{channel}` responses return `appendix_text=""`

#### Scenario: Disable preserves notifier appendix state
- **WHEN** a caller stores non-empty `appendix_text` and later sends `DELETE /v1/mail-notifier/{channel}`
- **THEN** the gateway disables notifier polling
- **AND THEN** later `GET /v1/mail-notifier/{channel}` responses still return the previously stored appendix text

### Requirement: Server-managed notifier control projects the same gateway-owned notifier state
When notifier control is exposed through server-owned managed-agent gateway routes, those server routes SHALL read and write the same gateway-owned notifier configuration and runtime state used by the direct gateway `/v1/mail-notifier/{channel}` routes.

The server projection SHALL NOT create a second notifier state store, a second unread-state source, or a second deduplication history separate from the gateway-owned notifier records.

The gateway sidecar SHALL remain the source of truth for notifier configuration, polling history, and per-poll audit evidence.

The channel SHALL be explicit and SHALL be `offline` or `online`. Each channel SHALL keep its own configuration, appendix, polling observations, compaction eligibility, and audit scope. Changing one channel SHALL preserve the other. Mailbox binding discovery SHALL use the current revision-owned runtime state rather than process environment snapshots.

#### Scenario: Enabling notifier through the server route is visible through the direct gateway route
- **WHEN** a caller enables notifier behavior through a server-owned managed-agent gateway route
- **THEN** the corresponding direct gateway `/v1/mail-notifier/{channel}` read returns the same enabled configuration
- **AND THEN** the system does not maintain separate server-only and gateway-only notifier state

#### Scenario: Disabling notifier through the direct gateway route is visible through the server route
- **WHEN** a caller disables notifier behavior through the direct gateway `/v1/mail-notifier/{channel}` surface
- **THEN** a later read through the server-owned managed-agent gateway route reports notifier as disabled
- **AND THEN** both surfaces continue reflecting the same gateway-owned notifier truth

## ADDED Requirements

### Requirement: Both mail channels preserve periodic reminder semantics
Each enabled channel SHALL continue periodic reminders while mode-eligible inbox work remains, even when that work is unchanged. Duplicate suppression SHALL apply to overlapping attempts or repeated admission within one reminder cycle, not permanent per-message notification history. Body readiness and existing queue-admission gates SHALL coordinate both channels.

#### Scenario: Unchanged mail generates later reminders
- **WHEN** eligible offline or online work remains across configured reminder intervals
- **AND WHEN** body readiness and admission gates pass
- **THEN** later intervals can each generate a reminder without requiring a new message

#### Scenario: Simultaneous channel reminders respect body admission
- **WHEN** both channels have eligible work at the same time
- **THEN** reminders retain their channel and binding context
- **AND THEN** gateway admission prevents overlapping terminal mutations and preserves pending-input guards

### Requirement: Notifier channel and compaction state remain independent
A notifier prompt SHALL identify its selected channel and current gateway endpoint. Delivery SHALL not mark mail read or archived. Compaction eligibility SHALL remain distinct from prompt deduplication and metadata caching; changing canonical mail identity or evicting cached metadata SHALL not reset eligibility for unchanged mail.

#### Scenario: Online attachment does not reset offline compaction history
- **WHEN** an offline message remains eligible after the agent gains online mail
- **THEN** its existing one-shot compaction bookkeeping remains associated with the offline binding
- **AND THEN** later periodic reminders do not repeat compaction solely because the canonical address changed
