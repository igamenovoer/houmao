## MODIFIED Requirements

### Requirement: Pair-authority client detection accepts `houmao-passive-server`
The system SHALL provide a pair-authority client factory that probes `GET /health` and accepts `houmao_service == "houmao-passive-server"` as the maintained pair authority.

The factory SHALL return a passive-server-aware managed client for `houmao-passive-server` and SHALL reject raw CAO, standalone `houmao-server`, or unknown service identities with an explicit unsupported-pair error for maintained manager/API operations.

Retained old-server client classes MAY remain importable as internal compatibility helpers while maintained callers are migrated, but factory selection for current user-facing flows SHALL NOT treat standalone `houmao-server` as a supported authority.

#### Scenario: Passive server health selects the passive client
- **WHEN** a pair-facing consumer resolves a client for a base URL whose `GET /health` response is `{"status": "ok", "houmao_service": "houmao-passive-server"}`
- **THEN** the factory returns a passive-server-aware managed client
- **AND THEN** the caller does not reject the passive server as an unsupported authority

#### Scenario: Old server health is rejected explicitly
- **WHEN** a pair-facing consumer resolves a client for a base URL whose health identity is `houmao-server`
- **THEN** client resolution fails explicitly for maintained user-facing flows
- **AND THEN** the error points to `houmao-passive-server` as the maintained server API authority

#### Scenario: Unknown pair identity is rejected explicitly
- **WHEN** a pair-facing consumer resolves a client for a base URL whose health identity is neither `houmao-passive-server` nor another explicitly maintained future authority
- **THEN** client resolution fails explicitly
- **AND THEN** the error does not pretend the target is a supported Houmao pair authority

### Requirement: Managed-api-base-url consumers support passive server managed authorities
Any runtime component that uses `managed_api_base_url` metadata to create a managed client SHALL resolve that client through the pair-authority client factory and SHALL support `houmao-passive-server` as the maintained managed authority.

Runtime components SHALL NOT require standalone `houmao-server` support for new or current `managed_api_base_url` metadata. Legacy metadata that points at `houmao-server` MAY fail with explicit retirement guidance rather than silently falling back to old server clients.

#### Scenario: Gateway-managed headless adapter talks to a passive server
- **WHEN** a gateway-managed headless adapter receives `managed_api_base_url` metadata pointing to a passive server
- **THEN** it creates a passive-server-aware managed client through the pair-authority factory
- **AND THEN** it can inspect managed-agent detail and submit prompt or interrupt requests without requiring `HoumaoServerClient`

#### Scenario: Gateway-managed metadata rejects retired old-server authority
- **WHEN** a gateway-managed headless adapter receives `managed_api_base_url` metadata pointing to a standalone old-server authority
- **THEN** managed client resolution fails explicitly
- **AND THEN** the failure does not imply that old-server authority is still maintained for current launches
