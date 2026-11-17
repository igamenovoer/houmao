# Spec Delta

## MODIFIED Requirements

### Requirement: All gateway proxy endpoints use consistent agent resolution and error handling
All gateway proxy endpoints SHALL resolve the `{agent_ref}` path parameter using the same logic as `GET /houmao/agents/{agent_ref}`:
1. Try direct lookup by `agent_id`.
2. Fall back to canonical `agent_name` lookup.
3. Return 404 if not found, 409 if ambiguous.

When the resolved agent has no live gateway (gateway is None or host/port are None), all proxy endpoints SHALL return 502 with `detail` describing that the gateway is not attached.

When the `GatewayClient` call fails with a connection or HTTP error, all proxy endpoints SHALL return 502 with the upstream error detail forwarded, except that native-home and native-refresh proxy routes SHALL preserve typed upstream observation, capability, validation, admission, and execution outcomes with their native HTTP status and safe response body. A connection failure without such an upstream result SHALL remain 502 and SHALL NOT authorize a retry or relaunch.

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

## ADDED Requirements

### Requirement: Passive Server Proxies Native Home and Common State Inspection

The passive server SHALL expose `GET /houmao/agents/{agent_ref}/gateway/native-home` and `GET /houmao/agents/{agent_ref}/gateway/control/refresh`. They SHALL forward typed home or common-plugin observation/capability results, including freshness, inventory coverage, health, boundaries, and evidence. Resolution and missing-gateway errors SHALL remain explicit without starting execution.

#### Scenario: Native Home Comes From the Owning Gateway
- **WHEN** an operator reads `/houmao/agents/agent-123/gateway/native-home` for an active gateway-attached agent
- **THEN** the response preserves the gateway's selected native home and bound agent identity
- **AND** it does not substitute a passive-server-local directory or expose configuration contents

#### Scenario: Common State Preserves Native Limitations
- **WHEN** a caller reads `/houmao/agents/agent-123/gateway/control/refresh`
- **THEN** the response preserves backend/version/profile capabilities, common freshness, scope, health, boundaries, and limitations from the gateway
- **AND** the proxy does not infer freshness from its installed tools or a previous Houmao receipt

#### Scenario: Unknown Freshness Is a Normal Observation
- **WHEN** the owning gateway returns HTTP 200 with pending or unknown common freshness
- **THEN** the proxy preserves that typed observation and HTTP 200
- **AND** it does not initiate reload, convert the state to a connection error, or invent a native-special-plugin inventory

#### Scenario: Agent Has No Live Gateway
- **WHEN** either native-home or common-state proxy read targets an agent without a live attached gateway
- **THEN** the proxy returns HTTP 502 with the missing-gateway diagnostic
- **AND** it does not attach a gateway or invoke manifest-backed launch recovery

### Requirement: Passive Server Proxies Native Refresh Without Owning Activation

The passive server SHALL expose `POST /houmao/agents/{agent_ref}/gateway/control/refresh` with strict shared models. It SHALL preserve common observations, method, outcome, native boundaries, identity, and safe partial-effect diagnostics. It SHALL NOT queue, retry, re-evaluate freshness/readiness, restrict allowed broader native effects, regenerate home material, or invoke relaunch.

#### Scenario: Native Reload Result Passes Through
- **WHEN** a gateway confirms native refresh for a valid proxied request
- **THEN** the proxy returns the typed common/native results with unchanged evidence, scope, and effective boundaries
- **AND** the passive server maintains no second refresh execution or content-generation store

#### Scenario: Already Current Passes Through Without Work
- **WHEN** the gateway returns `method=noop` and `outcome=already_current` after observing a native automatic update
- **THEN** the proxy preserves the result without initiating its own activation or requiring a Houmao update receipt

#### Scenario: Automatic Discovery Result Passes Through
- **WHEN** the gateway reports automatic discovery effective on the next step, turn, or load
- **THEN** the proxy preserves that future-boundary result
- **AND** it does not submit a prompt to make the future boundary happen

#### Scenario: Partial Common Restart Requirement Passes Through
- **WHEN** the gateway reports applied common changes and a remaining common resource requiring restart
- **THEN** the proxy preserves `restart_required`, the applied observations, and partial effects without calling relaunch
- **AND** the selected process and conversation remain under their existing authority

#### Scenario: Native Extension Remains Pending
- **WHEN** the gateway confirms current common-plugin state and readiness while a native extension remains pending
- **THEN** the proxy preserves that common result and any safe native diagnostic
- **AND** it does not promote an unrelated native pending reason into common restart-required

#### Scenario: Force or Replacement Content Is Supplied
- **WHEN** a caller submits restart, force, installation, home-override, or replacement-configuration fields to the refresh proxy
- **THEN** strict validation rejects the request before native effects
- **AND** the proxy does not translate it into another lifecycle operation

### Requirement: Native Home Proxy Controls Retain Managed Owner Boundaries

Native-home and refresh proxy routes SHALL use existing local managed-agent and control-exposure boundaries. They SHALL NOT turn an external communication-only reference or registry-only mailbox credential into body-control authority. Safe diagnostics SHALL exclude credentials and raw native configuration, and resource paths SHALL remain bound to the selected execution.

#### Scenario: Name Is Ambiguous
- **WHEN** a home or refresh proxy request names multiple managed agents
- **THEN** resolution returns HTTP 409 without selecting or mutating any agent

#### Scenario: Reference Is Communication Only
- **WHEN** a caller targets an external communication-only record through native-home or refresh control
- **THEN** the operation fails explicitly without adopting or controlling the external runtime

#### Scenario: Gateway Reports Private Native Failure
- **WHEN** a gateway returns a safe failed or uncertain refresh result after a native error
- **THEN** the proxy preserves the safe outcome and effect evidence
- **AND** it does not add raw provider exceptions, home-file contents, or credential-bearing diagnostics
