# passive-server-gateway-proxy Delta

## MODIFIED Requirements

### Requirement: Protected target proxy calls retain caller authority

A passive proxy SHALL enforce the selected target's route class and current key state. An admitted anonymous private or admin call SHALL be forwarded unsigned to the selected gateway for current admission. Discovery and source addresses SHALL serve as connection information.

#### Scenario: Unauthenticated caller requests privileged proxy control

- **WHEN** an unauthenticated caller invokes a target's prompt, raw-key, refresh, or mailbox-binding proxy while its admin list has entries
- **THEN** the request is rejected before any downstream operation
- **AND** owner-client credentials stay unused

#### Scenario: First enrollment races an anonymous admin proxy call

- **WHEN** a proxy admits an open private or admin call and a key is registered before the receiving gateway admits the downstream request
- **THEN** the downstream operation is refused under the key-required rule

#### Scenario: A private proxy call is anonymous in open mode

- **WHEN** an unsigned caller selects a private proxy operation on a target with a valid empty roster
- **THEN** both ingress and the receiving gateway apply the current open policy
- **AND THEN** the resulting operation preserves anonymous caller provenance

### Requirement: Signed proxy requests carry only admitted caller authority

The passive ingress SHALL consume signed self or admin proof at admission. It SHALL relay the verified principal, role, and current key through explicit owner-local authority using a short-lived, single-use record for the exact downstream request. The gateway SHALL verify that record, current grant, and target before effects.

#### Scenario: Request path or body changes across the proxy

- **WHEN** the passive ingress authorizes a signed request whose downstream path or body differs
- **THEN** the gateway uses a verified record for the exact transformed operation and preserves the caller's identity and role

#### Scenario: Admitted self caller is forwarded

- **WHEN** a proxy admits a self signature for a private operation
- **THEN** the downstream record retains its self role and current generation binding
- **AND** the original signature stays bound to the passive ingress

#### Scenario: The generation changes during a signed self relay

- **WHEN** the managed generation changes before the gateway admits the downstream private request
- **THEN** the receiving gateway refuses the relay before effects

#### Scenario: Relayed authority is replayed or the key has been removed

- **WHEN** a downstream request reuses a relay record or its admitted grant ceased to be current before gateway admission
- **THEN** the gateway refuses the request without using open access or a substitute credential

### Requirement: Direct passive paths cannot bypass protected agent access

Direct selected-agent operations SHALL enforce retained owner policy before effects. Routine protected reads SHALL use private access. A valid empty roster permits anonymous admission to private and admin operations. Direct turns, native observation and artifacts, interruption, stop, and gateway lifecycle SHALL use admin admission. The passive ingress SHALL issue and verify challenges for its own signed operations independently of live discovery.

#### Scenario: Direct stop would otherwise kill tmux

- **WHEN** an unauthenticated caller invokes direct stop for a discovered agent with a nonempty admin list
- **THEN** it is rejected before tmux termination or registry cleanup

#### Scenario: Direct headless match has no discovery record

- **WHEN** a protected managed-headless target is found through its retained control state without a live discovery record
- **THEN** prompt, interrupt, stop, private state, and artifact requests require their declared target access

#### Scenario: Gateway detachment removes its live record

- **WHEN** a protected target has no live gateway record after detachment
- **THEN** direct private and admin operations still use the recorded open or key-required state

#### Scenario: Enrollment races a direct anonymous operation

- **WHEN** a direct operation's anonymous grant has ceased to be current before its effect boundary
- **THEN** the operation is refused before accessing or changing the target
