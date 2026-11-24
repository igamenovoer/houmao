# Spec Delta

## ADDED Requirements

### Requirement: Selected-Agent Access Commands Use Verified Owner Authority

`agents single access` SHALL expose policy initialization, principal and credential administration, grant and revoke, list, and explain operations for the selected agent. The CLI SHALL resolve the observed owner binding before administrative effects. General policy changes and privileged inspection SHALL use verified local owner authority.

#### Scenario: An owner manages policy while the gateway is detached

- **WHEN** a verified owner selects the target and enrolls a principal or grants it a declared operation
- **THEN** the CLI updates that target's retained policy
- **AND THEN** the target gateway need not be attached

#### Scenario: An owner enrolls an offline or cross-account agent

- **WHEN** the verified target owner selects a logical agent principal and provides its authenticated peer public key
- **THEN** the CLI can enroll that key and assign scoped target operations
- **AND THEN** it requires no source runtime, registry record, or access to the source account

#### Scenario: The owner explicitly provisions a replacement policy

- **WHEN** a configured target has former authorization data and its owner initializes policy using a new-schema seed or an explicit empty selection
- **THEN** the CLI validates and initializes the new retained state for the selected domain
- **AND THEN** the command reports whether the resulting admin roster is open or keyed

#### Scenario: An owner inspects a scoped decision

- **WHEN** a verified owner lists grants or explains the effective permission for a principal, resource, and action
- **THEN** the command reports safe principal, assignment, and policy-revision evidence
- **AND THEN** it does not disclose private signing material, challenge state, or provider credentials

### Requirement: Selected-Agent Admin Commands Preserve First Enrollment and Live Roster Changes

The access command family SHALL expose per-key admin enrollment and removal separately from owner-local credential revocation. Remote first-key enrollment SHALL prove the proposed key. Subsequent remote roster changes SHALL prove a current admin-enrolled key and bind that proof to the selected target's roster operation.

#### Scenario: A remote operator enrolls the first key

- **WHEN** the target reports an available empty roster and a caller explicitly requests first-key enrollment
- **THEN** the CLI obtains and signs the exact first-enrollment challenge for that target
- **AND THEN** it reports the enrolled identity or the current enrollment conflict

#### Scenario: A signed admin removes the last key

- **WHEN** a caller using the final enrolled admin key removes that key's roster entry
- **THEN** the command reports the new open roster state
- **AND THEN** it does not repeat the mutation using anonymous authority

#### Scenario: The operator rotates the only admin key

- **WHEN** the operator enrolls the replacement explicitly as admin before removing the old admin entry
- **THEN** the CLI reports keyed access throughout rotation, even if both keys identify the same principal

### Requirement: Peer Caller Proof Selects Source and Target Independently

`agents self access public-key` SHALL export the logical agent ID, selected peer public key, and fingerprint from protected source configuration. The source owner SHALL be able to configure and select a stable peer credential locally. Peer requests SHALL select that signer independently of the selected target and verify the target endpoint before signing.

#### Scenario: Peer identity is exported without a gateway

- **WHEN** a managed caller requests its peer public identity with its source gateway detached
- **THEN** the CLI returns the configured peer public key, fingerprint, and logical agent ID
- **AND THEN** it omits all private key material and paths

#### Scenario: The target and source use different tmux servers

- **WHEN** an enrolled logical peer invokes a supported operation on a target in another account or tmux server
- **THEN** the CLI signs with the configured peer key and binds proof to the verified target
- **AND THEN** the target requires no source lookup or source gateway

#### Scenario: An owner selects a peer signer while its agent is stopped

- **WHEN** the source owner selects protected signer configuration for a logical agent whose runtime is stopped
- **THEN** the CLI can sign an authorized target request with that peer credential
- **AND THEN** signing does not use a current-generation self key or a credential from the selected target
