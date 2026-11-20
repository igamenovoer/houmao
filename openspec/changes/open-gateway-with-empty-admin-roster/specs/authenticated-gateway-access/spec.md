# authenticated-gateway-access Delta

## MODIFIED Requirements

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

- **WHEN** a caller reaches a private or admin route through loopback without proof while the admin list has entries
- **THEN** the gateway returns HTTP 401 with applicable challenge information

### Requirement: The matched route determines caller access

Enabled public routes SHALL admit anonymous callers. A valid empty admin list SHALL admit unsigned private and admin requests. With listed keys, private routes SHALL require current self or listed admin proof, and admin routes SHALL require listed admin proof. Verification of supplied proof SHALL precede body parsing, lifecycle handling, or effects. Missing core classifications SHALL prevent publication.

#### Scenario: Anonymous admin uses a valid empty list

- **WHEN** a caller invokes an admin control route without signing proof and the initialized list is empty
- **THEN** the gateway admits the request and an unsigned private call with anonymous provenance

#### Scenario: A private route is used by self and by admin

- **WHEN** the current agent and a listed admin separately call a private mailbox or memory route with valid proof
- **THEN** both can use the operation subject to its normal binding and input checks

#### Scenario: Self attempts key-required admin control

- **WHEN** the admin list contains entries and the agent presents only valid self proof on an admin route
- **THEN** the gateway returns HTTP 403 before the operation reaches its handler or backend

#### Scenario: Unauthenticated caller supplies a malformed protected body

- **WHEN** a caller sends invalid JSON without proof to a private or admin operation while the admin list has entries
- **THEN** it receives HTTP 401 with applicable challenge information before request-body validation

#### Scenario: Request fields claim another role

- **WHEN** a caller supplies a role, principal, or source identity in its body or forwarded headers
- **THEN** the gateway uses the matched operation and proof established by owner policy

#### Scenario: New core route lacks classification

- **WHEN** startup finds an application route without a core classification
- **THEN** it refuses to publish the application

#### Scenario: Invalid proof accompanies an open request

- **WHEN** a caller submits invalid signing proof on an enabled route while the list is empty
- **THEN** the attempt fails without granting anonymous admission

### Requirement: Private routes cover routine operations owned by the agent

Detailed gateway status, usage, memory, and routine operations on the bound mailbox SHALL require private access. Mail and plugin operations SHALL retain the configured service identity. The initiating principal SHALL reflect current proof or anonymous admission separately from the service identity.

#### Scenario: Self inspects usage and reads memory

- **WHEN** the current agent selects its bound gateway and signs with its current self key
- **THEN** it can use its usage and memory routes subject to each operation's normal bounds

#### Scenario: Admin sends mail through the owner's mailbox

- **WHEN** a verified admin sends ordinary mail with a current mailbox binding
- **THEN** the bound mailbox determines the service identity
- **AND** the caller remains the initiating admin principal

#### Scenario: Anonymous caller uses a bound mailbox

- **WHEN** the initialized roster is empty and an unsigned caller invokes an enabled private mailbox operation
- **THEN** the operation uses the configured mailbox binding and records anonymous caller provenance

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
- **AND** a separate unsigned request can use the current open access

### Requirement: The first admin key can be registered after startup

With a valid empty admin list, anyone SHALL be able to submit a public key and prove possession through a bootstrap challenge bound to that key and principal. Registration SHALL atomically add the first key only while the list is still empty. Later private and admin admissions SHALL apply the listed-key policy.

#### Scenario: First registration closes open admin access

- **WHEN** a running gateway with an empty list admits a valid first-key registration
- **THEN** it persists the public key as an admin and ends anonymous admission to later private and admin operations

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
- **THEN** later private and admin operations admit unsigned callers
- **AND** the gateway can accept a new first-key registration

### Requirement: Protected errors distinguish missing proof and denied authority

Operations requiring proof SHALL return HTTP 401 with applicable challenge information for missing or invalid proof. Valid proof with insufficient authority SHALL return HTTP 403. Elevated forms of a private operation SHALL require current anonymous open access or verified admin authority before privileged effects.

#### Scenario: Self requests an owner-file attachment

- **WHEN** the agent supplies an owner-local attachment path through a private mail route with only self proof and the roster has entries
- **THEN** the response is HTTP 403 before a file is opened or a provider is called

#### Scenario: A roster change invalidates an anonymous grant

- **WHEN** a deferred privileged operation reaches its authority check after the roster revision has changed
- **THEN** it rejects an earlier anonymous grant before the privileged effect

### Requirement: Unavailable access state fails closed

An invalid or unavailable required state SHALL prevent startup publication. If initialized state becomes unavailable during operation, admissions that depend on it SHALL return safe HTTP 503. Anonymous admission to protected operations SHALL require a valid recorded empty list. Restoring valid state SHALL enable later calls without replaying earlier attempts.

#### Scenario: Previously initialized state disappears after startup

- **WHEN** the admin state is missing, unreadable, unsafe, or malformed while an agent or gateway is known
- **THEN** new admin, private, and Web entry admissions relying on it fail with a policy error
- **AND** public process health remains available

#### Scenario: A valid policy is restored

- **WHEN** valid state for the same owner binding is restored
- **THEN** later admissions use its recorded mode and keys

### Requirement: Owner clients select proof for each protected target

Managed-self commands SHALL select their current self key, verify the HTTP challenge binding, and sign locally for private calls. Signed admin callers SHALL use an explicit signer. An unsigned client SHALL be able to use available private and admin operations under the current open policy. Owner-service backing calls SHALL use scoped bindings. Readiness health SHALL use public access. An admission refusal SHALL terminate the attempt.

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
- **THEN** the retained roster determines whether the operation admits anonymous access or requires its route-class proof

#### Scenario: Agent or gateway stops

- **WHEN** an HTTP request selects a configured target after the live gateway disappears
- **THEN** retained access policy applies to supported stopped-state paths
- **AND** an ended generation cannot authorize self

### Requirement: Browser entry issuance follows current direct gateway access

Direct owner-local Web ticket issuance SHALL accept an unsigned request with a valid empty roster or a request signed by a current enrolled admin. Admission SHALL precede native sign-in lookup. Ticket redemption SHALL require the issued bearer and confers authority only for the bound native redirect.

#### Scenario: The admin roster is empty

- **WHEN** an unsigned direct caller requests a ticket for an eligible live Web agent with a valid empty roster
- **THEN** the gateway issues the ticket with anonymous access bound to the current roster revision

#### Scenario: The current agent or a backing service requests issuance

- **WHEN** issuance presents valid self proof, a relay, or backing authority
- **THEN** the gateway returns HTTP 403 before looking up the native destination

#### Scenario: A signed gateway client requests a ticket for the browser

- **WHEN** the client completes signed issuance
- **THEN** it receives the ticket result without a redirect
- **AND THEN** only the browser follows the redemption redirect, independently of public prompt enablement

#### Scenario: Direct issuance is missing required proof

- **WHEN** an unsigned request reaches ticket issuance with enrolled keys
- **THEN** the gateway returns HTTP 401 with applicable challenge information

#### Scenario: Direct issuance carries invalid proof

- **WHEN** a request presents invalid signing proof with either roster mode
- **THEN** the gateway refuses it before reading native sign-in data

## RENAMED Requirements

- FROM: `### Requirement: Browser entry issuance requires direct enrolled admin proof`
- TO: `### Requirement: Browser entry issuance follows current direct gateway access`
