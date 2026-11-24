# Authenticated Gateway Access Delta

## MODIFIED Requirements

### Requirement: The matched route determines caller access

Each core route SHALL declare supported authorization operations. Ingress SHALL verify supplied proof before parsing the body or invoking operation handling. It SHALL derive the selected action from verified routing and validated input and apply current policy before effects. Omitted proof SHALL admit a caller anonymously only when public, open, or default-group authority supplies the operation and its proof requirements permit it.

#### Scenario: Anonymous admin uses a valid empty list

- **WHEN** a caller invokes an eligible control operation without signing proof and the initialized admin roster is empty
- **THEN** the gateway applies the full gateway-admin role with anonymous provenance

#### Scenario: A private route is used by self and by admin

- **WHEN** the current agent and a listed admin each prove their identity and have the selected mailbox or memory permission
- **THEN** both can use the operation subject to its normal binding and input checks

#### Scenario: Self attempts key-required admin control

- **WHEN** the admin roster has entries and the current agent proves its identity without the requested control permission
- **THEN** the gateway returns HTTP 403 before control handling or native effects

#### Scenario: Unauthenticated caller supplies a malformed protected body

- **WHEN** a caller sends invalid JSON without proof to an operation requiring authentication
- **THEN** it receives HTTP 401 with applicable challenge information before request-body validation

#### Scenario: Request fields claim another role

- **WHEN** a caller supplies a role, principal, or source identity in its body or forwarded headers
- **THEN** the gateway uses the verified caller and the owner policy for the selected operation

#### Scenario: New core route lacks classification

- **WHEN** startup finds a core route without a required operation declaration
- **THEN** it refuses to publish the application

#### Scenario: Invalid proof accompanies an open request

- **WHEN** a caller submits invalid signing proof on an enabled route while the admin roster is empty
- **THEN** the attempt fails before effects and grants no anonymous admission

### Requirement: A listed admin proves possession of its registered SSH key

Direct admin roster authority SHALL use `caller` proof checked against the current registered SSH key for the expected owner binding. Verification SHALL establish the principal, exact credential enrollment, and current admin qualification. Granting `agent-admin` effects through the configured default SHALL convey no roster identity.

#### Scenario: A listed admin requests a controlled operation

- **WHEN** an enrolled admin proves possession of its registered private key for a request
- **THEN** the gateway identifies the enrolled principal and applies the gateway-admin role to supported client-facing operations in the bound domain

#### Scenario: A valid signature targets a different owner binding

- **WHEN** a signature proves possession for a different agent or execution context
- **THEN** the target denies admission

#### Scenario: An admin principal signs with a second ordinary key

- **WHEN** the caller proves a current credential of the same principal as an admin key but the signing credential itself has no admin roster entry
- **THEN** a keyed gateway applies the principal's effective assigned or default permissions without borrowing the other key's roster qualification

#### Scenario: An enrolled service key proves identity

- **WHEN** a service signs an eligible request using an owner-enrolled key
- **THEN** ingress identifies the service credential and evaluates its current permission for the requested operation

### Requirement: Owner clients select proof for each protected target

Same-agent self callers SHALL use their verified generation credentials. Peer and other enrolled callers SHALL use explicitly selected signers. Unsigned clients SHALL use current public, open, or default-group permissions where the operation permits unsigned access. Service backing authority SHALL be scoped independently. Readiness health SHALL use public access. Admission refusal SHALL terminate the attempt.

#### Scenario: Scoped self command uses its private mailbox

- **WHEN** the current agent uses the maintained command surface for a granted mailbox operation
- **THEN** the client obtains and signs the target challenge using its current generation credential
- **AND THEN** guidance and command output omit private signing material

#### Scenario: Delegated attach uses an owner-only configuration path

- **WHEN** a restricted caller supplies an access configuration path in the recorded owner context
- **THEN** the owner resolves and validates it within the existing execution binding

#### Scenario: Signed admission fails

- **WHEN** a managed or named caller cannot prove its selected key or receives an admission refusal
- **THEN** it fails before an unsigned retry, another transport, or use of a backing credential

### Requirement: Current admins and open callers use the same gateway-admin role

`agent-admin` SHALL supply all supported client-facing effects. An empty verified roster SHALL confer it through open admission. With a keyed roster, a current admin key or an applicable `agent-admin` default SHALL supply those effects. Operation-specific proof and provenance SHALL remain independent.

#### Scenario: A signed caller uses open access

- **WHEN** an eligible operation receives valid caller proof while the initialized admin roster is empty
- **THEN** the gateway applies the full gateway-admin role to signed and unsigned callers
- **AND THEN** it records the verified signer as the initiating caller

#### Scenario: An open caller attempts first enrollment without key proof

- **WHEN** a caller relies on the gateway-admin role to register the first admin key without proving possession
- **THEN** the gateway refuses enrollment before changes
- **AND THEN** first-key bootstrap remains available through its purpose-specific proof contract

#### Scenario: The gateway-admin role covers every permission for the operation

- **WHEN** a verified current admin or a caller admitted under a valid empty roster requests a supported attachment, plugin, or peer file operation
- **THEN** the role supplies all permissions needed by the selected operation and its effects
- **AND THEN** normal input, target, capability, and runtime requirements still apply

#### Scenario: A nonadmin uses a keyed gateway

- **WHEN** a verified nonadmin invokes operations on a target with a nonempty admin roster
- **THEN** the gateway resolves group permissions from the caller's retained `builtin:` assignments or the configured default and adds applicable local roles, template roles, direct grants, and public rules

