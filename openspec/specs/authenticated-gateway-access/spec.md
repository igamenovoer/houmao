# authenticated-gateway-access Specification

## Purpose

Define public, private, and admin access to a managed agent gateway, including launch enrollment, live admin keys, request-bound signatures, and secure endpoint connections.

## Requirements

### Requirement: Gateway deployment is explicit and loopback by default

A gateway SHALL default to loopback. A broader listener SHALL require explicitly selected valid settings and initialized owner access state before publication or plugin activation. Every listener SHALL apply the same route access policy.

#### Scenario: Unconfigured gateway starts on loopback

- **WHEN** the owner first launches a gateway-capable agent without explicit access settings or admin keys
- **THEN** its gateway starts on loopback with a valid empty admin list and current self access
- **AND** public input and remote endpoint advertisement require explicit configuration

#### Scenario: Broader bind lacks validated settings

- **WHEN** startup selects a broader listener without valid explicit settings and owner access state
- **THEN** startup fails before publishing an endpoint or activating plugins

#### Scenario: Local protected access has the same proof requirement

- **WHEN** a caller reaches a private route or a key-required admin route through loopback without proof
- **THEN** the gateway returns HTTP 401 with applicable challenge information

### Requirement: The matched route determines caller access

The gateway SHALL admit anyone to enabled public routes. Private routes SHALL require signed proof of the current self key or a listed admin key. Admin routes SHALL admit anyone when the valid admin list is empty and require a listed-key proof when it contains entries. Check required proof before body parsing, lifecycle handling, or effects. Missing core classifications SHALL prevent publication.

#### Scenario: Anonymous admin uses a valid empty list

- **WHEN** a caller invokes an admin control route without signing proof and the initialized list is empty
- **THEN** the gateway admits the request with anonymous provenance
- **AND** a private call from that caller still requires current self or admin proof

#### Scenario: A private route is used by self and by admin

- **WHEN** the current agent and a listed admin separately call a private mailbox or memory route with valid proof
- **THEN** both can use the operation subject to its normal binding and input checks

#### Scenario: Self attempts key-required admin control

- **WHEN** the admin list contains entries and the agent presents only valid self proof on an admin route
- **THEN** the gateway returns HTTP 403 before the operation reaches its handler or backend

#### Scenario: Unauthenticated caller supplies a malformed protected body

- **WHEN** a caller sends invalid JSON to a private or key-required admin operation without proof and policy is available
- **THEN** it receives HTTP 401 with applicable challenge information before request-body validation

#### Scenario: Request fields claim another role

- **WHEN** a caller supplies a role, principal, or source identity in its body or forwarded headers
- **THEN** the gateway uses the matched operation and proof established by owner policy

#### Scenario: New core route lacks classification

- **WHEN** startup finds an application route without a core classification
- **THEN** it refuses to publish the application

### Requirement: Private routes cover routine operations owned by the agent

Detailed gateway status, usage, memory, and routine operations on the bound mailbox SHALL require private access. Mail and plugin operations SHALL retain the configured service identity. Caller proof SHALL identify the initiating principal separately from that service identity.

#### Scenario: Self inspects usage and reads memory

- **WHEN** the current agent selects its bound gateway and signs with its current self key
- **THEN** it can use its usage and memory routes subject to each operation's normal bounds

#### Scenario: Admin sends mail through the owner's mailbox

- **WHEN** a verified admin sends ordinary mail with a current mailbox binding
- **THEN** the bound mailbox determines the service identity
- **AND** the caller remains the initiating admin principal

### Requirement: Privileged operations use the admin route class

Queued requests, direct prompt control, interruption, raw input, session and model selection, reminders, notifier controls, native inspection and refresh, AG-UI, operator-origin post, mailbox binding changes, plugin controls, and admin key management SHALL use the admin class. Key registration SHALL also enforce its enrollment contract.

#### Scenario: An admitted admin selects a native conversation

- **WHEN** a caller admitted by the admin route policy submits supported session or execution selection
- **THEN** the gateway uses the existing control contract for the bound agent

### Requirement: The launch manifest seeds a durable admin key list

An owner-authorized first launch SHALL accept zero or more admin public keys and persist their seed in the launch manifest. It SHALL initialize a valid live list for the agent and execution context. Subsequent gateway startup, reattach, and ordinary relaunch of that binding SHALL use the retained live list.

#### Scenario: Launch pre-registers administrators

- **WHEN** an authorized launcher supplies admin public keys
- **THEN** each selected key and principal becomes part of the initial admin list
- **AND** admin operations require proof from the first published instance

