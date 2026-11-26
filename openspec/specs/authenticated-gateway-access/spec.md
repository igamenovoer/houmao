# authenticated-gateway-access Specification

## Purpose

Define public, private, and admin access to a managed agent gateway, including launch enrollment, live admin keys, request-bound signatures, and secure endpoint connections.

## Requirements

### Requirement: Gateway deployment is explicit and loopback by default

A gateway SHALL default to loopback. A broader listener SHALL require explicit valid settings and initialized owner authorization state before publication or plugin activation. Every listener SHALL enforce the same owner policy and any operation-specific transport constraints.

#### Scenario: Unconfigured gateway starts on loopback

- **WHEN** the owner first launches a gateway-capable agent without explicit access settings or admin keys
- **THEN** its gateway starts on loopback with a valid empty admin roster and current managed self authority
- **AND THEN** public input and remote endpoint advertisement require explicit configuration

#### Scenario: Broader bind lacks validated settings

- **WHEN** startup selects a broader listener without valid explicit settings and owner authorization state
- **THEN** startup fails before publishing an endpoint or activating plugins

#### Scenario: Local protected access has the same proof requirement

- **WHEN** a caller reaches a proof-required operation through loopback without proof
- **THEN** the gateway returns HTTP 401 with applicable challenge information

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

### Requirement: The launch manifest seeds a durable admin key list

An owner-authorized first launch SHALL accept zero or more named admin public keys in the current launch configuration and record the seed in the launch manifest. It SHALL initialize the current retained owner policy and admin roster for that binding. Restart, reattach, and ordinary relaunch SHALL use the retained state.

#### Scenario: Launch pre-registers administrators

- **WHEN** an authorized launcher supplies named admin public keys
- **THEN** each selected key becomes part of the initial admin roster and proof from that key receives the full gateway-admin role
- **AND THEN** proof is required for protected operations outside the public policy from the first publication

#### Scenario: Launch omits admin keys

- **WHEN** an authorized first launch supplies no admin keys
- **THEN** it records a valid empty roster and enables first-key bootstrap and eligible open operations

#### Scenario: A previously seeded key was removed

- **WHEN** a gateway restarts or the same agent binding relaunches after an admin removes a seeded key
- **THEN** startup uses retained owner state and does not restore the key's removed admin enrollment

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

### Requirement: Signed challenges bind one proof to the intended request

The ingress SHALL issue bounded, expiring, single-use SSHSIG challenges for `caller` and first-admin bootstrap. Each challenge SHALL bind purpose, issuer, target execution and listener incarnation, method, path, query, and raw body digest. Caller challenges SHALL bind the selected enrollment or same-target self generation and key. Bootstrap SHALL bind the proposed key, principal, and empty roster revision.

#### Scenario: Expired or used proof is presented

- **WHEN** a caller presents an expired challenge or repeats a consumed proof
- **THEN** the requested operation is refused before effects

#### Scenario: Signed request is altered or retargeted

- **WHEN** the method, path, query, raw body, issuer, target execution, or listener incarnation differs from the issued challenge
- **THEN** ingress refuses the proof before operation handling

#### Scenario: A bound generation or policy revision changes during proof

- **WHEN** a bound target generation, same-target self generation, credential enrollment, or bootstrap roster revision changes before admission commits
- **THEN** the earlier proof cannot authorize the new state

#### Scenario: Caller attempts to use a proof for a different purpose

- **WHEN** a proof issued for `caller`, first-admin bootstrap, or interactive Web approval is presented for another purpose
- **THEN** the purpose check refuses it before effects

#### Scenario: Earlier signed proof follows the final key removal

- **WHEN** a caller presents stale signed proof for a revoked enrollment after the final admin key is removed
- **THEN** the signed attempt fails before effects
- **AND THEN** a separate unsigned request can use the full gateway-admin role through open admission

### Requirement: Ingress verifies standard signatures in process

Gateway and passive ingress SHALL verify SSHSIG proofs in process. They SHALL check the expected namespace and the public key selected by owner enrollment, current same-target self authority, or bootstrap. Malformed, unsupported, or mismatched proofs SHALL be rejected before effects.

#### Scenario: Verifier runs with external SSH tools absent

- **WHEN** an ingress receives valid SSHSIG proof for a supported key while external SSH commands are unavailable
- **THEN** its in-process verifier establishes caller provenance for current policy evaluation

#### Scenario: The envelope supplies a different key or namespace

- **WHEN** the SSHSIG envelope names a key or namespace different from the expected proof binding
- **THEN** admission fails even if the signature could verify under the supplied key and namespace

### Requirement: The first admin key can be registered after startup