### Requirement: Peer proof identifies an enrolled logical agent

An enrolled peer SHALL prove its stable logical identity with `caller` proof for its revocable enrolled key. Ingress SHALL verify possession, current enrollment, and exact target and request binding without source runtime lookup. The default SHALL provide unaffiliated caller permissions without establishing a peer identity.

#### Scenario: A managed peer uses an explicit operation grant

- **WHEN** an enrolled peer proves possession of its key for a granted operation on a keyed target
- **THEN** ingress applies the stable logical agent principal's current target-domain permissions
- **AND THEN** the peer can sign across OS accounts or after relaunch without a source gateway or live runtime verification

#### Scenario: The target owner rotates a peer credential

- **WHEN** the owner explicitly enrolls a replacement key for an existing peer principal and revokes its prior enrollment
- **THEN** the replacement key can prove the same principal and use its current grants
- **AND THEN** proof bound to the revoked enrollment fails

#### Scenario: Peer identity is supplied only as a name or key

- **WHEN** a caller offers a peer identifier or public key without valid proof bound to a current enrollment
- **THEN** ingress confers no peer identity and creates no enrollment or grant

### Requirement: Versioned File Operations Use Shared Gateway Authorization

The live target gateway SHALL authorize each file operation through the retained owner policy for the exact mount and action. Explicit identities SHALL use applicable current proof. Current agent-admin, scoped, or default-group authority SHALL supply the corresponding effects. Unsupported mounts or actions SHALL remain unavailable.

#### Scenario: An enrolled peer uses a scoped file operation

- **WHEN** an enrolled logical agent signs the exact file request with its enrolled key and current policy grants the operation on the selected mount
- **THEN** the gateway authorizes it under that peer identity
- **AND THEN** a source restart, execution context change, or unavailable source liveness evidence leaves the enrollment valid

#### Scenario: A peer requests a different mount or operation

- **WHEN** a verified nonadmin invokes a file operation on a keyed gateway outside that caller's current permissions
- **THEN** the gateway refuses the operation before effects

#### Scenario: A caller claims an enrolled identity

- **WHEN** a caller presents a logical agent label or a managed self credential without proving possession of that agent's enrolled peer key
- **THEN** the gateway assigns no authority from that peer enrollment

#### Scenario: An administrator invokes a supported file operation

- **WHEN** a caller using a current admin-enrolled key or admitted under a valid empty roster requests a supported file operation
- **THEN** gateway-admin policy supplies its required permissions for the selected target
- **AND THEN** proof, input, target, and runtime requirements still apply

#### Scenario: An unsigned caller edits under a maintainer default

- **WHEN** a keyed target's default supplies the exact qualified mount edit effect and an unsigned caller opens a draft
- **THEN** the caller can edit under the usual anonymous lease capability and mount checks
- **AND THEN** the gateway creates no peer enrollment or claimed authorship

### Requirement: File Effects Require Current Direct Target Authority

File requests SHALL use direct SSHSIG v2 proof or authorized unsigned admission at the verified target gateway. Before each effect or disclosure, it SHALL recheck the target generation, listener, exact permission, provenance, and original authority. Revalidation SHALL use the qualifying admin entry, open epoch, default setting revision, or scoped permission as applicable. Unsigned requests SHALL retain anonymous provenance.

#### Scenario: A peer's credential or grant changes after admission

- **WHEN** the owner revokes the credential or removes permission for the mount and action before the operation takes effect
- **THEN** the gateway refuses the pending operation under its earlier admission

#### Scenario: A publisher loses admin qualification

- **WHEN** the signing key loses the admin roster entry that authorized an admitted push before handoff
- **THEN** the gateway refuses the push and retains the candidate
- **AND THEN** another request may publish the candidate under current call authority

#### Scenario: The target body or gateway incarnation changes

- **WHEN** the bound target generation or listener incarnation changes before the operation takes effect
- **THEN** the gateway refuses to apply the pending operation to the replacement

#### Scenario: Open access resumes after an earlier admission

- **WHEN** a signed or unsigned request received open authority and the roster becomes keyed and then empty again before the effect
- **THEN** the gateway refuses the operation under its earlier open epoch
- **AND THEN** a fresh request can use the current open epoch

#### Scenario: A file route receives delegated proof

- **WHEN** a file route receives relay or backing-service proof in place of direct caller admission
- **THEN** the gateway refuses the request before effects

#### Scenario: The verified live target is unavailable

- **WHEN** the client cannot reach a verified live target gateway, including cases where the passive service can resolve the target
- **THEN** the file operation reports unavailable through the direct client path
- **AND THEN** no passive fallback carries out the operation

#### Scenario: A default changes before draft publication

- **WHEN** a publication admitted through a default awaits handoff and the target replaces that default
- **THEN** the earlier admission cannot publish, even if the group is selected again
- **AND THEN** the candidate remains available for a fresh authorized attempt

### Requirement: Self access follows the current managed generation

The runtime SHALL bind each active `managed-self` key to the target, execution context, and current generation. Self clients SHALL load the matching registered key from the verified owner's SQLite store and sign the bound SSHSIG challenge. Gateway restart and reattach SHALL reuse the registration. Proof checks SHALL use the active public key and current registration revision. Replacement or revocation SHALL require effective admin authority or proof from the registered key.

#### Scenario: A managed agent uses its own gateway

- **WHEN** the owner runtime establishes a generation through launch or supported join and registers its key
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
