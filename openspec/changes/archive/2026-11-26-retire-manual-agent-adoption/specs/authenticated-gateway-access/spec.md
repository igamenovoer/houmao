## MODIFIED Requirements

### Requirement: Self access follows the current managed generation

The runtime SHALL bind each active `managed-self` key to the target, execution context, and current generation. Self clients SHALL load the matching registered key from the verified owner's SQLite store and sign the bound SSHSIG challenge. Gateway restart and reattach SHALL reuse the registration. Proof checks SHALL use the active public key and current registration revision. Replacement or revocation SHALL require effective admin authority or proof from the registered key.

#### Scenario: A managed agent uses its own gateway

- **WHEN** the owner runtime establishes a generation through a supported launch and registers its key
- **THEN** the current managed caller can sign `caller` proof for its granted self operations on the same target agent

#### Scenario: A launch profile starts the runtime and gateway together

- **WHEN** a profile-driven launch returns success for the running agent and its auto-attached gateway
- **THEN** a self client in that verified generation can load its registered private key record and sign a fresh listener-bound challenge
- **AND THEN** the gateway resolves that registration whether its administrator roster is empty or keyed

#### Scenario: A fresh process signs after same-generation recovery

- **WHEN** Bob starts another headless worker or resumes within the same verified live generation
- **THEN** the self client loads the private key record selected by the current registration and signs a fresh challenge for the intended listener
- **AND THEN** the receiving ingress checks the original generation and current registration revision

#### Scenario: A managed-self key record is unavailable or invalid

- **WHEN** the owner SQLite store is missing, corrupt, or unsafe, or the selected record is absent or disagrees with the active public registration
- **THEN** the self client reports unavailable self authority before signing
- **AND THEN** it retains the selected caller without retrying unsigned or substituting another key

#### Scenario: An agent presents its key to a different gateway

- **WHEN** a managed caller presents its generation's self credential as proof for another target agent
- **THEN** ingress refuses the supplied self proof
- **AND THEN** a separate peer request can use the target's default or a valid peer enrollment

#### Scenario: Old body tries to use a retired credential

- **WHEN** an ended or replaced generation presents self proof using its previous key
- **THEN** the target denies self proof even if the logical agent ID remains known

#### Scenario: Retired joined-session proof is refused

- **WHEN** a saved `joined_tmux` session presents proof using its former managed-self registration
- **THEN** gateway and passive ingress deny managed-self proof for that retired session
- **AND THEN** retained registration data and an advertised gateway address do not authorize a new effect

#### Scenario: The gateway restarts while the agent stays live

- **WHEN** the gateway reattaches to the same managed generation and authorization selection
- **THEN** the current generation key can sign a fresh challenge for the new listener and the caller's granted operations

#### Scenario: First admin registration races a self challenge

- **WHEN** the first admin enrolls after a current managed caller receives a challenge for an explicitly granted self operation
- **THEN** otherwise valid proof can still authorize that operation if the credential and exact permission remain current

#### Scenario: The registered key changes after proof was admitted

- **WHEN** a protected effect is pending and an authorized replacement changes the current managed-self registration
- **THEN** proof tied to the earlier revision cannot authorize that effect
- **AND THEN** the new key must obtain proof for the current target and listener
