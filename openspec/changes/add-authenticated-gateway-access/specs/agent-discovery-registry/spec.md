# Spec Delta

## ADDED Requirements

### Requirement: Live gateway advertisements expose a non-secret remote descriptor

Live gateway presence SHALL support an explicit advertised base URL, gateway protocol, authentication requirement, logical agent identity, execution-context identity, and current presence identity. Remote descriptor export SHALL omit credentials, verifier values, credential paths, owner-local state paths, copied manifests, and private connection configuration. Listener coordinates SHALL remain separately qualified local metadata.

#### Scenario: Owner exports a remote endpoint without sharing runtime files

- **WHEN** an owner publishes or exports a live authenticated gateway descriptor
- **THEN** an external hub can obtain its advertised URL and authentication requirement without opening a manifest, state path, or owner filesystem
- **AND** credential distribution remains separate from that descriptor

#### Scenario: Proxy endpoint differs from local listener

- **WHEN** the owner-local gateway listens on loopback behind an explicitly configured HTTPS proxy
- **THEN** the remote descriptor publishes that HTTPS URL
- **AND** local listener metadata does not replace it with caller-local loopback

### Requirement: Gateway advertisement follows live presence without owning access policy

Advertised gateway availability SHALL be ephemeral presence metadata. Gateway stop or detach SHALL clear or invalidate live advertised availability while preserving logical identity and independently retained owner-side access configuration. Publication and discovery SHALL NOT become policy authority or infer that a protected stopped agent is anonymously controllable.

#### Scenario: Gateway detaches while its agent remains known

- **WHEN** an authenticated gateway detaches from a known agent
- **THEN** live discovery ceases advertising a reachable gateway instance
- **AND** retained owner-side protection and execution ownership remain unchanged

#### Scenario: Discovery publication lags a configuration change

- **WHEN** a published descriptor is stale or cannot be refreshed
- **THEN** clients treat it as possibly unavailable locator metadata
- **AND** it cannot override the gateway's actual access policy or establish current execution authority

### Requirement: Remote descriptors grant no credentials or lifecycle rights

Discovery SHALL NOT turn endpoint metadata into credential selection, execution delegation, or lifecycle adoption. Communication-only imports SHALL retain their existing restrictions. Foreign paths and loopback addresses SHALL remain owner-context metadata. A changed advertised origin or base path SHALL require explicit client credential rebinding before credential-bearing access.

#### Scenario: Communication import contains an authenticated gateway URL

- **WHEN** a communication-only import references a protected gateway endpoint
- **THEN** that locator alone grants no raw input, stop, relaunch, refresh, or execution-owner routing authority

#### Scenario: Registry descriptor is replaced with another origin

- **WHEN** discovery returns a different origin or base path for an existing private client binding
- **THEN** the existing credential is not automatically attached to that replacement endpoint

#### Scenario: Owner loopback port also exists on the caller host

- **WHEN** a remote execution record contains owner-local loopback listener coordinates
- **THEN** remote discovery does not authorize connecting to the same port on the caller host as a substitute

