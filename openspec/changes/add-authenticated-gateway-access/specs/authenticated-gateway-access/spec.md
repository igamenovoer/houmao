# Spec Delta

## Purpose

Define authenticated access to one execution-bound agent gateway across user and network boundaries, including caller authority, private credentials, safe client connections, and protection against alternate HTTP ingress.

## ADDED Requirements

### Requirement: Gateway access mode is explicit and safe by default

A gateway SHALL default to trusted-local access on loopback. Authenticated access SHALL require an explicitly selected owner-side policy and SHALL apply equally to loopback and broader listeners. A broader listener without authenticated access SHALL fail startup before publication or plugin activation. Trusted-local access SHALL be documented as trusting callers that can reach host loopback.

#### Scenario: Unconfigured gateway retains a local default

- **WHEN** an operator starts a gateway without access configuration
- **THEN** it listens on loopback with trusted-local semantics
- **AND** it does not publish a remote-access endpoint or require newly provisioned credentials for existing local operations

#### Scenario: Broad listener lacks authentication

- **WHEN** startup selects a non-loopback listener without a valid authenticated deployment configuration
- **THEN** startup fails before publishing a live endpoint or activating plugin resources

#### Scenario: Another local user reaches an authenticated loopback gateway

- **WHEN** a caller reaches an authenticated gateway through loopback without a credential
- **THEN** protected operations return HTTP 401
- **AND** source address does not confer operator authority

### Requirement: Provisioned credentials authenticate a bound principal

Authenticated access SHALL use explicitly provisioned opaque bearer credentials. Verification SHALL resolve a caller principal and fixed peer or operator role within the expected agent ID and execution context. The hub SHALL retain provisioning ownership. Request-supplied identities, roles, executor names, and forwarded identity headers SHALL NOT grant authority.

#### Scenario: Peer credential identifies its provisioned principal

- **WHEN** a valid peer credential is presented to its configured agent and execution context
- **THEN** authorization uses that credential's provisioned principal and peer role

#### Scenario: Client claims an operator role

- **WHEN** a peer supplies an operator role or another identity in its request or forwarded headers
- **THEN** the claim does not increase its authority

#### Scenario: Policy belongs to another owner binding

- **WHEN** the selected policy's expected agent ID or execution-context ID differs from runtime authority
- **THEN** the policy cannot authorize protected access to that runtime

### Requirement: Credential sources are explicit private files

Server policy and file-based client credential bindings SHALL use explicit, bounded, regular private files outside project checkouts. Unsafe ownership, permissions, symlinks, malformed documents, and duplicate credential IDs SHALL be rejected without exposing contents. Credential lookup SHALL NOT scan homes or use ambient login, mailbox, plugin, provider, or delegation credentials.

#### Scenario: Unsafe policy is selected

- **WHEN** a policy source is shared with other users, follows a symlink, belongs to an unexpected owner, or resides in the checkout
- **THEN** it is rejected before authenticated service startup
- **AND** diagnostics disclose no credential values or credential-file contents

#### Scenario: Duplicate verifier identity is supplied

- **WHEN** a policy repeats a credential ID or contains duplicate document keys
- **THEN** policy loading fails without selecting an order-dependent entry

#### Scenario: Selected client credential disappears

- **WHEN** a configured client credential file is missing while another credential is available in the environment
- **THEN** the request fails locally without trying that ambient credential

### Requirement: Authentication precedes protected request processing

A protected HTTP operation SHALL authenticate before parsing its body or invoking application handlers, plugins, backing services, or mutations. Missing or invalid credentials SHALL return HTTP 401 with a bearer challenge. An authenticated principal lacking operation authority SHALL receive HTTP 403 before side effects. Authorization SHALL use the operation's declared authority rather than its HTTP method alone.

#### Scenario: Unauthenticated caller supplies a malformed body

- **WHEN** an unauthenticated caller sends invalid JSON to a protected operation
- **THEN** the response is HTTP 401
- **AND** no request-body validation result or operation side effect is produced

#### Scenario: Peer invokes a privileged operation

- **WHEN** an authenticated peer invokes an operator operation with a valid body
- **THEN** it receives HTTP 403 before that operation or its backend runs

### Requirement: Peer authority covers ordinary delegated operations

Peer authority SHALL allow safe status, endpoint and usage inspection, ordinary message delivery, and ordinary owner-mailbox list, peek, read, send, reply, mark, move, and archive. Explicitly classified ordinary plugin routes SHALL accept peers. This grant SHALL preserve the gateway owner's sender and mailbox identity and SHALL NOT permit caller-selected replacement credentials or service accounts.

#### Scenario: Peer queries usage during active work

- **WHEN** a valid peer requests bounded usage from its gateway
- **THEN** the request uses the existing read-only usage contract without acquiring execution-control authority

#### Scenario: Peer sends owner-bound mail

- **WHEN** a peer sends mail through the configured channel and expected binding
- **THEN** existing mailbox authority determines the sender and delivery scope
- **AND** the authenticated caller remains separate initiating provenance

