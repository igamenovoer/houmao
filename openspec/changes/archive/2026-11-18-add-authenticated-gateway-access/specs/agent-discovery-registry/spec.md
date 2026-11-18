# Spec Delta

## ADDED Requirements

### Requirement: Live gateway advertisements expose a non-secret remote descriptor

Live gateway presence SHALL support an advertised URL, protocol, target and presence identity, admin access state, signed self and admin proof requirements, and enabled public operations. The descriptor SHALL omit key membership, signatures, challenge material, credentials, and private runtime state. Listener coordinates SHALL remain separately qualified local metadata.

#### Scenario: Owner exports a remote endpoint without sharing runtime files

- **WHEN** an owner publishes a bound gateway with public input enabled
- **THEN** an external hub can discover its advertised URL, available public notification and prompt operations, and whether admin calls are open or key-required
- **AND** the descriptor identifies private proof requirements separately

#### Scenario: Proxy endpoint differs from local listener

- **WHEN** the owner-local gateway listens on loopback behind an explicitly configured HTTPS proxy
- **THEN** the remote descriptor publishes that HTTPS URL
- **AND** local listener metadata does not replace it with caller-local loopback

### Requirement: Gateway advertisement follows live presence without owning access policy

Advertised gateway availability SHALL be ephemeral presence metadata. Gateway stop or detach SHALL clear or invalidate live advertised availability while preserving logical identity and independently retained owner-side access configuration. Publication and discovery SHALL NOT become policy authority or infer that a protected stopped agent is anonymously controllable.

#### Scenario: Gateway detaches while its agent remains known

- **WHEN** a protected gateway detaches from a known agent
- **THEN** live discovery ceases advertising a reachable gateway instance
- **AND** retained owner-side protection and execution ownership remain unchanged

#### Scenario: Discovery publication lags a configuration change

- **WHEN** a published descriptor is stale or cannot be refreshed
- **THEN** clients treat it as possibly unavailable locator metadata
- **AND** it cannot override the gateway's actual access policy or establish current execution authority

#### Scenario: Discovery still advertises open access after first enrollment

- **WHEN** discovery's last publication predates first-key registration
- **THEN** using that descriptor cannot bypass the target's current listed-key requirement

### Requirement: Remote descriptors grant no credentials or lifecycle rights

Discovery SHALL treat endpoint metadata as a locator. Protected credential selection, execution delegation, and lifecycle adoption SHALL require their own authority. Communication-only imports SHALL retain their existing scope. Foreign paths and loopback addresses SHALL remain owner-context metadata. Changed advertised target or endpoint bindings SHALL require explicit client rebinding before credential-bearing access.

#### Scenario: Communication import contains an authenticated gateway URL

- **WHEN** a communication-only import references a gateway with public input enabled
- **THEN** it can locate and call the available public operations
- **AND** admin admission uses the live key list, private calls require verified proof, and execution delegation follows its existing authority

#### Scenario: Registry descriptor is replaced with another origin

- **WHEN** discovery returns a different origin or base path for an existing private client binding
- **THEN** the existing credential is not automatically attached to that replacement endpoint

#### Scenario: Owner loopback port also exists on the caller host

- **WHEN** a remote execution record contains owner-local loopback listener coordinates
- **THEN** remote discovery does not authorize connecting to the same port on the caller host as a substitute