#### Scenario: Launch omits admin keys

- **WHEN** an authorized first launch supplies no admin keys
- **THEN** it persists a valid empty list and allows the gateway to start and accept first-key registration

#### Scenario: A previously seeded key was removed

- **WHEN** a gateway restarts or the same agent binding relaunches after an admin removes a seeded key
- **THEN** startup uses the retained list without restoring the removed key from the manifest

### Requirement: A listed admin proves possession of its registered SSH key

Admin proof SHALL use an SSH signature checked against a public key in the live list for the expected agent and execution context. The registered entry SHALL identify the principal. Verified admin authority SHALL cover private and admin operations of that bound agent.

#### Scenario: A listed admin requests a controlled operation

- **WHEN** a listed caller proves possession of its private key for the request
- **THEN** the gateway admits it as the registered principal
- **AND** that proof can authorize the selected private or admin operation

#### Scenario: A valid signature targets a different owner binding

- **WHEN** a signature proves possession for a different agent or execution context
- **THEN** the target denies admission

### Requirement: Signed challenges bind one proof to the intended request

The public challenge operation SHALL issue bounded, expiring, single-use challenges for self, admin, and first registration. Bind each to its purpose, issuer, target and incarnation, and HTTP method, path, query, and body digest. Self challenges SHALL bind the current generation and self key. Admin and registration challenges SHALL bind the admin list revision. Admission SHALL consume verified proof before effects.

#### Scenario: Expired or used proof is presented

- **WHEN** a caller presents an expired challenge or repeats a proof consumed earlier
- **THEN** the requested operation is refused before effects

#### Scenario: Signed request is altered or retargeted

- **WHEN** the method, path, query, body, admitting endpoint, or target differs from the issued challenge
- **THEN** the proof is refused before operation handling

#### Scenario: A bound generation or policy revision changes during proof

- **WHEN** the challenge's bound target incarnation, self generation, or admin list revision changes before admission commits
- **THEN** the earlier proof cannot authorize the new state

#### Scenario: Caller attempts to use a proof for a different purpose

- **WHEN** a proof signed for a self request is presented as listed admin or first-key proof
- **THEN** the purpose check refuses it before effects

#### Scenario: Earlier signed proof follows the final key removal

- **WHEN** a caller presents stale signed proof after the final admin key is removed
- **THEN** the signed attempt fails before effects
- **AND** a separate unsigned request can use the current open admin access

### Requirement: Ingress verifies standard signatures in process

Gateway and passive ingress SHALL verify SSHSIG proofs inside their Python processes using a cryptographic library. They SHALL use the expected namespace and the public key selected by owner authority or first registration. Malformed, unsupported, or mismatched proofs SHALL be rejected before effects.

#### Scenario: Verifier runs with external SSH tools absent

- **WHEN** an ingress receives a valid SSHSIG proof using a supported key and external SSH commands are unavailable
- **THEN** its in-process verifier admits the proof subject to route policy

#### Scenario: The envelope supplies a different key or namespace

- **WHEN** the submitted SSHSIG envelope identifies a key or namespace different from the expected proof binding
- **THEN** admission fails even if that signature could verify under the supplied key and namespace

### Requirement: The first admin key can be registered after startup

With a valid empty admin list, anyone SHALL be able to submit a public key and prove possession through a bootstrap challenge bound to that key and principal. Registration SHALL atomically add the first key only while the list is still empty. Later admin admissions SHALL require a listed key.

#### Scenario: First registration closes open admin access

- **WHEN** a running gateway with an empty list admits a valid first-key registration
- **THEN** it persists the public key as an admin and begins requiring listed-key proof for later admin operations

#### Scenario: Registrant supplies a key without matching proof

- **WHEN** a caller attempts the first registration without a valid signature from the proposed key
- **THEN** the gateway refuses registration and leaves the empty list intact

#### Scenario: Two callers compete to register first

- **WHEN** two distinct callers both obtain bootstrap challenges for the same empty revision
- **THEN** only the first successful registration commits
- **AND** the other caller receives HTTP 409 without adding its key

### Requirement: Current admins can add and remove keys live

A verified current admin SHALL be able to add another public key or remove a listed key, including its own. The service SHALL check current admin authority at mutation commit and update membership and its revision atomically. Admin lists SHALL support multiple keys. Removing the final key SHALL commit a valid empty list.

#### Scenario: Multiple admins use their own keys

- **WHEN** a listed admin adds another public key
- **THEN** both holders can prove their own admin identity on later calls without restarting the gateway

#### Scenario: An admin key is revoked