Any caller SHALL be able to register the first named admin key through the bootstrap operation by proving possession of the proposed key. Registration SHALL bind a verified empty roster and commit the first enrollment only while that exact roster revision remains empty. The resulting policy SHALL end open admission.

#### Scenario: First registration closes open admin access

- **WHEN** a running gateway commits valid first-admin registration against the current empty roster
- **THEN** it enrolls the named admin and stops conferring the gateway-admin role on all callers

#### Scenario: Registrant supplies a key without matching proof

- **WHEN** a caller attempts first registration without valid proof from the proposed key
- **THEN** the gateway returns HTTP 401 and leaves the empty roster intact

#### Scenario: A registrant reuses another principal's display label

- **WHEN** a first-key registrant supplies a display label already used by a distinct principal
- **THEN** registration cannot attach the proposed key to the other principal or acquire that principal's separate grants

#### Scenario: Two callers compete to register first

- **WHEN** two distinct callers prove possession for first-admin challenges issued against the same empty revision
- **THEN** only the first successful registration commits
- **AND THEN** the other valid competitor receives HTTP 409 without adding its key

### Requirement: Current admins can add and remove keys live

Proof with a current admin-enrolled key SHALL allow adding or removing admin roster entries, including the signing entry. The gateway SHALL recheck the exact key's roster membership at commit. Roster changes SHALL update membership and revision atomically. Removing admin enrollment SHALL preserve the underlying credential. Revoking the credential SHALL invalidate proof and remove its admin entry atomically.

#### Scenario: Multiple admins use their own keys

- **WHEN** a current admin enrolls another named admin key
- **THEN** each holder can prove its own identity and use the full gateway-admin role without restarting the gateway

#### Scenario: An admin key is revoked

- **WHEN** the verified owner revokes a credential enrolled as admin and another admin key remains
- **THEN** later admissions reject proofs for the revoked credential and assess proofs for remaining keys normally
- **AND THEN** work already handed off follows its existing execution contract

#### Scenario: An admin removes only a key's admin qualification

- **WHEN** a current administrator removes one key's roster entry and another admin key remains
- **THEN** that key can still authenticate the same principal and use its ordinary grants
- **AND THEN** an earlier admission bound to the removed roster entry cannot authorize new effects

#### Scenario: The last admin key is removed

- **WHEN** the final admin key loses its roster entry, including when ordinary keys for the same principal remain
- **THEN** subsequent callers receive the full gateway-admin role through open admission
- **AND THEN** the gateway can accept a new first-admin bootstrap

#### Scenario: A current caller lacks roster permission

- **WHEN** an authenticated nonadmin requests live roster management on a target with a nonempty admin roster
- **THEN** the gateway returns HTTP 403 before changing the roster

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

### Requirement: State and client proofs use explicit sources

Retained policy and file-based signing material SHALL use owner-verified, bounded storage outside project checkouts. Unsafe ownership, permissions, symlinks, duplicates, and malformed values SHALL fail validation. Peer signers SHALL come from explicit protected source configuration independently of the selected destination. Other enrolled callers SHALL also select signers explicitly.

#### Scenario: An unsafe source is selected

- **WHEN** a required state or credential source is shared, symlinked, checkout-local, or owned by an unexpected account
- **THEN** the gateway rejects the source with a safe error

#### Scenario: Duplicate keys or fields are supplied

- **WHEN** an admin roster repeats a public key or a state document repeats a field
- **THEN** validation fails without selecting an order-dependent entry

#### Scenario: A selected signer or secret is missing

- **WHEN** a client lacks its selected source while another login, provider, mailbox, plugin, or admin credential is available
- **THEN** the client reports the unavailable binding before transmitting the protected request

### Requirement: Protected errors distinguish missing proof and denied authority

Ingress SHALL return HTTP 401 with applicable challenge information for missing required or invalid proof, and HTTP 403 when verified proof has insufficient authority. Elevated forms of an operation SHALL require their own permission before privileged effects.

#### Scenario: Self requests an owner-file attachment

- **WHEN** a managed nonadmin on a target with a nonempty admin roster has ordinary mail permission and requests an owner-local attachment without its required permission
- **THEN** the response is HTTP 403 before a file is opened or a provider is called

#### Scenario: A roster change invalidates an anonymous grant

- **WHEN** a deferred operation relying on an earlier open permission reaches its effect check after the first admin enrolls
- **THEN** the current policy denies that stale permission before the privileged effect

### Requirement: Unavailable access state fails closed

Invalid, unavailable, or obsolete required authorization state SHALL prevent gateway publication. If state becomes unavailable during operation, dependent admission SHALL return safe HTTP 503. Open admission SHALL require a verified, initialized empty admin roster. Restoring valid current state SHALL allow later requests without replaying earlier work.

