# Spec Delta

## MODIFIED Requirements

### Requirement: All gateway proxy endpoints use consistent agent resolution and error handling
All gateway proxy endpoints SHALL resolve the `{agent_ref}` path parameter using the same logic as `GET /houmao/agents/{agent_ref}`:
1. Try direct lookup by `agent_id`.
2. Fall back to canonical `agent_name` lookup.
3. Return 404 if not found, 409 if ambiguous.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The proxy SHALL apply the resolved target domain's current policy to the canonical operation before handling gateway availability. If an admitted caller's target has no live gateway (gateway is None or host/port are None), the proxy SHALL return 502 with `detail` describing that the gateway is not attached.

When the `GatewayClient` call returns HTTP 401 or 403, all proxy endpoints SHALL preserve that admission failure with safe detail and challenge information for the caller's ingress on 401. Target policy failure SHALL return safe HTTP 503. Admission failure SHALL end the request. Other connection or HTTP errors SHALL return 502 with safe upstream error detail, except that native-home and native-refresh routes SHALL preserve typed upstream observation, capability, validation, admission, and execution outcomes with their native HTTP status and safe response body. A connection failure without such an upstream result SHALL remain 502 and SHALL NOT authorize a retry or relaunch.

#### Scenario: All proxy endpoints return 409 for ambiguous agent name
- **WHEN** the discovery index contains two agents both named `AGENTSYS-alpha` with different agent_id values
- **AND WHEN** a caller sends any gateway proxy request to `/houmao/agents/alpha/gateway`
- **THEN** the response status code is 409
- **AND THEN** the response body contains the ambiguous agent IDs

#### Scenario: Native Refresh Refusal Is Not a Connectivity Error
- **WHEN** the owning gateway returns a typed busy or restart-required result with HTTP 409 for a proxied native refresh
- **THEN** the proxy preserves HTTP 409 and the typed safe outcome
- **AND** it does not collapse the result into HTTP 502 or retry the operation

#### Scenario: Native Refresh Connection Is Lost
- **WHEN** a gateway refresh request loses its connection before the proxy obtains a typed native outcome
- **THEN** the proxy returns HTTP 502 with safe connection-failure information
- **AND** it does not claim that refresh succeeded, infer that no native effects occurred, or initiate another attempt

#### Scenario: Gateway rejects a missing credential

- **WHEN** a gateway returns HTTP 401 for a proxied operation
- **THEN** the passive server preserves HTTP 401 with safe detail and challenge information applicable to the passive endpoint
- **AND** it does not convert rejection into a connectivity fallback

#### Scenario: Gateway rejects self authority for admin control

- **WHEN** the gateway returns HTTP 403 for a caller proving its managed identity whose policy denies the selected control operation
- **THEN** the passive server preserves HTTP 403 without replacing the caller's credential or using direct control

### Requirement: Protected target proxy calls retain caller authority

A passive proxy SHALL apply the selected target domain's current policy to the admitted caller, canonical resource, and action. It SHALL relay admitted protected operations with owner-local evidence that identifies the caller or anonymous provenance and any open epoch. Discovery and source addresses SHALL serve as connection information.

#### Scenario: Unauthenticated caller requests privileged proxy control

- **WHEN** an unauthenticated caller invokes a target's prompt, raw-key, refresh, or mailbox-binding proxy when the current policy requires proof for that operation
- **THEN** the request is rejected before any downstream operation
- **AND** owner-client credentials stay unused

#### Scenario: First enrollment races an anonymous admin proxy call

- **WHEN** a proxy admits an unsigned operation through open gateway-admin access and the first administrator enrolls before downstream admission
- **THEN** the downstream operation is refused under current policy

#### Scenario: A private proxy call is anonymous in open mode

- **WHEN** an unsigned caller selects a supported protected client operation on a target with a valid empty administrator roster
- **THEN** both ingress and the receiving gateway authorize the exact operation under current policy
- **AND THEN** the resulting operation preserves anonymous caller provenance

#### Scenario: Open access reopens while an earlier relay is pending

- **WHEN** the roster becomes keyed and then empty after the passive server admitted a request under open access
- **THEN** the gateway refuses the earlier relay under its expired open epoch
- **AND THEN** a new request can use the current open epoch

### Requirement: Signed proxy requests carry only admitted caller authority

