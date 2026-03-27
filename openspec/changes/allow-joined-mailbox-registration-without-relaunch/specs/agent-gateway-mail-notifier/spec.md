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
- the current live mailbox actionability state for the attached session.

The gateway SHALL continue using the manifest as the durable mailbox capability source and SHALL NOT introduce a second persisted mailbox-capability flag in gateway-owned attach or notifier state.

For tmux-backed sessions, live mailbox actionability SHALL be evaluated from the current targeted `AGENTSYS_MAILBOX_*` projection published in the owning tmux session environment rather than from the provider process's inherited launch-time env snapshot.

For joined tmux-backed sessions, notifier support SHALL NOT treat unavailable relaunch posture as an additional readiness precondition once durable mailbox capability and live mailbox actionability are both satisfied.

If that manifest pointer is missing, unreadable, unparsable, or its launch plan has no mailbox binding, enabling notifier behavior SHALL fail explicitly and SHALL leave notifier inactive.

If the manifest exposes durable mailbox capability but the current live mailbox projection is unavailable, incomplete, or fails transport-specific validation for actionable mailbox work, notifier enablement SHALL fail explicitly and SHALL leave notifier inactive.

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

#### Scenario: Tmux-backed late registration becomes notifier-ready after live mailbox projection refresh
- **WHEN** a tmux-backed managed session has a durable mailbox binding in its manifest
- **AND WHEN** the owning tmux session environment publishes the current actionable mailbox projection for that binding
- **THEN** the gateway treats notifier support as available for that session without requiring provider relaunch solely to refresh inherited process env
- **AND THEN** notifier enablement may proceed using that durable-plus-live mailbox contract

#### Scenario: Joined tmux session without relaunch posture becomes notifier-ready after late registration
- **WHEN** a joined tmux-backed managed session has a durable mailbox binding in its manifest
- **AND WHEN** that joined session's relaunch posture is unavailable
- **AND WHEN** the owning tmux session environment publishes the current actionable mailbox projection for that binding
- **THEN** the gateway treats notifier support as available for that joined session
- **AND THEN** notifier enablement may proceed without requiring joined-session relaunch posture

#### Scenario: Durable mailbox presence without live mailbox actionability rejects notifier enablement
- **WHEN** a tmux-backed managed session has a durable mailbox binding in its manifest
- **AND WHEN** the owning tmux session environment lacks the current actionable mailbox projection or a required transport-local live prerequisite
- **THEN** the gateway rejects notifier enablement explicitly
- **AND THEN** notifier status reports that the session is not yet live-mailbox-actionable for notifier work
