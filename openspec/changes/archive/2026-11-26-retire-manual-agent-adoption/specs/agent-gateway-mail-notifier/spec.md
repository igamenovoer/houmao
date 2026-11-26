# Agent Gateway Mail Notifier Delta

## ADDED Requirements

### Requirement: Supported Managed Runtimes Configure Gateway Mail Notifiers Through Dedicated HTTP Routes
The system SHALL provide a gateway-owned mail notifier capability for each configured mail channel through dedicated HTTP routes served by the gateway sidecar.

That notifier surface SHALL include:

- `PUT /v1/mail-notifier/{channel}` to enable or reconfigure notifier behavior,
- `GET /v1/mail-notifier/{channel}` to inspect notifier configuration and runtime status,
- `DELETE /v1/mail-notifier/{channel}` to disable notifier behavior.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

A manifest for a retired manual adoption SHALL confer no notifier authority, even when the channel binding remains actionable or the notifier was previously enabled.

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

#### Scenario: Retired Adoption Does Not Dispatch Mail Wakeups
- **WHEN** notifier enablement or a poll targets a retired adopted runtime with a previously actionable mailbox binding
- **THEN** Houmao refuses the target without polling or submitting a wakeup
- **AND THEN** it preserves the mailbox contents and retained notifier configuration

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

## REMOVED Requirements

### Requirement: Gateway mail notifier can be configured through dedicated HTTP control routes

**Reason**: This requirement included notifier authority for manually adopted sessions. The replacement requirement preserves notifier behavior for supported managed runtimes.

**Migration**: Configure the required mail channels and notifier on a supported Houmao launch. Existing mailbox contents and retired notifier configuration remain in place.
