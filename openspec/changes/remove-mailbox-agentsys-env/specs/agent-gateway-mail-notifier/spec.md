## MODIFIED Requirements

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