#### Scenario: Peer attempts sender replacement

- **WHEN** a peer attempts to replace the configured sender, account, or credential selection
- **THEN** the request fails before using the replacement identity

### Requirement: Operator authority protects control and private state

Authenticated queued requests, direct prompts, interrupts, raw input, session and model selection, reminders, notifier configuration, native-home inspection and refresh, memory, AG-UI, operator-origin mail post, mailbox attachment controls, and plugin connection controls SHALL require operator authority. Unclassified core routes SHALL block authenticated startup; undeclared plugin routes SHALL require operator authority.

#### Scenario: Peer uses the queued request route as a prompt shortcut

- **WHEN** a peer submits either submit_prompt or interrupt through POST /v1/requests
- **THEN** it receives HTTP 403
- **AND** no request is persisted or executed

#### Scenario: Peer schedules raw input

- **WHEN** a peer creates or updates a reminder containing raw keys or semantic prompt delivery
- **THEN** it receives HTTP 403 before reminder state changes

#### Scenario: Newly registered core route lacks classification

- **WHEN** authenticated startup finds a core, documentation, or extension route without an access classification
- **THEN** startup refuses to publish the authenticated application

### Requirement: Anonymous health exposes only process liveness

GET /health SHALL remain usable without credentials for launch readiness and SHALL expose only process-health and protocol information. Anonymous health SHALL NOT expose agent identity, owner paths, listener advertisements, active work, plugin configuration, mailbox state, or credentials.

#### Scenario: Anonymous readiness probe succeeds

- **WHEN** a caller requests health from a healthy authenticated gateway
- **THEN** the response reports process health and gateway protocol information
- **AND** it contains no target-specific or private state

### Requirement: Credential rotation is live and admission-bound

Atomic replacement of the selected policy SHALL affect subsequent admissions without restarting the gateway or agent. Overlapping credential IDs SHALL support explicit rotation. Revoked credentials SHALL receive HTTP 401, and changed roles SHALL affect later authorization. Already admitted work SHALL retain its existing execution contract; a prepared ordinary dispatch SHALL stop when revocation is observed before handoff.

#### Scenario: New and old credentials overlap

- **WHEN** a replacement policy admits both rotation credentials for the same principal
- **THEN** either credential can authenticate within its granted role
- **AND** removing the old entry denies later admissions using that credential

#### Scenario: Role is reduced

- **WHEN** an operator credential is changed to peer authority
- **THEN** later privileged requests return HTTP 403 without a process restart

#### Scenario: Revocation is observed during message preparation

- **WHEN** an ordinary message is still awaiting native handoff and its request observes credential revocation
- **THEN** the remaining dispatch permission is withdrawn
- **AND** the gateway does not retain the message for later delivery

#### Scenario: Rotation follows confirmed admission

- **WHEN** a credential is revoked after work has been admitted and handed off
- **THEN** revocation does not replay, roll back, or implicitly interrupt that work

### Requirement: Policy failures never restore anonymous or stale authority

An invalid or unavailable initial policy SHALL prevent authenticated startup. If the selected policy becomes unreadable, unsafe, oversized, or malformed during operation, protected admissions SHALL return a safe HTTP 503 until a valid policy is available. The gateway SHALL NOT revert to trusted-local mode or continue admitting through a cached previous grant.

#### Scenario: Malformed replacement follows revocation

- **WHEN** a running gateway observes a malformed replacement policy
- **THEN** protected operations return HTTP 503
- **AND** neither earlier credentials nor loopback source address restore admission

#### Scenario: Valid policy is restored

- **WHEN** a valid policy for the same selected owner binding replaces an invalid policy
- **THEN** subsequent requests are evaluated against the restored policy without restarting the agent

### Requirement: Remote deployment protects credential transport

The supported remote deployment SHALL use HTTPS through a documented TLS proxy and a protected backend connection. Gateway-side credential verification SHALL remain authoritative. Non-loopback plaintext client URLs SHALL be rejected. Explicit loopback HTTP connections SHALL be supported for owner-local access and configured encrypted tunnels. Proxy headers SHALL NOT establish authentication or advertised endpoint identity.

#### Scenario: TLS proxy forwards an authorized request

- **WHEN** a caller uses the configured HTTPS endpoint and the proxy forwards its bearer credential over the protected backend
- **THEN** the gateway authorizes the request using its own selected policy

#### Scenario: Client selects remote plaintext

- **WHEN** a credential-bearing client is configured with a non-loopback HTTP URL
- **THEN** client configuration fails before transmitting the credential

### Requirement: Client credentials remain bound to a selected endpoint

A credential-bearing client SHALL use an explicit endpoint binding, verify HTTPS certificates, preserve any configured base-path prefix, and reject redirects. A changed discovered origin or base path SHALL NOT receive an existing credential without explicit rebinding. Credentials SHALL NOT appear in URLs, query parameters, public endpoint descriptors, exceptions, or request diagnostics.

