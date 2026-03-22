## ADDED Requirements

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