#### Scenario: Previously initialized state disappears after startup

- **WHEN** a known agent's current required policy becomes missing, unreadable, unsafe, or malformed
- **THEN** new admissions relying on it fail with HTTP 503
- **AND THEN** public process health remains available

#### Scenario: A valid policy is restored

- **WHEN** valid current state for the same owner binding is restored
- **THEN** later admissions use its recorded grants and admin roster

### Requirement: Gateway transport supports verified deployment trust

Remote gateway clients SHALL use HTTPS with certificate verification. A supported reverse proxy SHALL use a protected backend leg and leave proof verification and operation authorization to the ingress. Clients SHALL support explicitly provisioned deployment trust and explicit loopback HTTP for owner-local access or an encrypted tunnel.

#### Scenario: Private CA or explicitly trusted deployment certificate

- **WHEN** the caller selects deployment trust and HTTPS verifies for the advertised host
- **THEN** it can reach the configured gateway through the proxy
- **AND THEN** the gateway independently authorizes the selected operation

#### Scenario: Client selects remote plaintext

- **WHEN** a client is configured with a non-loopback HTTP base URL
- **THEN** it rejects the URL before sending a request

#### Scenario: Certificate verification fails

- **WHEN** the HTTPS certificate does not verify for the expected endpoint
- **THEN** the client stops without retrying it over HTTP

### Requirement: Client proof is bound to the expected endpoint

Credential-bearing clients SHALL pin the origin, base path, target execution, and live listener incarnation. They SHALL verify the challenge's purpose, credential, and full request binding before signing, carry proof in headers, and reject redirects. Changed bindings SHALL require explicit rebinding.

#### Scenario: Reverse proxy uses a path prefix

- **WHEN** a client selects an HTTPS gateway binding with an agent-specific prefix
- **THEN** the challenge and operation requests stay under that configured prefix

#### Scenario: Discovery retargets the endpoint

- **WHEN** discovered identity, origin, base path, or listener incarnation differs from a selected binding
- **THEN** the client reports a conflict before transmitting proof

#### Scenario: Endpoint redirects a call

- **WHEN** a selected endpoint responds with a redirect
- **THEN** the client stops with a redirect failure before following it or replaying the operation

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

### Requirement: Retained owner policy protects alternate HTTP paths

Alternate HTTP paths SHALL apply the selected target's retained owner policy to their semantic operations before effects. Discovery and gateway presence SHALL serve as lookup evidence. Required authority that cannot be resolved SHALL prevent admission.

#### Scenario: Direct managed-headless target resolves before registry discovery

- **WHEN** an HTTP operation selects a configured agent through retained headless authority without a live registry or gateway record
- **THEN** the retained policy determines whether it admits anonymous access or requires a verified permitted caller

#### Scenario: Agent or gateway stops

- **WHEN** an HTTP request selects a configured target after its live gateway disappears
- **THEN** the retained policy applies to supported stopped-state operations
- **AND THEN** an ended generation cannot authenticate a self caller

### Requirement: Gateway proof is scoped to an existing execution binding

HTTP admission SHALL apply only to the verified target agent, execution context, and listener incarnation. Mailbox binding, readiness, and body-incarnation checks SHALL remain authoritative. Direct local execution and policy administration SHALL require verified owner authority, and internal backing entrances SHALL require their bound service authority.

#### Scenario: Caller claims a different execution owner

- **WHEN** a caller supplies another executor, UID, host, or container
- **THEN** the request gains no replacement execution binding

#### Scenario: Body changes during dispatch

- **WHEN** execution authority changes between admission and handoff
- **THEN** the current-body guard refuses the stale operation before replay to a replacement

### Requirement: Deployment settings change through explicit gateway reconfiguration

Changing listener, public-input enablement, advertised URL, or selected client binding SHALL require explicit gateway reconfiguration and restart. Conflicting live attach SHALL fail before persistence. Authorized roster and policy updates SHALL be independent of deployment settings.

#### Scenario: Conflicting attach supplies a different selection

- **WHEN** a live attach changes its listener or public-input setting
- **THEN** the gateway reports a restart-required conflict before persisting the candidate

#### Scenario: Equivalent attach reuses the gateway

- **WHEN** attach resolves the same deployment settings
- **THEN** it can reuse the listener and preserve the managed generation and retained policy

### Requirement: Access diagnostics expose safe provenance

Public status, discovery, errors, and diagnostics SHALL exclude secrets, signatures, replayable challenge material, raw auth headers, private paths, and roster contents. Safe request diagnostics SHALL identify the operation, result, target, and verified principal or anonymous provenance.

#### Scenario: A recognizable invalid proof is presented

- **WHEN** a caller sends a recognizable invalid signature or owner-service credential
- **THEN** the response and diagnostics omit the proof and raw headers