#### Scenario: Reverse proxy uses a path prefix

- **WHEN** a client is bound to an HTTPS base URL with an agent-specific prefix
- **THEN** gateway routes are appended within that prefix and use the selected credential

#### Scenario: Endpoint metadata is retargeted

- **WHEN** discovery changes the origin or base path of a credential's bound endpoint
- **THEN** the client reports an endpoint-binding conflict before sending that credential to the replacement

#### Scenario: Upstream redirects a credential-bearing request

- **WHEN** the selected endpoint responds with a redirect
- **THEN** the client returns an explicit redirect failure without following it or replaying the operation

#### Scenario: Certificate cannot be verified

- **WHEN** HTTPS certificate verification fails
- **THEN** the client fails the connection without disabling verification or retrying over HTTP

### Requirement: Owner-local clients receive explicit credential bindings

Protected owner-local gateway controls and necessary server-managed backing calls SHALL use explicitly selected private client bindings. CLI, library, and delegated attach inputs SHALL resolve access configuration in the recorded owner context. Readiness health SHALL remain anonymous. Credential references SHALL remain private and SHALL NOT enter agent homes, tmux discovery variables, public registries, or harness environments.

#### Scenario: Delegated attach selects an owner-only configuration path

- **WHEN** a restricted operator attaches a gateway with an access configuration that exists only in the recorded owner context
- **THEN** the owner validates the configuration and its private references without caller-side file reads
- **AND** the execution binding remains unchanged

#### Scenario: Server-managed gateway needs a backing call

- **WHEN** an authenticated gateway invokes its existing server-managed backing authority
- **THEN** that call presents the explicitly configured owner-side credential and passes target authorization
- **AND** no unauthenticated backing route or trusted-source-address exception is introduced

### Requirement: Alternate HTTP ingress preserves protected-target authority

Every HTTP route that controls or exposes private state of a protected agent SHALL enforce its current target policy or refuse access. This includes passive-server proxies, direct headless operations, observation, artifacts, interruption, stop, and gateway lifecycle controls. Discovery or gateway detachment SHALL NOT erase protection. Global passive-server remote deployment SHALL remain outside this capability.

#### Scenario: Caller bypasses the gateway with direct stop

- **WHEN** an unauthenticated caller targets a protected agent through the passive server's direct stop or interrupt route
- **THEN** the request is rejected before runtime, headless, tmux, or registry mutation

#### Scenario: Headless direct match bypasses discovery

- **WHEN** a protected managed-headless target resolves without a live registry or gateway record
- **THEN** its retained owner-side access configuration still governs HTTP control and private reads

#### Scenario: Gateway is detached

- **WHEN** a protected agent's gateway stops and its live endpoint is removed
- **THEN** alternate HTTP access does not become anonymous because live gateway presence disappeared

### Requirement: Gateway credentials do not grant execution delegation

Gateway authentication SHALL authorize only operations on the gateway's already-bound logical agent and execution context. Existing generation, mailbox binding, readiness, and native handoff checks SHALL remain authoritative. A credential or discovery descriptor SHALL NOT grant an executor route, user switch, container change, host change, or lifecycle rights to a communication-only import.

#### Scenario: Network operator requests a different execution owner

- **WHEN** a caller supplies another executor, UID, container, or host through a gateway request
- **THEN** it gains no delegation authority or replacement execution binding

#### Scenario: Body changes during an authorized dispatch

- **WHEN** execution authority changes after authentication and before native handoff
- **THEN** existing incarnation guards refuse the stale attempt without replaying it against a replacement body

### Requirement: Access selections are immutable during a live gateway instance

Changing deployment mode, selected policy path, listener, advertised URL, or owner-client binding SHALL require explicit gateway reconfiguration and restart. A conflicting live attach SHALL leave active and persisted selections unchanged. Policy contents and selected client credential contents SHALL rotate live within their existing binding without restarting the agent body.

#### Scenario: Live attach changes policy selection

- **WHEN** attach supplies a different policy path or deployment mode for a live gateway
- **THEN** it reports restart-required conflict without partially persisting the replacement

#### Scenario: Equivalent attach reuses the gateway

- **WHEN** attach resolves the same access selections as the live gateway
- **THEN** it can reuse that instance without interrupting the body

### Requirement: Access diagnostics exclude verification and secret material

Public status, discovery, validation errors, and default diagnostics SHALL exclude bearer values, verifier values, authorization and cookie headers, credential paths, raw policy contents, and provider secrets. Safe diagnostics SHALL identify operation, result, target, and authenticated principal where available. Errors SHALL NOT echo supplied credential material.

#### Scenario: Invalid credential contains recognizable secret text

- **WHEN** a request with a recognizable invalid credential is rejected
- **THEN** neither its response nor emitted diagnostics contain that credential or a raw header dump

#### Scenario: Policy validation fails

- **WHEN** a private policy or client binding fails validation
- **THEN** diagnostics report safe field locations and error categories without input-value or credential-path dumps