- **WHEN** a verified admin removes a key and another key remains
- **THEN** later admissions reject proof from the removed key while accepting valid remaining keys
- **AND** work already handed off follows its existing execution contract

#### Scenario: The last admin key is removed

- **WHEN** a verified admin removes the final key
- **THEN** later admin operations admit anonymous callers
- **AND** the gateway can accept a new first-key registration

### Requirement: Self access follows the current managed generation

The runtime SHALL provision an Ed25519 self key pair per managed generation. It SHALL bind the public key to the agent ID, execution context, and generation. The private key SHALL remain in owner-private state. Managed-self clients SHALL select it through verified runtime authority. Gateway restart or reattach in the same generation SHALL use that generation's key.

#### Scenario: A managed agent uses its own gateway

- **WHEN** the owner runtime establishes a generation through launch or supported join
- **THEN** its current self client can sign a challenge for private operations with that generation's key

#### Scenario: An agent presents its key to a different gateway

- **WHEN** a caller signs self proof with a key from another agent or execution context
- **THEN** the target denies the protected operation

#### Scenario: Old body tries to use a retired credential

- **WHEN** an ended or replaced generation signs with its previous self key
- **THEN** the target denies it even if its logical agent ID remains known

#### Scenario: The gateway restarts while the agent stays live

- **WHEN** the gateway reattaches to the same managed generation and access selection
- **THEN** a fresh signature from the current self key can authorize that agent's private operations

#### Scenario: First admin registration races a self challenge

- **WHEN** an admin registers the first key after a self challenge was issued for the current generation
- **THEN** a valid self proof can still authorize its bound private request

### Requirement: State and client proofs use explicit sources

Owner access state and file-based client secrets SHALL use explicit bounded regular files outside project checkouts. The loader SHALL reject unsafe ownership, permissions, symlinks, duplicate entries, and malformed values. Admin signers SHALL be selected explicitly. Lookup SHALL use only the selected target binding.

#### Scenario: An unsafe source is selected

- **WHEN** a required state or credential source is shared, symlinked, checkout-local, or owned by an unexpected account
- **THEN** the gateway rejects the source with a safe error

#### Scenario: Duplicate keys or fields are supplied

- **WHEN** an admin list repeats a public key or a state document repeats a field
- **THEN** validation fails without selecting an order-dependent entry

#### Scenario: A selected signer or secret is missing

- **WHEN** a client lacks its selected source while another login, provider, mailbox, plugin, or admin credential is available
- **THEN** the client reports the unavailable binding before transmitting the protected request

### Requirement: Protected errors distinguish missing proof and denied authority

Operations requiring proof SHALL return HTTP 401 with applicable challenge information for missing or invalid proof. Valid proof with insufficient authority SHALL return HTTP 403. An admin-only form on a private operation SHALL require verified admin proof before its privileged effects.

#### Scenario: Self requests an owner-file attachment

- **WHEN** the agent supplies an owner-local attachment path through a private mail route with only self proof
- **THEN** the response is HTTP 403 before a file is opened or a provider is called

### Requirement: Unavailable access state fails closed

An invalid or unavailable required state SHALL prevent startup publication. If initialized state becomes unavailable during operation, admissions that depend on it SHALL return safe HTTP 503. The open admin decision SHALL require a valid recorded empty list. Restoring valid state SHALL enable later calls without replaying earlier attempts.

#### Scenario: Previously initialized state disappears after startup

- **WHEN** the admin state is missing, unreadable, unsafe, or malformed while an agent or gateway is known
- **THEN** new admin and private admissions relying on it fail with a policy error
- **AND** public process health remains available

#### Scenario: A valid policy is restored

- **WHEN** valid state for the same owner binding is restored
- **THEN** later admissions use its recorded mode and keys

### Requirement: Gateway transport supports verified deployment trust

Remote gateway clients SHALL use HTTPS with certificate verification. The supported deployment SHALL use an HTTPS reverse proxy with a protected backend leg and gateway-side proof checks. Clients SHALL support explicitly provisioned deployment trust and explicit loopback HTTP for owner-local access or an encrypted tunnel.

#### Scenario: Private CA or explicitly trusted deployment certificate

- **WHEN** the caller selects deployment trust and HTTPS verifies for the advertised host
- **THEN** it can reach the configured gateway through the proxy
- **AND** the gateway independently checks the selected operation's access policy

#### Scenario: Client selects remote plaintext

- **WHEN** a client is configured with a non-loopback HTTP base URL
- **THEN** it rejects the URL before sending a request

#### Scenario: Certificate verification fails