The ingress SHALL consume SSHSIG proof at admission. A short-lived, single-use owner-local relay SHALL bind the caller, credential, admitted authority, target domain, generation, gateway incarnation, exact transformed request, resource, and action. Only a same-target self credential SHALL bind the caller's generation. The receiver SHALL verify the relay and recheck current authority before effects.

#### Scenario: Request path or body changes across the proxy

- **WHEN** the passive ingress authorizes a signed request whose downstream path or body differs
- **THEN** the gateway verifies the exact downstream request, resource, and action and preserves the original verified caller

#### Scenario: Admitted self caller is forwarded

- **WHEN** a proxy admits a managed self credential for an authorized operation on the caller's own agent
- **THEN** the downstream record retains the verified caller and its bound generation
- **AND** the original signature stays bound to the passive ingress

#### Scenario: The generation changes during a signed self relay

- **WHEN** the bound source or target generation changes before the gateway admits the downstream request
- **THEN** the receiving gateway refuses the relay before effects

#### Scenario: An enrolled peer relaunches before the relay arrives

- **WHEN** a proxy admits a caller using a stable peer key enrolled by the target owner and the source agent relaunches before downstream admission
- **THEN** the receiving gateway checks the enrolled credential, the bound target generation and gateway incarnation, and permission for the exact operation
- **AND THEN** changes to the source generation or its liveness leave otherwise valid relay authority intact

#### Scenario: Relayed authority is replayed or the key has been removed

- **WHEN** a downstream request reuses a relay or its caller credential, qualifying admin entry, open epoch, or permission ceased to be current before gateway admission
- **THEN** the gateway refuses the request without using open access or a substitute credential

### Requirement: The passive server issues scoped proof challenges

The passive server SHALL expose public `POST /houmao/agents/{agent_ref}/auth/challenge` for SSHSIG caller proof on selected-agent routes. It SHALL bind the challenge to the resolved target domain and intended passive request. After verifying proof, the passive ingress SHALL evaluate policy for the canonical resource and action.

#### Scenario: Admin requests a challenge while the gateway is detached

- **WHEN** an enrolled administrator requests proof for a supported direct operation against a detached agent with valid retained policy
- **THEN** the passive ingress can issue a challenge for the exact operation, verify the response, and apply the target's current policy

### Requirement: Direct passive paths cannot bypass protected agent access

Direct selected-agent operations SHALL apply retained policy to the exact target, resource, and action before effects. Current administrators SHALL have access to every supported client-facing operation in that domain. A valid empty roster SHALL give callers the same access. Operation-specific proof and runtime guards SHALL still apply. The passive ingress SHALL issue and verify its own challenges independently of gateway discovery.

#### Scenario: Direct stop would otherwise kill tmux

- **WHEN** an unauthenticated caller invokes direct stop for a discovered agent with a nonempty admin list
- **THEN** the server rejects it before tmux termination or registry cleanup

#### Scenario: Direct headless match has no discovery record

- **WHEN** a protected managed-headless target is found through its retained control state without a live discovery record
- **THEN** prompt, interrupt, stop, protected state, and artifact requests require permission for the exact resource and action

#### Scenario: Gateway detachment removes its live record

- **WHEN** a protected target has no live gateway record after detachment
- **THEN** direct protected operations still use the current retained policy for that target domain

#### Scenario: Enrollment races a direct anonymous operation

- **WHEN** a direct operation's anonymous grant has ceased to be current before its effect boundary
- **THEN** the operation is refused before accessing or changing the target

### Requirement: Necessary owner backing calls are explicitly authenticated

Server-managed backing calls SHALL authenticate with separate owner-service authority bound to the exact target, resource, action, and request. It SHALL remain independent of caller admission and administrator enrollment. The backing authority SHALL check proof and target on loopback and preserve generation and operation guards.

#### Scenario: Gateway inspects or dispatches through its managed backing authority

- **WHEN** a protected server-managed gateway needs a maintained backing operation
- **THEN** it presents its selected owner-service credential for that target and operation
- **AND** the backing authority evaluates it before execution

#### Scenario: First enrollment occurs on a server-managed gateway

- **WHEN** a running server-managed gateway acquires its first admin key
- **THEN** its existing scoped service binding continues authorizing its required backing operations

#### Scenario: Caller impersonates a backing gateway

- **WHEN** an unauthenticated caller sets gateway-looking headers or uses the backing loopback endpoint
- **THEN** the request is refused before runtime access
