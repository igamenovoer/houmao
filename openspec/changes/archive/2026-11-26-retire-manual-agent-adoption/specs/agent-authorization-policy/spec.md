## ADDED Requirements

### Requirement: Managed Runtime Registration Requires a Verified Supported Generation

The verified execution owner SHALL prepare a fresh Ed25519 key and its public registration for each generation established by a supported Houmao launch or managed relaunch. Provisioning SHALL work independently of any listener. Registration SHALL bind the key to its owner, target, and generation. Gateway and passive ingress SHALL accept managed-self proof only for the live current generation and its current registration revision.

#### Scenario: A combined launch prepares registration before startup

- **WHEN** the owner reserves a new generation to launch Bob and attach his gateway
- **THEN** Houmao commits the private key record and public registration before starting Bob's native runtime or attaching his gateway

#### Scenario: A retired joined session has an existing registration

- **WHEN** a saved `joined_tmux` session still has a public registration and private key record
- **THEN** the retired session does not qualify for managed-self authorization
- **AND THEN** recognizing it does not rewrite or remove the retained authorization state

#### Scenario: A gateway attaches after the runtime starts

- **WHEN** Bob starts with the gateway detached and an operator later attaches it
- **THEN** the gateway uses the registration prepared by Bob's verified execution owner
- **AND THEN** another detach and reattach within that generation uses the same registration with fresh proof for the new listener

#### Scenario: The passive server serves the live runtime without a gateway

- **WHEN** the current managed-self signer proves a qualified operation on its own target through the passive server while the agent gateway is detached
- **THEN** the passive server resolves the current runtime registration and checks the target's retained policy
- **AND THEN** the operation neither starts a gateway nor uses a backing service credential as client proof

#### Scenario: A prepared generation is unavailable for self proof

- **WHEN** the owner creates the key and registration before the generation becomes live and current
- **THEN** the prepared registration becomes usable for self proof only after Houmao verifies that generation as live and current

#### Scenario: The current key is unavailable on a keyed target

- **WHEN** a managed-self call selects a keyed gateway but the current runtime's registration or private key record is unavailable
- **THEN** the call reports unavailable self authorization without substituting an enrolled peer or administrator credential

#### Scenario: A managed-self key collides with an enrolled key

- **WHEN** an enrollment attempts to qualify the current managed-self public key as a peer or administrator, or registration presents a public key already enrolled for those purposes
- **THEN** the gateway or owner policy operation rejects the conflicting use

## REMOVED Requirements

### Requirement: Managed Runtime Registration Uses Verified Local Authority

**Reason:** The owner no longer registers generations through manual session adoption.

**Migration:** Use managed launch or relaunch for newly registered generations. Existing retained state remains subject to current runtime verification.
