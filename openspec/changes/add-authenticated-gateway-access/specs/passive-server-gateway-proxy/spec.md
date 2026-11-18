# Spec Delta

## MODIFIED Requirements

### Requirement: All gateway proxy endpoints use consistent agent resolution and error handling
All gateway proxy endpoints SHALL resolve the `{agent_ref}` path parameter using the same logic as `GET /houmao/agents/{agent_ref}`:
1. Try direct lookup by `agent_id`.
2. Fall back to canonical `agent_name` lookup.
3. Return 404 if not found, 409 if ambiguous.

The proxy SHALL enforce target access before handling gateway availability. If an admitted caller's target has no live gateway (gateway is None or host/port are None), the proxy SHALL return 502 with `detail` describing that the gateway is not attached.

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

- **WHEN** the gateway returns HTTP 403 for a self caller's admin request
- **THEN** the passive server preserves HTTP 403 without replacing the caller's credential or using direct control

## ADDED Requirements

### Requirement: Protected target proxy calls retain caller authority

A passive proxy SHALL enforce the selected target's route class and current key state. Admitted open admin calls SHALL preserve anonymous provenance and require the receiving gateway's current empty-list admission. Discovery and source addresses SHALL serve as connection information.

#### Scenario: Unauthenticated caller requests privileged proxy control

- **WHEN** an unauthenticated caller invokes a target's prompt, raw-key, refresh, or mailbox-binding proxy while its admin list has entries
- **THEN** the request is rejected before any downstream operation
- **AND** owner-client credentials stay unused

#### Scenario: First enrollment races an anonymous admin proxy call

- **WHEN** a proxy admits an open admin call and a key is registered before the receiving gateway admits the downstream request
- **THEN** the downstream operation is refused under the key-required rule

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
- **THEN** the gateway refuses the request without using open admin access or a substitute credential

### Requirement: The passive server issues scoped proof challenges

The passive server SHALL expose public `POST /houmao/agents/{agent_ref}/auth/challenge` for self and admin proof on selected-agent routes. It SHALL bind the challenge to the resolved owner target and intended passive request. The challenge SHALL convey no authority until the passive ingress verifies the signature.

#### Scenario: Admin requests a challenge while the gateway is detached

- **WHEN** a detached agent's retained owner state identifies a key-required target for a supported direct operation
- **THEN** the passive ingress can issue and verify a challenge scoped to that operation

### Requirement: Direct passive paths cannot bypass protected agent access

Direct selected-agent operations SHALL enforce retained owner policy before effects. Routine protected reads SHALL require private access. Direct turns, native observation and artifacts, interruption, stop, and gateway lifecycle SHALL use admin admission. The passive ingress SHALL issue and verify challenges for its own signed operations independently of live discovery.

#### Scenario: Direct stop would otherwise kill tmux

- **WHEN** an unauthenticated caller invokes direct stop for a discovered agent with a nonempty admin list
- **THEN** it is rejected before tmux termination or registry cleanup

#### Scenario: Direct headless match has no discovery record

- **WHEN** a protected managed-headless target is found through its retained control state without a live discovery record
- **THEN** prompt, interrupt, stop, private state, and artifact requests require their declared target access

#### Scenario: Gateway detachment removes its live record

- **WHEN** a protected target has no live gateway record after detachment
- **THEN** direct admin control still uses the recorded empty or key-required state

### Requirement: Necessary owner backing calls are explicitly authenticated

Server-managed backing calls SHALL authenticate with a separate owner-service binding scoped to the required target and backing operations. This service binding SHALL be independent of admin enrollment. The backing authority SHALL check proof and target on loopback and preserve the existing generation and operation guards.

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

