## MODIFIED Requirements

### Requirement: Gateway mail notifier can be configured through dedicated HTTP control routes
The system SHALL provide a gateway-owned mail notifier capability for mailbox-enabled sessions through dedicated HTTP routes served by the gateway sidecar.

That notifier surface SHALL include:

- `PUT /v1/mail-notifier` to enable or reconfigure notifier behavior,
- `GET /v1/mail-notifier` to inspect notifier configuration and runtime status,
- `DELETE /v1/mail-notifier` to disable notifier behavior.

Notifier configuration SHALL include at minimum:

- whether notifier is enabled,
- the unread-mail polling interval in seconds,
- the effective notification mode,
- the effective appendix text as a string, defaulting to the empty string.

If the managed session is not mailbox-enabled, notifier enablement SHALL fail explicitly rather than silently enabling a broken poll loop.

The gateway SHALL determine notifier support from two inputs:

- the durable mailbox capability published in the runtime-owned session manifest referenced by the attach contract's `manifest_path`,
- the current actionable mailbox state derived from that durable mailbox binding.

The gateway SHALL continue using the manifest as the durable mailbox capability source and SHALL NOT introduce a second persisted mailbox-capability flag in gateway-owned attach or notifier state.

For tmux-backed sessions, current mailbox actionability SHALL be evaluated from runtime-owned validation of the manifest-backed mailbox binding rather than from mailbox-specific `AGENTSYS_MAILBOX_*` projection in the owning tmux session environment.

For joined tmux-backed sessions, notifier support SHALL NOT treat unavailable relaunch posture as an additional readiness precondition once durable mailbox capability and actionable mailbox validation are both satisfied.

If that manifest pointer is missing, unreadable, unparsable, or its launch plan has no mailbox binding, enabling notifier behavior SHALL fail explicitly and SHALL leave notifier inactive.

If the manifest exposes durable mailbox capability but the resulting mailbox binding cannot be validated as actionable for notifier work, notifier enablement SHALL fail explicitly and SHALL leave notifier inactive.

When a caller omits `appendix_text` from `PUT /v1/mail-notifier`, the gateway SHALL preserve the currently stored appendix text unchanged.

When a caller provides non-empty `appendix_text`, the gateway SHALL replace the stored appendix text with that exact string.

When a caller provides `appendix_text=""`, the gateway SHALL clear the stored appendix text.

`DELETE /v1/mail-notifier` SHALL disable polling without erasing the stored appendix text.

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

#### Scenario: Omitted appendix preserves stored notifier appendix
- **WHEN** a caller has previously stored non-empty `appendix_text`
- **AND WHEN** the caller sends `PUT /v1/mail-notifier` without an `appendix_text` field
- **THEN** the gateway preserves the previously stored appendix text unchanged
- **AND THEN** subsequent `GET /v1/mail-notifier` responses return that preserved appendix text

#### Scenario: Provided appendix replaces stored notifier appendix
- **WHEN** a caller sends `PUT /v1/mail-notifier` with non-empty `appendix_text`
- **THEN** the gateway stores that exact appendix text in notifier state
- **AND THEN** subsequent `GET /v1/mail-notifier` responses return the updated appendix text

#### Scenario: Empty appendix clears stored notifier appendix
- **WHEN** a caller sends `PUT /v1/mail-notifier` with `appendix_text=""`
- **THEN** the gateway clears the stored appendix text
- **AND THEN** subsequent `GET /v1/mail-notifier` responses return `appendix_text=""`

#### Scenario: Disable preserves notifier appendix state
- **WHEN** a caller stores non-empty `appendix_text` and later sends `DELETE /v1/mail-notifier`
- **THEN** the gateway disables notifier polling
- **AND THEN** later `GET /v1/mail-notifier` responses still return the previously stored appendix text

## ADDED Requirements

### Requirement: Gateway notifier prompt appends configured runtime appendix text
When the gateway mail notifier enqueues an internal prompt, it SHALL append the configured runtime appendix text only when notifier state currently stores a non-empty `appendix_text`.

The appended appendix text SHALL be rendered after the gateway-owned wake-up context and SHALL remain additive prompt context rather than a replacement for notifier mode, gateway base URL, mailbox API summary, or mailbox-processing skill guidance.

When `appendix_text` is the empty string, the notifier SHALL render no appendix block.

#### Scenario: Non-empty appendix appears in notifier prompt
- **WHEN** notifier state stores non-empty `appendix_text`
- **AND WHEN** the gateway enqueues a notifier prompt
- **THEN** the prompt includes that appendix text as an appended runtime guidance block
- **AND THEN** the prompt still includes the gateway-owned notifier context

#### Scenario: Empty appendix does not render an appendix block
- **WHEN** notifier state stores `appendix_text=""`
- **AND WHEN** the gateway enqueues a notifier prompt
- **THEN** the prompt does not include an appendix block
- **AND THEN** the prompt remains otherwise valid notifier output