#### Scenario: Private source validation fails

- **WHEN** policy or client selection fails validation
- **THEN** diagnostics use safe field locations and error categories

### Requirement: Browser entry issuance follows current direct gateway access

Direct owner-local Web ticket issuance SHALL require the current `web.enter` permission, whether granted through the gateway-admin role or scoped policy. Admission SHALL precede native sign-in lookup. Ticket redemption SHALL require the issued bearer and recheck authority for the same bound native redirect.

#### Scenario: The admin roster is empty

- **WHEN** an unsigned direct caller requests a ticket for an eligible live Web agent with a valid empty admin roster
- **THEN** the gateway issues the ticket under the gateway-admin role and binds it to the current roster revision

#### Scenario: The current agent or a backing service requests issuance

- **WHEN** the current managed caller lacks `web.enter` or a caller relies on delegated relay or backing authority for issuance
- **THEN** the gateway returns HTTP 403 before looking up the native destination

#### Scenario: A signed gateway client requests a ticket for the browser

- **WHEN** a named or managed caller signs a direct request and has `web.enter`
- **THEN** it receives the ticket result without a redirect, including when the caller holds only scoped Web entry permission
- **AND THEN** only the browser follows the redemption redirect, independently of public prompt enablement

#### Scenario: Direct issuance is missing required proof

- **WHEN** an unsigned request reaches ticket issuance with a nonempty admin roster
- **THEN** the gateway returns HTTP 401 with applicable challenge information

#### Scenario: Direct issuance carries invalid proof

- **WHEN** a request presents invalid signing proof with either roster state
- **THEN** the gateway returns HTTP 401 before reading native sign-in data

### Requirement: Interactive Web login proof authorizes only its pending entry

The terminal callback SHALL verify a short-lived SSHSIG challenge specific to Web approval. The challenge SHALL bind the waiting browser attempt, issuer, listener incarnation, target execution, and approval operation. A valid signature from a current credential with `web.enter` SHALL authorize one browser claim for that attempt. The callback SHALL return only an outcome.

#### Scenario: A valid signature is mixed with unenrolled candidates

- **WHEN** one bounded callback submits multiple signatures for the exact challenge
- **THEN** the gateway approves the login if any signature verifies for a currently authorized `web.enter` caller
- **AND THEN** earlier invalid or unauthorized candidates do not consume the challenge before a permitted signer is evaluated

#### Scenario: A proof is replayed or used outside its purpose

- **WHEN** a caller reuses successful Web proof or supplies it for another gateway, attempt, agent, or operation
- **THEN** the request grants no additional approval or ticket

#### Scenario: An unenrolled identity attempts approval

- **WHEN** the callback has only unknown, invalid, delegated, or unpermitted proofs
- **THEN** the terminal receives a safe refusal that omits roster details and browser and native credentials

### Requirement: Gateway operations require their declared permissions

The ingress SHALL authorize the admitted caller for the selected target, resource, and semantic action under the retained owner policy. Detailed status, usage, memory, bound mail, control, and plugin operations SHALL each declare their permissions. A service's configured identity SHALL remain separate from an initiating caller.

#### Scenario: A granted caller selects a native conversation

- **WHEN** a caller with the selected target's conversation selection permission requests a supported session or execution selection
- **THEN** the gateway uses the existing control contract for the bound agent

#### Scenario: Self inspects usage and reads memory

- **WHEN** the current agent signs with its generation key and holds the respective usage and memory permissions
- **THEN** it can use those operations subject to their normal bounds

#### Scenario: Admin sends mail through the owner's mailbox

- **WHEN** a verified admin with mail send permission uses a current mailbox binding
- **THEN** the configured binding determines the mailbox service identity
- **AND THEN** the caller remains the initiating admin principal

#### Scenario: Anonymous caller uses a bound mailbox

- **WHEN** an unsigned caller invokes an eligible bound mailbox operation under a valid empty admin roster
- **THEN** the operation preserves the configured mailbox identity and anonymous caller provenance

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

### Requirement: Gateway access requires current authorization formats

Gateway and passive ingress SHALL use the current proof and policy contracts. Old proof envelopes SHALL be rejected. Old retained authorization state SHALL be unavailable until explicitly reprovisioned through trusted owner authority.

#### Scenario: A deployment presents an earlier roster format

- **WHEN** the owner has only earlier authorization state for the target
- **THEN** protected access remains unavailable
- **AND THEN** the ingress does not interpret the old roster as an empty current roster

#### Scenario: A client sends an earlier proof format

- **WHEN** a caller presents a proof envelope from an earlier gateway contract
- **THEN** ingress refuses the protected request before operation handling

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