- **WHEN** the HTTPS certificate does not verify for the expected endpoint
- **THEN** the client stops without retrying it over HTTP

### Requirement: Client proof is bound to the expected endpoint

Credential-bearing clients SHALL bind the exact origin and base path to the expected agent and execution context. They SHALL preserve the prefix, reject redirects and changed bindings, and verify a challenge's request binding before signing. Callers SHALL carry proof in headers. Changed bindings SHALL require explicit rebinding.

#### Scenario: Reverse proxy uses a path prefix

- **WHEN** a client selects a binding to an HTTPS base URL with an agent-specific prefix
- **THEN** challenge and operation requests stay under that configured prefix

#### Scenario: Discovery retargets the endpoint

- **WHEN** discovered identity, origin, or base path differs from a selected binding
- **THEN** the client reports a conflict before transmitting proof

#### Scenario: Endpoint redirects a call

- **WHEN** a selected endpoint responds with a redirect
- **THEN** the client stops with a redirect failure before following it or replaying the operation

### Requirement: Owner clients select proof for each protected target

Managed-self commands SHALL select their current self key, verify the HTTP challenge binding, and sign locally for private calls. Admin callers SHALL use an explicit signer. Owner-service backing calls SHALL use scoped bindings. Readiness health SHALL use public access. An admission refusal SHALL terminate the attempt.

#### Scenario: Scoped self command uses its private mailbox

- **WHEN** the current agent selects its live gateway through the maintained command surface
- **THEN** `houmao-mgr agents self ...` obtains and signs the challenge as part of the normal mailbox command
- **AND** projected guidance and command output omit signing material

#### Scenario: Delegated attach uses an owner-only configuration path

- **WHEN** a restricted caller supplies an access configuration path that exists in the recorded owner context
- **THEN** the owner resolves and validates it within the existing execution binding

#### Scenario: Signed admission fails

- **WHEN** an owner-local self or admin call cannot prove its selected key or receives an admission refusal
- **THEN** it fails before an unsigned retry, another transport, or use of a backing credential

### Requirement: Retained owner policy protects alternate HTTP paths

Alternate HTTP paths to a configured agent SHALL apply its retained access policy before effects. Live discovery and gateway presence SHALL serve as lookup evidence. A known required policy that cannot be resolved SHALL prevent admission.

#### Scenario: Direct managed-headless target resolves before registry discovery

- **WHEN** an HTTP operation matches a configured agent through retained headless authority without a live registry or gateway record
- **THEN** the retained admin list and private proof requirements govern the operation

#### Scenario: Agent or gateway stops

- **WHEN** an HTTP request selects a configured target after the live gateway disappears
- **THEN** retained admin access applies to supported stopped-state paths
- **AND** an ended generation cannot authorize self

### Requirement: Gateway proof is scoped to an existing execution binding

HTTP admission SHALL apply only to the gateway's existing agent and execution context. Existing mailbox binding, readiness, and body-incarnation checks SHALL stay authoritative. Execution delegation and lifecycle adoption SHALL require their own owner authority.

#### Scenario: Caller claims a different execution owner

- **WHEN** a caller supplies another executor, UID, host, or container
- **THEN** the request gains no replacement execution binding

#### Scenario: Body changes during dispatch

- **WHEN** execution authority changes between admission and handoff
- **THEN** the current-body guard refuses the stale operation before replay to a replacement

### Requirement: Deployment settings change through explicit gateway reconfiguration

Changing listener, public-input enablement, advertised URL, or selected client binding SHALL require explicit gateway reconfiguration and restart. Conflicting live attach SHALL fail before persistence. Admin key operations SHALL update retained membership independently of deployment settings.

#### Scenario: Conflicting attach supplies a different selection

- **WHEN** a live attach changes its listener or public-input setting
- **THEN** the gateway reports a restart-required conflict before persisting the candidate

#### Scenario: Equivalent attach reuses the gateway

- **WHEN** attach resolves the same access settings
- **THEN** it can reuse the instance and preserve the managed generation and live list

### Requirement: Access diagnostics expose safe provenance

Public status, discovery, errors, and diagnostics SHALL omit secrets, signatures, replayable challenge material, raw auth headers, private paths, and roster contents. Safe request diagnostics SHALL identify operation, result, target, and the verified principal or anonymous provenance.

#### Scenario: A recognizable invalid proof is presented

- **WHEN** a caller sends a recognizable invalid signature or owner-service credential
- **THEN** the response and diagnostics omit the proof and raw headers

#### Scenario: Private source validation fails

- **WHEN** policy or client selection fails validation
- **THEN** diagnostics use safe field locations and error categories
