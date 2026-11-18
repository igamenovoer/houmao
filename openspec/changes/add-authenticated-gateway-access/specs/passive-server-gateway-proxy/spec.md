# Spec Delta

## MODIFIED Requirements

### Requirement: All gateway proxy endpoints use consistent agent resolution and error handling
All gateway proxy endpoints SHALL resolve the `{agent_ref}` path parameter using the same logic as `GET /houmao/agents/{agent_ref}`:
1. Try direct lookup by `agent_id`.
2. Fall back to canonical `agent_name` lookup.
3. Return 404 if not found, 409 if ambiguous.

When the resolved agent has no live gateway (gateway is None or host/port are None), all proxy endpoints SHALL return 502 with `detail` describing that the gateway is not attached.

When the `GatewayClient` call returns HTTP 401 or 403, all proxy endpoints SHALL preserve that authentication or authorization failure with safe detail and SHALL NOT retry, substitute a credential, or invoke another control path. Other connection or HTTP errors SHALL return 502 with safe upstream error detail, except that native-home and native-refresh routes SHALL preserve typed upstream observation, capability, validation, admission, and execution outcomes with their native HTTP status and safe response body. A connection failure without such an upstream result SHALL remain 502 and SHALL NOT authorize a retry or relaunch.

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
- **THEN** the passive server preserves HTTP 401 and the bearer challenge with safe authentication-required detail
- **AND** it does not convert rejection into a connectivity fallback

#### Scenario: Gateway rejects peer authority

- **WHEN** the gateway returns HTTP 403 for a privileged proxied request
- **THEN** the passive server preserves HTTP 403 without replacing the caller's credential or using direct control

## ADDED Requirements

### Requirement: Protected target proxy calls retain caller authority

A passive proxy to a protected gateway SHALL enforce the selected target's policy or refuse the call. It SHALL NOT load a stored operator credential for an unauthenticated caller. An admitted forwarded bearer SHALL remain bound to the resolved owner-local gateway endpoint and SHALL not be persisted. Source loopback, registry discovery, and a pair-port override SHALL confer no privilege.

#### Scenario: Unauthenticated caller requests privileged proxy control

- **WHEN** an unauthenticated caller invokes a protected target's prompt, raw-key, refresh, or mailbox-binding proxy
- **THEN** the request is rejected before any downstream operation
- **AND** no owner-local operator credential is substituted

#### Scenario: Admitted caller is forwarded

- **WHEN** a proxy admits an explicit caller credential under the protected target policy
- **THEN** downstream authorization retains that credential's actual role and target binding
- **AND** caller authentication material is neither logged nor saved

### Requirement: Direct passive paths cannot bypass protected agent access

Direct passive-server operations that control or expose private state of a protected target SHALL enforce the same target policy or refuse access before effects. This includes direct managed-headless resolution, turn submission and artifacts, observation, interruption, stop, and gateway lifecycle operations. Protection SHALL derive from retained owner authority independently of live gateway or registry presence.

#### Scenario: Direct stop would otherwise kill tmux

- **WHEN** an unauthenticated caller invokes direct stop for a protected discovered agent
- **THEN** it is rejected before tmux termination or registry cleanup

#### Scenario: Direct headless match has no discovery record

- **WHEN** a protected managed-headless target is found through its retained control state without a live discovery record
- **THEN** prompt, interrupt, stop, private state, and artifact requests still require their declared target authority

#### Scenario: Gateway detachment removes its live record

- **WHEN** a protected target has no live gateway record after detachment
- **THEN** direct control does not become anonymous and cannot use missing gateway metadata as permission to fall back

### Requirement: Necessary owner backing calls are explicitly authenticated

Existing server-managed gateway backing calls for protected targets SHALL authenticate through an explicitly provisioned owner-side client binding. The backing authority SHALL validate target and operation permission before runtime access. It SHALL NOT exempt calls because they originate on loopback or claim to be the gateway. These calls SHALL preserve the existing managed-agent generation and operation guards.

#### Scenario: Gateway inspects or dispatches through its managed backing authority

- **WHEN** a protected server-managed gateway needs a maintained backing operation
- **THEN** it presents its explicitly selected owner-side credential for that target and operation
- **AND** the backing authority evaluates it before execution

#### Scenario: Caller impersonates a backing gateway

- **WHEN** an unauthenticated caller sets gateway-looking headers or uses the backing loopback endpoint
- **THEN** it receives no owner-service exception or operator authority

